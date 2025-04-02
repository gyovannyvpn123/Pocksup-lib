"""
Message classes for the pocksup library.
"""

import time
import os
import logging
from typing import Dict, Any, Optional, List, Union, ByteString

from pocksup.constants import (
    MESSAGE_TYPE_TEXT,
    MESSAGE_TYPE_MEDIA,
    MESSAGE_TYPE_LOCATION,
    MESSAGE_TYPE_CONTACT,
    MEDIA_TYPE_IMAGE,
    MEDIA_TYPE_VIDEO,
    MEDIA_TYPE_AUDIO,
    MEDIA_TYPE_DOCUMENT,
    MEDIA_TYPE_STICKER
)
from pocksup.utils import get_mime_type, get_file_size

logger = logging.getLogger(__name__)

class Message:
    """
    Base class for WhatsApp messages.
    """
    
    def __init__(self, message_id: Optional[str] = None, 
                 recipient: Optional[str] = None,
                 sender: Optional[str] = None, 
                 timestamp: Optional[int] = None):
        """
        Initialize a WhatsApp message.
        
        Args:
            message_id: Unique message ID.
            recipient: JID of the recipient.
            sender: JID of the sender.
            timestamp: Message timestamp.
        """
        self.message_id = message_id or f"msg_{int(time.time())}_{id(self) % 10000}"
        self.recipient = recipient
        self.sender = sender
        self.timestamp = timestamp or int(time.time())
        self.message_type = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the message to a dictionary.
        
        Returns:
            Dictionary representation of the message.
        """
        return {
            "id": self.message_id,
            "recipient": self.recipient,
            "sender": self.sender,
            "timestamp": self.timestamp,
            "type": self.message_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """
        Create a message from a dictionary.
        
        Args:
            data: Dictionary representation of a message.
            
        Returns:
            A Message instance.
        """
        message_type = data.get("type")
        
        if message_type == MESSAGE_TYPE_TEXT:
            return TextMessage.from_dict(data)
        elif message_type == MESSAGE_TYPE_MEDIA:
            return MediaMessage.from_dict(data)
        elif message_type == MESSAGE_TYPE_LOCATION:
            return LocationMessage.from_dict(data)
        elif message_type == MESSAGE_TYPE_CONTACT:
            return ContactMessage.from_dict(data)
        else:
            # Generic message
            return cls(
                message_id=data.get("id"),
                recipient=data.get("recipient"),
                sender=data.get("sender"),
                timestamp=data.get("timestamp")
            )


class TextMessage(Message):
    """
    Text message class.
    """
    
    def __init__(self, text: str, **kwargs):
        """
        Initialize a text message.
        
        Args:
            text: Message text.
            **kwargs: Additional message parameters.
        """
        super().__init__(**kwargs)
        self.text = text
        self.message_type = MESSAGE_TYPE_TEXT
        self.quoted_message_id = kwargs.get("quoted_message_id")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the text message to a dictionary.
        
        Returns:
            Dictionary representation of the text message.
        """
        data = super().to_dict()
        data["text"] = self.text
        
        if self.quoted_message_id:
            data["quoted_msg_id"] = self.quoted_message_id
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextMessage':
        """
        Create a text message from a dictionary.
        
        Args:
            data: Dictionary representation of a text message.
            
        Returns:
            A TextMessage instance.
        """
        return cls(
            text=data.get("text", ""),
            message_id=data.get("id"),
            recipient=data.get("recipient"),
            sender=data.get("sender"),
            timestamp=data.get("timestamp"),
            quoted_message_id=data.get("quoted_msg_id")
        )


