"""
Utility functions for the pocksup library.
"""

import os
import re
import uuid
import time
import logging
import hashlib
import base64
from typing import Dict, Any, Optional, List, Tuple, Union

logger = logging.getLogger(__name__)

def generate_message_id() -> str:
    """
    Generate a unique message ID.
    
    Returns:
        A unique message ID string.
    """
    return str(uuid.uuid4())


def generate_client_id() -> str:
    """
    Generate a WhatsApp client ID.
    
    Returns:
        A client ID string.
    """
    # WhatsApp client IDs follow a specific format
    return f"PocksupClient-{uuid.uuid4().hex[:8]}"


def validate_phone_number(phone_number: str) -> bool:
    """
    Validate a phone number format for WhatsApp.
    
    Args:
        phone_number: The phone number to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    # Simple validation: digits only, with or without country code
    phone_number = phone_number.strip().replace('+', '')
    return bool(re.match(r'^\d{10,15}$', phone_number))


def normalize_phone_number(phone_number: str) -> str:
    """
    Normalize a phone number for WhatsApp usage.
    
    Args:
        phone_number: The phone number to normalize.
        
    Returns:
        Normalized phone number string.
    """
    # Remove all non-digit characters
    phone_number = re.sub(r'\D', '', phone_number)
    
    # Ensure phone number has country code
    if len(phone_number) <= 10:
        # Assume US/CA number if no country code
        phone_number = "1" + phone_number
    
    return phone_number


def format_jid(phone_number: str, is_group: bool = False) -> str:
    """
    Format a phone number into a WhatsApp JID (Jabber ID).
    
    Args:
        phone_number: The phone number to format.
        is_group: Whether this is a group JID.
        
    Returns:
        A formatted JID string.
    """
    phone_number = normalize_phone_number(phone_number)
    domain = "g.us" if is_group else "s.whatsapp.net"
    return f"{phone_number}@{domain}"


def extract_phone_from_jid(jid: str) -> str:
    """
    Extract the phone number from a WhatsApp JID.
    
    Args:
        jid: The JID to extract from.
        
    Returns:
        The extracted phone number.
    """
    return jid.split('@')[0]


def is_group_jid(jid: str) -> bool:
    """
    Check if a JID is for a group.
    
    Args:
        jid: The JID to check.
        
    Returns:
        True if it's a group JID, False otherwise.
    """
    return jid.endswith("g.us")


def generate_timestamp() -> int:
    """
    Generate a timestamp for protocol messages.
    
    Returns:
        Current Unix timestamp in seconds.
    """
    return int(time.time())


def hmac_sha256(key: bytes, data: bytes) -> bytes:
    """
    Compute HMAC-SHA256 of data with key.
    
    Args:
        key: The key for HMAC.
        data: The data to sign.
        
    Returns:
        The computed HMAC-SHA256 digest.
    """
    return hashlib.hmac_sha256(key, data).digest()


def sha256(data: bytes) -> bytes:
    """
    Compute SHA-256 hash of data.
    
    Args:
        data: The data to hash.
        
    Returns:
        The computed SHA-256 digest.
    """
    return hashlib.sha256(data).digest()


def base64_encode(data: bytes) -> str:
    """
    Encode bytes as base64 string.
    
    Args:
        data: The data to encode.
        
    Returns:
        Base64 encoded string.
    """
    return base64.b64encode(data).decode('utf-8')


def base64_decode(data: str) -> bytes:
    """
    Decode base64 string to bytes.
    
    Args:
        data: The base64 string to decode.
        
    Returns:
        Decoded bytes.
    """
    return base64.b64decode(data)


def get_mime_type(file_path: str) -> str:
    """
    Determine MIME type from file extension.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        MIME type string.
    """
    extension = os.path.splitext(file_path)[1].lower()
    
    mime_types = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.webp': 'image/webp',
        '.mp4': 'video/mp4',
        '.mp3': 'audio/mp3',
        '.ogg': 'audio/ogg',
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.txt': 'text/plain'
    }
    
    return mime_types.get(extension, 'application/octet-stream')


def get_file_size(file_path: str) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file.
        
    Returns:
        File size in bytes.
    """
    return os.path.getsize(file_path)


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0):
    """
    Decorator for retrying a function with exponential backoff.
    
    Args:
        max_retries: Maximum number of retries.
        base_delay: Base delay between retries in seconds.
        
    Returns:
        Decorated function.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries > max_retries:
                        raise
                    
                    delay = base_delay * (2 ** (retries - 1))
                    logger.warning(f"Retry {retries}/{max_retries} after error: {str(e)}. Waiting {delay:.2f}s")
                    time.sleep(delay)
        return wrapper
    return decorator
