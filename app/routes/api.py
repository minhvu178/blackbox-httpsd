"""
API routes for target management.
"""
from flask import Blueprint, request, jsonify
from app.services.target_service import TargetService
from app.models.probe import Probe

# Create a Blueprint
api = Blueprint('api', __name__)

@api.route('/targets', methods=['GET'])
def get_targets():
    """Get all targets or search targets"""
    # Handle search query
    search_query = request.args.get('q', '')
    include_probes = request.args.get('include_probes', 'false').lower() == 'true'
    
    return jsonify(TargetService.search_targets(search_query, include_probes))

@api.route('/targets/<int:target_id>', methods=['GET'])
def get_target(target_id):
    """Get a specific target by ID"""
    include_probes = request.args.get('include_probes', 'false').lower() == 'true'
    target = TargetService.get_target_by_id(target_id, include_probes)
    
    if not target:
        return jsonify({'error': 'Target not found'}), 404
        
    return jsonify(target)

@api.route('/targets', methods=['POST'])
def create_target():
    """Create a new target"""
    data = request.json
    
    # Validation
    required_fields = ['hostname', 'address', 'region', 'zone', 'probe_type', 'assignees']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400
    
    result = TargetService.create_target(data)
    return jsonify(result), 201

@api.route('/targets/<int:target_id>', methods=['PUT'])
def update_target(target_id):
    """Update a target"""
    data = request.json
    
    result = TargetService.update_target(target_id, data)
    if not result:
        return jsonify({'error': 'Target not found'}), 404
        
    return jsonify(result)

@api.route('/targets/<int:target_id>', methods=['DELETE'])
def delete_target(target_id):
    """Delete a target"""
    result = TargetService.delete_target(target_id)
    if not result:
        return jsonify({'error': 'Target not found'}), 404
        
    return jsonify(result)

@api.route('/targets/batch', methods=['POST'])
def batch_operation():
    """Perform batch operations on targets"""
    data = request.json
    
    if not data or 'operation' not in data or 'target_ids' not in data:
        return jsonify({'error': 'Missing required fields: operation, target_ids'}), 400
    
    operation = data['operation']
    target_ids = data['target_ids']
    fields = data.get('fields')
    
    if not isinstance(target_ids, list) or not target_ids:
        return jsonify({'error': 'target_ids must be a non-empty array'}), 400
    
    result, status_code = TargetService.batch_operation(operation, target_ids, fields)
    return jsonify(result), status_code

@api.route('/probes', methods=['GET'])
def get_probes():
    """Get all probes"""
    probes = Probe.query.all()
    return jsonify([probe.to_dict() for probe in probes])

@api.route('/statistics', methods=['GET'])
def get_statistics():
    """Get system statistics"""
    return jsonify(TargetService.get_statistics())