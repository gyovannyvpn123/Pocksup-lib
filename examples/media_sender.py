#!/usr/bin/env python
"""
Example media file sender using pocksup.

This script demonstrates how to send different types of media files
to WhatsApp contacts or groups.
"""

import os
import sys
import time
import argparse
import logging
from typing import Optional, List

# Add parent directory to path to allow importing pocksup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pocksup.client import PocksupClient
from pocksup.exceptions import PocksupException, AuthenticationError, ConnectionError, MediaError
from pocksup.constants import (
    MEDIA_TYPE_IMAGE,
    MEDIA_TYPE_VIDEO,
    MEDIA_TYPE_AUDIO,
    MEDIA_TYPE_DOCUMENT
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def determine_media_type(file_path: str) -> int:
    """
    Determine the media type based on file extension.
    
    Args:
        file_path: Path to the media file.
        
    Returns:
        Media type constant.
    """
    extension = os.path.splitext(file_path)[1].lower()
    
    if extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return MEDIA_TYPE_IMAGE
    elif extension in ['.mp4', '.3gp', '.mov', '.avi']:
        return MEDIA_TYPE_VIDEO
    elif extension in ['.mp3', '.ogg', '.m4a', '.wav']:
        return MEDIA_TYPE_AUDIO
    else:
        return MEDIA_TYPE_DOCUMENT

def send_media(recipient: str, file_path: str, caption: Optional[str] = None, 
               config_path: Optional[str] = None) -> str:
    """
    Send a media file to a WhatsApp recipient.
    
    Args:
        recipient: The recipient's phone number or JID.
        file_path: Path to the media file to send.
        caption: Optional caption for the media.
        config_path: Path to the configuration file.
        
    Returns:
        Message ID of the sent media.
        
    Raises:
        FileNotFoundError: If the media file doesn't exist.
        Various PocksupExceptions: For connection or sending errors.
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")
    
    # Create client
    client = PocksupClient(config_path)
    
    try:
        # Connect to WhatsApp
        if not client.auth.is_authenticated():
            logger.info("Authenticating...")
            client.auth.login()
        
        logger.info("Connecting to WhatsApp...")
        client.connect()
        
        # Get file information
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        media_type = determine_media_type(file_path)
        
        # Log the file information
        logger.info(f"Sending file: {file_name} ({file_size} bytes)")
        logger.info(f"Media type: {media_type}")
        logger.info(f"Caption: {caption or 'None'}")
        
        # Send the media
        logger.info(f"Sending media to {recipient}...")
        message_id = client.send_media_message(recipient, file_path, caption)
        
        logger.info(f"Media sent successfully! Message ID: {message_id}")
        
        # Clean up
        client.disconnect()
        
        return message_id
        
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise
    except ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        raise
    except MediaError as e:
        logger.error(f"Media error: {str(e)}")
        raise
    except PocksupException as e:
        logger.error(f"Pocksup error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise
    finally:
        # Ensure we disconnect
        if client.connection.connected:
            client.disconnect()

def send_bulk_media(recipients: List[str], file_path: str, caption: Optional[str] = None,
                    config_path: Optional[str] = None) -> List[str]:
    """
    Send a media file to multiple WhatsApp recipients.
    
    Args:
        recipients: List of recipient phone numbers or JIDs.
        file_path: Path to the media file to send.
        caption: Optional caption for the media.
        config_path: Path to the configuration file.
        
    Returns:
        List of message IDs for the sent media.
        
    Raises:
        FileNotFoundError: If the media file doesn't exist.
        Various PocksupExceptions: For connection or sending errors.
    """
    if not recipients:
        logger.warning("No recipients specified.")
        return []
    
    # Check if file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Media file not found: {file_path}")
    
    # Create client
    client = PocksupClient(config_path)
    message_ids = []
    
    try:
        # Connect to WhatsApp
        if not client.auth.is_authenticated():
            logger.info("Authenticating...")
            client.auth.login()
        
        logger.info("Connecting to WhatsApp...")
        client.connect()
        
        # Get file information
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        media_type = determine_media_type(file_path)
        
        # Log the file information
        logger.info(f"Sending file: {file_name} ({file_size} bytes)")
        logger.info(f"Media type: {media_type}")
        logger.info(f"Caption: {caption or 'None'}")
        
        # Send to each recipient
        for recipient in recipients:
            try:
                logger.info(f"Sending media to {recipient}...")
                message_id = client.send_media_message(recipient, file_path, caption)
                message_ids.append(message_id)
                
                logger.info(f"Media sent to {recipient}! Message ID: {message_id}")
                
                # Brief pause between sends to avoid rate limiting
                time.sleep(1)
                
            except PocksupException as e:
                logger.error(f"Error sending to {recipient}: {str(e)}")
                # Continue with next recipient
                
        # Clean up
        client.disconnect()
        
        return message_ids
        
    except AuthenticationError as e:
        logger.error(f"Authentication error: {str(e)}")
        raise
    except ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        raise
    except MediaError as e:
        logger.error(f"Media error: {str(e)}")
        raise
    except PocksupException as e:
        logger.error(f"Pocksup error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise
    finally:
        # Ensure we disconnect
        if client.connection.connected:
            client.disconnect()

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Pocksup Media Sender')
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug logging')
    parser.add_argument('--recipient', '-r', required=True, help='Recipient phone number or JID')
    parser.add_argument('--file', '-f', required=True, help='Path to media file')
    parser.add_argument('--caption', help='Caption for the media')
    parser.add_argument('--bulk', '-b', action='store_true', help='Send to multiple recipients (comma-separated)')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        if args.bulk:
            # Split recipient string into list
            recipients = [r.strip() for r in args.recipient.split(',') if r.strip()]
            result = send_bulk_media(recipients, args.file, args.caption, args.config)
            print(f"Media sent to {len(result)} recipients.")
        else:
            result = send_media(args.recipient, args.file, args.caption, args.config)
            print(f"Media sent successfully! Message ID: {result}")
            
    except FileNotFoundError as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except PocksupException as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
