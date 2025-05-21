"""
Target model definition.
"""
from datetime import datetime
from app import db
from .probe import Probe

# Association table for targets and probes (many-to-many relationship)
target_probes = db.Table('target_probes',
    db.Column('target_id', db.Integer, db.ForeignKey('targets.id'), primary_key=True),
    db.Column('probe_id', db.Integer, db.ForeignKey('probes.id'), primary_key=True)
)

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
        """Convert target object to dictionary"""
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