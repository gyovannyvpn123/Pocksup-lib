# Pocksup - Modern WhatsApp Library for Python

Pocksup is a robust and modern Python library for connecting to WhatsApp, similar to the legendary yowsup library but with improved error handling and protocol compatibility for 2025 and beyond. Through reverse engineering of the WhatsApp protocol, Pocksup provides a secure and reliable way to interact with WhatsApp services.

## Features

- 💬 Send and receive text messages
- 📸 Send and receive media files (images, videos, audio, documents)
- 👥 Full support for group chats
- 📋 Contact management
- 🛡️ Enhanced error handling (avoids "bad_baram" error that plagued yowsup)
- 🧬 Clean and well-documented API
- 🌐 RESTful web interface
- 🔐 End-to-end encryption support
- 📱 Comprehensive protocol implementation

## Installation

```bash
pip install pocksup
```

## Quick Start

### Using the Python API

```python
from pocksup.client import PocksupClient

# Create client instance
client = PocksupClient()

# Connect to WhatsApp
client.connect()

# Send a text message
client.send_text_message("1234567890", "Hello from Pocksup!")

# Send a media message
client.send_media_message("1234567890", "/path/to/image.jpg", "Check this out!")

# Create a group
group_id = client.create_group("My Group", ["1234567890", "9876543210"])

# Disconnect
client.disconnect()
```

### Using the Command Line Interface

Pocksup comes with three command-line utilities:

#### Chat Client

```bash
# Start the chat client
pocksup-chat

# With debug logging
pocksup-chat --debug

# With custom config
pocksup-chat --config /path/to/config.json
```

#### Media Sender

```bash
# Send a media file
pocksup-media --recipient 1234567890 --file /path/to/image.jpg --caption "Check this out!"

# Send to multiple recipients
pocksup-media --recipient 1234567890,9876543210 --file /path/to/image.jpg --bulk
```

#### Web API

```bash
# Start the Web API
pocksup-api

# With custom host and port
pocksup-api --host 127.0.0.1 --port 8000

# With debug mode
pocksup-api --debug
```

## API Documentation

### Client Methods

- `connect()` - Connect to WhatsApp
- `disconnect()` - Disconnect from WhatsApp
- `register(phone_number, method)` - Register a phone number
- `verify_code(phone_number, code)` - Verify a registration code
- `send_text_message(recipient, text, quoted_message_id)` - Send a text message
- `send_media_message(recipient, file_path, caption)` - Send a media message
- `send_location_message(recipient, latitude, longitude, name)` - Send a location
- `send_contact_message(recipient, contacts)` - Send contact information
- `download_media(url, file_name)` - Download media from a message
- `create_group(subject, participants)` - Create a new group
- `add_group_participants(group_id, participants)` - Add participants to a group
- `remove_group_participants(group_id, participants)` - Remove participants from a group
- `leave_group(group_id)` - Leave a group
- `set_group_subject(group_id, subject)` - Set a group's subject
- `set_presence(presence_type)` - Set presence status
- `set_chat_state(recipient, state)` - Set chat state (typing, etc.)

### Event Handlers

```python
# Register a message handler
client.register_message_handler(callback_function, message_type)

# Register an event handler
client.register_event_handler(callback_function, event_type)

# Register a status handler
client.register_status_handler(callback_function, status_type)
```

## Web API

The Pocksup Web API provides a RESTful interface to the library's functionality.

### Endpoints

- `/api/auth/register` - Register a phone number
- `/api/auth/verify` - Verify a registration code
- `/api/auth/login` - Login using saved credentials
- `/api/auth/logout` - Logout from WhatsApp
- `/api/connection/status` - Get connection status
- `/api/connection/connect` - Connect to WhatsApp
- `/api/connection/disconnect` - Disconnect from WhatsApp
- `/api/messages/send/text` - Send a text message
- `/api/messages/send/media` - Send a media message
- `/api/messages/send/location` - Send a location message
- `/api/messages/send/contact` - Send a contact message
- `/api/media/download` - Download media from a URL
- `/api/groups/create` - Create a new group
- `/api/groups/add` - Add participants to a group
- `/api/groups/remove` - Remove participants from a group
- `/api/groups/leave` - Leave a group
- `/api/groups/subject` - Set a group's subject
- `/api/presence/set` - Set presence status
- `/api/chat/state` - Set chat state

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

* Inspired by the original yowsup library
* Uses reverse engineering of the WhatsApp protocol for compatibility in 2025 and beyond
