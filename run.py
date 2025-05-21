#!/usr/bin/env python3
"""
Entry point for the Blackbox Target Manager application.
"""
from app import create_app

# Create the Flask application
app = create_app()

if __name__ == '__main__':
    # Run the application
    app.run(host='0.0.0.0', port=80, debug=True)