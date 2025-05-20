from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_, and_, text, func
import re
from datetime import datetime
import os
import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blackbox_monitoring.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Association table for targets and probes (many-to-many relationship)
target_probes = db.Table('target_probes',
    db.Column('target_id', db.Integer, db.ForeignKey('targets.id'), primary_key=True),
    db.Column('probe_id', db.Integer, db.ForeignKey('probes.id'), primary_key=True)
)

class Probe(db.Model):
    """Model for monitoring probes that perform checks"""
    __tablename__ = 'probes'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)  # e.g., "Singapore", "USA", "KOREA"
    provider = db.Column(db.String(100), nullable=False)  # e.g., "Viettel", "FCI", "CMC"
    ip_address = db.Column(db.String(50), nullable=False)
    enabled = db.Column(db.Boolean, default=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'provider': self.provider,
            'ip_address': self.ip_address,
            'enabled': self.enabled,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

class Target(db.Model):
    """Model for target endpoints to be monitored"""
    __tablename__ = 'targets'
    
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    region = db.Column(db.String(100), nullable=False)
    zone = db.Column(db.String(100), nullable=False)
    probe_type = db.Column(db.String(50), nullable=False)  # HTTP, ICMP, TCP, etc.
    assignees = db.Column(db.String(200), nullable=False)  # Comma-separated list
    enabled = db.Column(db.Boolean, default=True)
    port = db.Column(db.Integer)  # Optional for TCP
    protocol = db.Column(db.String(10))  # http, https, etc.
    path = db.Column(db.String(255))  # URL path for HTTP
    expect_status_code = db.Column(db.String(20))  # Expected status code(s) for HTTP
    timeout = db.Column(db.Integer, default=10)  # Timeout in seconds
    last_status = db.Column(db.String(20))  # UP, DOWN, UNKNOWN
    last_status_code = db.Column(db.String(20))  # HTTP status code or error code
    last_check = db.Column(db.DateTime)  # Time of last check
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Many-to-many relationship with probes
    probes = db.relationship('Probe', secondary=target_probes, lazy='subquery',
                             backref=db.backref('targets', lazy=True))
    
    def to_dict(self, include_probes=False):
        result = {
            'id': self.id,
            'hostname': self.hostname,
            'address': self.address,
            'region': self.region,
            'zone': self.zone,
            'probe_type': self.probe_type,
            'assignees': self.assignees,
            'enabled': self.enabled,
            'port': self.port,
            'protocol': self.protocol,
            'path': self.path,
            'expect_status_code': self.expect_status_code,
            'timeout': self.timeout,
            'last_status': self.last_status,
            'last_status_code': self.last_status_code,
            'last_check': self.last_check.isoformat() if self.last_check else None,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }
        
        if include_probes:
            result['probes'] = [probe.to_dict() for probe in self.probes]
            
        return result

# Create all tables
with app.app_context():
    db.create_all()
    
    # Add default probe if the table is empty
    if Probe.query.count() == 0:
        default_probes = [
            Probe(
                name="Singapore Probe",
                location="Singapore",
                provider="Viettel",
                ip_address="192.168.1.100",
                enabled=True
            ),
            Probe(
                name="USA Probe",
                location="USA",
                provider="FCI",
                ip_address="192.168.1.101",
                enabled=True
            ),
            Probe(
                name="Korea Probe",
                location="KOREA",
                provider="CMC",
                ip_address="192.168.1.102",
                enabled=True
            )
        ]
        db.session.add_all(default_probes)
        db.session.commit()

# Helper functions for search query parsing
def parse_search_query(query_string):
    """Parse Splunk-like search queries like 'hostname=example.com region=US-East status=enabled'"""
    if not query_string:
        return {}
    
    conditions = {}
    # Handle quoted values (for spaces in values)
    pattern = r'(\w+)=(?:"([^"]*)"|([^ ]*))'
    
    matches = re.findall(pattern, query_string)
    for match in matches:
        field = match[0]
        # Use quoted value if it exists, otherwise use the unquoted value
        value = match[1] if match[1] else match[2]
        conditions[field] = value
    
    return conditions

def build_filter_conditions(parsed_query):
    """Convert parsed query dict to SQLAlchemy filter conditions"""
    conditions = []
    
    for field, value in parsed_query.items():
        if field == 'enabled' and value.lower() in ('true', 'false'):
            conditions.append(Target.enabled == (value.lower() == 'true'))
        elif hasattr(Target, field):
            # Handle wildcard searches with %
            if '*' in value:
                value = value.replace('*', '%')
                conditions.append(getattr(Target, field).like(value))
            else:
                conditions.append(getattr(Target, field) == value)
    
    return conditions

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/static/<path:path>')
def send_static(path):
    return app.send_static_file(path)

# Add specific route for modernUI.html
@app.route('/static/modernUI.html')
def modern_ui():
    return app.send_static_file('index.html')
    
# Fallback route for SPA (Single Page Application)
@app.route('/<path:path>')
def catch_all(path):
    return render_template('index.html')

# API Routes
@app.route('/api/targets', methods=['GET'])
def get_targets():
    # Handle search query
    search_query = request.args.get('q', '')
    include_probes = request.args.get('include_probes', 'false').lower() == 'true'
    
    if search_query:
        parsed_query = parse_search_query(search_query)
        conditions = build_filter_conditions(parsed_query)
        
        if conditions:
            targets = Target.query.filter(and_(*conditions)).all()
        else:
            # For free-text search without field specifications
            search_terms = search_query.split()
            query = Target.query
            
            for term in search_terms:
                if term:
                    search_condition = or_(
                        Target.hostname.contains(term),
                        Target.region.contains(term),
                        Target.zone.contains(term),
                        Target.probe_type.contains(term),
                        Target.assignees.contains(term),
                        Target.last_status.contains(term)
                    )
                    query = query.filter(search_condition)
            
            targets = query.all()
    else:
        targets = Target.query.all()
    
    return jsonify([target.to_dict(include_probes=include_probes) for target in targets])

@app.route('/api/targets/<int:target_id>', methods=['GET'])
def get_target(target_id):
    target = Target.query.get_or_404(target_id)
    include_probes = request.args.get('include_probes', 'false').lower() == 'true'
    return jsonify(target.to_dict(include_probes=include_probes))

@app.route('/api/targets', methods=['POST'])
def create_target():
    data = request.json
    
    # Validation
    required_fields = ['hostname', 'address', 'region', 'zone', 'probe_type', 'assignees']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    # Create new target
    new_target = Target(
        hostname=data['hostname'],
        address=data['address'],
        region=data['region'],
        zone=data['zone'],
        probe_type=data['probe_type'],
        assignees=data['assignees'],
        enabled=data.get('enabled', True),
        port=data.get('port'),
        protocol=data.get('protocol'),
        path=data.get('path'),
        expect_status_code=data.get('expect_status_code'),
        timeout=data.get('timeout', 10)
    )
    
    # Add associated probes if provided
    if 'probe_ids' in data and isinstance(data['probe_ids'], list):
        for probe_id in data['probe_ids']:
            probe = Probe.query.get(probe_id)
            if probe:
                new_target.probes.append(probe)
    
    db.session.add(new_target)
    db.session.commit()
    
    return jsonify({'message': 'Target created successfully', 'id': new_target.id}), 201

@app.route('/api/targets/<int:target_id>', methods=['PUT'])
def update_target(target_id):
    target = Target.query.get_or_404(target_id)
    data = request.json
    
    # Update target fields
    for field in ['hostname', 'address', 'region', 'zone', 'probe_type', 'assignees', 
                  'enabled', 'port', 'protocol', 'path', 'expect_status_code', 'timeout']:
        if field in data:
            setattr(target, field, data[field])
    
    # Update associated probes if provided
    if 'probe_ids' in data and isinstance(data['probe_ids'], list):
        # Clear existing associations
        target.probes = []
        
        # Add new associations
        for probe_id in data['probe_ids']:
            probe = Probe.query.get(probe_id)
            if probe:
                target.probes.append(probe)
    
    db.session.commit()
    
    return jsonify({'message': 'Target updated successfully'})

@app.route('/api/targets/<int:target_id>', methods=['DELETE'])
def delete_target(target_id):
    target = Target.query.get_or_404(target_id)
    db.session.delete(target)
    db.session.commit()
    
    return jsonify({'message': 'Target deleted successfully'})

@app.route('/api/targets/batch', methods=['POST'])
def batch_operation():
    data = request.json
    
    if not data or 'operation' not in data or 'target_ids' not in data:
        return jsonify({'error': 'Missing required fields: operation, target_ids'}), 400
    
    operation = data['operation']
    target_ids = data['target_ids']
    
    if not isinstance(target_ids, list) or not target_ids:
        return jsonify({'error': 'target_ids must be a non-empty array'}), 400
    
    targets = Target.query.filter(Target.id.in_(target_ids)).all()
    
    if not targets:
        return jsonify({'error': 'No valid targets found'}), 404
    
    if operation == 'delete':
        for target in targets:
            db.session.delete(target)
    elif operation == 'enable':
        for target in targets:
            target.enabled = True
    elif operation == 'disable':
        for target in targets:
            target.enabled = False
    elif operation == 'update' and 'fields' in data:
        fields = data['fields']
        for target in targets:
            for field, value in fields.items():
                if hasattr(target, field):
                    setattr(target, field, value)
    else:
        return jsonify({'error': 'Unsupported operation'}), 400
    
    db.session.commit()
    
    return jsonify({
        'message': f'Batch {operation} successful',
        'affected_count': len(targets)
    })

@app.route('/api/probes', methods=['GET'])
def get_probes():
    probes = Probe.query.all()
    return jsonify([probe.to_dict() for probe in probes])

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    # Count total targets
    total_targets = Target.query.count()
    
    # Count enabled/disabled targets
    enabled_targets = Target.query.filter_by(enabled=True).count()
    disabled_targets = Target.query.filter_by(enabled=False).count()
    
    # Count targets by status
    status_counts = db.session.query(
        Target.last_status, func.count(Target.id)
    ).group_by(Target.last_status).all()
    
    status_stats = {status: count for status, count in status_counts}
    
    # Count targets by probe type
    type_counts = db.session.query(
        Target.probe_type, func.count(Target.id)
    ).group_by(Target.probe_type).all()
    
    type_stats = {probe_type: count for probe_type, count in type_counts}
    
    # Count targets by region
    region_counts = db.session.query(
        Target.region, func.count(Target.id)
    ).group_by(Target.region).all()
    
    region_stats = {region: count for region, count in region_counts}
    
    return jsonify({
        'total': total_targets,
        'enabled': enabled_targets,
        'disabled': disabled_targets,
        'by_status': status_stats,
        'by_type': type_stats,
        'by_region': region_stats
    })

if __name__ == '__main__':
    # Make sure templates directory exists
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create index.html if it doesn't exist
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
                <script>
                    window.location.href = '/static/modernUI.html';
                </script>
            </body>
            </html>
            """)
    
    # Create static directory and subdirectories
    if not os.path.exists('static'):
        os.makedirs('static')
    
    if not os.path.exists('static/js'):
        os.makedirs('static/js')
    
    if not os.path.exists('static/css'):
        os.makedirs('static/css')
    
    # Save our HTML file as modernUI.html
    static_html_path = os.path.join('static', 'modernUI.html')
    if not os.path.exists(static_html_path):
        # We'll create this file manually, but this ensures the directory exists
        pass
    
    # Configure app to run on port 8080
    app.run(host='0.0.0.0', port=8080, debug=True)