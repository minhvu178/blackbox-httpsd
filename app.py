from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blackbox_targets.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Shared base model for common fields
class BaseTarget(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    team = db.Column(db.String(50), nullable=False)
    region = db.Column(db.String(50), nullable=False)
    assignees = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class HttpTarget(BaseTarget):
    __tablename__ = 'http_targets'
    
    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'module': self.module,
            'team': self.team,
            'region': self.region,
            'assignees': self.assignees,
            'address': self.address,
            'enabled': self.enabled,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class IcmpTarget(BaseTarget):
    __tablename__ = 'icmp_targets'
    
    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'module': self.module,
            'team': self.team,
            'region': self.region,
            'assignees': self.assignees,
            'address': self.address,
            'enabled': self.enabled,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class TcpTarget(BaseTarget):
    __tablename__ = 'tcp_targets'
    port = db.Column(db.Integer, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'module': self.module,
            'team': self.team,
            'region': self.region,
            'assignees': self.assignees,
            'address': self.address,
            'enabled': self.enabled,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None,
            'port': self.port
        }

# Create all tables
with app.app_context():
    db.create_all()

# Helper function to get the model based on protocol
def get_model(protocol):
    return {
        'http': HttpTarget,
        'icmp': IcmpTarget,
        'tcp': TcpTarget
    }.get(protocol.lower())

# Main page
@app.route('/')
def index():
    return render_template('index.html')

# API to get all targets for a protocol
@app.route('/api/targets/<protocol>', methods=['GET'])
def get_targets(protocol):
    model = get_model(protocol)
    if model is None:
        return jsonify({'error': 'Unsupported protocol'}), 400
        
    # Get all targets, filter by enabled status if requested
    enabled = request.args.get('enabled')
    if enabled is not None:
        enabled = enabled.lower() == 'true'
        entries = model.query.filter_by(enabled=enabled).all()
    else:
        entries = model.query.all()
    
    # Format in Prometheus file_sd_config format
    result = []
    for entry in entries:
        item = {
            "targets": [entry.address if protocol != 'tcp' else f"{entry.address}:{entry.port}"],
            "labels": {
                "id": str(entry.id),
                "hostname": entry.hostname,
                "module": entry.module,
                "team": entry.team,
                "region": entry.region,
                "assignees": entry.assignees,
                "enabled": str(entry.enabled).lower()
            }
        }
        result.append(item)
    
    return jsonify(result)

# API to get all targets with full details
@app.route('/api/targets/<protocol>/details', methods=['GET'])
def get_targets_details(protocol):
    model = get_model(protocol)
    if model is None:
        return jsonify({'error': 'Unsupported protocol'}), 400
        
    entries = model.query.all()
    result = [entry.to_dict() for entry in entries]
    return jsonify(result)

# API to get a specific target
@app.route('/api/targets/<protocol>/<int:entry_id>', methods=['GET'])
def get_target(protocol, entry_id):
    model = get_model(protocol)
    if model is None:
        return jsonify({'error': 'Unsupported protocol'}), 400
        
    entry = model.query.get(entry_id)
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404
        
    return jsonify(entry.to_dict())

# API to add a new target
@app.route('/api/targets/<protocol>', methods=['POST'])
def add_target(protocol):
    model = get_model(protocol)
    if model is None:
        return jsonify({'error': 'Unsupported protocol'}), 400
    
    try:
        data = request.json
        
        # Basic validation
        required_fields = ['hostname', 'module', 'team', 'region', 'assignees', 'address']
        
        # Add protocol-specific required fields
        if protocol == 'tcp':
            required_fields.append('port')
        
        # Check for missing fields
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create new entry
        entry = model(**data)
        db.session.add(entry)
        db.session.commit()
        
        return jsonify({"status": "success", "id": entry.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API to update a target
@app.route('/api/targets/<protocol>/<int:entry_id>', methods=['PUT'])
def update_target(protocol, entry_id):
    model = get_model(protocol)
    if model is None:
        return jsonify({'error': 'Unsupported protocol'}), 400
    
    try:
        entry = model.query.get(entry_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404
        
        data = request.json
        
        # Update fields
        for key, value in data.items():
            if hasattr(entry, key):
                setattr(entry, key, value)
        
        db.session.commit()
        return jsonify({'status': 'updated', 'id': entry.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API to delete a target
@app.route('/api/targets/<protocol>/<int:entry_id>', methods=['DELETE'])
def delete_target(protocol, entry_id):
    model = get_model(protocol)
    if model is None:
        return jsonify({'error': 'Unsupported protocol'}), 400
    
    try:
        entry = model.query.get(entry_id)
        if not entry:
            return jsonify({'error': 'Entry not found'}), 404
        
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'status': 'deleted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API to update the enabled status for multiple targets
@app.route('/api/targets/batch/status', methods=['PUT'])
def batch_update_status():
    try:
        data = request.json
        if not data or 'targets' not in data or 'enabled' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        targets = data['targets']
        enabled = data['enabled']
        
        updated_count = 0
        
        for target in targets:
            if 'protocol' not in target or 'id' not in target:
                continue
                
            model = get_model(target['protocol'])
            if not model:
                continue
                
            entry = model.query.get(target['id'])
            if not entry:
                continue
                
            entry.enabled = enabled
            updated_count += 1
        
        db.session.commit()
        return jsonify({'status': 'updated', 'count': updated_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API to delete multiple targets
@app.route('/api/targets/batch/delete', methods=['DELETE'])
def batch_delete():
    try:
        data = request.json
        if not data or 'targets' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        targets = data['targets']
        deleted_count = 0
        
        for target in targets:
            if 'protocol' not in target or 'id' not in target:
                continue
                
            model = get_model(target['protocol'])
            if not model:
                continue
                
            entry = model.query.get(target['id'])
            if not entry:
                continue
                
            db.session.delete(entry)
            deleted_count += 1
        
        db.session.commit()
        return jsonify({'status': 'deleted', 'count': deleted_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API to export all targets in prometheus format
@app.route('/api/export/prometheus', methods=['GET'])
def export_prometheus():
    protocols = ['http', 'icmp', 'tcp']
    all_targets = {}
    
    for protocol in protocols:
        model = get_model(protocol)
        entries = model.query.filter_by(enabled=True).all()
        
        targets = []
        for entry in entries:
            target_address = entry.address
            if protocol == 'tcp':
                target_address = f"{entry.address}:{entry.port}"
            
            target_data = {
                "targets": [target_address],
                "labels": {
                    "hostname": entry.hostname,
                    "module": entry.module,
                    "team": entry.team,
                    "region": entry.region,
                    "assignees": entry.assignees,
                    "job": f"blackbox_{protocol}"
                }
            }
            targets.append(target_data)
        
        all_targets[protocol] = targets
    
    return jsonify(all_targets)

if __name__ == '__main__':
    # Make sure templates directory exists
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create a basic index.html file if it doesn't exist
    index_path = os.path.join('templates', 'index.html')
    if not os.path.exists(index_path):
        with open(index_path, 'w') as f:
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Blackbox Target Manager</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                    }
                    h1 {
                        color: #333;
                    }
                </style>
            </head>
            <body>
                <h1>Welcome to Blackbox Target Manager</h1>
                <p>Loading application...</p>
                <script>
                    window.location.href = '/static/index.html';
                </script>
            </body>
            </html>
            """)
    
    # Create static directory for front-end files
    if not os.path.exists('static'):
        os.makedirs('static')
        
    app.run(host='0.0.0.0', port=5000, debug=True)
