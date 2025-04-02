"""
Main client module for the pocksup library.
"""

import os
import time
import logging
import threading
from typing import Dict, Any, Optional, List, Callable, Union, Tuple

from pocksup.config import Config
from pocksup.auth import Auth
from pocksup.connection import Connection
from pocksup.handlers import MessageHandler, StatusHandler
from pocksup.media import MediaManager
from pocksup.encryption import EncryptionManager
from pocksup.messages import (
    Message, 
    TextMessage, 
    MediaMessage, 
    LocationMessage, 
    ContactMessage
)
from pocksup.utils import (
    validate_phone_number, 
    normalize_phone_number, 
    format_jid, 
    is_group_jid,
    extract_phone_from_jid
)
from pocksup.protocol import Protocol
from pocksup.constants import (
    MEDIA_TYPE_IMAGE,
    MEDIA_TYPE_VIDEO,
    MEDIA_TYPE_AUDIO,
    MEDIA_TYPE_DOCUMENT,
    STATUS_ONLINE,
    STATUS_OFFLINE,
    STATUS_TYPING,
    STATUS_RECORDING,
    STATUS_PAUSED
)
from pocksup.exceptions import (
    PocksupException,
    AuthenticationError,
    ConnectionError,
    ProtocolError,
    MediaError,
    BadParamError
)

logger = logging.getLogger(__name__)

