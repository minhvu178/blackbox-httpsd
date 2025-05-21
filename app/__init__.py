"""
Initialize the Flask application.
"""
import os
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from .config import config

# Initialize extensions
db = SQLAlchemy()

def create_app(config_name=None):
    """Create and configure the Flask application."""
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    app.config.from_object(config[config_name])
    
    # Initialize extensions with app
    db.init_app(app)
    
    with app.app_context():
        # Register blueprints
        from .routes.main import main
        from .routes.api import api
        from .routes.prometheus import prometheus
        
        app.register_blueprint(main)
        app.register_blueprint(api, url_prefix='/api')
        app.register_blueprint(prometheus, url_prefix='/api/sd')
        
        # Create database tables
        db.create_all()
        
        # Initialize default data
        from .models.probe import init_default_probes
        init_default_probes()
        
        @app.after_request
        def add_header(response):
            """Ensure API responses have the correct content type header"""
            if request.path.startswith('/api/'):
                # Only modify if it's an API endpoint
                if not response.headers.get('Content-Type'):
                    # Set Content-Type for API responses if not already set
                    response.headers['Content-Type'] = 'application/json'
            return response
    
    return app

# Import models to ensure they are registered with SQLAlchemy
from .models import probe, target