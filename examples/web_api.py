#!/usr/bin/env python
"""
Example web API using pocksup.

This script demonstrates how to run the pocksup web API
as a standalone service.
"""

import os
import sys
import argparse
import logging
from typing import Optional

# Add parent directory to path to allow importing pocksup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pocksup.web.app import create_app, run_app
from pocksup.client import PocksupClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Pocksup Web API')
    parser.add_argument('--config', '-c', help='Path to configuration file')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', '-p', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode')
    parser.add_argument('--no-auto-connect', action='store_true', help='Do not automatically connect to WhatsApp')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create client
    client = PocksupClient(args.config)
    
    # Try to connect if credentials are available and auto-connect is enabled
    if not args.no_auto_connect:
        try:
            if client.auth.is_authenticated():
                logger.info("Connecting to WhatsApp...")
                client.connect()
                logger.info("Connected to WhatsApp successfully!")
            else:
                logger.info("No valid credentials found. Please use the API to register and connect.")
        except Exception as e:
            logger.error(f"Error connecting to WhatsApp: {str(e)}")
            logger.info("You can still use the API to authenticate and connect.")
    
    # Run the web API
    logger.info(f"Starting pocksup web API on {args.host}:{args.port}...")
    run_app(host=args.host, port=args.port, debug=args.debug, config_path=args.config)

if __name__ == '__main__':
    main()
