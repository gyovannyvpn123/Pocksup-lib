"""
Protocol module for the pocksup library.

Handles serialization and deserialization of WhatsApp protocol messages.
"""

import time
import logging
import json
import struct
import base64
from typing import Dict, Any, Optional, List, Tuple, Union, ByteString

from pocksup.exceptions import ProtocolError
from pocksup.constants import (
    MESSAGE_TYPE_TEXT,
    MESSAGE_TYPE_MEDIA,
    MESSAGE_TYPE_LOCATION,
    MESSAGE_TYPE_CONTACT
)

logger = logging.getLogger(__name__)

class Protocol:
    """
    Handles WhatsApp protocol serialization and deserialization.
    """
    
    @staticmethod
    def encode_message(message_type: int, data: Dict[str, Any]) -> bytes:
        """
        Encode a message for sending to WhatsApp.
        
        Args:
            message_type: Type of message.
            data: Message data.
            
        Returns:
            Encoded message bytes.
        """
        # Create message packet
        packet = {
            "type": message_type,
            "data": data,
            "timestamp": int(time.time())
        }
        
        # Convert to JSON
        json_data = json.dumps(packet)
        
        # In a real implementation, this would properly implement the WhatsApp
        # protocol format with the correct binary framing
        
        # For now, use a simple format: [length (4 bytes)][json data]
        length = len(json_data)
        header = struct.pack('>I', length)
        
        return header + json_data.encode('utf-8')
    
    @staticmethod
    def decode_message(data: bytes) -> Dict[str, Any]:
        """
        Decode a message received from WhatsApp.
        
        Args:
            data: Raw message data.
            
        Returns:
            Decoded message.
            
        Raises:
            ProtocolError: If message cannot be decoded.
        """
        try:
            # In a real implementation, this would properly parse the WhatsApp
            # protocol format with the correct binary framing
            
            # For our simple format: [length (4 bytes)][json data]
            if len(data) < 4:
                raise ProtocolError("Message too short")
                
            length = struct.unpack('>I', data[:4])[0]
            json_data = data[4:4+length].decode('utf-8')
            
            return json.loads(json_data)
            
        except Exception as e:
            raise ProtocolError(f"Failed to decode message: {str(e)}")
    
    @staticmethod
    def encode_text_message(recipient: str, text: str, quoted_message_id: Optional[str] = None) -> bytes:
        """
        Encode a text message.
        
        Args:
            recipient: JID of the recipient.
            text: Message text.
            quoted_message_id: ID of the message being quoted/replied to.
            
        Returns:
            Encoded message bytes.
        """
        data = {
            "recipient": recipient,
            "text": text,
            "id": f"msg_{int(time.time())}_{id(text) % 10000}",
        }
        
        if quoted_message_id:
            data["quoted_msg_id"] = quoted_message_id
            
        return Protocol.encode_message(MESSAGE_TYPE_TEXT, data)
    
    @staticmethod
    def encode_media_message(
            recipient: str, 
            media_type: int, 
            url: str, 
            mime_type: str, 
            caption: Optional[str] = None, 
            file_name: Optional[str] = None, 
            file_size: Optional[int] = None) -> bytes:
        """
        Encode a media message.
        
        Args:
            recipient: JID of the recipient.
            media_type: Type of media.
            url: URL of the media.
            mime_type: MIME type of the media.
            caption: Caption for the media.
            file_name: File name.
            file_size: File size in bytes.
            
        Returns:
            Encoded message bytes.
        """
        data = {
            "recipient": recipient,
            "media_type": media_type,
            "url": url,
            "mime_type": mime_type,
            "id": f"media_{int(time.time())}_{id(url) % 10000}",
        }
        
        if caption:
            data["caption"] = caption
            
        if file_name:
            data["file_name"] = file_name
            
        if file_size:
            data["file_size"] = file_size
            
        return Protocol.encode_message(MESSAGE_TYPE_MEDIA, data)
    
    @staticmethod
    def encode_location_message(recipient: str, latitude: float, longitude: float, name: Optional[str] = None) -> bytes:
        """
        Encode a location message.
        
        Args:
            recipient: JID of the recipient.
            latitude: Location latitude.
            longitude: Location longitude.
            name: Optional location name.
            
        Returns:
            Encoded message bytes.
        """
        data = {
            "recipient": recipient,
            "latitude": latitude,
            "longitude": longitude,
            "id": f"loc_{int(time.time())}_{int((latitude + longitude) * 1000) % 10000}",
        }
        
        if name:
            data["name"] = name
            
        return Protocol.encode_message(MESSAGE_TYPE_LOCATION, data)
    
    @staticmethod
    def encode_contact_message(recipient: str, contacts: List[Dict[str, str]]) -> bytes:
        """
        Encode a contact message.
        
        Args:
            recipient: JID of the recipient.
            contacts: List of contact dictionaries.
            
        Returns:
            Encoded message bytes.
        """
        data = {
            "recipient": recipient,
            "contacts": contacts,
            "id": f"contact_{int(time.time())}_{len(contacts)}",
        }
            
        return Protocol.encode_message(MESSAGE_TYPE_CONTACT, data)
    
    @staticmethod
    def encode_group_command(group_id: str, command: str, participants: Optional[List[str]] = None) -> bytes:
        """
        Encode a group command.
        
        Args:
            group_id: Group JID.
            command: Group command.
            participants: List of participant JIDs (for commands that need them).
            
        Returns:
            Encoded command bytes.
        """
        data = {
            "group": group_id,
            "command": command,
            "id": f"group_{int(time.time())}_{id(command) % 10000}",
        }
        
        if participants:
            data["participants"] = participants
            
        return Protocol.encode_message(5, data)  # 5 = group command type
    
    @staticmethod
    def encode_presence(presence_type: str) -> bytes:
        """
        Encode a presence update.
        
        Args:
            presence_type: Type of presence update.
            
        Returns:
            Encoded presence bytes.
        """
        data = {
            "presence": presence_type,
            "timestamp": int(time.time())
        }
            
        return Protocol.encode_message(6, data)  # 6 = presence update type
