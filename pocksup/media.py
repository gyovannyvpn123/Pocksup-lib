"""
Media handling module for the pocksup library.

Handles media upload, download, and processing.
"""

import os
import time
import logging
import hashlib
import requests
import mimetypes
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO, Tuple, Union

from pocksup.config import Config
from pocksup.auth import Auth
from pocksup.constants import WA_SERVER
from pocksup.exceptions import MediaError
from pocksup.utils import get_mime_type, get_file_size, retry_with_backoff

logger = logging.getLogger(__name__)

class MediaUploader:
    """
    Handles media uploads to WhatsApp servers.
    """
    
    def __init__(self, config: Config, auth: Auth):
        """
        Initialize the media uploader.
        
        Args:
            config: Configuration instance.
            auth: Authentication handler.
        """
        self.config = config
        self.auth = auth
        
    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """
        Upload a file to WhatsApp servers.
        
        Args:
            file_path: Path to the file to upload.
            
        Returns:
            Dictionary with upload details (url, file_hash, etc.).
            
        Raises:
            MediaError: If upload fails.
            FileNotFoundError: If file doesn't exist.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        # Get file details
        file_size = get_file_size(file_path)
        file_name = os.path.basename(file_path)
        mime_type = get_mime_type(file_path)
        
        # Calculate file hash for verification
        file_hash = self._calculate_file_hash(file_path)
        
        # Ensure we're authenticated
        if not self.auth.is_authenticated():
            logger.debug("Not authenticated, performing login")
            self.auth.login()
            
        # Get session data
        session = self.auth.get_session()
        if not session:
            raise MediaError("No valid session for media upload")
        
        # Get upload server
        upload_server = self.auth.credentials.get("media_server", WA_SERVER)
        
        # Build upload URL
        upload_url = f"https://{upload_server}/v1/media/upload"
        
        # Setup request headers
        headers = {
            "User-Agent": self.config.get("user_agent", "Pocksup/0.1.0"),
            "X-WA-Session": session.get("session_id", ""),
            "X-WA-Client": self.auth.client_id,
            "Content-Type": "multipart/form-data"
        }
        
        try:
            # Prepare upload data
            files = {'file': (file_name, open(file_path, 'rb'), mime_type)}
            
            data = {
                "hash": file_hash,
                "type": mime_type,
                "size": file_size
            }
            
            # Make upload request
            response = requests.post(
                upload_url, 
                headers=headers, 
                files=files, 
                data=data, 
                timeout=self.config.get("request_timeout", 60)
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("status") == "ok":
                logger.info(f"Successfully uploaded file: {file_name} ({file_size} bytes)")
                
                # Add local file info
                result["local_path"] = file_path
                result["file_name"] = file_name
                result["mime_type"] = mime_type
                result["file_size"] = file_size
                
                return result
            else:
                error = result.get("reason", "Unknown error")
                logger.error(f"Media upload failed: {error}")
                raise MediaError(f"Media upload failed: {error}")
                
        except requests.RequestException as e:
            logger.error(f"Media upload request failed: {str(e)}")
            raise MediaError(f"Media upload request failed: {str(e)}")
            
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate file hash for verification.
        
        Args:
            file_path: Path to the file.
            
        Returns:
            File hash as a hex string.
        """
        # Use SHA-256 hash
        sha256_hash = hashlib.sha256()
        
        # Read file in chunks to handle large files
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
                
        return sha256_hash.hexdigest()


class MediaDownloader:
    """
    Handles media downloads from WhatsApp servers.
    """
    
    def __init__(self, config: Config, auth: Auth):
        """
        Initialize the media downloader.
        
        Args:
            config: Configuration instance.
            auth: Authentication handler.
        """
        self.config = config
        self.auth = auth
        self.media_path = self.config.get("media_path", "./media")
        
        # Ensure media directory exists
        os.makedirs(self.media_path, exist_ok=True)
        
    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def download_file(self, url: str, file_name: Optional[str] = None) -> str:
        """
        Download a file from WhatsApp servers.
        
        Args:
            url: URL of the file to download.
            file_name: Optional file name to save as.
            
        Returns:
            Path to the downloaded file.
            
        Raises:
            MediaError: If download fails.
        """
        # Ensure we're authenticated
        if not self.auth.is_authenticated():
            logger.debug("Not authenticated, performing login")
            self.auth.login()
            
        # Get session data
        session = self.auth.get_session()
        if not session:
            raise MediaError("No valid session for media download")
        
        # Generate file name if not provided
        if not file_name:
            timestamp = int(time.time())
            # Extract extension from URL if possible
            extension = os.path.splitext(url.split('?')[0])[1]
            if not extension:
                extension = '.dat'  # Default extension
            file_name = f"media_{timestamp}{extension}"
            
        # Full path to save file
        file_path = os.path.join(self.media_path, file_name)
        
        # Setup request headers
        headers = {
            "User-Agent": self.config.get("user_agent", "Pocksup/0.1.0"),
            "X-WA-Session": session.get("session_id", ""),
            "X-WA-Client": self.auth.client_id
        }
        
        try:
            # Make download request with streaming
            response = requests.get(
                url, 
                headers=headers, 
                stream=True, 
                timeout=self.config.get("request_timeout", 60)
            )
            
            response.raise_for_status()
            
            # Get file size if available
            file_size = int(response.headers.get('content-length', 0))
            
            # Save the file
            with open(file_path, 'wb') as f:
                downloaded = 0
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress for large files
                        if file_size > 1024*1024 and downloaded % (1024*1024) == 0:  # Log every MB
                            logger.debug(f"Downloaded {downloaded / (1024*1024):.1f} MB of {file_size / (1024*1024):.1f} MB")
            
            logger.info(f"Successfully downloaded file to: {file_path} ({file_size} bytes)")
            return file_path
                
        except requests.RequestException as e:
            logger.error(f"Media download request failed: {str(e)}")
            raise MediaError(f"Media download request failed: {str(e)}")


class MediaManager:
    """
    Manages media operations for pocksup.
    """
    
    def __init__(self, config: Config, auth: Auth):
        """
        Initialize the media manager.
        
        Args:
            config: Configuration instance.
            auth: Authentication handler.
        """
        self.config = config
        self.auth = auth
        self.uploader = MediaUploader(config, auth)
        self.downloader = MediaDownloader(config, auth)
        
    def upload(self, file_path: str) -> Dict[str, Any]:
        """
        Upload a file to WhatsApp servers.
        
        Args:
            file_path: Path to the file to upload.
            
        Returns:
            Dictionary with upload details.
        """
        return self.uploader.upload_file(file_path)
        
    def download(self, url: str, file_name: Optional[str] = None) -> str:
        """
        Download a file from WhatsApp servers.
        
        Args:
            url: URL of the file to download.
            file_name: Optional file name to save as.
            
        Returns:
            Path to the downloaded file.
        """
        return self.downloader.download_file(url, file_name)
