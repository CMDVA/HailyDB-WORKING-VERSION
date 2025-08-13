"""
Template Filters for HailyDB
Custom Jinja2 filters used across templates
"""

import json
from config import Config

def number_format(value):
    """Format numbers with commas for thousands"""
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value

def hail_display_name(size_inches):
    """Get display name for hail size using centralized configuration"""
    return Config.get_hail_display_name(size_inches)

def hail_severity(size_inches):
    """Get severity category for hail size using centralized configuration"""
    return Config.get_hail_severity(size_inches)

def determine_enhanced_status(log_row):
    """Determine enhanced status display and color coding for operation logs"""
    # Extract metadata if available
    metadata = {}
    if hasattr(log_row, 'operation_metadata') and log_row.operation_metadata:
        try:
            if isinstance(log_row.operation_metadata, str):
                metadata = json.loads(log_row.operation_metadata)
            else:
                metadata = log_row.operation_metadata
        except:
            pass
    
    # Determine status based on operation type and metadata
    if log_row.operation_type == 'spc_match':
        matched = metadata.get('matched_count', 0)
        processed = metadata.get('processed_count', 0)
        if matched > 0:
            return f"✓ {matched}/{processed} matched", "text-green-600"
        elif processed > 0:
            return f"◦ {processed} processed", "text-gray-600"
        else:
            return "No matches", "text-gray-500"
    
    elif log_row.operation_type == 'enhanced_context':
        success_count = metadata.get('success_count', 0)
        if success_count > 0:
            return f"✓ {success_count} enriched", "text-green-600"
        else:
            return "No enrichment", "text-gray-500"
    
    elif log_row.operation_type == 'spc_verification':
        verified = metadata.get('verified_count', 0)
        if verified > 0:
            return f"✓ {verified} verified", "text-green-600"
        else:
            return "No verification", "text-gray-500"
    
    # Default status
    if log_row.status == 'SUCCESS':
        return "✓ Success", "text-green-600"
    elif log_row.status == 'ERROR':
        return "✗ Error", "text-red-600"
    else:
        return log_row.status or "Unknown", "text-gray-600"