from PIL import Image
import os
import hashlib
from datetime import datetime
from models import db, Event, EventImage
from config import Config

class ImageProcessor:
    
    
    def __init__(self, upload_folder=None):
        self.upload_folder = upload_folder or Config.UPLOAD_FOLDER
        self.images_folder = os.path.join(self.upload_folder, 'images')
        self.max_images = Config.MAX_IMAGES_PER_EVENT
        self.thumbnail_size = (150, 150)
        
        os.makedirs(self.images_folder, exist_ok=True)
    
    def save_image(self, image_data, event_id, source='upload'):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            hash_str = hashlib.md5(image_data).hexdigest()[:8]
            filename = f"event_{event_id}_{timestamp}_{hash_str}.jpg"
            filepath = os.path.join(self.images_folder, filename)
            
            with open(filepath, 'wb') as f:
                f.write(image_data)
            
            thumbnail_path = self.create_thumbnail(filepath)
            
            event_image = EventImage(
                event_id=event_id,
                image_path=filepath,
                thumbnail_path=thumbnail_path,
                source=source
            )
            db.session.add(event_image)
            db.session.commit()
            
            return event_image
        except Exception as e:
            print(f"Error saving image: {e}")
            return None
    
    def create_thumbnail(self, image_path):
        """Create thumbnail from image"""
        try:
            img = Image.open(image_path)
            
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            img.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
            
            base, ext = os.path.splitext(image_path)
            thumbnail_path = f"{base}_thumb.jpg"
            img.save(thumbnail_path, 'JPEG', quality=85)
            
            return thumbnail_path
        except Exception as e:
            print(f"Error creating thumbnail: {e}")
            return None
    
    def extract_images_from_email(self, email_content):
        import re
        from urllib.parse import urlparse
        import base64
        
        images = []
        
        base64_pattern = r'data:image/([^;]+);base64,([^\s"\']+)'
        matches = re.findall(base64_pattern, email_content)
        
        for match in matches:
            img_format, img_data = match
            try:
                image_bytes = base64.b64decode(img_data)
                images.append(image_bytes)
            except:
                pass
        
        url_pattern = r'<img[^>]+src=["\']([^"\']+)["\']'
        url_matches = re.findall(url_pattern, email_content)
        
        
        return images
    
    def get_event_images(self, event_id, limit=None):
        limit = limit or self.max_images
        images = EventImage.query.filter_by(event_id=event_id)\
            .order_by(EventImage.created_at.desc())\
            .limit(limit)\
            .all()
        return images
    
    def delete_image(self, image_id):
        try:
            image = EventImage.query.get(image_id)
            if not image:
                return False
            
            if os.path.exists(image.image_path):
                os.remove(image.image_path)
            if image.thumbnail_path and os.path.exists(image.thumbnail_path):
                os.remove(image.thumbnail_path)
            
            db.session.delete(image)
            db.session.commit()
            
            return True
        except Exception as e:
            print(f"Error deleting image: {e}")
            db.session.rollback()
            return False