class PocksupClient:
    """
    Main client class for the pocksup library.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the pocksup client.
        
        Args:
            config_path: Path to the configuration file. If None, uses default config.
        """
        self.config = Config(config_path)
        self.auth = Auth(self.config)
        self.connection = Connection(self.config, self.auth)
        self.message_handler = MessageHandler()
        self.status_handler = StatusHandler()
        self.media = MediaManager(self.config, self.auth)
        self.encryption = EncryptionManager()
        
        # Set up callbacks
        self.connection.add_message_callback(self._on_message)
        self.connection.add_state_callback(self._on_state_change)
        
        # Set up basic logging
        log_level = getattr(logging, self.config.get("log_level", "INFO"))
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        logger.debug("PocksupClient initialized")
    
    def connect(self) -> bool:
        """
        Connect to WhatsApp.
        
        Returns:
            True if connection successful, False otherwise.
            
        Raises:
            AuthenticationError: If authentication fails.
            ConnectionError: If connection fails.
        """
        try:
            # Ensure we're authenticated
            if not self.auth.is_authenticated():
                logger.debug("Not authenticated, performing login")
                self.auth.login()
                
            # Connect
            result = self.connection.connect()
            
            if result:
                # Initialize encryption system
                self.encryption.setup()
                
                # Set online status
                self.set_presence(STATUS_ONLINE)
                
            return result
            
        except AuthenticationError as e:
            logger.error(f"Authentication error: {str(e)}")
            raise
        except ConnectionError as e:
            logger.error(f"Connection error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise ConnectionError(f"Failed to connect: {str(e)}")
    
    def disconnect(self) -> bool:
        """
        Disconnect from WhatsApp.
        
        Returns:
            True if disconnect successful, False otherwise.
        """
        try:
            # Set offline status before disconnecting
            self.set_presence(STATUS_OFFLINE)
            
            # Disconnect from server
            self.connection.disconnect()
            
            # Logout (session cleanup)
            return self.auth.logout()
            
        except Exception as e:
            logger.error(f"Error during disconnect: {str(e)}")
            return False
    
    def register(self, phone_number: str, method: str = "sms") -> Dict[str, Any]:
        """
        Register a phone number with WhatsApp.
        
        Args:
            phone_number: The phone number to register.
            method: Registration method ('sms' or 'voice').
            
        Returns:
            Registration response data.
            
        Raises:
            BadParamError: If phone number is invalid or method is unsupported.
            AuthenticationError: If registration fails.
        """
        if not validate_phone_number(phone_number):
            raise BadParamError(f"Invalid phone number format: {phone_number}")
            
        return self.auth.register(phone_number, method)
    
    def verify_code(self, phone_number: str, code: str) -> Dict[str, Any]:
        """
        Verify a registration code.
        
        Args:
            phone_number: The phone number being registered.
            code: The verification code received.
            
        Returns:
            Verification response data with login credentials.
            
        Raises:
            BadParamError: If phone number is invalid or code is invalid.
            AuthenticationError: If verification fails.
        """
        if not validate_phone_number(phone_number):
            raise BadParamError(f"Invalid phone number format: {phone_number}")
            
        if not code or not code.isdigit() or len(code) < 4:
            raise BadParamError(f"Invalid verification code: {code}")
            
        return self.auth.verify_code(phone_number, code)
    
    def send_text_message(self, recipient: str, text: str, quoted_message_id: Optional[str] = None) -> str:
        """
        Send a text message.
        
        Args:
            recipient: Phone number or JID of the recipient.
            text: Message text.
            quoted_message_id: ID of the message being quoted/replied to.
            
        Returns:
            ID of the sent message.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If message sending fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Format recipient if needed
        if not '@' in recipient:
            recipient = format_jid(recipient)
            
        # Create message
        message = TextMessage(
            text=text,
            recipient=recipient,
            quoted_message_id=quoted_message_id
        )
        
        # Set typing status briefly
        self.set_chat_state(recipient, STATUS_TYPING)
        time.sleep(min(0.5, len(text) / 20))  # Simulate typing, max 0.5 seconds
        self.set_chat_state(recipient, STATUS_PAUSED)
        
        # Serialize message
        data = Protocol.encode_text_message(recipient, text, quoted_message_id)
        
        # Send message
        self.connection.send(data)
        
        logger.info(f"Sent text message to {recipient}: {text[:30]}...")
        return message.message_id
    
    def send_media_message(self, recipient: str, file_path: str, caption: Optional[str] = None) -> str:
        """
        Send a media message.
        
        Args:
            recipient: Phone number or JID of the recipient.
            file_path: Path to the media file.
            caption: Optional caption for the media.
            
        Returns:
            ID of the sent message.
            
        Raises:
            FileNotFoundError: If file doesn't exist.
            MediaError: If media upload fails.
            ConnectionError: If connection fails.
            ProtocolError: If message sending fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Format recipient if needed
        if not '@' in recipient:
            recipient = format_jid(recipient)
            
        # Upload media
        upload_result = self.media.upload(file_path)
        
        # Get media details
        media_url = upload_result.get("url")
        mime_type = upload_result.get("mime_type")
        file_name = upload_result.get("file_name")
        file_size = upload_result.get("file_size")
        
        # Determine media type
        media_type = MEDIA_TYPE_DOCUMENT  # Default
        
        if mime_type.startswith("image/"):
            media_type = MEDIA_TYPE_IMAGE
        elif mime_type.startswith("video/"):
            media_type = MEDIA_TYPE_VIDEO
        elif mime_type.startswith("audio/"):
            media_type = MEDIA_TYPE_AUDIO
            
        # Create message
        message = MediaMessage(
            media_type=media_type,
            url=media_url,
            mime_type=mime_type,
            recipient=recipient,
            caption=caption,
            file_name=file_name,
            file_size=file_size
        )
        
        # Serialize message
        data = Protocol.encode_media_message(
            recipient=recipient,
            media_type=media_type,
            url=media_url,
            mime_type=mime_type,
            caption=caption,
            file_name=file_name,
            file_size=file_size
        )
        
        # Send message
        self.connection.send(data)
        
        logger.info(f"Sent media message to {recipient}: {file_name}")
        return message.message_id
    
    def send_location_message(self, recipient: str, latitude: float, longitude: float, name: Optional[str] = None) -> str:
        """
        Send a location message.
        
        Args:
            recipient: Phone number or JID of the recipient.
            latitude: Location latitude.
            longitude: Location longitude.
            name: Optional location name.
            
        Returns:
            ID of the sent message.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If message sending fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Format recipient if needed
        if not '@' in recipient:
            recipient = format_jid(recipient)
            
        # Create message
        message = LocationMessage(
            latitude=latitude,
            longitude=longitude,
            recipient=recipient,
            name=name
        )
        
        # Serialize message
        data = Protocol.encode_location_message(recipient, latitude, longitude, name)
        
        # Send message
        self.connection.send(data)
        
        logger.info(f"Sent location message to {recipient}: {latitude}, {longitude}")
        return message.message_id
    
    def send_contact_message(self, recipient: str, contacts: List[Dict[str, str]]) -> str:
        """
        Send a contact message.
        
        Args:
            recipient: Phone number or JID of the recipient.
            contacts: List of contact dictionaries.
            
        Returns:
            ID of the sent message.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If message sending fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Format recipient if needed
        if not '@' in recipient:
            recipient = format_jid(recipient)
            
        # Create message
        message = ContactMessage(
            contacts=contacts,
            recipient=recipient
        )
        
        # Serialize message
        data = Protocol.encode_contact_message(recipient, contacts)
        
        # Send message
        self.connection.send(data)
        
        logger.info(f"Sent contact message to {recipient}: {len(contacts)} contacts")
        return message.message_id
    
    def download_media(self, url: str, file_name: Optional[str] = None) -> str:
        """
        Download media from a message.
        
        Args:
            url: URL of the media to download.
            file_name: Optional file name to save as.
            
        Returns:
            Path to the downloaded file.
            
        Raises:
            MediaError: If download fails.
        """
        return self.media.download(url, file_name)
    
    def create_group(self, subject: str, participants: List[str]) -> str:
        """
        Create a new group.
        
        Args:
            subject: Group subject/name.
            participants: List of participant phone numbers or JIDs.
            
        Returns:
            JID of the created group.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If group creation fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Format participants if needed
        formatted_participants = []
        for participant in participants:
            if not '@' in participant:
                formatted_participants.append(format_jid(participant))
            else:
                formatted_participants.append(participant)
                
        # Create group command
        data = Protocol.encode_group_command(
            group_id="create",
            command="create",
            participants=formatted_participants
        )
        
        # Add subject to data
        import json
        json_data = json.loads(data[4:].decode('utf-8'))
        json_data["data"]["subject"] = subject
        updated_data = json.dumps(json_data).encode('utf-8')
        header = data[:4]
        data = header + updated_data
        
        # Send command
        self.connection.send(data)
        
        logger.info(f"Created group {subject} with {len(participants)} participants")
        # Note: In a real implementation, we would wait for the server response
        # to get the actual group JID, but for now we'll return a placeholder
        return "waiting_for_server_response@g.us"
    
    def add_group_participants(self, group_id: str, participants: List[str]) -> bool:
        """
        Add participants to a group.
        
        Args:
            group_id: JID of the group.
            participants: List of participant phone numbers or JIDs to add.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If adding participants fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Ensure group_id is a group JID
        if not is_group_jid(group_id):
            group_id = f"{group_id}@g.us"
            
        # Format participants if needed
        formatted_participants = []
        for participant in participants:
            if not '@' in participant:
                formatted_participants.append(format_jid(participant))
            else:
                formatted_participants.append(participant)
                
        # Create group command
        data = Protocol.encode_group_command(
            group_id=group_id,
            command="add",
            participants=formatted_participants
        )
        
        # Send command
        self.connection.send(data)
        
        logger.info(f"Added {len(participants)} participants to group {group_id}")
        return True
    
    def remove_group_participants(self, group_id: str, participants: List[str]) -> bool:
        """
        Remove participants from a group.
        
        Args:
            group_id: JID of the group.
            participants: List of participant phone numbers or JIDs to remove.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If removing participants fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Ensure group_id is a group JID
        if not is_group_jid(group_id):
            group_id = f"{group_id}@g.us"
            
        # Format participants if needed
        formatted_participants = []
        for participant in participants:
            if not '@' in participant:
                formatted_participants.append(format_jid(participant))
            else:
                formatted_participants.append(participant)
                
        # Create group command
        data = Protocol.encode_group_command(
            group_id=group_id,
            command="remove",
            participants=formatted_participants
        )
        
        # Send command
        self.connection.send(data)
        
        logger.info(f"Removed {len(participants)} participants from group {group_id}")
        return True
    
    def leave_group(self, group_id: str) -> bool:
        """
        Leave a group.
        
        Args:
            group_id: JID of the group.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If leaving group fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Ensure group_id is a group JID
        if not is_group_jid(group_id):
            group_id = f"{group_id}@g.us"
                
        # Create group command
        data = Protocol.encode_group_command(
            group_id=group_id,
            command="leave"
        )
        
        # Send command
        self.connection.send(data)
        
        logger.info(f"Left group {group_id}")
        return True
    
    def set_group_subject(self, group_id: str, subject: str) -> bool:
        """
        Set a group's subject.
        
        Args:
            group_id: JID of the group.
            subject: New group subject.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If setting subject fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Ensure group_id is a group JID
        if not is_group_jid(group_id):
            group_id = f"{group_id}@g.us"
                
        # Create group command
        data = Protocol.encode_group_command(
            group_id=group_id,
            command="subject"
        )
        
        # Add subject to data
        import json
        json_data = json.loads(data[4:].decode('utf-8'))
        json_data["data"]["subject"] = subject
        updated_data = json.dumps(json_data).encode('utf-8')
        header = data[:4]
        data = header + updated_data
        
        # Send command
        self.connection.send(data)
        
        logger.info(f"Set group {group_id} subject to: {subject}")
        return True
    
    def set_presence(self, presence_type: str) -> bool:
        """
        Set presence status.
        
        Args:
            presence_type: Type of presence.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If setting presence fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
                
        # Create presence update
        data = Protocol.encode_presence(presence_type)
        
        # Send update
        self.connection.send(data)
        
        logger.debug(f"Set presence to: {presence_type}")
        return True
    
    def set_chat_state(self, recipient: str, state: str) -> bool:
        """
        Set chat state (typing, etc.).
        
        Args:
            recipient: Phone number or JID of the recipient.
            state: Chat state.
            
        Returns:
            True if successful, False otherwise.
            
        Raises:
            ConnectionError: If connection fails.
            ProtocolError: If setting chat state fails.
        """
        # Validate connection
        if not self.connection.connected:
            self.connect()
            
        # Format recipient if needed
        if not '@' in recipient:
            recipient = format_jid(recipient)
                
        # Create chat state update
        data = {
            "type": "chatstate",
            "recipient": recipient,
            "state": state,
            "timestamp": int(time.time())
        }
        
        # Send update
        self.connection.send(data)
        
        logger.debug(f"Set chat state to {state} for {recipient}")
        return True
    
    def register_message_handler(self, callback: Callable[[Message], None], message_type: Optional[Union[int, str]] = None) -> None:
        """
        Register a handler for incoming messages.
        
        Args:
            callback: Function to call when message is received.
            message_type: Type of message to handle (None for all messages).
        """
        if message_type is None:
            message_type = "all"
            
        self.message_handler.register_message_callback(message_type, callback)
    
    def register_event_handler(self, callback: Callable[[Dict[str, Any]], None], event_type: Optional[str] = None) -> None:
        """
        Register a handler for events.
        
        Args:
            callback: Function to call when event occurs.
            event_type: Type of event to handle (None for all events).
        """
        if event_type is None:
            event_type = "all"
            
        self.message_handler.register_event_callback(event_type, callback)
    
    def register_status_handler(self, callback: Callable[[str, Dict[str, Any]], None], status_type: Optional[str] = None) -> None:
        """
        Register a handler for status updates.
        
        Args:
            callback: Function to call when status update is received.
            status_type: Type of status to handle (None for all status updates).
        """
        if status_type is None:
            status_type = "all"
            
        self.status_handler.register_status_callback(status_type, callback)
    
    def _on_message(self, message_data: Union[bytes, str]) -> None:
        """
        Handle incoming message.
        
        Args:
            message_data: Raw message data.
        """
        self.message_handler.handle_message(message_data)
    
    def _on_state_change(self, state: str, data: Dict[str, Any]) -> None:
        """
        Handle connection state change.
        
        Args:
            state: State name.
            data: State data.
        """
        self.status_handler.handle_status(state, data)
        
        if state == "disconnected" and self.config.get("auto_reconnect", True):
            logger.info("Connection lost, scheduling reconnect")
            # Schedule reconnect in a separate thread
            threading.Thread(target=self._delayed_reconnect).start()
    
    def _delayed_reconnect(self) -> None:
        """Perform a delayed reconnection attempt."""
        try:
            # Wait a moment before reconnecting
            time.sleep(self.config.get("reconnect_delay", 5))
            
            # Attempt to reconnect
            if not self.connection.connected:
                logger.info("Attempting to reconnect")
                self.connect()
                
        except Exception as e:
            logger.error(f"Reconnection attempt failed: {str(e)}")
