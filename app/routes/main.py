"""
Main routes for the frontend.
"""
from flask import Blueprint, render_template, send_from_directory

# Create a Blueprint
main = Blueprint('main', __name__)

@main.route('/')
def index():
    """Main page route"""
    return render_template('index.html')

@main.route('/static/<path:path>')
def send_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

@main.route('/static/modernUI.html')
def modern_ui():
    """Modern UI route"""
    return send_from_directory('static', 'index.html')

@main.route('/<path:path>')
def catch_all(path):
    """Fallback route for SPA (Single Page Application)"""
    return render_template('index.html')