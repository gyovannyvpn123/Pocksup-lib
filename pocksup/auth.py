"""
Authentication module for the pocksup library.

Handles WhatsApp authentication, registration, and session management.
"""

import os
import time
import json
import base64
import logging
import hashlib
import requests
from typing import Dict, Any, Optional, Tuple

from pocksup.config import Config
from pocksup.exceptions import AuthenticationError, ConnectionError, BadParamError
from pocksup.utils import generate_client_id, retry_with_backoff
from pocksup.constants import WA_SERVER, LOGIN_TIMEOUT, PROTOCOL_VERSION

logger = logging.getLogger(__name__)

class Auth:
    """
    Handles WhatsApp authentication and session management.
    """
    
    def __init__(self, config: Config):
        """
        Initialize the authentication handler.
        
        Args:
            config: Configuration instance.
        """
        self.config = config
        self.credentials = config.load_credentials() or {}
        self.client_id = generate_client_id()
        self.session = None
        self.authenticated = False
        
    def register(self, phone_number: str, method: str = "sms") -> Dict[str, Any]:
        """
        Register a phone number with WhatsApp.
        
        Args:
            phone_number: The phone number to register.
            method: Registration method ('sms' or 'voice').
            
        Returns:
            Registration response data.
        """
        if method not in ["sms", "voice"]:
            raise BadParamError("Registration method must be 'sms' or 'voice'")
        
        # WhatsApp registration endpoint
        url = f"https://{WA_SERVER}/v1/code"
        
        data = {
            "cc": self._extract_country_code(phone_number),
            "in": self._extract_phone_number(phone_number),
            "method": method,
            "sim_mcc": "000",
            "sim_mnc": "000",
            "token": self._generate_registration_token(),
            "client": self.client_id,
            "lg": "en",
            "lc": "US"
        }
        
        try:
            response = requests.post(url, json=data, timeout=self.config.get("request_timeout", 15))
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "ok":
                logger.info(f"Registration code sent via {method} to {phone_number}")
                return result
            else:
                error = result.get("reason", "Unknown error")
                logger.error(f"Registration failed: {error}")
                raise AuthenticationError(f"Registration failed: {error}")
                
        except requests.RequestException as e:
            logger.error(f"Registration request failed: {str(e)}")
            raise ConnectionError(f"Registration request failed: {str(e)}")
    
    def verify_code(self, phone_number: str, code: str) -> Dict[str, Any]:
        """
        Verify a registration code.
        
        Args:
            phone_number: The phone number being registered.
            code: The verification code received.
            
        Returns:
            Verification response data with login credentials.
        """
        # WhatsApp verification endpoint
        url = f"https://{WA_SERVER}/v1/register"
        
        data = {
            "cc": self._extract_country_code(phone_number),
            "in": self._extract_phone_number(phone_number),
            "code": code,
            "client": self.client_id
        }
        
        try:
            response = requests.post(url, json=data, timeout=self.config.get("request_timeout", 15))
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "ok":
                # Save credentials
                self.credentials = {
                    "phone_number": phone_number,
                    "login_token": result.get("login"),
                    "edge_routing_info": result.get("edge_routing_info", ""),
                    "chat_dns_domain": result.get("chat_dns_domain", WA_SERVER),
                    "expiration": int(time.time()) + result.get("ttl", 31536000)  # Default to 1 year
                }
                
                self.config.save_credentials(self.credentials)
                logger.info(f"Verification successful for {phone_number}")
                return result
            else:
                error = result.get("reason", "Unknown error")
                logger.error(f"Verification failed: {error}")
                raise AuthenticationError(f"Verification failed: {error}")
                
        except requests.RequestException as e:
            logger.error(f"Verification request failed: {str(e)}")
            raise ConnectionError(f"Verification request failed: {str(e)}")
    
    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def login(self) -> bool:
        """
        Login to WhatsApp using saved credentials.
        
        Returns:
            True if login successful, False otherwise.
        
        Raises:
            AuthenticationError: If authentication fails.
            ConnectionError: If connection to WhatsApp fails.
        """
        if not self.credentials or not self.credentials.get("login_token"):
            logger.error("No login credentials available")
            raise AuthenticationError("No login credentials available")
        
        # Check if credentials are expired
        if self.credentials.get("expiration", 0) < int(time.time()):
            logger.error("Login credentials have expired, re-registration required")
            raise AuthenticationError("Login credentials have expired, re-registration required")
        
        # WhatsApp login endpoint
        login_server = self.credentials.get("chat_dns_domain", WA_SERVER)
        url = f"https://{login_server}/v1/login"
        
        data = {
            "credentials": self.credentials.get("login_token"),
            "device_id": self.client_id,
            "protocol_version": PROTOCOL_VERSION
        }
        
        try:
            response = requests.post(url, json=data, timeout=LOGIN_TIMEOUT)
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "ok":
                self.session = {
                    "session_id": result.get("session_id"),
                    "session_key": result.get("session_key"),
                    "server_id": result.get("server_id", ""),
                    "expiration": int(time.time()) + result.get("ttl", 3600)  # Default to 1 hour
                }
                
                # Update credentials with any new information
                if result.get("refresh_token"):
                    self.credentials["login_token"] = result.get("refresh_token")
                    self.credentials["expiration"] = int(time.time()) + result.get("refresh_ttl", 31536000)
                    self.config.save_credentials(self.credentials)
                
                self.authenticated = True
                logger.info("Login successful")
                return True
            else:
                error = result.get("reason", "Unknown error")
                
                # Check for "bad_param" error which is the improved version of "bad_baram"
                if error == "bad_param":
                    details = result.get("param_name", "unknown parameter")
                    raise BadParamError(f"Invalid parameter: {details}")
                    
                logger.error(f"Login failed: {error}")
                raise AuthenticationError(f"Login failed: {error}")
                
        except requests.RequestException as e:
            logger.error(f"Login request failed: {str(e)}")
            raise ConnectionError(f"Login request failed: {str(e)}")
    
    def refresh_session(self) -> bool:
        """
        Refresh the current session.
        
        Returns:
            True if refresh successful, False otherwise.
        """
        # Check if we need to refresh
        if self.session and self.session.get("expiration", 0) > int(time.time()) + 300:
            # Still valid for more than 5 minutes
            return True
            
        logger.debug("Refreshing WhatsApp session")
        return self.login()
    
    def logout(self) -> bool:
        """
        Logout from WhatsApp.
        
        Returns:
            True if logout successful, False otherwise.
        """
        if not self.authenticated or not self.session:
            logger.debug("Not logged in, nothing to logout from")
            return True
            
        # WhatsApp logout endpoint
        login_server = self.credentials.get("chat_dns_domain", WA_SERVER)
        url = f"https://{login_server}/v1/logout"
        
        data = {
            "session_id": self.session.get("session_id")
        }
        
        try:
            response = requests.post(url, json=data, timeout=self.config.get("request_timeout", 15))
            response.raise_for_status()
            
            self.authenticated = False
            self.session = None
            logger.info("Logout successful")
            return True
                
        except requests.RequestException as e:
            logger.warning(f"Logout request failed: {str(e)}")
            # Still mark as logged out locally even if request fails
            self.authenticated = False
            self.session = None
            return False
    
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated.
        
        Returns:
            True if authenticated, False otherwise.
        """
        if not self.authenticated or not self.session:
            return False
            
        # Check if session is expired
        if self.session.get("expiration", 0) < int(time.time()):
            self.authenticated = False
            return False
            
        return True
        
    def get_session(self) -> Dict[str, Any]:
        """
        Get the current session data.
        
        Returns:
            Session data dictionary.
        """
        return self.session or {}
    
    def _generate_registration_token(self) -> str:
        """
        Generate a token for registration.
        
        Returns:
            A registration token.
        """
        # In a real implementation, this would follow WhatsApp's token generation algorithm
        # For now, we'll use a simple random token
        token_bytes = os.urandom(16)
        return base64.b64encode(token_bytes).decode('utf-8')
    
    def _extract_country_code(self, phone_number: str) -> str:
        """
        Extract country code from a phone number.
        
        Args:
            phone_number: The phone number.
            
        Returns:
            Country code as string.
        """
        # Simple extraction - in a real implementation, this would be more robust
        phone_number = phone_number.strip().replace('+', '')
        
        # Attempt to extract country code
        if phone_number.startswith('1'):  # US/Canada
            return '1'
        elif phone_number.startswith('44'):  # UK
            return '44'
        elif phone_number.startswith('91'):  # India
            return '91'
        elif phone_number.startswith('33'):  # France
            return '33'
        elif phone_number.startswith('49'):  # Germany
            return '49'
        elif phone_number.startswith('55'):  # Brazil
            return '55'
        elif phone_number.startswith('52'):  # Mexico
            return '52'
        elif phone_number.startswith('34'):  # Spain
            return '34'
        elif phone_number.startswith('39'):  # Italy
            return '39'
        elif phone_number.startswith('7'):  # Russia
            return '7'
        # Default to US if unrecognized
        return '1'
    
    def _extract_phone_number(self, phone_number: str) -> str:
        """
        Extract the local phone number without country code.
        
        Args:
            phone_number: The full phone number.
            
        Returns:
            Local phone number without country code.
        """
        # Simple extraction - in a real implementation, this would be more robust
        country_code = self._extract_country_code(phone_number)
        phone_number = phone_number.strip().replace('+', '')
        
        if phone_number.startswith(country_code):
            return phone_number[len(country_code):]
        
        return phone_number
