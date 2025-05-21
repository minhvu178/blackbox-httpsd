"""
Prometheus service discovery routes.
"""
from flask import Blueprint, jsonify, request
from app.models.target import Target

# Create a Blueprint
prometheus = Blueprint('prometheus', __name__)

@prometheus.route('/test', methods=['GET'])
def prometheus_sd_test():
    """Test endpoint that always returns a sample target"""
    # Return a static example response for testing
    result = [
        {
            "targets": ["192.168.56.104"],
            "labels": {
                "id": "1",
                "hostname": "example.com",
                "module": "icmp",
                "region": "US-East",
                "assignees": "team-network",
                "job": "blackbox_icmp"
            }
        }
    ]
    
    print(f"Test endpoint returning sample target: {result}")
    
    response = jsonify(result)
    response.headers['Content-Type'] = 'application/json'
    return response

@prometheus.route('/<protocol>', methods=['GET'])
def prometheus_sd(protocol):
    """Endpoint specifically for Prometheus service discovery"""
    # Log the request
    print(f"Prometheus SD endpoint called for protocol: {protocol}")
    
    # Get all targets first to check if any exist
    all_targets = Target.query.all()
    print(f"Total targets in database: {len(all_targets)}")
    for t in all_targets:
        print(f"Target: {t.hostname}, probe_type: {t.probe_type}, enabled: {t.enabled}")
    
    # Get enabled targets first
    enabled_targets = Target.query.filter_by(enabled=True).all()
    print(f"Enabled targets: {len(enabled_targets)}")
    
    # More flexible filtering approach
    entries = []
    protocol_lower = protocol.lower()
    for target in enabled_targets:
        # Try multiple fields that might contain protocol information
        probe_type = target.probe_type.lower() if target.probe_type else ""
        
        # Check for match in probe_type field
        if (protocol_lower in probe_type or 
            (protocol_lower == 'icmp' and any(x in probe_type for x in ['icmp', 'ping'])) or
            (protocol_lower == 'http' and any(x in probe_type for x in ['http', 'web', 'url'])) or
            (protocol_lower == 'tcp' and any(x in probe_type for x in ['tcp', 'socket']))):
            entries.append(target)
    
    print(f"Matching targets for protocol {protocol}: {len(entries)}")
    
    # If still no targets, add all enabled targets as a fallback for testing
    if not entries and protocol_lower == 'icmp' and enabled_targets:
        print(f"No targets found for {protocol}, using all enabled targets as fallback")
        entries = enabled_targets
    
    result = []
    for entry in entries:
        target_address = entry.address
        if protocol_lower == 'tcp' and entry.port:
            target_address = f"{entry.address}:{entry.port}"
            
        item = {
            "targets": [target_address],
            "labels": {
                "id": str(entry.id),
                "hostname": entry.hostname,
                "module": protocol_lower,  # Use the protocol as the module
                "region": entry.region,
                "assignees": entry.assignees,
                "job": f"blackbox_{protocol_lower}"
            }
        }
        result.append(item)
        print(f"Added target to result: {target_address}")
    
    # Log the result to help with debugging
    print(f"Prometheus SD endpoint for {protocol} returned {len(result)} targets")
    if result:
        print(f"Sample result item: {result[0]}")
    
    response = jsonify(result)
    response.headers['Content-Type'] = 'application/json'
    return response