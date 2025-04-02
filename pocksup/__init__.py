"""
Pocksup - A modern Python library for WhatsApp connectivity.

Provides a robust implementation for connecting to WhatsApp,
sending/receiving messages, managing contacts, and more.

Designed with strong error handling and compatibility with
the latest WhatsApp protocol.
"""

from pocksup.version import __version__
from pocksup.client import PocksupClient
from pocksup.exceptions import (
    PocksupException,
    AuthenticationError,
    ConnectionError,
    ProtocolError,
    MediaError
)
from pocksup.messages import Message, TextMessage, MediaMessage
from pocksup.auth import Auth

__all__ = [
    '__version__',
    'PocksupClient',
    'PocksupException',
    'AuthenticationError',
    'ConnectionError',
    'ProtocolError',
    'MediaError',
    'Message',
    'TextMessage',
    'MediaMessage',
    'Auth'
]
