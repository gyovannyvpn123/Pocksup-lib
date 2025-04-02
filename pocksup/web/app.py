"""
Flask application for pocksup web API.
"""

import os
import logging
from typing import Dict, Any, Optional
from flask import Flask, jsonify, render_template, redirect, url_for, request, flash, Response

from pocksup.client import PocksupClient
from pocksup.web.api import PocksupAPI

logger = logging.getLogger(__name__)

def create_app(client: Optional[PocksupClient] = None, config_path: Optional[str] = None) -> Flask:
    """
    Create a Flask application for the pocksup web API.
    
    Args:
        client: Optional PocksupClient instance.
        config_path: Path to configuration file if creating a new client.
        
    Returns:
        Flask application.
    """
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24).hex())
    
    # Configure basic logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Create client if not provided
    if not client:
        client = PocksupClient(config_path)
    
    # Create and register API
    api = PocksupAPI(client)
    api.register_with_app(app)
    
    # Home route
    @app.route('/')
    def home():
        is_connected = client.connection.connected
        is_authenticated = client.auth.is_authenticated()
        
        return render_template(
            'index.html',
            connected=is_connected,
            authenticated=is_authenticated
        )
    
    # Health check route
    @app.route('/health')
    def health():
        return jsonify({
            'status': 'ok',
            'version': client.config.get('version', '0.1.0')
        })
    
    # Return the app
    return app

# Helper function to run the app directly
def run_app(host: str = '0.0.0.0', port: int = 5000, debug: bool = True, 
            config_path: Optional[str] = None) -> None:
    """
    Run the Flask application.
    
    Args:
        host: Host to bind to.
        port: Port to bind to.
        debug: Whether to enable debug mode.
        config_path: Path to configuration file.
    """
    app = create_app(config_path=config_path)
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_app()
