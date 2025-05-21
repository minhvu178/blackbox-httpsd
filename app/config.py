"""
Configuration settings for the Flask application.
"""
import os

class Config:
    """Base configuration class"""
    # SQLAlchemy settings
    SQLALCHEMY_DATABASE_URI = 'sqlite:///blackbox_monitoring.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Application settings
    DEBUG = True
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    
class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    
class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test_blackbox_monitoring.db'
    
class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    # Use environment variables for sensitive information in production
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///blackbox_monitoring.db'
    SECRET_KEY = os.environ.get('SECRET_KEY')

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}