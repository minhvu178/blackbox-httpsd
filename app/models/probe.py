"""
Probe model definition.
"""
from datetime import datetime
from app import db

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
        """Convert probe object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'provider': self.provider,
            'ip_address': self.ip_address,
            'enabled': self.enabled,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }

def init_default_probes():
    """Initialize default probes if none exist"""
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