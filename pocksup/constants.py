"""
Constants used throughout the pocksup library.
"""

# WhatsApp connection constants
WA_SERVER = "e.whatsapp.net"
WA_PORT = 443

# Protocol versions
PROTOCOL_VERSION = "2.2410.0"
CLIENT_VERSION = "2.2410.0"

# Authentication constants
LOGIN_TIMEOUT = 30  # seconds
CONN_TIMEOUT = 15  # seconds
RETRY_MAX = 3

# Message types
MESSAGE_TYPE_TEXT = 0
MESSAGE_TYPE_MEDIA = 1
MESSAGE_TYPE_LOCATION = 2
MESSAGE_TYPE_CONTACT = 3

# Media types
MEDIA_TYPE_IMAGE = 1
MEDIA_TYPE_VIDEO = 2
MEDIA_TYPE_AUDIO = 3
MEDIA_TYPE_DOCUMENT = 4
MEDIA_TYPE_STICKER = 5

# Group chat constants
GROUP_CREATE = "create"
GROUP_LEAVE = "leave"
GROUP_ADD = "add"
GROUP_REMOVE = "remove"
GROUP_SUBJECT = "subject"
GROUP_DESCRIPTION = "description"
GROUP_PICTURE = "picture"
GROUP_ADMIN = "admin"

# Status constants
STATUS_ONLINE = "available"
STATUS_OFFLINE = "unavailable"
STATUS_TYPING = "composing"
STATUS_RECORDING = "recording"
STATUS_PAUSED = "paused"

# Security constants
ENCRYPTION_ALGORITHM = "AES-256-CBC"
HASH_ALGORITHM = "SHA-256"
KEY_LENGTH = 32
