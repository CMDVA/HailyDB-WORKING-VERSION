#!/usr/bin/env python3
"""
Fix template URL references after blueprint refactoring
Updates all url_for() calls to use correct blueprint namespaces
"""

import os
import re

# Mapping of old endpoint names to new blueprint.endpoint format
URL_MAPPINGS = {
    # Web routes
    'internal_dashboard': 'web.index',
    'view_spc_reports': 'web.view_spc_reports',
    'view_spc_report_detail': 'web.view_spc_report_detail',
    'view_radar_alerts': 'web.view_radar_alerts',
    'live_radar_dashboard': 'web.live_radar_dashboard',
    'spc_matches': 'web.spc_matches',
    'hurricane_tracks': 'web.hurricane_tracks',
    'address_targeting': 'web.address_targeting',
    'spc_enrichment_dashboard': 'web.spc_enrichment_dashboard',
    
    # API routes
    'get_alerts': 'api.get_alerts',
    'get_alert': 'api.get_alert',
    'get_alerts_summary': 'api.get_alerts_summary',
    'get_unified_report': 'api.get_unified_report',
    'get_spc_reports': 'api.get_spc_reports',
    'api_radar_alerts_summary': 'api.api_radar_alerts_summary',
    'api_live_radar_alerts': 'api.api_live_radar_alerts',
    'get_webhook_rules': 'api.get_webhook_rules',
    
    # Admin routes
    'internal_status': 'admin.internal_status',
    'internal_metrics': 'admin.internal_metrics',
    'ingestion_logs': 'admin.ingestion_logs',
    'spc_matches_data': 'admin.spc_matches_data',
}

def fix_template_urls():
    """Fix all template URL references"""
    templates_dir = 'templates'
    
    for filename in os.listdir(templates_dir):
        if not filename.endswith('.html'):
            continue
            
        filepath = os.path.join(templates_dir, filename)
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Fix each URL mapping
        for old_endpoint, new_endpoint in URL_MAPPINGS.items():
            # Pattern to match url_for calls with the old endpoint
            pattern = rf"url_for\(['\"]({old_endpoint})['\"]"
            replacement = rf"url_for('{new_endpoint}'"
            content = re.sub(pattern, replacement, content)
        
        # Only write if content changed
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Updated {filename}")
        else:
            print(f"No changes needed for {filename}")

if __name__ == '__main__':
    fix_template_urls()
    print("Template URL fixing complete")