class MediaMessage(Message):
    """
    Media message class.
    """
    
    def __init__(self, media_type: int, url: str, mime_type: str, **kwargs):
        """
        Initialize a media message.
        
        Args:
            media_type: Type of media.
            url: URL of the media.
            mime_type: MIME type of the media.
            **kwargs: Additional message parameters.
        """
        super().__init__(**kwargs)
        self.media_type = media_type
        self.url = url
        self.mime_type = mime_type
        self.message_type = MESSAGE_TYPE_MEDIA
        self.caption = kwargs.get("caption")
        self.file_name = kwargs.get("file_name")
        self.file_size = kwargs.get("file_size")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the media message to a dictionary.
        
        Returns:
            Dictionary representation of the media message.
        """
        data = super().to_dict()
        data["media_type"] = self.media_type
        data["url"] = self.url
        data["mime_type"] = self.mime_type
        
        if self.caption:
            data["caption"] = self.caption
            
        if self.file_name:
            data["file_name"] = self.file_name
            
        if self.file_size:
            data["file_size"] = self.file_size
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MediaMessage':
        """
        Create a media message from a dictionary.
        
        Args:
            data: Dictionary representation of a media message.
            
        Returns:
            A MediaMessage instance.
        """
        return cls(
            media_type=data.get("media_type", MEDIA_TYPE_IMAGE),
            url=data.get("url", ""),
            mime_type=data.get("mime_type", "application/octet-stream"),
            message_id=data.get("id"),
            recipient=data.get("recipient"),
            sender=data.get("sender"),
            timestamp=data.get("timestamp"),
            caption=data.get("caption"),
            file_name=data.get("file_name"),
            file_size=data.get("file_size")
        )
    
    @classmethod
    def from_file(cls, file_path: str, recipient: str, caption: Optional[str] = None, **kwargs) -> 'MediaMessage':
        """
        Create a media message from a local file.
        
        Args:
            file_path: Path to the media file.
            recipient: JID of the recipient.
            caption: Optional media caption.
            **kwargs: Additional message parameters.
            
        Returns:
            A MediaMessage instance.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Media file not found: {file_path}")
            
        file_name = os.path.basename(file_path)
        mime_type = get_mime_type(file_path)
        file_size = get_file_size(file_path)
        
        # Determine media type from mime type
        media_type = MEDIA_TYPE_DOCUMENT  # Default
        
        if mime_type.startswith("image/"):
            media_type = MEDIA_TYPE_IMAGE
        elif mime_type.startswith("video/"):
            media_type = MEDIA_TYPE_VIDEO
        elif mime_type.startswith("audio/"):
            media_type = MEDIA_TYPE_AUDIO
            
        # For a real implementation, this would upload the file to WhatsApp's servers
        # and get a URL. For now, we'll use a placeholder URL.
        url = f"file://{os.path.abspath(file_path)}"
        
        return cls(
            media_type=media_type,
            url=url,
            mime_type=mime_type,
            recipient=recipient,
            caption=caption,
            file_name=file_name,
            file_size=file_size,
            **kwargs
        )


class LocationMessage(Message):
    """
    Location message class.
    """
    
    def __init__(self, latitude: float, longitude: float, **kwargs):
        """
        Initialize a location message.
        
        Args:
            latitude: Location latitude.
            longitude: Location longitude.
            **kwargs: Additional message parameters.
        """
        super().__init__(**kwargs)
        self.latitude = latitude
        self.longitude = longitude
        self.message_type = MESSAGE_TYPE_LOCATION
        self.name = kwargs.get("name")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the location message to a dictionary.
        
        Returns:
            Dictionary representation of the location message.
        """
        data = super().to_dict()
        data["latitude"] = self.latitude
        data["longitude"] = self.longitude
        
        if self.name:
            data["name"] = self.name
            
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LocationMessage':
        """
        Create a location message from a dictionary.
        
        Args:
            data: Dictionary representation of a location message.
            
        Returns:
            A LocationMessage instance.
        """
        return cls(
            latitude=data.get("latitude", 0.0),
            longitude=data.get("longitude", 0.0),
            message_id=data.get("id"),
            recipient=data.get("recipient"),
            sender=data.get("sender"),
            timestamp=data.get("timestamp"),
            name=data.get("name")
        )


class ContactMessage(Message):
    """
    Contact message class.
    """
    
    def __init__(self, contacts: List[Dict[str, str]], **kwargs):
        """
        Initialize a contact message.
        
        Args:
            contacts: List of contact dictionaries.
            **kwargs: Additional message parameters.
        """
        super().__init__(**kwargs)
        self.contacts = contacts
        self.message_type = MESSAGE_TYPE_CONTACT
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the contact message to a dictionary.
        
        Returns:
            Dictionary representation of the contact message.
        """
        data = super().to_dict()
        data["contacts"] = self.contacts
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContactMessage':
        """
        Create a contact message from a dictionary.
        
        Args:
            data: Dictionary representation of a contact message.
            
        Returns:
            A ContactMessage instance.
        """
        return cls(
            contacts=data.get("contacts", []),
            message_id=data.get("id"),
            recipient=data.get("recipient"),
            sender=data.get("sender"),
            timestamp=data.get("timestamp")
        )
