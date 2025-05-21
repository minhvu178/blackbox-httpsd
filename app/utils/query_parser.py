"""
Utilities for parsing search queries.
"""
import re
from sqlalchemy import and_, or_
from app.models.target import Target

def parse_search_query(query_string):
    """
    Parse Splunk-like search queries like 'hostname=example.com region=US-East status=enabled'
    
    Args:
        query_string: The search query string
        
    Returns:
        A dictionary of field-value pairs extracted from the query
    """
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
    """
    Convert parsed query dict to SQLAlchemy filter conditions
    
    Args:
        parsed_query: Dictionary of field-value pairs
        
    Returns:
        List of SQLAlchemy filter conditions
    """
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