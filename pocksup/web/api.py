"""
REST API for pocksup library.

Provides a RESTful interface to the pocksup WhatsApp client.
"""

import os
import time
import logging
import json
from typing import Dict, Any, Optional, List, Union, Tuple
from flask import Flask, request, jsonify, Response, Blueprint

from pocksup.client import PocksupClient
from pocksup.utils import validate_phone_number, normalize_phone_number, format_jid
from pocksup.exceptions import PocksupException, AuthenticationError, ConnectionError, MediaError

logger = logging.getLogger(__name__)

class PocksupAPI:
    """
    REST API wrapper for pocksup client.
    """
    
    def __init__(self, client: Optional[PocksupClient] = None, config_path: Optional[str] = None):
        """
        Initialize the API.
        
        Args:
            client: PocksupClient instance. If None, a new one will be created.
            config_path: Path to configuration file for new client.
        """
        self.client = client or PocksupClient(config_path)
        self.bp = Blueprint('pocksup_api', __name__)
        self._setup_routes()
        
    def _setup_routes(self) -> None:
        """Set up the API routes."""
        # Authentication routes
        self.bp.route('/auth/register', methods=['POST'])(self._register)
        self.bp.route('/auth/verify', methods=['POST'])(self._verify)
        self.bp.route('/auth/login', methods=['GET'])(self._login)
        self.bp.route('/auth/logout', methods=['GET'])(self._logout)
        
        # Connection routes
        self.bp.route('/connection/status', methods=['GET'])(self._connection_status)
        self.bp.route('/connection/connect', methods=['GET'])(self._connect)
        self.bp.route('/connection/disconnect', methods=['GET'])(self._disconnect)
        
        # Message routes
        self.bp.route('/messages/send/text', methods=['POST'])(self._send_text)
        self.bp.route('/messages/send/media', methods=['POST'])(self._send_media)
        self.bp.route('/messages/send/location', methods=['POST'])(self._send_location)
        self.bp.route('/messages/send/contact', methods=['POST'])(self._send_contact)
        
        # Media routes
        self.bp.route('/media/download', methods=['POST'])(self._download_media)
        
        # Group routes
        self.bp.route('/groups/create', methods=['POST'])(self._create_group)
        self.bp.route('/groups/add', methods=['POST'])(self._add_group_participants)
        self.bp.route('/groups/remove', methods=['POST'])(self._remove_group_participants)
        self.bp.route('/groups/leave', methods=['POST'])(self._leave_group)
        self.bp.route('/groups/subject', methods=['POST'])(self._set_group_subject)
        
        # Presence routes
        self.bp.route('/presence/set', methods=['POST'])(self._set_presence)
        self.bp.route('/chat/state', methods=['POST'])(self._set_chat_state)
        
    def register_with_app(self, app: Flask) -> None:
        """
        Register the API with a Flask app.
        
        Args:
            app: Flask app to register with.
        """
        app.register_blueprint(self.bp, url_prefix='/api')
        
        # Add error handlers
        @app.errorhandler(PocksupException)
        def handle_pocksup_exception(error):
            response = jsonify({
                'error': type(error).__name__,
                'message': str(error)
            })
            response.status_code = 400
            return response
            
        @app.errorhandler(404)
        def handle_not_found(error):
            response = jsonify({
                'error': 'NotFound',
                'message': 'The requested resource was not found.'
            })
            response.status_code = 404
            return response
            
        @app.errorhandler(500)
        def handle_server_error(error):
            response = jsonify({
                'error': 'ServerError',
                'message': 'An internal server error occurred.'
            })
            response.status_code = 500
            return response
            
    def _register(self) -> Response:
        """
        Register a phone number.
        
        Expected JSON body:
        {
            "phone_number": "1234567890",
            "method": "sms"  # or "voice"
        }
        
        Returns:
            JSON response with registration result.
        """
        try:
            data = request.get_json()
            
            if not data or 'phone_number' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required field: phone_number'
                }), 400
                
            phone_number = data['phone_number']
            method = data.get('method', 'sms')
            
            result = self.client.register(phone_number, method)
            
            return jsonify({
                'success': True,
                'data': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred during registration.'
            }), 500
    
    def _verify(self) -> Response:
        """
        Verify a registration code.
        
        Expected JSON body:
        {
            "phone_number": "1234567890",
            "code": "123456"
        }
        
        Returns:
            JSON response with verification result.
        """
        try:
            data = request.get_json()
            
            if not data or 'phone_number' not in data or 'code' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: phone_number and code'
                }), 400
                
            phone_number = data['phone_number']
            code = data['code']
            
            result = self.client.verify_code(phone_number, code)
            
            return jsonify({
                'success': True,
                'data': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred during verification.'
            }), 500
    
    def _login(self) -> Response:
        """
        Login using saved credentials.
        
        Returns:
            JSON response with login result.
        """
        try:
            result = self.client.auth.login()
            
            return jsonify({
                'success': True,
                'authenticated': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred during login.'
            }), 500
    
    def _logout(self) -> Response:
        """
        Logout from WhatsApp.
        
        Returns:
            JSON response with logout result.
        """
        try:
            result = self.client.auth.logout()
            
            return jsonify({
                'success': True,
                'logged_out': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred during logout.'
            }), 500
    
    def _connection_status(self) -> Response:
        """
        Get connection status.
        
        Returns:
            JSON response with connection status.
        """
        try:
            is_connected = self.client.connection.connected
            is_authenticated = self.client.auth.is_authenticated()
            
            return jsonify({
                'success': True,
                'connected': is_connected,
                'authenticated': is_authenticated
            })
            
        except Exception as e:
            logger.error(f"Status check error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred checking connection status.'
            }), 500
    
    def _connect(self) -> Response:
        """
        Connect to WhatsApp.
        
        Returns:
            JSON response with connection result.
        """
        try:
            result = self.client.connect()
            
            return jsonify({
                'success': True,
                'connected': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred during connection.'
            }), 500
    
    def _disconnect(self) -> Response:
        """
        Disconnect from WhatsApp.
        
        Returns:
            JSON response with disconnection result.
        """
        try:
            result = self.client.disconnect()
            
            return jsonify({
                'success': True,
                'disconnected': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Disconnection error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred during disconnection.'
            }), 500
    
    def _send_text(self) -> Response:
        """
        Send a text message.
        
        Expected JSON body:
        {
            "recipient": "1234567890",
            "text": "Hello, world!",
            "quoted_message_id": "msg_123"  # optional
        }
        
        Returns:
            JSON response with send result.
        """
        try:
            data = request.get_json()
            
            if not data or 'recipient' not in data or 'text' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: recipient and text'
                }), 400
                
            recipient = data['recipient']
            text = data['text']
            quoted_message_id = data.get('quoted_message_id')
            
            message_id = self.client.send_text_message(recipient, text, quoted_message_id)
            
            return jsonify({
                'success': True,
                'message_id': message_id
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Send text error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred sending the text message.'
            }), 500
    
    def _send_media(self) -> Response:
        """
        Send a media message.
        
        Expected JSON body:
        {
            "recipient": "1234567890",
            "file_path": "/path/to/file.jpg",
            "caption": "Check this out!"  # optional
        }
        
        Returns:
            JSON response with send result.
        """
        try:
            data = request.get_json()
            
            if not data or 'recipient' not in data or 'file_path' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: recipient and file_path'
                }), 400
                
            recipient = data['recipient']
            file_path = data['file_path']
            caption = data.get('caption')
            
            if not os.path.exists(file_path):
                return jsonify({
                    'success': False,
                    'error': 'FileNotFound',
                    'message': f'Media file not found: {file_path}'
                }), 400
            
            message_id = self.client.send_media_message(recipient, file_path, caption)
            
            return jsonify({
                'success': True,
                'message_id': message_id
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Send media error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred sending the media message.'
            }), 500
    
    def _send_location(self) -> Response:
        """
        Send a location message.
        
        Expected JSON body:
        {
            "recipient": "1234567890",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "name": "San Francisco"  # optional
        }
        
        Returns:
            JSON response with send result.
        """
        try:
            data = request.get_json()
            
            if not data or 'recipient' not in data or 'latitude' not in data or 'longitude' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: recipient, latitude, and longitude'
                }), 400
                
            recipient = data['recipient']
            latitude = float(data['latitude'])
            longitude = float(data['longitude'])
            name = data.get('name')
            
            message_id = self.client.send_location_message(recipient, latitude, longitude, name)
            
            return jsonify({
                'success': True,
                'message_id': message_id
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Send location error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred sending the location message.'
            }), 500
    
    def _send_contact(self) -> Response:
        """
        Send a contact message.
        
        Expected JSON body:
        {
            "recipient": "1234567890",
            "contacts": [
                {
                    "name": "John Doe",
                    "phone": "1234567890"
                }
            ]
        }
        
        Returns:
            JSON response with send result.
        """
        try:
            data = request.get_json()
            
            if not data or 'recipient' not in data or 'contacts' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: recipient and contacts'
                }), 400
                
            recipient = data['recipient']
            contacts = data['contacts']
            
            if not isinstance(contacts, list) or not contacts:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Contacts must be a non-empty list'
                }), 400
            
            message_id = self.client.send_contact_message(recipient, contacts)
            
            return jsonify({
                'success': True,
                'message_id': message_id
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Send contact error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred sending the contact message.'
            }), 500
    
    def _download_media(self) -> Response:
        """
        Download media from a URL.
        
        Expected JSON body:
        {
            "url": "https://example.com/media.jpg",
            "file_name": "downloaded_media.jpg"  # optional
        }
        
        Returns:
            JSON response with download result.
        """
        try:
            data = request.get_json()
            
            if not data or 'url' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required field: url'
                }), 400
                
            url = data['url']
            file_name = data.get('file_name')
            
            file_path = self.client.download_media(url, file_name)
            
            return jsonify({
                'success': True,
                'file_path': file_path
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Download media error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred downloading the media.'
            }), 500
    
    def _create_group(self) -> Response:
        """
        Create a new group.
        
        Expected JSON body:
        {
            "subject": "Group Name",
            "participants": ["1234567890", "0987654321"]
        }
        
        Returns:
            JSON response with creation result.
        """
        try:
            data = request.get_json()
            
            if not data or 'subject' not in data or 'participants' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: subject and participants'
                }), 400
                
            subject = data['subject']
            participants = data['participants']
            
            if not isinstance(participants, list) or not participants:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Participants must be a non-empty list'
                }), 400
            
            group_id = self.client.create_group(subject, participants)
            
            return jsonify({
                'success': True,
                'group_id': group_id
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Create group error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred creating the group.'
            }), 500
    
    def _add_group_participants(self) -> Response:
        """
        Add participants to a group.
        
        Expected JSON body:
        {
            "group_id": "1234567890-group",
            "participants": ["1234567890", "0987654321"]
        }
        
        Returns:
            JSON response with result.
        """
        try:
            data = request.get_json()
            
            if not data or 'group_id' not in data or 'participants' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: group_id and participants'
                }), 400
                
            group_id = data['group_id']
            participants = data['participants']
            
            if not isinstance(participants, list) or not participants:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Participants must be a non-empty list'
                }), 400
            
            result = self.client.add_group_participants(group_id, participants)
            
            return jsonify({
                'success': True,
                'result': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Add group participants error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred adding group participants.'
            }), 500
    
    def _remove_group_participants(self) -> Response:
        """
        Remove participants from a group.
        
        Expected JSON body:
        {
            "group_id": "1234567890-group",
            "participants": ["1234567890", "0987654321"]
        }
        
        Returns:
            JSON response with result.
        """
        try:
            data = request.get_json()
            
            if not data or 'group_id' not in data or 'participants' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: group_id and participants'
                }), 400
                
            group_id = data['group_id']
            participants = data['participants']
            
            if not isinstance(participants, list) or not participants:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Participants must be a non-empty list'
                }), 400
            
            result = self.client.remove_group_participants(group_id, participants)
            
            return jsonify({
                'success': True,
                'result': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Remove group participants error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred removing group participants.'
            }), 500
    
    def _leave_group(self) -> Response:
        """
        Leave a group.
        
        Expected JSON body:
        {
            "group_id": "1234567890-group"
        }
        
        Returns:
            JSON response with result.
        """
        try:
            data = request.get_json()
            
            if not data or 'group_id' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required field: group_id'
                }), 400
                
            group_id = data['group_id']
            
            result = self.client.leave_group(group_id)
            
            return jsonify({
                'success': True,
                'result': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Leave group error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred leaving the group.'
            }), 500
    
    def _set_group_subject(self) -> Response:
        """
        Set a group's subject.
        
        Expected JSON body:
        {
            "group_id": "1234567890-group",
            "subject": "New Group Name"
        }
        
        Returns:
            JSON response with result.
        """
        try:
            data = request.get_json()
            
            if not data or 'group_id' not in data or 'subject' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: group_id and subject'
                }), 400
                
            group_id = data['group_id']
            subject = data['subject']
            
            result = self.client.set_group_subject(group_id, subject)
            
            return jsonify({
                'success': True,
                'result': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Set group subject error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred setting the group subject.'
            }), 500
    
    def _set_presence(self) -> Response:
        """
        Set presence status.
        
        Expected JSON body:
        {
            "presence_type": "available"  # or "unavailable", "composing", etc.
        }
        
        Returns:
            JSON response with result.
        """
        try:
            data = request.get_json()
            
            if not data or 'presence_type' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required field: presence_type'
                }), 400
                
            presence_type = data['presence_type']
            
            result = self.client.set_presence(presence_type)
            
            return jsonify({
                'success': True,
                'result': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Set presence error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred setting presence.'
            }), 500
    
    def _set_chat_state(self) -> Response:
        """
        Set chat state.
        
        Expected JSON body:
        {
            "recipient": "1234567890",
            "state": "composing"  # or "paused", "recording", etc.
        }
        
        Returns:
            JSON response with result.
        """
        try:
            data = request.get_json()
            
            if not data or 'recipient' not in data or 'state' not in data:
                return jsonify({
                    'success': False,
                    'error': 'BadRequest',
                    'message': 'Missing required fields: recipient and state'
                }), 400
                
            recipient = data['recipient']
            state = data['state']
            
            result = self.client.set_chat_state(recipient, state)
            
            return jsonify({
                'success': True,
                'result': result
            })
            
        except PocksupException as e:
            return jsonify({
                'success': False,
                'error': type(e).__name__,
                'message': str(e)
            }), 400
        except Exception as e:
            logger.error(f"Set chat state error: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'ServerError',
                'message': 'An error occurred setting chat state.'
            }), 500
