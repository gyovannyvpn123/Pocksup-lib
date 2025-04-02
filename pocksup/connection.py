"""
Connection module for the pocksup library.

Handles networking, WebSocket connections, and protocol serialization.
"""

import time
import socket
import logging
import threading
import websocket
import json
import queue
from typing import Dict, Any, Optional, List, Callable, Tuple, Union, ByteString

from pocksup.config import Config
from pocksup.exceptions import ConnectionError, ProtocolError
from pocksup.constants import WA_SERVER, WA_PORT, CONN_TIMEOUT, RETRY_MAX
from pocksup.auth import Auth

logger = logging.getLogger(__name__)

class Connection:
    """
    Manages WebSocket connection to WhatsApp servers.
    """
    
    def __init__(self, config: Config, auth: Auth):
        """
        Initialize the connection manager.
        
        Args:
            config: Configuration instance.
            auth: Authentication handler.
        """
        self.config = config
        self.auth = auth
        self.ws = None
        self.connected = False
        self.reconnect_count = 0
        self.message_queue = queue.Queue()
        self.message_callbacks = []
        self.state_callbacks = []
        self.reader_thread = None
        self.writer_thread = None
        self.exit_flag = False
        self.heartbeat_thread = None
        self.last_heartbeat = 0
        
    def connect(self) -> bool:
        """
        Connect to WhatsApp servers.
        
        Returns:
            True if connection successful, False otherwise.
        
        Raises:
            ConnectionError: If connection fails after max retries.
        """
        if self.connected and self.ws and self.ws.connected:
            logger.debug("Already connected")
            return True
            
        # Ensure we're authenticated
        if not self.auth.is_authenticated():
            logger.debug("Not authenticated, performing login")
            self.auth.login()
            
        # Get session data
        session = self.auth.get_session()
        if not session:
            raise ConnectionError("No valid session for connection")
            
        # Determine server to connect to
        server = session.get("server_id") or self.auth.credentials.get("chat_dns_domain", WA_SERVER)
        
        # Build WebSocket URL
        ws_url = f"wss://{server}/ws"
        
        # Setup WebSocket headers
        headers = {
            "User-Agent": self.config.get("user_agent", "Pocksup/0.1.0"),
            "Origin": f"https://{server}",
            "X-WA-Session": session.get("session_id", ""),
            "X-WA-Client": self.auth.client_id
        }
        
        retry_count = 0
        
        while retry_count < RETRY_MAX:
            try:
                # Create WebSocket connection
                self.ws = websocket.WebSocketApp(
                    ws_url,
                    header=headers,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close
                )
                
                # Start WebSocket thread
                ws_thread = threading.Thread(target=self.ws.run_forever)
                ws_thread.daemon = True
                ws_thread.start()
                
                # Wait for connection to establish
                timeout = time.time() + CONN_TIMEOUT
                while time.time() < timeout:
                    if self.connected:
                        # Start message processing threads
                        self._start_threads()
                        logger.info(f"Connected to WhatsApp server: {server}")
                        return True
                    time.sleep(0.1)
                
                # Connection timeout
                logger.warning(f"Connection timeout after {CONN_TIMEOUT} seconds")
                retry_count += 1
                
            except Exception as e:
                logger.error(f"Connection error: {str(e)}")
                retry_count += 1
                
            # Connection failed, retry with backoff
            if retry_count < RETRY_MAX:
                backoff = 2 ** retry_count
                logger.warning(f"Connection failed, retrying in {backoff} seconds (attempt {retry_count+1}/{RETRY_MAX})")
                time.sleep(backoff)
        
        self.connected = False
        raise ConnectionError(f"Failed to connect after {RETRY_MAX} attempts")
    
    def disconnect(self) -> None:
        """
        Disconnect from WhatsApp servers.
        """
        self.exit_flag = True
        
        # Stop threads
        if self.reader_thread or self.writer_thread or self.heartbeat_thread:
            logger.debug("Stopping message processing threads")
            # Wait for threads to exit
            if self.reader_thread:
                self.reader_thread.join(2.0)
            if self.writer_thread:
                self.writer_thread.join(2.0)
            if self.heartbeat_thread:
                self.heartbeat_thread.join(2.0)
        
        # Close WebSocket
        if self.ws:
            logger.debug("Closing WebSocket connection")
            self.ws.close()
            
        self.connected = False
        logger.info("Disconnected from WhatsApp server")
    
    def send(self, data: Union[Dict, bytes, str]) -> bool:
        """
        Send data to WhatsApp servers.
        
        Args:
            data: Data to send (dict, bytes, or string).
            
        Returns:
            True if send successful, False otherwise.
        """
        if not self.connected:
            logger.warning("Not connected, attempting to connect")
            self.connect()
            
        # Add to message queue
        if isinstance(data, dict):
            self.message_queue.put(json.dumps(data))
        else:
            self.message_queue.put(data)
            
        return True
    
    def add_message_callback(self, callback: Callable[[Dict], None]) -> None:
        """
        Add a callback for received messages.
        
        Args:
            callback: Function to call with received message.
        """
        self.message_callbacks.append(callback)
    
    def add_state_callback(self, callback: Callable[[str, Dict], None]) -> None:
        """
        Add a callback for connection state changes.
        
        Args:
            callback: Function to call with state change.
        """
        self.state_callbacks.append(callback)
    
    def _start_threads(self) -> None:
        """Start message processing threads."""
        # Start reader thread
        self.reader_thread = threading.Thread(target=self._reader_loop)
        self.reader_thread.daemon = True
        self.reader_thread.start()
        
        # Start writer thread
        self.writer_thread = threading.Thread(target=self._writer_loop)
        self.writer_thread.daemon = True
        self.writer_thread.start()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
    
    def _reader_loop(self) -> None:
        """Reader thread to process received messages."""
        logger.debug("Message reader thread started")
        
        while not self.exit_flag:
            try:
                time.sleep(0.01)  # Prevent CPU spinning
                # Messages are handled by the WebSocket callbacks
            except Exception as e:
                logger.error(f"Error in reader loop: {str(e)}")
                
        logger.debug("Message reader thread exited")
    
    def _writer_loop(self) -> None:
        """Writer thread to send queued messages."""
        logger.debug("Message writer thread started")
        
        while not self.exit_flag:
            try:
                # Get a message from the queue (non-blocking)
                try:
                    message = self.message_queue.get(block=True, timeout=0.5)
                except queue.Empty:
                    continue
                
                # Send the message
                if self.ws and self.connected:
                    if isinstance(message, str):
                        self.ws.send(message)
                    else:
                        self.ws.send(message, opcode=websocket.ABNF.OPCODE_BINARY)
                    
                    self.message_queue.task_done()
                else:
                    # Put message back in queue
                    self.message_queue.put(message)
                    logger.warning("Connection lost, reconnecting")
                    self.reconnect()
                    time.sleep(1)  # Wait before retrying
                
            except Exception as e:
                logger.error(f"Error in writer loop: {str(e)}")
                
        logger.debug("Message writer thread exited")
    
    def _heartbeat_loop(self) -> None:
        """Heartbeat thread to keep connection alive."""
        logger.debug("Heartbeat thread started")
        
        heartbeat_interval = self.config.get("heartbeat_interval", 60)
        
        while not self.exit_flag:
            try:
                time.sleep(1)  # Check every second
                
                # Check if it's time to send a heartbeat
                current_time = time.time()
                if current_time - self.last_heartbeat >= heartbeat_interval:
                    if self.ws and self.connected:
                        # Send heartbeat message
                        heartbeat = {"type": "ping", "timestamp": int(current_time)}
                        self.ws.send(json.dumps(heartbeat))
                        self.last_heartbeat = current_time
                        logger.debug("Sent heartbeat ping")
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {str(e)}")
                
        logger.debug("Heartbeat thread exited")
    
    def reconnect(self) -> bool:
        """
        Reconnect to WhatsApp servers.
        
        Returns:
            True if reconnection successful, False otherwise.
        """
        self.reconnect_count += 1
        backoff = min(30, 2 ** self.reconnect_count)  # Cap at 30 seconds
        
        try:
            # Close existing connection
            if self.ws:
                self.ws.close()
                
            self.connected = False
            logger.info(f"Reconnecting in {backoff} seconds (attempt {self.reconnect_count})")
            time.sleep(backoff)
            
            # Refresh session if needed
            self.auth.refresh_session()
            
            # Reconnect
            return self.connect()
            
        except Exception as e:
            logger.error(f"Reconnection error: {str(e)}")
            return False
    
    def _on_open(self, ws) -> None:
        """
        WebSocket on_open callback.
        
        Args:
            ws: WebSocket instance.
        """
        self.connected = True
        self.reconnect_count = 0
        logger.debug("WebSocket connection opened")
        
        # Send init message
        session = self.auth.get_session()
        init_message = {
            "type": "init",
            "session_id": session.get("session_id", ""),
            "client_id": self.auth.client_id,
            "timestamp": int(time.time())
        }
        ws.send(json.dumps(init_message))
        
        # Notify state callbacks
        for callback in self.state_callbacks:
            try:
                callback("connected", {})
            except Exception as e:
                logger.error(f"Error in state callback: {str(e)}")
    
    def _on_message(self, ws, message) -> None:
        """
        WebSocket on_message callback.
        
        Args:
            ws: WebSocket instance.
            message: Received message.
        """
        try:
            # Process the message
            if isinstance(message, str):
                # Parse JSON message
                data = json.loads(message)
                
                # Handle system messages
                if data.get("type") == "pong":
                    logger.debug("Received heartbeat pong")
                    return
                    
                elif data.get("type") == "error":
                    error_code = data.get("code", "unknown")
                    error_msg = data.get("message", "Unknown error")
                    logger.error(f"Received error from server: {error_code} - {error_msg}")
                    
                    # Handle specific errors
                    if error_code == "session_expired":
                        logger.info("Session expired, refreshing")
                        self.auth.refresh_session()
                        self.reconnect()
                    
                    return
            
            # Notify message callbacks
            for callback in self.message_callbacks:
                try:
                    callback(message)
                except Exception as e:
                    logger.error(f"Error in message callback: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    def _on_error(self, ws, error) -> None:
        """
        WebSocket on_error callback.
        
        Args:
            ws: WebSocket instance.
            error: Error information.
        """
        logger.error(f"WebSocket error: {str(error)}")
        
        # Notify state callbacks
        for callback in self.state_callbacks:
            try:
                callback("error", {"error": str(error)})
            except Exception as e:
                logger.error(f"Error in state callback: {str(e)}")
    
    def _on_close(self, ws, close_status_code, close_msg) -> None:
        """
        WebSocket on_close callback.
        
        Args:
            ws: WebSocket instance.
            close_status_code: Close status code.
            close_msg: Close message.
        """
        self.connected = False
        logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        
        # Notify state callbacks
        for callback in self.state_callbacks:
            try:
                callback("disconnected", {
                    "code": close_status_code,
                    "reason": close_msg
                })
            except Exception as e:
                logger.error(f"Error in state callback: {str(e)}")
        
        # Auto reconnect if enabled
        if not self.exit_flag and self.config.get("auto_reconnect", True):
            threading.Thread(target=self.reconnect).start()
