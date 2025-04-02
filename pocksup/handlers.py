"""
Message and event handlers for the pocksup library.
"""

import logging
import threading
from typing import Dict, Any, Optional, List, Callable, Union

from pocksup.messages import Message
from pocksup.protocol import Protocol

logger = logging.getLogger(__name__)

class MessageHandler:
    """
    Handles incoming and outgoing messages.
    """
    
    def __init__(self):
        """Initialize the message handler."""
        self.message_callbacks = {}
        self.event_callbacks = {}
        
    def register_message_callback(self, message_type: Union[int, str], callback: Callable[[Message], None]) -> None:
        """
        Register a callback for a specific message type.
        
        Args:
            message_type: The message type to register for.
            callback: The callback function.
        """
        if message_type not in self.message_callbacks:
            self.message_callbacks[message_type] = []
            
        self.message_callbacks[message_type].append(callback)
        logger.debug(f"Registered callback for message type: {message_type}")
    
    def register_event_callback(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback for a specific event type.
        
        Args:
            event_type: The event type to register for.
            callback: The callback function.
        """
        if event_type not in self.event_callbacks:
            self.event_callbacks[event_type] = []
            
        self.event_callbacks[event_type].append(callback)
        logger.debug(f"Registered callback for event type: {event_type}")
    
    def handle_message(self, raw_data: Union[bytes, str]) -> None:
        """
        Handle a raw message.
        
        Args:
            raw_data: Raw message data.
        """
        try:
            # Parse message
            if isinstance(raw_data, bytes):
                # Binary protocol message
                data = Protocol.decode_message(raw_data)
            else:
                # JSON message (for events, etc.)
                import json
                data = json.loads(raw_data)
                
            # Check if it's an event
            if "type" in data and data["type"] in ["connected", "disconnected", "error"]:
                self._handle_event(data)
                return
                
            # Convert to message object
            message = Message.from_dict(data)
            
            # Call appropriate callbacks
            message_type = message.message_type
            
            if message_type in self.message_callbacks:
                for callback in self.message_callbacks[message_type]:
                    # Run callback in a separate thread to avoid blocking
                    threading.Thread(target=self._safe_callback, args=(callback, message)).start()
                    
            # Call callbacks for all message types
            if "all" in self.message_callbacks:
                for callback in self.message_callbacks["all"]:
                    # Run callback in a separate thread to avoid blocking
                    threading.Thread(target=self._safe_callback, args=(callback, message)).start()
                    
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}")
    
    def _handle_event(self, event_data: Dict[str, Any]) -> None:
        """
        Handle an event.
        
        Args:
            event_data: Event data.
        """
        event_type = event_data.get("type")
        
        if event_type in self.event_callbacks:
            for callback in self.event_callbacks[event_type]:
                # Run callback in a separate thread to avoid blocking
                threading.Thread(target=self._safe_callback, args=(callback, event_data)).start()
                
        # Call callbacks for all event types
        if "all" in self.event_callbacks:
            for callback in self.event_callbacks["all"]:
                # Run callback in a separate thread to avoid blocking
                threading.Thread(target=self._safe_callback, args=(callback, event_data)).start()
    
    def _safe_callback(self, callback: Callable, data: Any) -> None:
        """
        Safely execute a callback function.
        
        Args:
            callback: The callback function.
            data: Data to pass to the callback.
        """
        try:
            callback(data)
        except Exception as e:
            logger.error(f"Error in callback function: {str(e)}")


class StatusHandler:
    """
    Handles status updates.
    """
    
    def __init__(self):
        """Initialize the status handler."""
        self.status_callbacks = {}
        
    def register_status_callback(self, status_type: str, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """
        Register a callback for a specific status type.
        
        Args:
            status_type: The status type to register for.
            callback: The callback function.
        """
        if status_type not in self.status_callbacks:
            self.status_callbacks[status_type] = []
            
        self.status_callbacks[status_type].append(callback)
        logger.debug(f"Registered callback for status type: {status_type}")
    
    def handle_status(self, status_type: str, data: Dict[str, Any]) -> None:
        """
        Handle a status update.
        
        Args:
            status_type: Type of status update.
            data: Status data.
        """
        try:
            if status_type in self.status_callbacks:
                for callback in self.status_callbacks[status_type]:
                    # Run callback in a separate thread to avoid blocking
                    threading.Thread(target=self._safe_callback, args=(callback, status_type, data)).start()
                    
            # Call callbacks for all status types
            if "all" in self.status_callbacks:
                for callback in self.status_callbacks["all"]:
                    # Run callback in a separate thread to avoid blocking
                    threading.Thread(target=self._safe_callback, args=(callback, status_type, data)).start()
                    
        except Exception as e:
            logger.error(f"Error handling status: {str(e)}")
    
    def _safe_callback(self, callback: Callable, status_type: str, data: Dict[str, Any]) -> None:
        """
        Safely execute a callback function.
        
        Args:
            callback: The callback function.
            status_type: Type of status update.
            data: Status data.
        """
        try:
            callback(status_type, data)
        except Exception as e:
            logger.error(f"Error in callback function: {str(e)}")
