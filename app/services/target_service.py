"""
Target-related business logic.
"""
from sqlalchemy import and_, or_, func
from app import db
from app.models.target import Target
from app.models.probe import Probe
from app.utils.query_parser import parse_search_query, build_filter_conditions

class TargetService:
    @staticmethod
    def get_all_targets(include_probes=False):
        """
        Get all targets
        
        Args:
            include_probes: Whether to include probe information
            
        Returns:
            List of target dictionaries
        """
        targets = Target.query.all()
        return [target.to_dict(include_probes=include_probes) for target in targets]
    
    @staticmethod
    def get_target_by_id(target_id, include_probes=False):
        """
        Get a target by ID
        
        Args:
            target_id: The target ID
            include_probes: Whether to include probe information
            
        Returns:
            Target dictionary or None if not found
        """
        target = Target.query.get(target_id)
        if target:
            return target.to_dict(include_probes=include_probes)
        return None
    
    @staticmethod
    def search_targets(search_query, include_probes=False):
        """
        Search targets using a query string
        
        Args:
            search_query: The search query string
            include_probes: Whether to include probe information
            
        Returns:
            List of matching target dictionaries
        """
        if not search_query:
            return TargetService.get_all_targets(include_probes)
        
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
        
        return [target.to_dict(include_probes=include_probes) for target in targets]
    
    @staticmethod
    def create_target(data):
        """
        Create a new target
        
        Args:
            data: Dictionary containing target data
            
        Returns:
            Dictionary with status message and target ID
        """
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
        
        return {'message': 'Target created successfully', 'id': new_target.id}
    
    @staticmethod
    def update_target(target_id, data):
        """
        Update a target
        
        Args:
            target_id: The target ID
            data: Dictionary containing updated target data
            
        Returns:
            Dictionary with status message or None if target not found
        """
        target = Target.query.get(target_id)
        if not target:
            return None
        
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
        
        return {'message': 'Target updated successfully'}
    
    @staticmethod
    def delete_target(target_id):
        """
        Delete a target
        
        Args:
            target_id: The target ID
            
        Returns:
            Dictionary with status message or None if target not found
        """
        target = Target.query.get(target_id)
        if not target:
            return None
        
        db.session.delete(target)
        db.session.commit()
        
        return {'message': 'Target deleted successfully'}
    
    @staticmethod
    def batch_operation(operation, target_ids, fields=None):
        """
        Perform a batch operation on multiple targets
        
        Args:
            operation: The operation to perform ('delete', 'enable', 'disable', 'update')
            target_ids: List of target IDs
            fields: Dictionary of fields to update (for 'update' operation)
            
        Returns:
            Dictionary with status message and affected count
        """
        targets = Target.query.filter(Target.id.in_(target_ids)).all()
        
        if not targets:
            return {'error': 'No valid targets found'}, 404
        
        if operation == 'delete':
            for target in targets:
                db.session.delete(target)
        elif operation == 'enable':
            for target in targets:
                target.enabled = True
        elif operation == 'disable':
            for target in targets:
                target.enabled = False
        elif operation == 'update' and fields:
            for target in targets:
                for field, value in fields.items():
                    if hasattr(target, field):
                        setattr(target, field, value)
        else:
            return {'error': 'Unsupported operation'}, 400
        
        db.session.commit()
        
        return {
            'message': f'Batch {operation} successful',
            'affected_count': len(targets)
        }
    
    @staticmethod
    def get_statistics():
        """
        Get statistics about targets
        
        Returns:
            Dictionary containing various statistics
        """
        # Count total targets
        total_targets = Target.query.count()
        
        # Count enabled/disabled targets
        enabled_targets = Target.query.filter_by(enabled=True).count()
        disabled_targets = Target.query.filter_by(enabled=False).count()
        
        # Count targets by status
        status_counts = db.session.query(
            Target.last_status, func.count(Target.id)
        ).group_by(Target.last_status).all()
        
        status_stats = {status: count for status, count in status_counts if status is not None}
        
        # Count targets by probe type
        type_counts = db.session.query(
            Target.probe_type, func.count(Target.id)
        ).group_by(Target.probe_type).all()
        
        type_stats = {probe_type: count for probe_type, count in type_counts if probe_type is not None}
        
        # Count targets by region
        region_counts = db.session.query(
            Target.region, func.count(Target.id)
        ).group_by(Target.region).all()
        
        region_stats = {region: count for region, count in region_counts if region is not None}
        
        return {
            'total': total_targets,
            'enabled': enabled_targets,
            'disabled': disabled_targets,
            'by_status': status_stats,
            'by_type': type_stats,
            'by_region': region_stats
        }