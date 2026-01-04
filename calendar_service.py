from ics import Calendar, Event as ICSEvent
from datetime import datetime
import pytz
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from models import Event

class CalendarService:
    
    def __init__(self, mail_server=None, mail_port=None, mail_username=None, mail_password=None):
        self.mail_server = mail_server
        self.mail_port = mail_port
        self.mail_username = mail_username
        self.mail_password = mail_password
    
    def generate_ics_file(self, event):
        calendar = Calendar()
        ics_event = ICSEvent()
        
        ics_event.name = event.title
        ics_event.begin = event.start_time
        ics_event.end = event.end_time
        ics_event.description = event.description or ''
        ics_event.location = event.location or ''
        ics_event.uid = f"event-{event.id}@calendar-system"
        
        if event.all_day:
            ics_event.make_all_day()
        
        calendar.events.add(ics_event)
        
        return str(calendar)
    
    def send_ics_update(self, event, recipient_email=None):
        if not self.mail_server or not self.mail_username or not self.mail_password:
            print("Email configuration not set. Skipping ICS email.")
            return False
        
        try:
            ics_content = self.generate_ics_file(event)
            
            msg = MIMEMultipart()
            msg['From'] = self.mail_username
            msg['To'] = recipient_email or event.organizer_email
            msg['Subject'] = f'Updated: {event.title}'
            
            ics_attachment = MIMEText(ics_content, 'calendar', 'utf-8')
            ics_attachment.add_header('Content-Disposition', 'attachment', filename='event.ics')
            ics_attachment.add_header('Content-Type', 'text/calendar; charset=utf-8; method=REQUEST')
            msg.attach(ics_attachment)
            
            body = f"""
Event Updated: {event.title}

Time: {event.start_time.strftime('%Y-%m-%d %H:%M')} - {event.end_time.strftime('%H:%M')}
Location: {event.location or 'N/A'}
Description: {event.description or 'N/A'}

Please see the attached ICS file to update your calendar.
"""
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.mail_server, self.mail_port)
            server.starttls()
            server.login(self.mail_username, self.mail_password)
            server.send_message(msg)
            server.quit()
            
            return True
        except Exception as e:
            print(f"Error sending ICS email: {e}")
            return False
    
    def sync_calendar(self, user_id, ics_files):
        from ics_parser import ICSParser
        parser = ICSParser()
        
        all_events = []
        for ics_file in ics_files:
            try:
                events = parser.parse_ics_file(ics_file, user_id)
                all_events.extend(events)
            except Exception as e:
                print(f"Error syncing ICS file: {e}")
        
        return all_events

