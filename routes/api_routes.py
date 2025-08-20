"""
API Routes for HailyDB
RESTful API endpoints for external integrations
"""

import logging
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
from models import Alert, SPCReport, db

logger = logging.getLogger(__name__)

# Create API Blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/health')
def health():
    """API health check endpoint"""
    try:
        # Get basic system stats
        alert_count = Alert.query.count()
        spc_count = SPCReport.query.count()
        
        return jsonify({
            "status": "healthy",
            "service": "HailyDB API v2.0",
            "version": "2.0.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "database": {
                "alerts": alert_count,
                "spc_reports": spc_count
            },
            "documentation": "/documentation"
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@api_bp.route('/alerts/active')
def active_alerts():
    """Get currently active NWS alerts"""
    try:
        # Get active alerts (not expired)
        current_time = datetime.utcnow()
        alerts = Alert.query.filter(
            Alert.expires > current_time
        ).order_by(Alert.effective.desc()).limit(50).all()
        
        return jsonify({
            'alerts': [alert.to_dict() for alert in alerts],
            'count': len(alerts),
            'timestamp': current_time.isoformat() + 'Z'
        })
        
    except Exception as e:
        logger.error(f"Error fetching active alerts: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alerts/by-state/<state>')
def alerts_by_state(state):
    """Get alerts for a specific state"""
    try:
        # Query alerts by state code in affected_states JSONB field  
        from sqlalchemy import text
        alerts = Alert.query.filter(
            text("affected_states @> :state_array")
        ).params(state_array=f'["{state.upper()}"]').order_by(Alert.effective.desc()).limit(100).all()
        
        return jsonify({
            'alerts': [alert.to_dict() for alert in alerts],
            'state': state.upper(),
            'count': len(alerts)
        })
        
    except Exception as e:
        logger.error(f"Error fetching alerts for state {state}: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/alerts/by-county/<state>/<county>')
def alerts_by_county(state, county):
    """Get alerts for a specific county"""
    try:
        # Query alerts by county name in county_names JSONB field
        from sqlalchemy import text
        alerts = Alert.query.filter(
            text("county_names @> :county_obj")
        ).params(county_obj=f'[{{"state": "{state.upper()}", "county": "{county}"}}]').order_by(Alert.effective.desc()).limit(50).all()
        
        return jsonify({
            'alerts': [alert.to_dict() for alert in alerts],
            'state': state.upper(),
            'county': county,
            'count': len(alerts)
        })
        
    except Exception as e:
        logger.error(f"Error fetching alerts for {county}, {state}: {e}")
        return jsonify({'error': str(e)}), 500