import email
import imaplib
import re
from email.header import decode_header
from datetime import datetime, timedelta
from image_processor import ImageProcessor
from models import db, Event, EventImage, Attachment
import os

class EmailService:
    
    def __init__(self, imap_server=None, imap_port=993, username=None, password=None):
        self.imap_server = imap_server
        self.imap_port = imap_port
        self.username = username
        self.password = password
        self.image_processor = ImageProcessor()
    
    def connect(self):
        if not all([self.imap_server, self.username, self.password]):
            return None
        
        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port)
            mail.login(self.username, self.password)
            return mail
        except Exception as e:
            print(f"Error connecting to email: {e}")
            return None
    
    def extract_images_from_email_message(self, msg):
        images = []
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type.startswith('image/'):
                    image_data = part.get_payload(decode=True)
                    if image_data:
                        images.append(image_data)
        else:
            content_type = msg.get_content_type()
            if content_type.startswith('image/'):
                image_data = msg.get_payload(decode=True)
                if image_data:
                    images.append(image_data)
        
        html_content = self._get_html_content(msg)
        if html_content:
            html_images = self.image_processor.extract_images_from_email(html_content)
            images.extend(html_images)
        
        return images
    
    def _get_html_content(self, msg):
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            if msg.get_content_type() == 'text/html':
                return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        return None
    
    def get_recent_calendar_emails(self, days=30, limit=50):
        mail = self.connect()
        if not mail:
            return []
        
        try:
            mail.select('inbox')
            
            date_since = (datetime.now() - timedelta(days=days)).strftime('%d-%b-%Y')
            search_criteria = f'(SINCE {date_since})'
            
            status, messages = mail.search(None, search_criteria)
            
            email_ids = messages[0].split()
            email_ids = email_ids[-limit:]  
            
            calendar_emails = []
            
            for email_id in email_ids:
                status, msg_data = mail.fetch(email_id, '(RFC822)')
                email_body = msg_data[0][1]
                msg = email.message_from_bytes(email_body)
                
                subject = self._decode_header(msg['Subject'])
                if self._is_calendar_email(subject, msg):
                    calendar_emails.append({
                        'id': email_id.decode(),
                        'subject': subject,
                        'from': self._decode_header(msg['From']),
                        'date': msg['Date'],
                        'message': msg
                    })
            
            mail.close()
            mail.logout()
            
            return calendar_emails
        except Exception as e:
            print(f"Error fetching emails: {e}")
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except:
                    pass
            return []
    
    def _is_calendar_email(self, subject, msg):
        calendar_keywords = ['meeting', 'appointment', 'calendar', 'invite', 'invitation', 'event']
        subject_lower = subject.lower()
        
        if any(keyword in subject_lower for keyword in calendar_keywords):
            return True
        
        if msg.is_multipart():
            for part in msg.walk():
                filename = part.get_filename()
                if filename and filename.endswith('.ics'):
                    return True
        
        return False
    
    def _decode_header(self, header):
        if not header:
            return ''
        
        decoded_parts = decode_header(header)
        decoded_string = ''
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                decoded_string += part.decode(encoding or 'utf-8', errors='ignore')
            else:
                decoded_string += part
        return decoded_string
    
    def process_email_images_for_event(self, event_id, email_message):
        images = self.extract_images_from_email_message(email_message)
        
        saved_images = []
        for image_data in images[:20]:
            event_image = self.image_processor.save_image(image_data, event_id, source='email')
            if event_image:
                saved_images.append(event_image)
        
        return saved_images

