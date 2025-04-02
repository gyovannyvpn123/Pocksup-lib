#!/usr/bin/env python
"""
Example chat client using pocksup.

This is a simple command-line client that connects to WhatsApp
and allows sending and receiving messages.
"""

import os
import sys
import time
import argparse
import logging
import threading
from typing import Dict, Any, Optional, List

# Add parent directory to path to allow importing pocksup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pocksup.client import PocksupClient
from pocksup.messages import Message, TextMessage, MediaMessage
from pocksup.exceptions import PocksupException, AuthenticationError, ConnectionError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class ChatClient:
    """
    Simple command-line chat client using pocksup.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the chat client.
        
        Args:
            config_path: Path to configuration file.
        """
        self.client = PocksupClient(config_path)
        self.running = False
        self.contacts = {}  # Store contacts for quick access
        
        # Register message handlers
        self.client.register_message_handler(self._on_message)
        self.client.register_status_handler(self._on_status)
        
    def start(self) -> None:
        """Start the chat client."""
        print("Starting pocksup chat client...")
        
        try:
            # Try to connect using saved credentials
            self._authenticate()
            self._connect()
            
            # Start command loop
            self.running = True
            self._command_loop()
            
        except KeyboardInterrupt:
            print("\nExiting by user request.")
        except PocksupException as e:
            logger.error(f"Pocksup error: {str(e)}")
            print(f"Error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            print(f"Unexpected error: {str(e)}")
        finally:
            # Clean up
            if self.client.connection.connected:
                print("Disconnecting...")
                self.client.disconnect()
                
    def _authenticate(self) -> None:
        """Authenticate with WhatsApp."""
        if self.client.auth.is_authenticated():
            print("Already authenticated.")
            return
            
        print("\nAuthentication required.")
        
        # Try to login with saved credentials
        try:
            print("Trying to login with saved credentials...")
            self.client.auth.login()
            print("Login successful!")
            return
        except AuthenticationError:
            # Need to register
            print("No valid credentials found or login failed.")
        
        # Registration flow
        while True:
            phone_number = input("Enter your phone number (with country code): ")
            
            try:
                # Request registration code
                method = input("Send verification code via (sms/voice) [sms]: ") or "sms"
                print(f"Requesting verification code via {method}...")
                self.client.register(phone_number, method)
                
                # Verify code
                code = input("Enter the verification code: ")
                print("Verifying code...")
                self.client.verify_code(phone_number, code)
                
                print("Registration successful!")
                
                # Login with new credentials
                self.client.auth.login()
                print("Login successful!")
                return
                
            except PocksupException as e:
                print(f"Registration error: {str(e)}")
                retry = input("Try again? (y/n) [y]: ") or "y"
                if retry.lower() != "y":
                    raise
    
    def _connect(self) -> None:
        """Connect to WhatsApp."""
        if not self.client.connection.connected:
            print("Connecting to WhatsApp...")
            self.client.connect()
            print("Connected successfully!")
    
    def _command_loop(self) -> None:
        """Main command loop."""
        print("\nWelcome to the pocksup chat client!")
        print("Type 'help' for available commands.")
        
        while self.running:
            try:
                command = input("\n> ").strip()
                
                if not command:
                    continue
                    
                if command == "help":
                    self._show_help()
                elif command == "exit" or command == "quit":
                    self.running = False
                elif command == "status":
                    self._show_status()
                elif command.startswith("chat "):
                    self._start_chat(command[5:].strip())
                elif command.startswith("send "):
                    parts = command[5:].strip().split(" ", 1)
                    if len(parts) == 2:
                        recipient, message = parts
                        self._send_message(recipient, message)
                    else:
                        print("Usage: send <recipient> <message>")
                elif command.startswith("media "):
                    parts = command[6:].strip().split(" ", 2)
                    if len(parts) >= 2:
                        recipient, file_path = parts[0], parts[1]
                        caption = parts[2] if len(parts) > 2 else None
                        self._send_media(recipient, file_path, caption)
                    else:
                        print("Usage: media <recipient> <file_path> [caption]")
                elif command == "reconnect":
                    self._reconnect()
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands.")
                
            except PocksupException as e:
                print(f"Error: {str(e)}")
            except Exception as e:
                logger.error(f"Command error: {str(e)}")
                print(f"Unexpected error: {str(e)}")
    
    def _show_help(self) -> None:
        """Show help information."""
        print("\nAvailable commands:")
        print("  help             - Show this help information")
        print("  status           - Show connection status")
        print("  chat <recipient> - Start a chat with a recipient")
        print("  send <recipient> <message> - Send a message to a recipient")
        print("  media <recipient> <file_path> [caption] - Send media to a recipient")
        print("  reconnect        - Reconnect to WhatsApp")
        print("  exit/quit        - Exit the chat client")
        print("\nRecipient can be a phone number or a JID (e.g., 1234567890@s.whatsapp.net)")
    
    def _show_status(self) -> None:
        """Show connection status."""
        is_connected = self.client.connection.connected
        is_authenticated = self.client.auth.is_authenticated()
        
        print("\nConnection status:")
        print(f"  Connected: {is_connected}")
        print(f"  Authenticated: {is_authenticated}")
        
        if is_authenticated:
            credentials = self.client.auth.credentials
            phone = credentials.get("phone_number", "Unknown")
            expiration = credentials.get("expiration", 0)
            expiration_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expiration))
            
            print(f"  Phone number: {phone}")
            print(f"  Credentials expire: {expiration_str}")
    
    def _start_chat(self, recipient: str) -> None:
        """
        Start a chat with a recipient.
        
        Args:
            recipient: Phone number or JID of the recipient.
        """
        print(f"\nStarting chat with {recipient}")
        print("Type your messages. Enter an empty line to exit the chat.")
        
        while True:
            message = input(f"[To {recipient}] ").strip()
            
            if not message:
                break
                
            try:
                self.client.send_text_message(recipient, message)
            except PocksupException as e:
                print(f"Error sending message: {str(e)}")
                break
    
    def _send_message(self, recipient: str, message: str) -> None:
        """
        Send a message to a recipient.
        
        Args:
            recipient: Phone number or JID of the recipient.
            message: Message to send.
        """
        try:
            message_id = self.client.send_text_message(recipient, message)
            print(f"Message sent (ID: {message_id})")
        except PocksupException as e:
            print(f"Error sending message: {str(e)}")
    
    def _send_media(self, recipient: str, file_path: str, caption: Optional[str] = None) -> None:
        """
        Send media to a recipient.
        
        Args:
            recipient: Phone number or JID of the recipient.
            file_path: Path to the media file.
            caption: Optional caption for the media.
        """
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return
                
            print(f"Sending media to {recipient}...")
            message_id = self.client.send_media_message(recipient, file_path, caption)
            print(f"Media sent (ID: {message_id})")
        except PocksupException as e:
            print(f"Error sending media: {str(e)}")
    
    def _reconnect(self) -> None:
        """Reconnect to WhatsApp."""
        try:
            print("Disconnecting...")
            self.client.disconnect()
            
            print("Reconnecting...")
            self.client.connect()
            
            print("Reconnected successfully!")
        except PocksupException as e:
            print(f"Reconnection error: {str(e)}")
    
    def _on_message(self, message: Message) -> None:
        """
        Handle incoming messages.
        
        Args:
            message: The received message.
        """
        sender = message.sender
        if not sender:
            return
            
        # Format sender
        sender_display = sender.split('@')[0] if '@' in sender else sender
        
        # Print message based on type
        if isinstance(message, TextMessage):
            print(f"\n[From {sender_display}] {message.text}")
        elif isinstance(message, MediaMessage):
            media_type = "Image" if message.media_type == 1 else \
                        "Video" if message.media_type == 2 else \
                        "Audio" if message.media_type == 3 else \
                        "Document" if message.media_type == 4 else \
                        "Media"
            
            caption = f" - {message.caption}" if message.caption else ""
            print(f"\n[From {sender_display}] {media_type}{caption}")
            print(f"Media URL: {message.url}")
            
            # Ask to download
            download = input("Download media? (y/n) [n]: ") or "n"
            if download.lower() == "y":
                try:
                    file_path = self.client.download_media(message.url)
                    print(f"Downloaded to: {file_path}")
                except Exception as e:
                    print(f"Download error: {str(e)}")
        else:
            print(f"\n[From {sender_display}] New message received (type: {message.message_type})")
            
        # Reset prompt
        print("\n> ", end="", flush=True)
    
    def _on_status(self, status_type: str, data: Dict[str, Any]) -> None:
        """
        Handle status updates.
        
        Args:
            status_type: Type of status update.
            data: Status data.
        """
        if status_type == "connected":
            print("\nConnection established")
        elif status_type == "disconnected":
            print("\nConnection lost")
            
            # Auto reconnect after delay
            def delayed_reconnect():
                time.sleep(5)
                try:
                    print("\nAttempting to reconnect...")
                    self.client.connect()
                    print("Reconnected successfully!")
                except Exception as e:
                    print(f"Reconnection failed: {str(e)}")
                print("\n> ", end="", flush=True)
                
            if self.running:
                threading.Thread(target=delayed_reconnect).start()
        elif status_type == "error":
            print(f"\nConnection error: {data.get('error', 'Unknown error')}")
            
        # Reset prompt if needed
        if self.running:
            print("\n> ", end="", flush=True)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Pocksup Chat Client')
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    client = ChatClient(args.config)
    client.start()

if __name__ == '__main__':
    main()
