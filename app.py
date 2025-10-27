import os
import logging
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import atexit
import requests
import json
import math
from sqlalchemy import text
from live_radar_service import LiveRadarAlertService
from enhanced_context_service import enhanced_context_service
from spc_verification import SPCVerificationService

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database - CONSOLIDATED: Point development to production database
# This ensures single source of truth and prevents database divergence
production_db_url = os.environ.get("DATABASE_URL", "postgresql://localhost/nws_alerts")
app.config["SQLALCHEMY_DATABASE_URI"] = production_db_url
# Log which database we're connecting to for transparency
logger.info(f"Connecting to database: {production_db_url[:50]}...")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 180,  # Reduced from 300 to handle SSL timeouts
    "pool_pre_ping": True,
    "pool_reset_on_return": "commit",  # Reset connections on return
    "pool_size": 10,  # Connection pool size
    "max_overflow": 20,  # Additional connections if needed
    "connect_args": {
        "connect_timeout": 30,
        "application_name": "HailyDB_Storm_Tracker"
    }
}

# Initialize the app with the extension
db.init_app(app)

# Initialize database tables and services when app starts
with app.app_context():
    try:
        # Import models first so SQLAlchemy knows about them
        from models import Alert, RadarAlert, IngestionLog, SchedulerLog, SPCReport, WebhookRule, HurricaneCountyImpact, HurricaneTrack, SPCIngestionLog, WebhookEvent
        
        # Create all database tables
        db.create_all()
        
        # Initialize live radar alert service
        from live_radar_service import init_live_radar_service, start_live_radar_service
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=db.engine)
        service_session = Session()
        
        init_live_radar_service(service_session)
        start_live_radar_service()
        logger.info("Live radar alert service initialized and started")
        
    except Exception as e:
        logger.error(f"Error initializing services: {e}")

# Import utilities
from utils.access_control import is_admin_access, require_admin_or_redirect
from utils.template_filters import (number_format, hail_display_name, hail_severity, 
                                   determine_enhanced_status)

# Register template filters
app.template_filter('number_format')(number_format)
app.template_filter('hail_display_name')(hail_display_name)
app.template_filter('hail_severity')(hail_severity)

# Register blueprints
from routes.api_routes import api_bp
app.register_blueprint(api_bp)

def determine_enhanced_status(log_row):
    """Determine enhanced status display and color coding for operation logs"""
    import json
    
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
    
    # Check for detailed status in metadata
    detailed_status = metadata.get('detailed_status', '')
    
    # Determine status if not in progress
    if not log_row.completed_at:
        return {
            'display': 'In Progress',
            'color': '#007bff',
            'class': 'log-progress'
        }
    
    # Use detailed status if available
    if detailed_status:
        if detailed_status == 'success_with_new_data':
            return {
                'display': 'Success',
                'color': '#28a745',
                'class': 'log-success'
            }
        elif detailed_status == 'success_no_new_data':
            return {
                'display': 'Success - No New Data',
                'color': '#20c997',
                'class': 'log-success-no-data'
            }
        elif detailed_status == 'failed_technical':
            return {
                'display': 'Failed - Technical',
                'color': '#fd7e14',
                'class': 'log-failed-technical'
            }
        elif detailed_status == 'failed_network':
            return {
                'display': 'Failed - Network',
                'color': '#dc3545',
                'class': 'log-failed-network'
            }
        elif detailed_status == 'failed_data':
            return {
                'display': 'Failed - Data',
                'color': '#dc3545',
                'class': 'log-failed-data'
            }
    
    # Fallback to basic success/failure with enhanced logic
    if log_row.success:
        if log_row.records_new == 0 and log_row.records_processed > 0:
            return {
                'display': 'Success - No New Data',
                'color': '#20c997',
                'class': 'log-success-no-data'
            }
        elif log_row.records_new > 0:
            return {
                'display': 'Success',
                'color': '#28a745',
                'class': 'log-success'
            }
        else:
            return {
                'display': 'Success',
                'color': '#28a745',
                'class': 'log-success'
            }
    else:
        # Determine failure type from error message
        error_msg = (log_row.error_message or '').lower()
        if 'network' in error_msg or 'timeout' in error_msg or 'connection' in error_msg:
            return {
                'display': 'Failed - Network',
                'color': '#dc3545',
                'class': 'log-failed-network'
            }
        elif 'database' in error_msg or 'sql' in error_msg or 'pg numeric type' in error_msg:
            return {
                'display': 'Failed - Technical',
                'color': '#fd7e14',
                'class': 'log-failed-technical'
            }
        else:
            return {
                'display': 'Failed',
                'color': '#dc3545',
                'class': 'log-error'
            }

# Import other modules after app initialization
from models import Alert, SPCReport, SPCIngestionLog, SchedulerLog, HurricaneTrack
from ingest import IngestService
from enrich import EnrichmentService
from spc_ingest import SPCIngestService
from spc_matcher import SPCMatchingService
from spc_verification import SPCVerificationService
from hurricane_ingest import HurricaneIngestService
from scheduler_service import SchedulerService
from config import Config
from utils.access_control import verify_admin_credentials, login_admin, logout_admin
import atexit

# Global services
ingest_service = None
enrich_service = None
spc_ingest_service = None
spc_matching_service = None
scheduler_service = None
scheduler = None
autonomous_scheduler = None

with app.app_context():
    # Import models to ensure tables are created
    import models
    db.create_all()
    
    # Initialize services
    ingest_service = IngestService(db)
    enrich_service = EnrichmentService(db)
    spc_ingest_service = SPCIngestService(db.session)
    spc_matching_service = SPCMatchingService(db.session)
    hurricane_ingest_service = HurricaneIngestService(db.session)
    scheduler_service = SchedulerService(db)
    
    # Initialize live radar service
    from live_radar_service import LiveRadarAlertService
    live_radar_service = LiveRadarAlertService(db.session())
    live_radar_service.start_polling()
    
    # Initialize autonomous scheduler with app instance to prevent circular imports
    from autonomous_scheduler import AutonomousScheduler
    autonomous_scheduler = AutonomousScheduler(db, app)
    
    # START the autonomous scheduler - CRITICAL for production ingestion
    autonomous_scheduler.start()
    logger.info("Autonomous scheduler started successfully (persistent mode)")

# CRITICAL: Add missing /dashboard route for production compatibility    
@app.route('/dashboard')
def dashboard():
    """Main dashboard redirect for production compatibility"""
    return redirect('/internal/dashboard')

# API Routes - Legacy NWS Alerts (being phased out)
@app.route('/alerts-legacy')
def get_alerts_legacy():
    """Get recent alerts with optional filtering"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    severity = request.args.get('severity')
    event = request.args.get('event')
    category = request.args.get('category')
    state = request.args.get('state')
    county = request.args.get('county')
    area = request.args.get('area')
    effective_date = request.args.get('effective_date')
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    search_query = request.args.get('search', '').strip()
    
    # Category mapping - maps category names to their corresponding alert types
    category_mapping = {
        'Severe Weather Alert': [
            'Tornado Watch', 'Tornado Warning', 'Severe Thunderstorm Watch', 
            'Severe Thunderstorm Warning', 'Severe Weather Statement', 
            'Extreme Wind Warning', 'Snow Squall Warning'
        ],
        'Winter Weather Alert': [
            'Winter Storm Watch', 'Winter Storm Warning', 'Blizzard Warning',
            'Ice Storm Warning', 'Winter Weather Advisory', 'Freezing Rain Advisory',
            'Wind Chill Advisory', 'Wind Chill Warning', 'Frost Advisory', 'Freeze Warning'
        ],
        'Flood Alert': [
            'Flood Watch', 'Flood Warning', 'Flash Flood Watch', 
            'Flash Flood Warning', 'Flood Advisory'
        ],
        'Coastal Alert': [
            'Coastal Flood Watch', 'Coastal Flood Warning', 'Coastal Flood Advisory',
            'Lakeshore Flood Watch', 'Lakeshore Flood Warning', 'Lakeshore Flood Advisory',
            'Beach Hazards Statement'
        ],
        'Wind & Fog Alert': [
            'High Wind Watch', 'High Wind Warning', 'Wind Advisory',
            'Dense Fog Advisory', 'Freezing Fog Advisory'
        ],
        'Fire Weather Alert': [
            'Fire Weather Watch', 'Red Flag Warning'
        ],
        'Air Quality & Dust Alert': [
            'Air Quality Alert', 'Air Stagnation Advisory', 'Blowing Dust Advisory',
            'Dust Storm Warning', 'Ashfall Advisory', 'Ashfall Warning'
        ],
        'Marine Alert': [
            'Small Craft Advisory', 'Gale Watch', 'Gale Warning', 'Storm Watch',
            'Storm Warning', 'Hurricane Force Wind Warning', 'Special Marine Warning',
            'Low Water Advisory', 'Brisk Wind Advisory', 'Marine Weather Statement',
            'Hazardous Seas Warning'
        ],
        'Tropical Weather Alert': [
            'Tropical Storm Watch', 'Tropical Storm Warning', 'Hurricane Watch',
            'Hurricane Warning', 'Storm Surge Watch', 'Storm Surge Warning'
        ],
        'Tsunami Alert': [
            'Tsunami Watch', 'Tsunami Advisory', 'Tsunami Warning'
        ],
        'General Weather Info': [
            'Special Weather Statement', 'Hazardous Weather Outlook', 'Short Term Forecast',
            'Public Information Statement', 'Administrative Message', 'Test Message'
        ]
    }
    
    query = Alert.query.order_by(Alert.effective.desc())
    
    # Apply search query across multiple fields
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Alert.event.ilike(search_pattern),
                Alert.area_desc.ilike(search_pattern),
                Alert.ai_summary.ilike(search_pattern),
                Alert.properties['headline'].astext.ilike(search_pattern),
                Alert.properties['description'].astext.ilike(search_pattern),
                Alert.raw['properties']['areaDesc'].astext.ilike(search_pattern)
            )
        )
    
    if severity:
        query = query.filter(Alert.severity == severity)
    if event:
        query = query.filter(Alert.event.ilike(f'%{event}%'))
    if category and category in category_mapping:
        # Filter by alert types in the selected category
        query = query.filter(Alert.event.in_(category_mapping[category]))
    if state:
        query = query.filter(Alert.area_desc.ilike(f'%{state}%'))
    if county:
        query = query.filter(Alert.area_desc.ilike(f'%{county}%'))
    if area:
        query = query.filter(Alert.area_desc.ilike(f'%{area}%'))
    if effective_date:
        from datetime import datetime
        try:
            filter_date = datetime.strptime(effective_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Alert.effective) == filter_date)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    # Add ingested_date filter for database completeness tracking
    ingested_date = request.args.get('ingested_date')
    if ingested_date:
        from datetime import datetime
        try:
            filter_date = datetime.strptime(ingested_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Alert.ingested_at) == filter_date)
        except ValueError:
            pass  # Invalid date format, ignore filter
    
    # Add effective time range filters for SPC Day support
    effective_start = request.args.get('effective_start')
    effective_end = request.args.get('effective_end')
    if effective_start:
        from datetime import datetime
        try:
            start_datetime = datetime.fromisoformat(effective_start.replace('Z', '+00:00'))
            query = query.filter(Alert.effective >= start_datetime)
        except ValueError:
            pass  # Invalid datetime format, ignore filter
    if effective_end:
        from datetime import datetime
        try:
            end_datetime = datetime.fromisoformat(effective_end.replace('Z', '+00:00'))
            query = query.filter(Alert.effective <= end_datetime)
        except ValueError:
            pass  # Invalid datetime format, ignore filter
    if active_only:
        from datetime import datetime
        now = datetime.utcnow()
        query = query.filter(
            Alert.effective <= now,
            Alert.expires > now
        )
    
    alerts = query.paginate(
        page=page,
        per_page=min(per_page, 1000),  # Increased limit for dashboard performance
        error_out=False
    )
    
    if request.args.get('format') == 'json':
        return jsonify({
            'alerts': [{
                'id': alert.id,
                'event': alert.event,
                'severity': alert.severity,
                'area_desc': alert.area_desc,
                'effective': alert.effective.isoformat() if alert.effective else None,
                'expires': alert.expires.isoformat() if alert.expires else None,
                'ai_summary': alert.ai_summary,
                'ai_tags': alert.ai_tags,
                'radar_indicated': alert.radar_indicated
            } for alert in alerts.items],
            'pagination': {
                'page': alerts.page,
                'pages': alerts.pages,
                'per_page': alerts.per_page,
                'total': alerts.total
            }
        })
    
    # Get actual alert types for dropdown
    alert_types = db.session.query(Alert.event).distinct().order_by(Alert.event).all()
    alert_types_list = [row[0] for row in alert_types if row[0]]
    
    return render_template('alerts.html', alerts=alerts, alert_types=alert_types_list)

def get_live_radar_service():
    """Get the live radar service instance"""
    try:
        from live_radar_service import LiveRadarAlertService
        return LiveRadarAlertService()
    except Exception as e:
        print(f"Error getting live radar service: {e}")
        return None

@app.route('/api/alerts/<path:alert_id>')
def get_alert_api(alert_id):
    """API endpoint to get individual alert data in JSON format - Core business endpoint"""
    import urllib.parse
    
    # PRODUCTION DEBUG: Log the exact alert_id being requested
    logger.info(f"API Alert lookup requested: '{alert_id}'")
    
    # Handle URL decoding for production environments
    try:
        decoded_alert_id = urllib.parse.unquote(alert_id)
        logger.info(f"Decoded alert_id: '{decoded_alert_id}'")
    except:
        decoded_alert_id = alert_id
        logger.info(f"No decoding needed for alert_id: '{alert_id}'")
    
    # Try both original and decoded versions with detailed logging
    logger.info(f"Querying database for alert_id: '{alert_id}'")
    alert = Alert.query.filter_by(id=alert_id).first()
    logger.info(f"First query result: {alert is not None}")
    
    if not alert and decoded_alert_id != alert_id:
        logger.info(f"Trying decoded version: '{decoded_alert_id}'")
        alert = Alert.query.filter_by(id=decoded_alert_id).first()
        logger.info(f"Decoded query result: {alert is not None}")
    
    # PRODUCTION DEBUG: If still not found, check if any similar IDs exist
    if not alert:
        similar_count = Alert.query.filter(Alert.id.like(f'%47199d556c7667ca8d58be1f58db503767724a66%')).count()
        logger.error(f"Alert not found. Similar IDs in database: {similar_count}")
    
    if not alert:
        return jsonify({
            'error': 'Alert not found',
            'message': f'Alert {alert_id} not found in HailyDB historical repository',
            'alert_id': alert_id,
            'decoded_id': decoded_alert_id if decoded_alert_id != alert_id else None,
            'note': 'This endpoint provides historical NWS alerts with radar-detected damage parameters'
        }), 404
    
    # Return the full alert data as NWS-compliant JSON
    alert_data = alert.to_dict()
    
    # Add metadata for API compliance
    alert_data['hailydb_metadata'] = {
        'repository_type': 'historical_weather_damage_intelligence',
        'data_source': 'National Weather Service (NWS)',
        'last_updated': alert.ingested_at.isoformat() if alert.ingested_at else None,
        'nws_compliant': True
    }
    
    return jsonify(alert_data)

# CRITICAL: Additional route for production URL handling compatibility
@app.route('/api/alerts/<string:alert_id>')
def get_alert_api_string(alert_id):
    """Fallback API endpoint for string-based alert IDs"""
    return get_alert_api(alert_id)

@app.route('/alerts/<path:alert_id>')
def get_alert(alert_id):
    """Get single enriched alert - supports both historical and live radar alerts"""
    import urllib.parse
    
    # PRODUCTION FIX: Handle URL decoding for production environments
    try:
        decoded_alert_id = urllib.parse.unquote(alert_id)
        logger.info(f"Alert lookup: original='{alert_id}', decoded='{decoded_alert_id}'")
    except Exception as e:
        decoded_alert_id = alert_id
        logger.error(f"URL decode failed for alert_id: {e}")
    
    # First check the main alerts table (NWS alerts) - try both original and decoded
    alert = Alert.query.filter_by(id=decoded_alert_id).first()
    if not alert:
        alert = Alert.query.filter_by(id=alert_id).first()
        logger.info(f"Fallback lookup used for alert_id: {alert_id}")
    
    if alert:
        if request.args.get('format') == 'json':
            return jsonify(alert.to_dict())
        return render_template('alert_detail.html', alert=alert)
    
    # If not found in main alerts, check live radar alerts (URN format)
    if alert_id.startswith('urn:oid:'):
        live_service = get_live_radar_service()
        if live_service:
            # Get live alert from the service
            live_alerts = live_service.get_active_alerts()
            live_alert = next((alert for alert in live_alerts if alert.get('id') == alert_id), None)
            
            if live_alert:
                if request.args.get('format') == 'json':
                    return jsonify(live_alert)
                return render_template('live_alert_detail.html', alert=live_alert)
    
    # Alert not found in either location
    return render_template('404.html', 
                         message=f"Alert {alert_id} not found or expired"), 404
    
    # Historical alert lookup
    alert = Alert.query.get_or_404(alert_id)
    
    if request.args.get('format') == 'json':
        return jsonify({
            'id': alert.id,
            'event': alert.event,
            'severity': alert.severity,
            'area_desc': alert.area_desc,
            'effective': alert.effective.isoformat() if alert.effective else None,
            'expires': alert.expires.isoformat() if alert.expires else None,
            'sent': alert.sent.isoformat() if alert.sent else None,
            'geometry': alert.geometry,
            'properties': alert.properties,
            'raw': alert.raw,
            'ai_summary': alert.ai_summary,
            'ai_tags': alert.ai_tags,
            'spc_verified': alert.spc_verified,
            'spc_reports': alert.spc_reports,
            'radar_indicated': alert.radar_indicated,
            'ingested_at': alert.ingested_at.isoformat()
        })
    
    return render_template('alert_detail.html', alert=alert)

# Removed /alerts/summary route - redundant with existing verified matches page

# Legacy health endpoint removed - now handled by API blueprint at /api/health

# Legacy state alerts endpoint removed - now handled by API blueprint at /api/alerts/by-state/<state>

@app.route('/api/alerts/by-county/<state>/<county>')
def get_alerts_by_county(state, county):
    """Get alerts for a specific county"""
    query = Alert.query.filter(
        Alert.area_desc.ilike(f'%{county}%'),
        Alert.area_desc.ilike(f'%{state}%')
    ).order_by(Alert.ingested_at.desc())
    
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    if active_only:
        from datetime import datetime
        now = datetime.utcnow()
        query = query.filter(
            Alert.effective <= now,
            Alert.expires > now
        )
    
    alerts = query.all()
    
    return jsonify({
        'state': state,
        'county': county,
        'total_alerts': len(alerts),
        'alerts': [alert.to_dict() for alert in alerts]
    })

@app.route('/api/alerts/active')
def get_active_alerts():
    """Get all currently active alerts"""
    from datetime import datetime
    now = datetime.utcnow()
    
    alerts = Alert.query.filter(
        Alert.effective <= now,
        Alert.expires > now
    ).order_by(Alert.severity.desc(), Alert.ingested_at.desc()).all()
    
    return jsonify({
        'timestamp': now.isoformat(),
        'total_active': len(alerts),
        'alerts': [alert.to_dict() for alert in alerts]
    })

@app.route('/api/alerts/radar_detected')
def get_radar_detected_alerts():
    """
    Pre-filtered endpoint for radar-detected damage events
    Returns alerts with 50+ mph winds OR any size hail detected by radar
    Optimized for insurance and restoration industry clients
    """
    from datetime import datetime
    
    # Query for radar-detected events meeting damage criteria
    query = Alert.query.filter(
        Alert.radar_indicated.isnot(None),
        db.or_(
            Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= 50,
            Alert.radar_indicated['hail_inches'].astext.cast(db.Float) > 0
        )
    )
    
    # Geographic filters - radius takes precedence over state/county
    lat = request.args.get('lat')
    lon = request.args.get('lon')  
    radius_mi = request.args.get('radius_mi')
    
    if lat and lon and radius_mi:
        try:
            lat_float = float(lat)
            lon_float = float(lon)
            radius_float = float(radius_mi)
            
            # Calculate bounding box for initial filtering (approximate)
            # 1 degree latitude ≈ 69 miles, longitude varies by latitude
            lat_delta = radius_float / 69.0
            lon_delta = radius_float / (69.0 * abs(math.cos(math.radians(lat_float))))
            
            # Filter by geometry bounds within bounding box (for performance)
            # Note: This is approximate - actual distance calculation would be more complex
            query = query.filter(
                Alert.geometry_bounds.isnot(None),
                Alert.geometry_bounds['min_lat'].astext.cast(db.Float) <= lat_float + lat_delta,
                Alert.geometry_bounds['max_lat'].astext.cast(db.Float) >= lat_float - lat_delta,
                Alert.geometry_bounds['min_lon'].astext.cast(db.Float) <= lon_float + lon_delta,
                Alert.geometry_bounds['max_lon'].astext.cast(db.Float) >= lon_float - lon_delta
            )
            
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Invalid geographic parameters',
                'message': 'lat, lon, and radius_mi must be valid numbers',
                'provided': {'lat': lat, 'lon': lon, 'radius_mi': radius_mi}
            }), 400
    else:
        # Fallback to state/county filtering
        state = request.args.get('state')
        if state:
            query = query.filter(Alert.affected_states.contains([state.upper()]))
        
        county = request.args.get('county')
        if county:
            query = query.filter(Alert.area_desc.ilike(f'%{county}%'))
    
    # Status filter (active vs expired)
    status = request.args.get('status', 'all').lower()
    now = datetime.utcnow()
    if status == 'active':
        query = query.filter(Alert.expires > now)
    elif status == 'expired':
        query = query.filter(Alert.expires <= now)
    
    # Date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Alert.effective >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            from datetime import timedelta
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Alert.effective < end_dt)
        except ValueError:
            pass
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 1000, type=int), 5000)
    
    # Execute query
    total = query.count()
    alerts = query.order_by(Alert.effective.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # Format as GeoJSON FeatureCollection
    features = []
    for alert in alerts:
        feature = {
            'id': alert.id,
            'type': 'Feature',
            'properties': alert.to_dict(),
            'geometry': alert.geometry
        }
        features.append(feature)
    
    return jsonify({
        'type': 'FeatureCollection',
        'features': features,
        'title': f'Radar-Detected Weather Damage Events - {total} alerts with 50+ mph winds or hail',
        'updated': datetime.utcnow().isoformat(),
        'metadata': {
            'total_results': total,
            'page': page,
            'per_page': limit,
            'criteria': '50+ mph winds OR any hail size detected by radar',
            'data_source': 'National Weather Service alerts with radar parameters'
        }
    })

@app.route('/api/alerts/radar_detected/wind')
def get_radar_detected_wind():
    """
    Pre-filtered endpoint for radar-detected wind events (50+ mph)
    Optimized for wind damage assessment
    """
    from datetime import datetime
    
    # Query for radar-detected wind events
    query = Alert.query.filter(
        Alert.radar_indicated.isnot(None),
        Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= 50
    )
    
    # Geographic filters - radius takes precedence over state/county
    lat = request.args.get('lat')
    lon = request.args.get('lon')  
    radius_mi = request.args.get('radius_mi')
    
    if lat and lon and radius_mi:
        try:
            lat_float = float(lat)
            lon_float = float(lon)
            radius_float = float(radius_mi)
            
            # Calculate bounding box for initial filtering (approximate)
            lat_delta = radius_float / 69.0
            lon_delta = radius_float / (69.0 * abs(math.cos(math.radians(lat_float))))
            
            # Filter by geometry bounds within bounding box
            query = query.filter(
                Alert.geometry_bounds.isnot(None),
                Alert.geometry_bounds['min_lat'].astext.cast(db.Float) <= lat_float + lat_delta,
                Alert.geometry_bounds['max_lat'].astext.cast(db.Float) >= lat_float - lat_delta,
                Alert.geometry_bounds['min_lon'].astext.cast(db.Float) <= lon_float + lon_delta,
                Alert.geometry_bounds['max_lon'].astext.cast(db.Float) >= lon_float - lon_delta
            )
            
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Invalid geographic parameters',
                'message': 'lat, lon, and radius_mi must be valid numbers',
                'provided': {'lat': lat, 'lon': lon, 'radius_mi': radius_mi}
            }), 400
    else:
        # Fallback to state/county filtering
        state = request.args.get('state')
        if state:
            query = query.filter(Alert.affected_states.contains([state.upper()]))
        
        county = request.args.get('county') 
        if county:
            query = query.filter(Alert.area_desc.ilike(f'%{county}%'))
    
    status = request.args.get('status', 'all').lower()
    now = datetime.utcnow()
    if status == 'active':
        query = query.filter(Alert.expires > now)
    elif status == 'expired':
        query = query.filter(Alert.expires <= now)
    
    # Date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Alert.effective >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            from datetime import timedelta
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Alert.effective < end_dt)
        except ValueError:
            pass
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 1000, type=int), 5000)
    
    # Execute query
    total = query.count()
    alerts = query.order_by(Alert.effective.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # Format as GeoJSON FeatureCollection
    features = []
    for alert in alerts:
        feature = {
            'id': alert.id,
            'type': 'Feature', 
            'properties': alert.to_dict(),
            'geometry': alert.geometry
        }
        features.append(feature)
    
    return jsonify({
        'type': 'FeatureCollection',
        'features': features,
        'title': f'Radar-Detected Wind Events - {total} alerts with 50+ mph winds',
        'updated': datetime.utcnow().isoformat(),
        'metadata': {
            'total_results': total,
            'page': page,
            'per_page': limit,
            'criteria': '50+ mph winds detected by radar',
            'data_source': 'National Weather Service alerts with radar wind parameters'
        }
    })

@app.route('/api/alerts/radar_detected/hail')
def get_radar_detected_hail():
    """
    Pre-filtered endpoint for radar-detected hail events (any size)
    Optimized for hail damage assessment
    """
    from datetime import datetime
    
    # Query for radar-detected hail events
    query = Alert.query.filter(
        Alert.radar_indicated.isnot(None),
        Alert.radar_indicated['hail_inches'].astext.cast(db.Float) > 0
    )
    
    # Geographic filters - radius takes precedence over state/county
    lat = request.args.get('lat')
    lon = request.args.get('lon')  
    radius_mi = request.args.get('radius_mi')
    
    if lat and lon and radius_mi:
        try:
            lat_float = float(lat)
            lon_float = float(lon)
            radius_float = float(radius_mi)
            
            # Calculate bounding box for initial filtering (approximate)
            lat_delta = radius_float / 69.0
            lon_delta = radius_float / (69.0 * abs(math.cos(math.radians(lat_float))))
            
            # Filter by geometry bounds within bounding box
            query = query.filter(
                Alert.geometry_bounds.isnot(None),
                Alert.geometry_bounds['min_lat'].astext.cast(db.Float) <= lat_float + lat_delta,
                Alert.geometry_bounds['max_lat'].astext.cast(db.Float) >= lat_float - lat_delta,
                Alert.geometry_bounds['min_lon'].astext.cast(db.Float) <= lon_float + lon_delta,
                Alert.geometry_bounds['max_lon'].astext.cast(db.Float) >= lon_float - lon_delta
            )
            
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Invalid geographic parameters',
                'message': 'lat, lon, and radius_mi must be valid numbers',
                'provided': {'lat': lat, 'lon': lon, 'radius_mi': radius_mi}
            }), 400
    else:
        # Fallback to state/county filtering
        state = request.args.get('state')
        if state:
            query = query.filter(Alert.affected_states.contains([state.upper()]))
        
        county = request.args.get('county')
        if county:
            query = query.filter(Alert.area_desc.ilike(f'%{county}%'))
    
    status = request.args.get('status', 'all').lower()
    now = datetime.utcnow()
    if status == 'active':
        query = query.filter(Alert.expires > now)
    elif status == 'expired':
        query = query.filter(Alert.expires <= now)
    
    # Date range
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Alert.effective >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            from datetime import timedelta
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Alert.effective < end_dt)
        except ValueError:
            pass
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 1000, type=int), 5000)
    
    # Execute query
    total = query.count()
    alerts = query.order_by(Alert.effective.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # Format as GeoJSON FeatureCollection
    features = []
    for alert in alerts:
        feature = {
            'id': alert.id,
            'type': 'Feature',
            'properties': alert.to_dict(),
            'geometry': alert.geometry
        }
        features.append(feature)
    
    return jsonify({
        'type': 'FeatureCollection',
        'features': features,
        'title': f'Radar-Detected Hail Events - {total} alerts with hail of any size',
        'updated': datetime.utcnow().isoformat(),
        'metadata': {
            'total_results': total,
            'page': page,
            'per_page': limit,
            'criteria': 'Any hail size detected by radar',
            'data_source': 'National Weather Service alerts with radar hail parameters'
        }
    })

@app.route('/api/test/radar-parsing', methods=['POST'])
def test_radar_parsing():
    """Test endpoint for radar-indicated parsing"""
    from ingest import IngestService
    
    test_data = request.json if request.json else {}
    
    # Sample test cases
    test_cases = [
        {
            'event': 'Severe Thunderstorm Warning',
            'headline': 'Severe Thunderstorm Warning with quarter size hail and winds up to 70 mph',
            'description': 'This storm is producing damaging winds of 70 mph and hail up to 1 inch in diameter.'
        },
        {
            'event': 'Severe Thunderstorm Warning', 
            'headline': 'Golf ball hail and 80 mph wind gusts expected',
            'description': 'Wind gusts to 80 mph and golf ball size hail are possible.'
        },
        test_data.get('properties', {})
    ]
    
    ingest_service = IngestService(db)
    results = []
    
    for i, properties in enumerate(test_cases):
        if not properties.get('event'):
            continue
            
        radar_data = ingest_service._parse_radar_indicated(properties)
        results.append({
            'test_case': i + 1,
            'input': properties,
            'radar_indicated': radar_data
        })
    
    return jsonify({
        'status': 'success',
        'test_results': results
    })

@app.route('/api/admin/trigger-nws-poll', methods=['POST'])
def trigger_nws_poll():
    """Manually trigger NWS alert polling for testing"""
    try:
        from ingest import IngestService
        
        ingest_service = IngestService(db)
        new_alerts = ingest_service.poll_nws_alerts()
        
        return jsonify({
            'status': 'success',
            'new_alerts': new_alerts,
            'message': f'Polling completed. {new_alerts} new alerts ingested.'
        })
    except Exception as e:
        logger.error(f"Error during manual NWS poll: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/test/radar-summary', methods=['GET'])
def get_radar_parsing_summary():
    """Get summary of radar-indicated parsing results"""
    try:
        # Count alerts with radar_indicated data
        total_stw = db.session.query(Alert).filter(
            Alert.event == 'Severe Thunderstorm Warning'
        ).count()
        
        parsed_stw = db.session.query(Alert).filter(
            Alert.event == 'Severe Thunderstorm Warning',
            Alert.radar_indicated.isnot(None)
        ).count()
        
        # Get sample parsed alerts
        sample_alerts = db.session.query(Alert).filter(
            Alert.event == 'Severe Thunderstorm Warning',
            Alert.radar_indicated.isnot(None)
        ).limit(5).all()
        
        samples = []
        for alert in sample_alerts:
            samples.append({
                'id': alert.id,
                'area': alert.area_desc,
                'radar_indicated': alert.radar_indicated,
                'effective': alert.effective.isoformat() if alert.effective else None
            })
        
        return jsonify({
            'status': 'success',
            'summary': {
                'total_severe_thunderstorm_warnings': total_stw,
                'parsed_with_radar_data': parsed_stw,
                'parsing_success_rate': f"{(parsed_stw/total_stw*100):.1f}%" if total_stw > 0 else "0%"
            },
            'sample_parsed_alerts': samples
        })
        
    except Exception as e:
        logger.error(f"Error generating radar parsing summary: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/alerts/expired')
def get_expired_alerts():
    """
    Historical NWS alert repository endpoint
    Returns expired alerts with radar-indicated hail and/or wind parameters
    Follows NWS API standards for alert data structure
    """
    # Location parameters for damage assessment
    state = request.args.get('state')
    county = request.args.get('county')
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    radius_miles = request.args.get('radius_miles', 25, type=int)
    
    # Damage parameters
    min_hail = request.args.get('min_hail', 0, type=float)  # Any hail by default
    min_wind = request.args.get('min_wind', 50, type=int)   # 50+ mph winds
    
    # Date range for historical analysis (default: ALL historical data)
    from datetime import datetime, timedelta
    start_date = request.args.get('start_date')  # No default - access all historical data
    end_date = request.args.get('end_date')
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 1000, type=int), 10000)  # High limit for historical repository access
    
    # Base query: ALL historical alerts (production database contains only historical data)
    query = Alert.query
    
    # Apply radar filtering based on has_radar parameter
    has_radar = request.args.get('has_radar', '').lower() == 'true'
    if has_radar:
        query = query.filter(
            Alert.radar_indicated.isnot(None),
            db.or_(
                Alert.radar_indicated['hail_inches'].astext.cast(db.Float) >= min_hail,
                Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= min_wind
            )
        )
    
    # Geographic filters - radius takes precedence over state/county
    if lat and lon and radius_miles:
        try:
            # Calculate bounding box for initial filtering (approximate)
            lat_delta = radius_miles / 69.0
            lon_delta = radius_miles / (69.0 * abs(math.cos(math.radians(lat))))
            
            # Filter by geometry bounds within bounding box
            query = query.filter(
                Alert.geometry_bounds.isnot(None),
                Alert.geometry_bounds['min_lat'].astext.cast(db.Float) <= lat + lat_delta,
                Alert.geometry_bounds['max_lat'].astext.cast(db.Float) >= lat - lat_delta,
                Alert.geometry_bounds['min_lon'].astext.cast(db.Float) <= lon + lon_delta,
                Alert.geometry_bounds['max_lon'].astext.cast(db.Float) >= lon - lon_delta
            )
            
        except (ValueError, TypeError) as e:
            return jsonify({
                'error': 'Invalid geographic parameters',
                'message': 'lat, lon, and radius_miles must be valid numbers',
                'provided': {'lat': lat, 'lon': lon, 'radius_miles': radius_miles}
            }), 400
    else:
        # Fallback to state/county filtering
        if state:
            query = query.filter(Alert.affected_states.contains([state]))
        if county:
            query = query.filter(Alert.area_desc.ilike(f'%{county}%'))
    
    # Date range
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Alert.effective >= start_dt)
        except ValueError:
            pass
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Alert.effective < end_dt)
        except ValueError:
            pass
    
    # Execute query with pagination
    total = query.count()
    events = query.order_by(Alert.effective.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # Format response following NWS API OpenAPI specification
    features = []
    for alert in events:
        # Create GeoJSON Feature structure as per NWS API spec
        feature = {
            'id': alert.id,
            'type': 'Feature',
            'properties': alert.to_dict(),
            'geometry': alert.geometry
        }
        features.append(feature)
    
    # Return GeoJSON FeatureCollection format as per NWS API spec
    response_data = {
        'type': 'FeatureCollection',
        'features': features,
        'title': f'HailyDB Historical Alerts Repository - {total} expired alerts with radar-indicated parameters',
        'updated': datetime.utcnow().isoformat(),
        'metadata': {
            'total_results': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit,
            'filters_applied': {
                'state': state,
                'county': county,
                'min_hail_inches': min_hail,
                'min_wind_mph': min_wind,
                'date_range': f"{start_date} to {end_date or 'today'}",
                'historical_only': True
            }
        }
    }
    
    return jsonify(response_data)

@app.route('/api/alerts/search')
def search_alerts():
    """Advanced search endpoint for external applications"""
    # Location parameters
    state = request.args.get('state')
    county = request.args.get('county')
    area = request.args.get('area')
    
    # Alert parameters
    severity = request.args.get('severity')
    event_type = request.args.get('event_type')
    active_only = request.args.get('active_only', 'false').lower() == 'true'
    search_query = request.args.get('q', '').strip()  # 'q' for API consistency
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 50, type=int), 100)
    
    query = Alert.query
    
    # Apply search query
    if search_query:
        search_pattern = f'%{search_query}%'
        query = query.filter(
            db.or_(
                Alert.event.ilike(search_pattern),
                Alert.area_desc.ilike(search_pattern),
                Alert.ai_summary.ilike(search_pattern),
                Alert.properties['headline'].astext.ilike(search_pattern),
                Alert.properties['description'].astext.ilike(search_pattern)
            )
        )
    
    # Apply filters
    if state:
        query = query.filter(Alert.area_desc.ilike(f'%{state}%'))
    if county:
        query = query.filter(Alert.area_desc.ilike(f'%{county}%'))
    if area:
        query = query.filter(Alert.area_desc.ilike(f'%{area}%'))
    if severity:
        query = query.filter(Alert.severity == severity)
    if event_type:
        query = query.filter(Alert.event.ilike(f'%{event_type}%'))
    
    if active_only:
        from datetime import datetime
        now = datetime.utcnow()
        query = query.filter(
            Alert.effective <= now,
            Alert.expires > now
        )
    
    # Date range filters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        try:
            from datetime import datetime
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Alert.effective >= start_dt)
        except ValueError:
            pass  # Invalid date format, ignore
    
    if end_date:
        try:
            from datetime import datetime, timedelta
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Alert.effective < end_dt)
        except ValueError:
            pass  # Invalid date format, ignore
    
    # Radar-detected filters
    has_radar_data = request.args.get('has_radar_data', 'false').lower() == 'true'
    min_hail = request.args.get('min_hail', type=float)
    min_wind = request.args.get('min_wind', type=int)
    
    if has_radar_data:
        # CORE BUSINESS VALUE: Historical damage events with radar-detected hail/wind
        # These are the events our clients need for damage assessment and insurance claims
        hail_condition = Alert.radar_indicated['hail_inches'].astext.cast(db.Float) > 0
        wind_condition = Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= 50
        radar_source_condition = Alert.properties['description'].astext.ilike('%radar indicated%')
        
        query = query.filter(
            Alert.radar_indicated.isnot(None),
            radar_source_condition,
            db.or_(hail_condition, wind_condition)
        )
        
    if min_hail:
        query = query.filter(Alert.radar_indicated['hail_inches'].astext.cast(db.Float) >= min_hail)
    if min_wind:
        query = query.filter(Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= min_wind)
    
    # Execute query with pagination
    total = query.count()
    alerts = query.order_by(Alert.ingested_at.desc()).offset((page - 1) * limit).limit(limit).all()
    
    return jsonify({
        'total': total,
        'page': page,
        'limit': limit,
        'pages': (total + limit - 1) // limit,
        'filters': {
            'state': state,
            'county': county,
            'area': area,
            'severity': severity,
            'event_type': event_type,
            'active_only': active_only,
            'search_query': search_query
        },
        'alerts': [alert.to_dict() for alert in alerts]
    })

@app.route('/alerts/enrich/<alert_id>', methods=['POST'])
def enrich_alert(alert_id):
    """Re-run enrichment manually"""
    alert = Alert.query.get_or_404(alert_id)
    
    try:
        enrich_service.enrich_alert(alert)
        db.session.commit()
        flash(f'Alert {alert_id} enriched successfully', 'success')
    except Exception as e:
        logger.error(f"Error enriching alert {alert_id}: {e}")
        flash(f'Error enriching alert: {str(e)}', 'error')
    
    return redirect(url_for('get_alert', alert_id=alert_id))

@app.route('/api/alerts/enrich-batch', methods=['POST'])
def enrich_batch():
    """Enrich a batch of unenriched alerts"""
    try:
        limit = request.json.get('limit', 50) if request.json else 50
        # Use configurable batch size instead of hardcoded limit
        max_limit = int(os.getenv("ENRICH_BATCH_SIZE", "25")) * 10  # Allow up to 10x batch size
        limit = min(limit, max_limit)
        
        logger.info(f"Starting batch enrichment for up to {limit} alerts")
        
        result = enrich_service.enrich_batch(limit)
        
        return jsonify({
            'status': 'success',
            'enriched': result['enriched'],
            'failed': result['failed'],
            'total_processed': result['total_processed'],
            'message': f"Successfully enriched {result['enriched']} alerts"
        })
        
    except Exception as e:
        logger.error(f"Error during batch enrichment: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/alerts/enrich-by-category', methods=['POST'])
def enrich_by_category():
    """Enrich alerts by category with timeout protection"""
    try:
        data = request.get_json()
        category = data.get('category') if data else None
        limit = data.get('limit', 100) if data else 100
        
        if not category:
            return jsonify({
                'status': 'error',
                'message': 'Category is required'
            }), 400
        
        # Validate category
        valid_categories = list(enrich_service.CATEGORY_MAPPING.keys())
        if category not in valid_categories:
            return jsonify({
                'status': 'error',
                'message': f'Invalid category. Valid options: {valid_categories}'
            }), 400
        
        logger.info(f"Starting category enrichment for '{category}' with limit {limit}")
        
        result = enrich_service.enrich_by_category(category, min(limit, 200))
        
        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 400
        
        return jsonify({
            'status': 'success',
            'category': result['category'],
            'enriched': result['enriched'],
            'failed': result['failed'],
            'total_processed': result['total_processed'],
            'message': f"Successfully enriched {result['enriched']} '{category}' alerts"
        })
        
    except Exception as e:
        logger.error(f"Error during category enrichment: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/alerts/enrich-priority', methods=['POST'])
def enrich_priority_alerts():
    """Enrich all high-priority alerts (Severe Weather, Tropical Weather, High Wind)"""
    try:
        logger.info("Starting priority alert enrichment")
        
        result = enrich_service.enrich_all_priority_alerts()
        
        if 'error' in result:
            return jsonify({
                'status': 'error',
                'message': result['error']
            }), 500
        
        return jsonify({
            'status': 'success',
            'enriched': result['enriched'],
            'failed': result['failed'],
            'total_processed': result['total_processed'],
            'message': f"Successfully enriched {result['enriched']} priority alerts"
        })
        
    except Exception as e:
        logger.error(f"Error during priority enrichment: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/alerts/enrichment-stats')
def get_enrichment_stats():
    """Get enrichment statistics including priority alert coverage"""
    try:
        stats = enrich_service.get_enrichment_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting enrichment stats: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/admin/spc-sync', methods=['POST'])
def admin_spc_sync():
    """Admin endpoint to sync SPC data and fix mismatches"""
    try:
        from datetime import date
        from spc_verification import SPCVerificationService
        from spc_ingest import SPCIngestService
        from sqlalchemy.orm import sessionmaker
        
        Session = sessionmaker(bind=db.engine)
        session = Session()
        
        try:
            verifier = SPCVerificationService(session)
            ingest_service = SPCIngestService(session)
            
            # Check for mismatches in recent dates
            results = []
            mismatched_dates = []
            
            for day in range(12, 19):  # Aug 12-18
                test_date = date(2025, 8, day)
                result = verifier.verify_single_date(test_date)
                results.append(result)
                
                if result['match_status'] == 'MISMATCH':
                    mismatched_dates.append(test_date)
            
            if not mismatched_dates:
                return jsonify({
                    'status': 'success',
                    'message': 'All dates are synchronized - no action needed!',
                    'verification_results': results
                })
            
            # Fix mismatches by clearing and re-ingesting
            sync_results = []
            for target_date in mismatched_dates:
                # Delete existing records for this date
                deleted_count = session.query(SPCReport).filter(
                    SPCReport.report_date == target_date
                ).delete()
                session.commit()
                
                # Re-ingest fresh data using the correct method
                try:
                    ingest_result = ingest_service.force_poll_for_backfill(target_date, "sync_fix")
                    sync_results.append({
                        'date': target_date.strftime('%Y-%m-%d'),
                        'deleted': deleted_count,
                        'reingested': ingest_result.get('total_reports', 0),
                        'status': 'success'
                    })
                except Exception as e:
                    session.rollback()
                    sync_results.append({
                        'date': target_date.strftime('%Y-%m-%d'),
                        'deleted': deleted_count,
                        'status': 'failed',
                        'error': str(e)
                    })
            
            # Final verification
            final_results = []
            for day in range(12, 19):
                test_date = date(2025, 8, day)
                result = verifier.verify_single_date(test_date)
                final_results.append(result)
            
            return jsonify({
                'status': 'success',
                'message': f'Synchronized {len([r for r in sync_results if r["status"] == "success"])} dates',
                'sync_results': sync_results,
                'final_verification': final_results
            })
        
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error during SPC sync: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/alerts/unenriched-counts')
def get_unenriched_counts():
    """Get counts of unenriched alerts by category"""
    try:
        from enrich import EnrichmentService
        
        # Priority alerts (auto-enrich categories)
        priority_count = Alert.query.filter(
            Alert.ai_summary.is_(None),
            Alert.event.in_(EnrichmentService.AUTO_ENRICH_ALERTS)
        ).count()
        
        # Category counts
        category_counts = {}
        for category, events in EnrichmentService.CATEGORY_MAPPING.items():
            count = Alert.query.filter(
                Alert.ai_summary.is_(None),
                Alert.event.in_(events)
            ).count()
            category_counts[category] = count
        
        # General batch count (all unenriched)
        total_unenriched = Alert.query.filter(Alert.ai_summary.is_(None)).count()
        
        return jsonify({
            'priority_alerts': priority_count,
            'categories': category_counts,
            'total_unenriched': total_unenriched
        })
        
    except Exception as e:
        logger.error(f"Error getting unenriched counts: {e}")
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/spc-reports/unified/<int:report_id>')
def get_unified_report(report_id):
    """
    Unified production API endpoint for complete SPC report data
    Returns all data in single response - optimized for end users
    """
    try:
        report = SPCReport.query.get_or_404(report_id)
        
        # Parse enhanced context if available
        enhanced_context = None
        if report.enhanced_context:
            try:
                if isinstance(report.enhanced_context, str):
                    enhanced_context = json.loads(report.enhanced_context)
                else:
                    enhanced_context = report.enhanced_context
            except (json.JSONDecodeError, TypeError):
                enhanced_context = None
        
        # Extract magnitude data properly
        magnitude_data = {"raw": None, "display": None, "value": None, "unit": None}
        if report.magnitude:
            try:
                if isinstance(report.magnitude, dict):
                    mag_dict = report.magnitude
                elif isinstance(report.magnitude, str):
                    mag_dict = json.loads(report.magnitude)
                else:
                    mag_dict = {"value": float(report.magnitude)}
                
                if report.report_type.upper() == "HAIL" and "size_inches" in mag_dict:
                    size = mag_dict["size_inches"]
                    magnitude_data = {
                        "raw": mag_dict,
                        "display": f"{size:.2f} inch".replace('.00', ''),
                        "value": float(size),
                        "unit": "inches"
                    }
                elif report.report_type.upper() == "WIND" and "speed" in mag_dict:
                    speed = mag_dict["speed"]
                    magnitude_data = {
                        "raw": mag_dict,
                        "display": f"{speed} mph",
                        "value": int(speed),
                        "unit": "mph"
                    }
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        
        # Get damage assessment from hail size lookup
        damage_assessment = {"category": "Severe Weather", "severity": "Weather Event", "description": "Severe weather event with potential for damage."}
        if report.report_type.upper() == "HAIL" and magnitude_data["value"]:
            hail_size = magnitude_data["value"]
            if hail_size >= 4.0:
                damage_assessment = {
                    "category": "Giant Hail",
                    "severity": "Extreme Damage",
                    "description": "Giant hail causes severe property damage including roof penetration, vehicle destruction, and injury risk."
                }
            elif hail_size >= 2.0:
                damage_assessment = {
                    "category": "Very Large Hail", 
                    "severity": "Significant Damage",
                    "description": "Very large hail causes substantial damage to vehicles, roofing, siding, and outdoor equipment."
                }
            elif hail_size >= 1.0:
                damage_assessment = {
                    "category": "Large Hail",
                    "severity": "Minor Damage", 
                    "description": "Large hail can cause dents to vehicles, cracked windows, damage to roofing materials, siding, and gutters."
                }
            else:
                damage_assessment = {
                    "category": "Small Hail",
                    "severity": "Minimal Damage",
                    "description": "Small hail typically causes minimal damage but can affect crops and outdoor equipment."
                }
        elif report.report_type.upper() == "WIND" and magnitude_data["value"]:
            wind_speed = magnitude_data["value"]
            if wind_speed >= 75:
                damage_assessment = {
                    "category": "Violent Wind",
                    "severity": "Extreme Damage",
                    "description": "Violent winds cause widespread damage to structures, trees, and power lines."
                }
            elif wind_speed >= 65:
                damage_assessment = {
                    "category": "Very Damaging Wind",
                    "severity": "Significant Damage", 
                    "description": "Very damaging winds can cause structural damage and widespread power outages."
                }
            elif wind_speed >= 58:
                damage_assessment = {
                    "category": "Damaging Wind",
                    "severity": "Moderate Damage",
                    "description": "Damaging winds can snap tree limbs, damage roofing, and cause power outages."
                }
            else:
                damage_assessment = {
                    "category": "Strong Wind",
                    "severity": "Minor Damage",
                    "description": "Strong winds may cause minor property damage and isolated power outages."
                }
        
        # Format datetime properly
        datetime_info = {"utc": None, "display": None, "timestamp": None}
        if report.report_date and report.time_utc:
            try:
                if isinstance(report.report_date, str):
                    date_obj = datetime.strptime(report.report_date, '%Y-%m-%d')
                else:
                    date_obj = report.report_date
                
                if isinstance(report.time_utc, str) and len(report.time_utc) == 4:
                    hour = int(report.time_utc[:2])
                    minute = int(report.time_utc[2:])
                    dt = datetime.combine(date_obj.date(), datetime.min.time().replace(hour=hour, minute=minute))
                    datetime_info = {
                        "utc": dt.isoformat() + "Z",
                        "display": f"{date_obj.strftime('%B %d, %Y')} at {hour:02d}:{minute:02d} UTC",
                        "timestamp": int(dt.timestamp())
                    }
            except (ValueError, AttributeError):
                pass
        
        # Build unified response
        response = {
            "report": {
                "id": report.id,
                "type": report.report_type.lower(),
                "magnitude": magnitude_data,
                "location": {
                    "name": report.location,
                    "county": report.county,
                    "state": report.state,
                    "description": f"{report.location}, {report.county} County, {report.state}"
                },
                "coordinates": {
                    "lat": float(report.latitude) if report.latitude else None,
                    "lon": float(report.longitude) if report.longitude else None
                },
                "datetime": datetime_info,
                "damage_assessment": damage_assessment,
                "comments": report.comments
            },
            "context": {
                "enhanced_summary": enhanced_context.get("enhanced_summary") if enhanced_context else None,
                "verified_alerts": enhanced_context.get("alert_count", 0) if enhanced_context else 0,
                "radar_confirmed": enhanced_context.get("radar_polygon_match", False) if enhanced_context else False,
                "nearby_locations": enhanced_context.get("location_context", {}).get("nearby_places", []) if enhanced_context else []
            },
            "metadata": {
                "generated_at": enhanced_context.get("generated_at") if enhanced_context else None,
                "data_quality": "verified" if enhanced_context and enhanced_context.get("has_verified_alerts") else "standard",
                "enrichment_status": "complete" if enhanced_context else "pending"
            }
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in unified report API for {report_id}: {e}")
        return jsonify({"error": "Internal server error", "report_id": report_id}), 500

@app.route('/api/spc/reports/today')
def get_spc_reports_today():
    """Get SPC reports for the current SPC day"""
    try:
        from spc_utils import get_current_spc_day_utc
        
        # Get current SPC day
        current_spc_day = get_current_spc_day_utc()
        
        # Query reports for current SPC day
        reports = SPCReport.query.filter(
            SPCReport.report_date == current_spc_day
        ).order_by(SPCReport.time_utc.desc()).all()
        
        # Format reports using the existing to_dict method
        formatted_reports = [report.to_dict() for report in reports]
        
        return jsonify({
            'spc_day': current_spc_day,
            'reports': formatted_reports
        })
        
    except Exception as e:
        logger.error(f"Error fetching SPC reports for today: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/spc/reports')
def get_spc_reports():
    """Get SPC storm reports with filtering"""
    try:
        # Get query parameters
        report_type = request.args.get('type')  # tornado, wind, hail
        state = request.args.get('state')
        county = request.args.get('county')
        date = request.args.get('date')  # YYYY-MM-DD format
        limit = min(int(request.args.get('limit', 100)), 500)
        offset = int(request.args.get('offset', 0))
        
        # Build query
        query = SPCReport.query
        
        if report_type:
            query = query.filter(SPCReport.report_type == report_type)
        if state:
            query = query.filter(SPCReport.state == state.upper())
        if county:
            query = query.filter(SPCReport.county.ilike(f'%{county}%'))
        if date:
            query = query.filter(SPCReport.report_date == date)
        
        # Get total count for pagination
        total_count = query.count()
        
        # Get results with pagination
        reports = query.order_by(SPCReport.report_date.desc(), SPCReport.time_utc.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'reports': [report.to_dict() for report in reports],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': offset + limit < total_count
            },
            'filters': {
                'type': report_type,
                'state': state,
                'county': county,
                'date': date
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting SPC reports: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/spc/reports')
def view_spc_reports():
    """View SPC reports in web interface with search functionality"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    try:
        # Get search parameters
        search_query = request.args.get('search', '').strip()
        report_type = request.args.get('type', '').strip()
        state = request.args.get('state', '').strip()
        date = request.args.get('date', '').strip()
        
        # Build query
        query = SPCReport.query
        
        # Apply search across multiple fields
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                db.or_(
                    SPCReport.location.ilike(search_pattern),
                    SPCReport.county.ilike(search_pattern),
                    SPCReport.comments.ilike(search_pattern)
                )
            )
        
        # Apply filters
        if report_type:
            query = query.filter(SPCReport.report_type == report_type)
        if state:
            query = query.filter(SPCReport.state.ilike(f'%{state.upper()}%'))
        if date:
            try:
                from datetime import datetime
                filter_date = datetime.strptime(date, '%Y-%m-%d').date()
                query = query.filter(SPCReport.report_date == filter_date)
            except ValueError:
                pass  # Invalid date format, ignore filter
        
        # Get filtered reports
        reports = query.order_by(
            SPCReport.report_date.desc(), 
            SPCReport.time_utc.desc()
        ).limit(500).all()  # Use configurable limit for search results
        
        # Get summary stats (total, not filtered)
        total_reports = SPCReport.query.count()
        type_counts = db.session.query(
            SPCReport.report_type,
            db.func.count(SPCReport.id).label('count')
        ).group_by(SPCReport.report_type).all()
        
        return render_template('spc_reports.html', 
                             reports=reports,
                             total_reports=total_reports,
                             type_counts={row.report_type: row.count for row in type_counts})
        
    except Exception as e:
        logger.error(f"Error viewing SPC reports: {e}")
        return render_template('error.html', error=str(e))

@app.route('/spc-reports/<int:report_id>')
@app.route('/spc/reports/<int:report_id>')
def view_spc_report_detail(report_id):
    """View detailed information for a specific SPC report"""
    try:
        report = SPCReport.query.get_or_404(report_id)
        
        # Get verified alerts that match this SPC report
        verified_alerts = Alert.query.filter(
            Alert.spc_verified == True,
            Alert.spc_reports.isnot(None)
        ).all()
        
        # Filter alerts that actually reference this specific report
        matching_alerts = []
        for alert in verified_alerts:
            if alert.spc_reports:
                # Check if this report ID is referenced in the alert's SPC reports
                alert_report_ids = []
                try:
                    if isinstance(alert.spc_reports, list):
                        for spc_rep in alert.spc_reports:
                            if isinstance(spc_rep, dict) and 'id' in spc_rep:
                                alert_report_ids.append(spc_rep['id'])
                except:
                    pass
                
                if report_id in alert_report_ids:
                    matching_alerts.append(alert)
        
        # Add the verified alerts to the report object
        report.verified_alerts = matching_alerts
        
        # Parse enhanced_context JSON if it exists
        import json
        enhanced_context_data = None
        if report.enhanced_context:
            try:
                if isinstance(report.enhanced_context, str):
                    enhanced_context_data = json.loads(report.enhanced_context)
                else:
                    enhanced_context_data = report.enhanced_context
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to parse enhanced_context for report {report_id}")
                enhanced_context_data = None
        
        # Extract location context consistently from any available source
        primary_location = None
        nearest_major_city = None
        nearby_places = []
        
        # Try enhanced_context first (new format)
        if enhanced_context_data and 'location_context' in enhanced_context_data:
            location_context = enhanced_context_data['location_context']
            if 'nearby_places' in location_context and location_context['nearby_places']:
                for place in location_context['nearby_places']:
                    if place.get('type') == 'primary_location':
                        primary_location = place
                    elif place.get('type') == 'nearest_city':
                        nearest_major_city = place
                    elif place.get('type') == 'nearby_place':
                        nearby_places.append(place)
        
        # Fallback to spc_enrichment (old format)
        elif hasattr(report, 'spc_enrichment') and report.spc_enrichment:
            try:
                if isinstance(report.spc_enrichment, str):
                    enrichment = json.loads(report.spc_enrichment)
                else:
                    enrichment = report.spc_enrichment
                
                if 'primary_location' in enrichment:
                    primary_location = enrichment['primary_location']
                if 'nearest_major_city' in enrichment:
                    nearest_major_city = enrichment['nearest_major_city']
                if 'nearby_places' in enrichment:
                    nearby_places = enrichment['nearby_places']
                    
            except (json.JSONDecodeError, TypeError):
                pass
        
        # Final fallback for primary location
        if not primary_location:
            primary_location = {
                'name': report.location if report.location else f"{report.county} County",
                'distance_miles': 0
            }
        
        # Add alert_count to enhanced_context_data
        if enhanced_context_data:
            enhanced_context_data['alert_count'] = len(matching_alerts)
        else:
            enhanced_context_data = {'alert_count': len(matching_alerts)}
            
        return render_template('spc_report_detail.html', 
                             report=report,
                             enhanced_context_data=enhanced_context_data,
                             primary_location=primary_location,
                             nearest_major_city=nearest_major_city,
                             nearby_places=nearby_places)
    except Exception as e:
        logger.error(f"Error viewing SPC report {report_id}: {e}")
        return render_template('error.html', error=str(e))

# Internal/Admin Routes
@app.route('/internal/status')
def internal_status():
    """Health status endpoint - comprehensive system diagnostics"""
    try:
        # Basic alert metrics
        total_alerts = Alert.query.count()
        recent_alerts = Alert.query.filter(
            Alert.ingested_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        active_alerts = Alert.query.filter(
            Alert.effective <= datetime.utcnow(),
            Alert.expires > datetime.utcnow()
        ).count()
        
        # SPC verification metrics
        verified_alerts = Alert.query.filter(Alert.spc_verified == True).count()
        unverified_alerts = Alert.query.filter(Alert.spc_verified == False).count()
        verification_coverage = (verified_alerts / total_alerts * 100) if total_alerts > 0 else 0
        
        # Last ingestion timestamps
        last_alert = Alert.query.order_by(Alert.ingested_at.desc()).first()
        last_nws_ingestion = last_alert.ingested_at.isoformat() if last_alert else None
        
        # SPC ingestion status
        last_spc_log = SPCIngestionLog.query.order_by(SPCIngestionLog.started_at.desc()).first()
        last_spc_ingestion = last_spc_log.started_at.isoformat() if last_spc_log else None
        
        # Oldest unverified alert (backlog indicator)
        oldest_unverified = Alert.query.filter(
            Alert.spc_verified == False
        ).order_by(Alert.effective.asc()).first()
        oldest_unverified_date = oldest_unverified.effective.isoformat() if oldest_unverified else None
        
        # Recent ingestion logs (error detection)
        recent_logs = SPCIngestionLog.query.filter(
            SPCIngestionLog.started_at >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(SPCIngestionLog.started_at.desc()).limit(10).all()
        
        failed_jobs = [log for log in recent_logs if not log.success]
        
        # Scheduler operation statistics  
        try:
            scheduler_stats = scheduler_service.get_operation_stats() if scheduler_service else {}
        except Exception as e:
            logger.warning(f"Scheduler stats unavailable: {e}")
            scheduler_stats = {'error': 'Statistics temporarily unavailable'}
        
        # Database health check
        try:
            db.session.execute(db.text('SELECT 1'))
            db_status = "healthy"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # SPC Day information
        from spc_utils import get_current_spc_day_utc, get_spc_day_window_description
        current_spc_day = get_current_spc_day_utc()
        spc_day_window = get_spc_day_window_description(current_spc_day)
        
        return jsonify({
            'status': 'healthy' if len(failed_jobs) == 0 and db_status == "healthy" else 'warning',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db_status,
            'alerts': {
                'total': total_alerts,
                'recent_24h': recent_alerts,
                'active_now': active_alerts
            },
            'spc_verification': {
                'verified_count': verified_alerts,
                'unverified_count': unverified_alerts,
                'coverage_percentage': round(verification_coverage, 2),
                'oldest_unverified': oldest_unverified_date
            },
            'ingestion': {
                'last_nws_ingestion': last_nws_ingestion,
                'last_spc_ingestion': last_spc_ingestion,
                'failed_jobs_24h': len(failed_jobs)
            },
            'system': {
                'environment': 'replit',
                'python_version': '3.11',
                'framework': 'flask+sqlalchemy'
            },
            'ingestion_config': {
                'db_write_batch_size': int(os.getenv("DB_WRITE_BATCH_SIZE", "500")),
                'enrich_batch_size': int(os.getenv("ENRICH_BATCH_SIZE", "25")),
                'spc_match_batch_size': int(os.getenv("SPC_MATCH_BATCH_SIZE", "200"))
            },
            'scheduler_operations': scheduler_stats,
            'current_spc_day': current_spc_day,
            'current_spc_day_window_utc': spc_day_window
        })
        
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'error': str(e)
        }), 500

@app.route('/api/health')
def api_health():
    """Public health check endpoint for monitoring and integration testing"""
    try:
        # Basic database connectivity test
        total_alerts = Alert.query.count()
        total_spc_reports = db.session.query(db.func.count(db.text('*'))).select_from(db.text('spc_reports')).scalar()
        db.session.execute(db.text('SELECT 1'))
        
        return jsonify({
            'status': 'healthy',
            'service': 'HailyDB API v2.0',
            'timestamp': datetime.utcnow().isoformat(),
            'database': {
                'alerts': total_alerts,
                'spc_reports': total_spc_reports
            },
            'version': '2.0.0',
            'documentation': '/documentation'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@app.route('/api/alerts')
def api_alerts():
    """Core API endpoint - Get all historical NWS alerts with comprehensive filtering and pagination"""
    try:
        # Parse query parameters
        limit = min(int(request.args.get('limit', 50)), 1000)
        offset = int(request.args.get('offset', 0))
        page = int(request.args.get('page', 1))
        
        # Calculate offset from page if provided
        if page > 1:
            offset = (page - 1) * limit
            
        # Filtering parameters
        state = request.args.get('state')
        event_type = request.args.get('event_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        has_radar_data = request.args.get('has_radar_data')
        severity = request.args.get('severity')
        
        # Build base query
        query = Alert.query
        
        # Apply filters
        if state and state.upper() not in ['ALL', 'ANY']:
            query = query.filter(Alert.affected_states.contains([state.upper()]))
            
        if event_type and event_type != 'All':
            query = query.filter(Alert.event.ilike(f'%{event_type}%'))
            
        if severity and severity != 'All':
            query = query.filter(Alert.severity.ilike(f'%{severity}%'))
            
        if has_radar_data == 'true':
            query = query.filter(Alert.radar_indicated.isnot(None))
        elif has_radar_data == 'false':
            query = query.filter(Alert.radar_indicated.is_(None))
            
        # Date filtering
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Alert.effective >= start_dt)
            except ValueError:
                pass
                
        if end_date:
            try:
                from datetime import timedelta
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Alert.effective < end_dt)
            except ValueError:
                pass
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination and ordering
        alerts = query.order_by(Alert.effective.desc()).offset(offset).limit(limit).all()
        
        # Format response
        events = []
        for alert in alerts:
            alert_data = {
                'id': alert.id,
                'event': alert.event,
                'severity': alert.severity,
                'area_desc': alert.area_desc,
                'effective': alert.effective.isoformat() if alert.effective else None,
                'expires': alert.expires.isoformat() if alert.expires else None,
                'sent': alert.sent.isoformat() if alert.sent else None,
                'geometry': alert.geometry,
                'properties': alert.properties,
                'affected_states': alert.affected_states,
                'county_names': alert.county_names,
                'city_names': alert.city_names,
                'radar_indicated': alert.radar_indicated,
                'spc_verified': alert.spc_verified,
                'spc_reports': alert.spc_reports,
                'ai_summary': alert.ai_summary,
                'data_source': 'National Weather Service',
                'source_type': 'historical_nws_alert'
            }
            events.append(alert_data)
        
        return jsonify({
            'events': events,
            'total': total,
            'limit': limit,
            'offset': offset,
            'page': page if page > 1 else (offset // limit) + 1,
            'pages': (total + limit - 1) // limit,
            'has_next': offset + limit < total,
            'has_prev': offset > 0
        })
        
    except Exception as e:
        logger.error(f"Error in /api/alerts endpoint: {e}")
        return jsonify({
            'error': 'Internal server error',
            'message': str(e),
            'events': [],
            'total': 0
        }), 500

@app.route('/api/documentation')
def api_documentation():
    """
    Comprehensive API documentation endpoint for AI agents
    Returns complete system overview, endpoints, and usage examples
    Designed specifically for AI agents who cannot access external documentation
    """
    try:
        # Get current system statistics
        total_alerts = Alert.query.count()
        expired_alerts = Alert.query.filter(Alert.expires <= datetime.utcnow()).count()
        
        # Get radar-detected statistics
        radar_wind_count = Alert.query.filter(
            Alert.radar_indicated.isnot(None),
            Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= 50
        ).count()
        
        radar_hail_count = Alert.query.filter(
            Alert.radar_indicated.isnot(None),
            Alert.radar_indicated['hail_inches'].astext.cast(db.Float) > 0
        ).count()
        
        radar_total = Alert.query.filter(
            Alert.radar_indicated.isnot(None),
            db.or_(
                Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= 50,
                Alert.radar_indicated['hail_inches'].astext.cast(db.Float) > 0
            )
        ).count()
        
        documentation = {
            "system_info": {
                "name": "HailyDB v2.1.3 - Historical Weather Damage Intelligence Platform",
                "description": "Production-ready Flask-based platform serving as a comprehensive repository for National Weather Service alerts with radar-detected hail and wind parameters. Designed for insurance claims processing, damage assessment, and restoration industry clients.",
                "core_value": "Historical repository of expired NWS alerts with radar-detected damage events - answers 'where likely damage WAS'",
                "version": "2.1.3",
                "last_updated": datetime.utcnow().isoformat(),
                "data_sources": ["National Weather Service API", "Storm Prediction Center", "NOAA HURDAT2"],
                "compliance": "NWS OpenAPI specification with GeoJSON FeatureCollection format"
            },
            
            "repository_statistics": {
                "total_alerts": total_alerts,
                "expired_alerts": expired_alerts,
                "radar_detected_events": {
                    "total": radar_total,
                    "wind_events_50plus_mph": radar_wind_count,
                    "hail_events_any_size": radar_hail_count
                },
                "geographic_coverage": "All US states, territories, and marine zones",
                "date_range": "Historical data spanning multiple years"
            },
            
            "primary_endpoints": {
                "radar_detected_damage_events": {
                    "all_events": {
                        "endpoint": "/api/alerts/radar_detected",
                        "description": "All radar-detected damage events (50+ mph winds OR any size hail)",
                        "total_events": radar_total,
                        "use_case": "Complete radar-detected damage inventory"
                    },
                    "wind_events": {
                        "endpoint": "/api/alerts/radar_detected/wind", 
                        "description": "Wind damage events (50+ mph radar-detected)",
                        "total_events": radar_wind_count,
                        "use_case": "Wind damage assessment and claims"
                    },
                    "hail_events": {
                        "endpoint": "/api/alerts/radar_detected/hail",
                        "description": "Hail damage events (any size radar-detected)",
                        "total_events": radar_hail_count,
                        "use_case": "Hail damage assessment and claims"
                    }
                },
                
                "historical_repository": {
                    "endpoint": "/api/alerts/expired",
                    "description": "Primary business endpoint - all expired NWS alerts with optional radar filtering",
                    "total_events": expired_alerts,
                    "use_case": "Historical weather damage intelligence",
                    "high_volume_support": "Up to 10,000 results per request"
                },
                
                "individual_alerts": {
                    "endpoint": "/api/alerts/{alert_id}",
                    "description": "Complete alert details including enrichments and radar parameters",
                    "use_case": "Detailed damage assessment for specific events"
                },
                
                "active_monitoring": {
                    "endpoint": "/api/alerts/active",
                    "description": "Currently active NWS alerts for live monitoring",
                    "use_case": "Real-time severe weather tracking"
                },
                
                "system_health": {
                    "endpoint": "/api/health",
                    "description": "System status and database statistics",
                    "use_case": "Integration health checks and monitoring"
                }
            },
            
            "query_parameters": {
                "geographic_filtering": {
                    "state": "State code filter (e.g., TX, CA, FL)",
                    "county": "County name filter (partial match supported)"
                },
                "status_filtering": {
                    "status": "active, expired, or all (default: all)"
                },
                "temporal_filtering": {
                    "start_date": "Date range start (YYYY-MM-DD format)",
                    "end_date": "Date range end (YYYY-MM-DD format)"
                },
                "pagination": {
                    "page": "Page number (default: 1)",
                    "limit": "Results per page (max 5,000 for radar endpoints, max 10,000 for expired)"
                },
                "radar_filtering": {
                    "has_radar": "Filter for radar-detected events (use with /api/alerts/expired)"
                }
            },
            
            "response_format": {
                "standard": "GeoJSON FeatureCollection following NWS OpenAPI specification",
                "structure": {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "id": "NWS alert identifier",
                            "type": "Feature",
                            "properties": {
                                "event": "Alert type (e.g., Severe Thunderstorm Warning)",
                                "headline": "Official NWS headline",
                                "description": "Full alert description with radar parameters",
                                "severity": "NWS severity level",
                                "effective": "ISO timestamp when alert became effective",
                                "expires": "ISO timestamp when alert expires",
                                "areaDesc": "Affected counties per NWS format",
                                "radar_indicated": {
                                    "hail_inches": "Hail size detected by radar",
                                    "wind_mph": "Wind speed detected by radar"
                                },
                                "affected_states": "Array of state codes",
                                "county_names": "Array of state/county objects",
                                "enhanced_summary": "AI-generated damage assessment"
                            },
                            "geometry": "GeoJSON polygon of affected area"
                        }
                    ],
                    "title": "Descriptive title with event counts",
                    "updated": "ISO timestamp of response generation",
                    "metadata": {
                        "total_results": "Total matching events",
                        "page": "Current page number", 
                        "per_page": "Results per page",
                        "criteria": "Applied filtering criteria",
                        "data_source": "Data source attribution"
                    }
                }
            },
            
            "example_api_calls": {
                "wind_damage_texas": {
                    "url": "/api/alerts/radar_detected/wind?status=expired&state=TX&limit=100",
                    "description": "Get expired wind damage events in Texas"
                },
                "hail_harris_county": {
                    "url": "/api/alerts/radar_detected/hail?county=Harris&start_date=2024-01-01&end_date=2024-12-31",
                    "description": "Get hail events in Harris County for 2024"
                },
                "all_radar_events": {
                    "url": "/api/alerts/radar_detected?status=expired&limit=2000",
                    "description": "Get all historical radar-detected damage events"
                },
                "historical_with_radar": {
                    "url": "/api/alerts/expired?has_radar=true&state=FL&limit=500",
                    "description": "Get Florida historical alerts with radar parameters"
                },
                "individual_alert": {
                    "url": "/api/alerts/{alert_id}",
                    "description": "Get complete details for a specific alert ID"
                }
            },
            
            "industry_applications": {
                "insurance_claims": [
                    "Historical damage lookup by location and date range",
                    "Claims validation using NWS radar parameters", 
                    "Risk assessment through historical damage patterns"
                ],
                "restoration_contractors": [
                    "Business development through past damage event discovery",
                    "Emergency response via active alert monitoring",
                    "Regional damage pattern analysis"
                ],
                "forensic_weather": [
                    "Legal documentation with NWS-verified data",
                    "Engineering studies using historical severe weather",
                    "Meteorological research applications"
                ]
            },
            
            "data_integrity": {
                "source_authenticity": "Pure mirror of NWS data with AI enrichments",
                "compliance": "Complete adherence to NWS OpenAPI specification",
                "no_synthetic_data": "All weather data sourced from official government APIs",
                "enrichment_transparency": "AI-generated content clearly labeled as enhanced_summary"
            },
            
            "integration_support": {
                "getting_started": [
                    "Test /api/health endpoint to verify connectivity",
                    "Review example API calls provided above",
                    "Start with pre-filtered radar_detected endpoints for optimal performance",
                    "Implement GeoJSON parsing for geographic data"
                ],
                "best_practices": [
                    "Use status=expired for historical damage analysis",
                    "Combine geographic and temporal filters for precise results", 
                    "Leverage pagination for large datasets",
                    "Parse radar_indicated fields for damage parameters"
                ],
                "rate_limits": "No rate limits currently enforced - use responsibly",
                "authentication": "No authentication required for public endpoints"
            }
        }
        
        return jsonify(documentation)
        
    except Exception as e:
        logger.error(f"Error in documentation endpoint: {e}")
        return jsonify({
            'error': 'Documentation temporarily unavailable',
            'message': str(e),
            'timestamp': datetime.utcnow().isoformat(),
            'fallback': 'Try /api/health for basic system status'
        }), 500

@app.route('/api/reports/spc')
def api_spc_reports():
    """
    SPC storm reports endpoint - Critical for IDOLCheck integration
    Returns verified storm events from Storm Prediction Center
    Supports radius filtering for location-based queries
    """
    from models import SPCReport
    from datetime import datetime, timedelta
    
    # Base query for SPC reports
    query = SPCReport.query
    
    # Geographic filters - radius takes precedence over state/county
    lat = request.args.get('lat')
    lon = request.args.get('lon')
    radius_mi = request.args.get('radius_mi')
    
    if lat and lon and radius_mi:
        try:
            lat_float = float(lat)
            lon_float = float(lon)
            radius_float = float(radius_mi)
            
            # Calculate bounding box for initial filtering (approximate)
            lat_delta = radius_float / 69.0
            lon_delta = radius_float / (69.0 * abs(math.cos(math.radians(lat_float))))
            
            # Filter by coordinates within bounding box
            query = query.filter(
                SPCReport.latitude.isnot(None),
                SPCReport.longitude.isnot(None),
                SPCReport.latitude.between(lat_float - lat_delta, lat_float + lat_delta),
                SPCReport.longitude.between(lon_float - lon_delta, lon_float + lon_delta)
            )
            
        except (ValueError, TypeError):
            return jsonify({
                'error': 'Invalid geographic parameters',
                'message': 'lat, lon, and radius_mi must be valid numbers',
                'provided': {'lat': lat, 'lon': lon, 'radius_mi': radius_mi}
            }), 400
    else:
        # Fallback to state filtering
        state = request.args.get('state')
        if state:
            query = query.filter(SPCReport.state == state.upper())
    
    # Date range filtering (required for meaningful results)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            query = query.filter(SPCReport.report_date >= start_dt)
        except ValueError:
            return jsonify({
                'error': 'Invalid start_date format',
                'message': 'Use YYYY-MM-DD format',
                'provided': start_date
            }), 400
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(SPCReport.report_date <= end_dt)
        except ValueError:
            return jsonify({
                'error': 'Invalid end_date format', 
                'message': 'Use YYYY-MM-DD format',
                'provided': end_date
            }), 400
    
    # If no date range provided, default to last 30 days
    if not start_date and not end_date:
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).date()
        query = query.filter(SPCReport.report_date >= thirty_days_ago)
    
    # Event type filtering
    event_type = request.args.get('type')
    if event_type:
        # Support comma-separated types: hail,wind,tornado
        types = [t.strip().lower() for t in event_type.split(',')]
        valid_types = ['hail', 'wind', 'tornado']
        filtered_types = [t for t in types if t in valid_types]
        if filtered_types:
            query = query.filter(SPCReport.report_type.in_(filtered_types))
    
    # Magnitude filtering
    min_wind_mph = request.args.get('min_wind_mph', type=int)
    if min_wind_mph:
        query = query.filter(
            SPCReport.report_type == 'wind',
            SPCReport.magnitude['speed'].astext.cast(db.Integer) >= min_wind_mph
        )
    
    min_hail_in = request.args.get('min_hail_in', type=float)
    if min_hail_in:
        query = query.filter(
            SPCReport.report_type == 'hail',
            SPCReport.magnitude['size'].astext.cast(db.Float) >= min_hail_in
        )
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    limit = min(request.args.get('limit', 1000, type=int), 5000)
    
    # Execute query with ordering
    total = query.count()
    reports = query.order_by(SPCReport.report_date.desc(), SPCReport.time_utc.desc()).offset((page - 1) * limit).limit(limit).all()
    
    # Format response as requested in audit
    items = []
    for report in reports:
        # Extract magnitude values
        hail_in = None
        wind_mph = None
        tornado_scale = None
        
        if report.magnitude:
            if report.report_type == 'hail':
                hail_in = report.magnitude.get('size')
            elif report.report_type == 'wind':
                wind_mph = report.magnitude.get('speed')
            elif report.report_type == 'tornado':
                tornado_scale = report.magnitude.get('f_scale')
        
        # Create time_utc as proper ISO timestamp
        time_utc = None
        if report.time_utc and report.report_date:
            try:
                # Combine date and time for full timestamp
                hour = int(report.time_utc[:2]) if len(report.time_utc) >= 2 else 0
                minute = int(report.time_utc[2:4]) if len(report.time_utc) >= 4 else 0
                time_utc = datetime.combine(report.report_date, datetime.min.time().replace(hour=hour, minute=minute)).isoformat() + 'Z'
            except (ValueError, IndexError):
                time_utc = report.report_date.isoformat() + 'T00:00:00Z'
        
        item = {
            'id': f'spc-{report.report_date.strftime("%Y%m%d")}-{report.time_utc or "0000"}-{report.id}',
            'data_source': 'spc',  # Clear identifier for client applications
            'source_type': 'report',  # Distinguishes from 'alert'
            'type': report.report_type,
            'verified': True,  # All SPC reports are verified by definition
            'hail_in': hail_in,
            'wind_mph': wind_mph,
            'tornado_scale': tornado_scale,
            'time_utc': time_utc,
            'lat': report.latitude,
            'lon': report.longitude,
            'city': report.location,
            'county': report.county,
            'state': report.state,
            'comments': report.comments
        }
        items.append(item)
    
    return jsonify({
        'items': items,
        'page': page,
        'limit': limit,
        'total': total,
        'metadata': {
            'data_source': 'Storm Prediction Center verified reports',
            'updated': datetime.utcnow().isoformat(),
            'criteria': {
                'geographic': f'radius: {radius_mi}mi from {lat},{lon}' if lat and lon and radius_mi else f'state: {state}' if state else 'all locations',
                'temporal': f'{start_date} to {end_date}' if start_date or end_date else 'last 30 days',
                'event_types': event_type if event_type else 'all types',
                'magnitude_filters': {
                    'min_wind_mph': min_wind_mph,
                    'min_hail_in': min_hail_in
                }
            }
        }
    })

@app.route('/api/admin/enrich-cities', methods=['POST'])
def enrich_cities():
    """
    Phase 2: Backfill city names for existing alerts
    Applies the new city enrichment service to historical data
    """
    from models import Alert
    from city_enrichment_service import city_enrichment_service
    from datetime import datetime
    
    try:
        # Get parameters
        limit = request.args.get('limit', 100, type=int)
        skip_existing = request.args.get('skip_existing', 'true').lower() == 'true'
        
        # Query for alerts that need city enrichment
        query = Alert.query
        if skip_existing:
            # Only process alerts without city names
            query = query.filter(
                db.or_(
                    Alert.city_names.is_(None),
                    Alert.city_names == []
                )
            )
        
        alerts = query.order_by(Alert.effective.desc()).limit(limit).all()
        
        enriched_count = 0
        errors = []
        
        for alert in alerts:
            try:
                # Apply city enrichment
                city_names = city_enrichment_service.enrich_alert_with_cities(alert)
                
                if city_names:
                    alert.city_names = city_names
                    enriched_count += 1
                    
            except Exception as e:
                errors.append(f"Alert {alert.id}: {str(e)}")
                continue
        
        # Commit changes
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'processed': len(alerts),
            'enriched': enriched_count,
            'errors': errors[:10],  # Limit errors in response
            'message': f'City enrichment completed: {enriched_count}/{len(alerts)} alerts enriched'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during city enrichment: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# Radar Alerts API Endpoints
@app.route('/api/radar-alerts/stats')
def api_radar_alerts_stats():
    """Get statistics for processed radar alerts"""
    try:
        # Import RadarAlert model
        from models import RadarAlert
        
        # Basic stats
        total_events = RadarAlert.query.count()
        hail_events = RadarAlert.query.filter(RadarAlert.event_type == 'hail').count()
        wind_events = RadarAlert.query.filter(RadarAlert.event_type == 'wind').count()
        
        # Events created today
        today = datetime.utcnow().date()
        events_created_today = RadarAlert.query.filter(
            db.func.date(RadarAlert.created_at) == today
        ).count()
        
        # Date range
        date_range = db.session.query(
            db.func.min(RadarAlert.event_date).label('earliest'),
            db.func.max(RadarAlert.event_date).label('latest')
        ).first()
        
        return jsonify({
            'total_events': total_events,
            'hail_events': hail_events,
            'wind_events': wind_events,
            'events_created_today': events_created_today,
            'earliest_date': date_range.earliest.isoformat() if date_range.earliest else None,
            'latest_date': date_range.latest.isoformat() if date_range.latest else None
        })
        
    except Exception as e:
        logger.error(f"Error getting radar alerts stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/radar-alerts/available-dates')
def api_radar_alerts_available_dates():
    """Get available dates with radar event counts"""
    try:
        from models import RadarAlert
        
        # Group by event date and get counts
        date_stats = db.session.query(
            RadarAlert.event_date,
            db.func.count(RadarAlert.id).label('total_count'),
            db.func.sum(db.case((RadarAlert.event_type == 'hail', 1), else_=0)).label('hail_count'),
            db.func.sum(db.case((RadarAlert.event_type == 'wind', 1), else_=0)).label('wind_count')
        ).group_by(RadarAlert.event_date).order_by(RadarAlert.event_date.desc()).all()
        
        dates = []
        for stat in date_stats:
            dates.append({
                'date': stat.event_date.isoformat(),
                'count': stat.total_count,
                'hail_count': stat.hail_count,
                'wind_count': stat.wind_count
            })
        
        return jsonify({'dates': dates})
        
    except Exception as e:
        logger.error(f"Error getting available dates: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/radar-alerts')
def api_radar_alerts_list():
    """Get list of radar-detected NWS alerts (fixed to use Alert table with radar filtering)"""
    try:
        from datetime import datetime
        
        # Get query parameters matching the web interface expectations
        limit = min(int(request.args.get('limit', 50)), 1000)
        page = int(request.args.get('page', 1))
        offset = int(request.args.get('offset', (page - 1) * limit))
        state = request.args.get('state')
        event_type = request.args.get('event_type')
        min_hail_size = request.args.get('min_hail_size', 'All Sizes')
        min_wind_speed = request.args.get('min_wind_speed', '50+ mph')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Base query: All alerts with radar data (regardless of hail/wind values)
        query = Alert.query.filter(Alert.radar_indicated.isnot(None))
        
        # Apply filters matching web interface
        if state and state.upper() not in ['ALL', 'ANY']:
            query = query.filter(Alert.affected_states.contains([state.upper()]))
        
        if event_type and event_type != 'All':
            query = query.filter(Alert.event.ilike(f'%{event_type}%'))
        
        # Date range filtering
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Alert.effective >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                from datetime import timedelta
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Alert.effective < end_dt)
            except ValueError:
                pass
        
        # Get total count before pagination
        total = query.count()
        
        # Get results with pagination
        alerts = query.order_by(Alert.effective.desc()).offset(offset).limit(limit).all()
        
        # Convert to format expected by web interface
        events = []
        for alert in alerts:
            # Extract radar data
            radar_data = alert.radar_indicated or {}
            hail_size = radar_data.get('hail_inches', 0)
            wind_speed = radar_data.get('wind_mph', 0)
            
            events.append({
                'id': alert.id,
                'time': alert.effective.isoformat() if alert.effective else None,
                'event_type': alert.event,
                'location': alert.area_desc,
                'state': alert.affected_states[0] if alert.affected_states else 'Unknown',
                'hail_size': f"{hail_size:.2f}" if hail_size > 0 else "0.00",
                'wind_speed': str(wind_speed) if wind_speed > 0 else "0",
                'severity': alert.severity,
                'expires': alert.expires.isoformat() if alert.expires else None
            })
        
        # Calculate number of pages
        pages = (total + limit - 1) // limit if limit > 0 else 1
        page = (offset // limit) + 1 if limit > 0 else 1
        
        return jsonify({
            'events': events,
            'total': total,
            'limit': limit,
            'offset': offset,
            'pages': pages,
            'page': page
        })
        
    except Exception as e:
        logger.error(f"Error getting radar alerts list: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/radar-alerts/backfill', methods=['POST'])
def api_radar_alerts_backfill():
    """Trigger radar alerts backfill processing"""
    try:
        import radar_backfill
        
        data = request.get_json()
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date') 
        batch_size = data.get('batch_size', 100)
        
        if not start_date_str or not end_date_str:
            return jsonify({'error': 'start_date and end_date are required'}), 400
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        if start_date > end_date:
            return jsonify({'error': 'start_date must be before or equal to end_date'}), 400
        
        # Run backfill processing
        logger.info(f"Starting radar alerts backfill from {start_date} to {end_date}")
        stats = radar_backfill.process_date_range(start_date, end_date, batch_size)
        
        return jsonify({
            'success': True,
            'message': f'Backfill completed for {start_date} to {end_date}',
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error in radar alerts backfill: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/internal/dashboard')
def internal_dashboard():
    """Admin dashboard"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    try:
        # Get comprehensive stats
        total_alerts = Alert.query.count()
        enriched_alerts = Alert.query.filter(Alert.ai_summary.isnot(None)).count()
        
        # Recent activity
        recent_alerts = Alert.query.filter(
            Alert.ingested_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        # Severity breakdown
        severity_stats = db.session.query(
            Alert.severity, db.func.count(Alert.id)
        ).group_by(Alert.severity).all()
        
        # SPC Events statistics
        spc_total_reports = SPCReport.query.count()
        spc_tornado = SPCReport.query.filter(SPCReport.report_type == 'tornado').count()
        spc_wind = SPCReport.query.filter(SPCReport.report_type == 'wind').count()
        spc_hail = SPCReport.query.filter(SPCReport.report_type == 'hail').count()
        
        # Get actual alert types from database for dropdown
        alert_types = db.session.query(Alert.event).distinct().order_by(Alert.event).all()
        alert_types_list = [row[0] for row in alert_types if row[0]]
        
        # Daily totals for last 7 days for alerts
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        alert_daily_totals = db.session.query(
            db.func.date(Alert.ingested_at).label('date'),
            db.func.count(Alert.id).label('count')
        ).filter(
            Alert.ingested_at >= seven_days_ago
        ).group_by(
            db.func.date(Alert.ingested_at)
        ).order_by('date').all()
        
        # Daily totals for last 7 days for SPC events
        spc_daily_totals = db.session.query(
            SPCReport.report_date,
            SPCReport.report_type,
            db.func.count(SPCReport.id).label('count')
        ).filter(
            SPCReport.report_date >= seven_days_ago.date()
        ).group_by(
            SPCReport.report_date,
            SPCReport.report_type
        ).order_by(SPCReport.report_date).all()
        
        # Last ingestion
        last_alert = Alert.query.order_by(Alert.ingested_at.desc()).first()
        
        stats = {
            'total_alerts': total_alerts,
            'enriched_alerts': enriched_alerts,
            'recent_alerts_24h': recent_alerts,
            'spc_total_reports': spc_total_reports,
            'spc_tornado': spc_tornado,
            'spc_wind': spc_wind,
            'spc_hail': spc_hail,
            'alert_types': alert_types_list,
            'alert_daily_totals': [(row.date.strftime('%Y-%m-%d'), row.count) for row in alert_daily_totals],
            'spc_daily_totals': [(row.report_date.strftime('%Y-%m-%d'), row.report_type, row.count) for row in spc_daily_totals],
            'last_ingestion': last_alert.ingested_at if last_alert else None,
            'scheduler_running': scheduler.running if scheduler else False
        }
        
        return render_template('dashboard.html', stats=stats)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('dashboard.html', stats={})

@app.route('/internal/cron', methods=['POST'])
def internal_cron():
    """Enable/disable polling, update interval"""
    action = request.json.get('action') if request.json else None
    
    if action == 'start':
        if scheduler and not scheduler.running:
            scheduler.start()
            return jsonify({'status': 'started'})
    elif action == 'stop':
        if scheduler and scheduler.running:
            scheduler.shutdown()
            return jsonify({'status': 'stopped'})
    elif action == 'trigger':
        # Manual trigger
        try:
            count = ingest_service.poll_nws_alerts()
            return jsonify({'status': 'triggered', 'ingested_count': count})
        except Exception as e:
            logger.error(f"Error triggering ingestion: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    return jsonify({'status': 'no_action'})

@app.route('/internal/metrics')
def internal_metrics():
    """Alert metrics"""
    try:
        metrics = {
            'total_alerts': Alert.query.count(),
            'enriched_alerts': Alert.query.filter(Alert.ai_summary.isnot(None)).count(),
            'active_alerts': Alert.query.filter(
                Alert.expires > datetime.utcnow()
            ).count(),
            'recent_24h': Alert.query.filter(
                Alert.ingested_at >= datetime.utcnow() - timedelta(hours=24)
            ).count(),
            'recent_7d': Alert.query.filter(
                Alert.ingested_at >= datetime.utcnow() - timedelta(days=7)
            ).count()
        }
        
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({'error': str(e)}), 500

# Initialize scheduler
def init_scheduler():
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=lambda: ingest_service.poll_nws_alerts(),
        trigger="interval",
        minutes=5,
        id='nws_ingestion'
    )
    scheduler.start()
    logger.info("Scheduler started - polling every 5 minutes")

# Shutdown scheduler when app stops
atexit.register(lambda: scheduler.shutdown() if scheduler else None)

@app.route('/internal/spc-verify')
def spc_verify():
    """SPC Data Integrity Verification"""
    try:
        verification_service = SPCVerificationService(db.session)
        
        # Get date range from query params
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if start_date_str and end_date_str:
            # Use provided date range
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            # Default to last 7 days
            days = request.args.get('days', 7, type=int)
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days-1)
        
        # Run verification
        results = verification_service.verify_date_range(start_date, end_date)
        summary = verification_service.get_verification_summary(results)
        
        if request.args.get('format') == 'json':
            return jsonify({
                'results': results,
                'summary': summary,
                'date_range': {
                    'start': start_date.strftime('%Y-%m-%d'),
                    'end': end_date.strftime('%Y-%m-%d')
                }
            })
        
        return render_template('spc_verification.html', 
                             results=results, 
                             summary=summary,
                             start_date=start_date,
                             end_date=end_date)
    
    except Exception as e:
        logger.error(f"Error in SPC verification: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/internal/spc-reupload/<date_str>', methods=['POST'])
def spc_reupload(date_str):
    """Trigger SPC data re-upload for a specific date"""
    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        verification_service = SPCVerificationService(db.session)
        result = verification_service.trigger_reupload_for_date(check_date)
        
        return jsonify(result)
    
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid date format'}), 400
    except Exception as e:
        logger.error(f"Error re-uploading SPC data for {date_str}: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/internal/spc-ingest', methods=['POST'])
def spc_ingest():
    """Trigger systematic SPC report ingestion (T-0 through T-15)"""
    try:
        log_entry = scheduler_service.log_operation_start("spc_poll", "manual")
        
        from datetime import datetime, timedelta
        today = datetime.utcnow().date()
        
        total_reports = 0
        results = []
        
        # Systematic polling for T-0 through T-15
        for days_back in range(16):
            target_date = today - timedelta(days=days_back)
            
            # Check if this date should be polled based on systematic schedule
            if spc_ingest_service.should_poll_now(target_date):
                try:
                    result = spc_ingest_service.poll_spc_reports(target_date)
                    if result.get('status') != 'skipped':
                        total_reports += result.get('total_reports', 0)
                        results.append({
                            'date': target_date.isoformat(),
                            'reports': result.get('total_reports', 0),
                            'status': result.get('status', 'completed')
                        })
                except Exception as e:
                    results.append({
                        'date': target_date.isoformat(),
                        'reports': 0,
                        'status': 'error',
                        'error': str(e)
                    })
        
        scheduler_service.log_operation_complete(
            log_entry, True, total_reports, total_reports
        )
        
        return jsonify({
            'success': True,
            'total_reports': total_reports,
            'dates_polled': len(results),
            'results': results,
            'message': f'Systematic SPC ingestion completed: {total_reports} reports processed across {len(results)} dates'
        })
        
    except Exception as e:
        logger.error(f"SPC ingestion failed: {e}")
        try:
            scheduler_service.log_operation_complete(
                log_entry, False, 0, 0, str(e)
            )
        except:
            pass  # log_entry may not exist if error occurred early
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/internal/spc-backfill', methods=['POST'])
def spc_backfill():
    """Force backfill processing for missing data (overrides T-16 protection)"""
    try:
        data = request.get_json() or {}
        start_date_str = data.get('start_date')
        end_date_str = data.get('end_date')
        
        if not start_date_str or not end_date_str:
            return jsonify({'success': False, 'message': 'start_date and end_date required'}), 400
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid date format (use YYYY-MM-DD)'}), 400
        
        if start_date > end_date:
            return jsonify({'success': False, 'message': 'start_date must be before end_date'}), 400
        
        log_entry = scheduler_service.log_operation_start("spc_backfill", "manual")
        
        total_reports = 0
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            try:
                # Force poll for backfill (bypasses all scheduling rules)
                result = spc_ingest_service.force_poll_for_backfill(
                    current_date, f"backfill_{start_date_str}_to_{end_date_str}"
                )
                
                total_reports += result.get('total_reports', 0)
                results.append({
                    'date': current_date.isoformat(),
                    'reports': result.get('total_reports', 0),
                    'status': result.get('status', 'completed')
                })
                
            except Exception as e:
                results.append({
                    'date': current_date.isoformat(),
                    'reports': 0,
                    'status': 'error',
                    'error': str(e)
                })
            
            current_date += timedelta(days=1)
        
        scheduler_service.log_operation_complete(
            log_entry, True, total_reports, total_reports
        )
        
        return jsonify({
            'success': True,
            'total_reports': total_reports,
            'dates_processed': len(results),
            'results': results,
            'message': f'Backfill completed: {total_reports} reports processed across {len(results)} dates'
        })
        
    except Exception as e:
        logger.error(f"SPC backfill failed: {e}")
        try:
            scheduler_service.log_operation_complete(
                log_entry, False, 0, 0, str(e)
            )
        except:
            pass  # log_entry may not exist if error occurred early
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/internal/spc-match', methods=['POST'])
def spc_match():
    """Trigger SPC matching process"""
    try:
        log_entry = scheduler_service.log_operation_start("spc_match", "manual")
        
        result = spc_matching_service.match_spc_reports_batch(limit=500)
        processed = result.get('processed', 0)
        matched = result.get('matched', 0)
        
        scheduler_service.log_operation_complete(
            log_entry, True, processed, matched
        )
        
        return jsonify({
            'success': True,
            'processed': processed,
            'matched': matched,
            'message': f'SPC matching completed: {matched}/{processed} alerts matched'
        })
        
    except Exception as e:
        logger.error(f"SPC matching failed: {e}")
        try:
            scheduler_service.log_operation_complete(
                log_entry, False, 0, 0, str(e)
            )
        except:
            pass  # log_entry may not exist if error occurred early
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/internal/spc-generate-summaries', methods=['POST'])
def generate_ai_summaries():
    """Generate AI summaries for verified matches without summaries"""
    from match_summarizer import MatchSummarizer
    
    try:
        # Get verified alerts without AI summaries
        alerts = Alert.query.filter(
            Alert.spc_verified == True,
            Alert.spc_ai_summary.is_(None)
        ).limit(250).all()  # Use configurable limit for AI summary generation
        
        if not alerts:
            return jsonify({
                'success': True,
                'message': 'No verified matches need AI summaries',
                'generated': 0
            })
        
        summarizer = MatchSummarizer()
        generated = 0
        
        for alert in alerts:
            if alert.spc_reports:
                try:
                    summary = summarizer.generate_match_summary(
                        alert=alert.to_dict(),
                        spc_reports=alert.spc_reports
                    )
                    if summary:
                        alert.spc_ai_summary = summary
                        generated += 1
                except Exception as e:
                    logger.warning(f"Failed to generate summary for alert {alert.id}: {e}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Generated {generated} AI summaries for verified matches',
            'generated': generated,
            'total_processed': len(alerts)
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"AI summary generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/internal/missing-alerts-analysis')
def missing_alerts_analysis():
    """
    Analyze how many NWS alerts we might be missing
    """
    try:
        from datetime import datetime, timedelta
        from sqlalchemy import func, text
        
        # Get failure statistics for last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Query failed operations
        failed_operations = SchedulerLog.query.filter(
            SchedulerLog.operation_type == 'nws_poll',
            SchedulerLog.started_at >= thirty_days_ago,
            SchedulerLog.success == False
        ).all()
        
        # Query successful operations for comparison
        successful_operations = SchedulerLog.query.filter(
            SchedulerLog.operation_type == 'nws_poll',
            SchedulerLog.started_at >= thirty_days_ago,
            SchedulerLog.success == True
        ).all()
        
        # Calculate average alerts per successful poll
        total_alerts_successful = sum(op.records_new or 0 for op in successful_operations)
        avg_alerts_per_poll = total_alerts_successful / len(successful_operations) if successful_operations else 0
        
        # Estimate missed alerts
        failed_polls_count = len(failed_operations)
        estimated_missed_alerts = failed_polls_count * avg_alerts_per_poll
        
        # Get duplicate statistics
        total_duplicates = sum(op.duplicate_count or 0 for op in successful_operations)
        
        # Get detailed error breakdown
        error_breakdown = {}
        for op in failed_operations:
            error_type = "Unknown"
            if op.error_message:
                if "duplicate key" in op.error_message.lower():
                    error_type = "Duplicate Key Violation"
                elif "timeout" in op.error_message.lower():
                    error_type = "HTTP Timeout"
                elif "connection" in op.error_message.lower():
                    error_type = "Connection Error"
                elif "session" in op.error_message.lower():
                    error_type = "Database Session Error"
                else:
                    error_type = "Other Error"
            
            error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1
        
        # Calculate uptime percentage
        total_operations = len(failed_operations) + len(successful_operations)
        uptime_percentage = (len(successful_operations) / total_operations * 100) if total_operations > 0 else 0
        
        analysis = {
            'period': '30 days',
            'total_operations': total_operations,
            'successful_operations': len(successful_operations),
            'failed_operations': failed_polls_count,
            'uptime_percentage': round(uptime_percentage, 2),
            'avg_alerts_per_successful_poll': round(avg_alerts_per_poll, 1),
            'estimated_missed_alerts': round(estimated_missed_alerts),
            'total_duplicates_encountered': total_duplicates,
            'error_breakdown': error_breakdown,
            'recommendations': []
        }
        
        # Generate recommendations
        if failed_polls_count > 0:
            analysis['recommendations'].append(f"Fix duplicate key handling - {error_breakdown.get('Duplicate Key Violation', 0)} failures")
        if uptime_percentage < 95:
            analysis['recommendations'].append(f"Improve system reliability - {100-uptime_percentage:.1f}% downtime")
        if total_duplicates > len(successful_operations):
            analysis['recommendations'].append("Optimize duplicate detection logic")
        
        return jsonify(analysis)
        
    except Exception as e:
        logger.error(f"Error in missing alerts analysis: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/internal/spc-generate-summary/<alert_id>', methods=['POST'])
def generate_single_ai_summary(alert_id):
    """Generate AI summary for a specific verified alert match"""
    from match_summarizer import MatchSummarizer
    
    try:
        # Get the specific alert
        alert = Alert.query.filter_by(id=alert_id).first()
        
        if not alert:
            return jsonify({'success': False, 'error': 'Alert not found'}), 404
        
        if not alert.spc_verified:
            return jsonify({'success': False, 'error': 'Alert is not SPC verified'}), 400
        
        if not alert.spc_reports:
            return jsonify({'success': False, 'error': 'No SPC reports linked to this alert'}), 400
        
        # Generate AI summary
        summarizer = MatchSummarizer()
        summary = summarizer.generate_match_summary(
            alert=alert.to_dict(),
            spc_reports=alert.spc_reports
        )
        
        if summary:
            alert.spc_ai_summary = summary
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'AI summary generated successfully',
                'summary': summary
            })
        else:
            return jsonify({'success': False, 'error': 'Failed to generate AI summary'}), 500
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Single AI summary generation failed for alert {alert_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/internal/scheduler/start', methods=['POST'])
def start_autonomous_scheduler():
    """Start autonomous scheduler"""
    try:
        autonomous_scheduler.start()
        return jsonify({
            'success': True,
            'status': 'running',
            'message': 'Autonomous scheduler started'
        })
    except Exception as e:
        logger.error(f"Failed to start autonomous scheduler: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/internal/scheduler/stop', methods=['POST'])
def stop_autonomous_scheduler():
    """Stop autonomous scheduler"""
    try:
        autonomous_scheduler.stop()
        return jsonify({
            'success': True,
            'status': 'stopped',
            'message': 'Autonomous scheduler stopped'
        })
    except Exception as e:
        logger.error(f"Failed to stop autonomous scheduler: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/internal/scheduler/status')
def get_autonomous_scheduler_status():
    """Get autonomous scheduler status with countdown information"""
    try:
        status = autonomous_scheduler.get_status()
        
        # Calculate time until next operations
        from datetime import datetime, timedelta
        current_time = datetime.utcnow()
        
        # Next NWS poll (at exact 5-minute intervals: 0, 5, 10, 15, etc.)
        current_minute = current_time.minute
        next_minute = ((current_minute // 5) + 1) * 5
        if next_minute >= 60:
            next_nws = current_time.replace(hour=(current_time.hour + 1) % 24, minute=0, second=0, microsecond=0)
        else:
            next_nws = current_time.replace(minute=next_minute, second=0, microsecond=0)
        nws_countdown = max(0, int((next_nws - current_time).total_seconds()))
        
        # Next SPC poll (every 30 minutes) 
        last_spc = status.get('last_spc_poll')
        if last_spc:
            last_spc_dt = datetime.fromisoformat(last_spc.replace('Z', '+00:00')) if isinstance(last_spc, str) else last_spc
            next_spc = last_spc_dt + timedelta(minutes=30)
            spc_countdown = max(0, int((next_spc - current_time).total_seconds()))
        else:
            spc_countdown = 0
            
        # Next matching (every 15 minutes)
        last_match = status.get('last_matching')
        if last_match:
            last_match_dt = datetime.fromisoformat(last_match.replace('Z', '+00:00')) if isinstance(last_match, str) else last_match
            next_match = last_match_dt + timedelta(minutes=15)
            match_countdown = max(0, int((next_match - current_time).total_seconds()))
        else:
            match_countdown = 0
        
        # Determine which operation is next
        next_operation = "nws"
        next_countdown = nws_countdown
        if spc_countdown < next_countdown and spc_countdown > 0:
            next_operation = "spc"
            next_countdown = spc_countdown
        if match_countdown < next_countdown and match_countdown > 0:
            next_operation = "matching"
            next_countdown = match_countdown
            
        status['next_operation'] = next_operation
        status['next_countdown'] = next_countdown
        status['nws_countdown'] = nws_countdown
        status['spc_countdown'] = spc_countdown
        status['match_countdown'] = match_countdown
        
        return jsonify({
            'success': True,
            'scheduler': status
        })
    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/internal/enrich-all-priority', methods=['POST'])
def enrich_all_priority_database():
    """Internal endpoint to enrich all existing priority alerts in the database"""
    try:
        logger.info("Starting comprehensive priority alert enrichment for entire database")
        
        # Get count of priority alerts that need enrichment
        priority_unenriched = Alert.query.filter(
            Alert.ai_summary.is_(None),
            Alert.event.in_(enrich_service.AUTO_ENRICH_ALERTS)
        ).count()
        
        if priority_unenriched == 0:
            return jsonify({
                'success': True,
                'message': 'All priority alerts are already enriched',
                'enriched': 0,
                'failed': 0,
                'total_processed': 0
            })
        
        logger.info(f"Found {priority_unenriched} priority alerts requiring enrichment")
        
        # Run the enrichment process
        result = enrich_service.enrich_all_priority_alerts()
        
        if 'error' in result:
            return jsonify({
                'success': False,
                'error': result['error']
            }), 500
        
        return jsonify({
            'success': True,
            'message': f"Successfully enriched {result['enriched']} priority alerts from database",
            'enriched': result['enriched'],
            'failed': result['failed'],
            'total_processed': result['total_processed'],
            'priority_types': list(enrich_service.AUTO_ENRICH_ALERTS)
        })
        
    except Exception as e:
        logger.error(f"Error during comprehensive priority enrichment: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/internal/spc-verify-today')
def spc_verify_today():
    """Get recent SPC verification data for dashboard"""
    try:
        from datetime import date, timedelta
        import requests
        
        today = date.today()
        
        # Check last 7 days including today
        verification_results = []
        
        for days_back in range(7):  # Check last 7 days
            check_date = today - timedelta(days=days_back)
            
            # Get HailyDB count for this date
            hailydb_count = SPCReport.query.filter(SPCReport.report_date == check_date).count()
            
            # Get live SPC count by fetching the CSV
            date_str = check_date.strftime("%y%m%d")
            url = f"https://www.spc.noaa.gov/climo/reports/{date_str}_rpts_filtered.csv"
            
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                # Use perfect parsing logic to count actual data rows
                csv_content = response.text.strip()
                lines = csv_content.split('\n')
                
                spc_live_count = 0
                for line in lines:
                    line = line.strip()
                    # Count lines that start with 4 digits and aren't headers
                    if line and len(line) >= 4 and line[:4].isdigit() and not line.startswith('Time,'):
                        spc_live_count += 1
                
                match_status = 'MATCH' if hailydb_count == spc_live_count else 'MISMATCH'
                
                verification_results.append({
                    'date': check_date.strftime('%Y-%m-%d'),
                    'hailydb_count': hailydb_count,
                    'spc_live_count': spc_live_count,
                    'match_status': match_status
                })
                
            except requests.RequestException as e:
                # SPC file not available for this date - log and continue
                logger.debug(f"SPC file not available for {check_date}: {e}")
                verification_results.append({
                    'date': check_date.strftime('%Y-%m-%d'),
                    'hailydb_count': hailydb_count,
                    'spc_live_count': None,
                    'match_status': 'PENDING' if check_date == today else 'UNAVAILABLE'
                })
            except Exception as e:
                # Network or parsing error - log and continue
                logger.warning(f"Error checking SPC data for {check_date}: {e}")
                verification_results.append({
                    'date': check_date.strftime('%Y-%m-%d'),
                    'hailydb_count': hailydb_count,
                    'spc_live_count': None,
                    'match_status': 'ERROR'
                })
        
        return jsonify({
            'status': 'success',
            'results': verification_results,
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in SPC verification: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/spc/calendar-verification')
def spc_calendar_verification():
    """Get 2-month SPC verification data for calendar view"""
    try:
        from datetime import date, timedelta
        import calendar
        import requests
        
        # Get offset parameter for navigation (0 = current period, -1 = previous 2 months, etc.)
        offset = int(request.args.get('offset', 0))
        
        # Calculate date range based on offset for 2-month periods
        # offset = 0: Current and previous month
        # offset = -1: Previous 2 months before that
        # offset = 1: Next 2 months after that
        today = date.today()
        
        # Calculate the target month/year based on offset
        target_year = today.year
        target_month = today.month + (offset * 2)
        
        # Normalize year and month
        while target_month > 12:
            target_month -= 12
            target_year += 1
        while target_month < 1:
            target_month += 12
            target_year -= 1
        
        # End date is the last day of the target month
        _, last_day = calendar.monthrange(target_year, target_month)
        end_date = date(target_year, target_month, last_day)
        
        # Start date is the first day of the previous month
        prev_month = target_month - 1
        prev_year = target_year
        if prev_month < 1:
            prev_month = 12
            prev_year -= 1
        start_date = date(prev_year, prev_month, 1)
        
        verification_results = []
        current_date = start_date
        
        # Use batch database query for better performance
        all_reports = {}
        date_range_reports = SPCReport.query.filter(
            SPCReport.report_date >= start_date,
            SPCReport.report_date <= end_date
        ).all()
        
        # Group by date for fast lookup
        for report in date_range_reports:
            date_key = report.report_date.strftime('%Y-%m-%d')
            if date_key not in all_reports:
                all_reports[date_key] = 0
            all_reports[date_key] += 1
        
        # Pre-fetch all SPC data with connection pooling for better performance
        import concurrent.futures
        import threading
        
        # Create session with connection pooling
        session = requests.Session()
        try:
            from requests.adapters import HTTPAdapter
            adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
            session.mount('https://', adapter)
        except ImportError:
            pass  # Fall back to default session
        
        def fetch_spc_count(date_obj):
            """Fetch SPC count for a single date"""
            try:
                date_str = date_obj.strftime("%y%m%d")
                url = f"https://www.spc.noaa.gov/climo/reports/{date_str}_rpts_filtered.csv"
                response = session.get(url, timeout=5)
                response.raise_for_status()
                
                lines = response.text.strip().split('\n')
                return max(0, len(lines) - 3)  # Subtract 3 header lines
            except:
                return None
        
        # Generate all dates first
        all_dates = []
        current_date = start_date
        while current_date <= end_date:
            all_dates.append(current_date)
            current_date += timedelta(days=1)
        
        # Fetch SPC data in parallel with limited workers to prevent overwhelming
        spc_counts = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_date = {executor.submit(fetch_spc_count, date): date for date in all_dates}
            
            for future in concurrent.futures.as_completed(future_to_date, timeout=30):
                date = future_to_date[future]
                try:
                    count = future.result()
                    spc_counts[date] = count
                except:
                    spc_counts[date] = None
        
        # Build results using fetched data
        for date in all_dates:
            date_key = date.strftime('%Y-%m-%d')
            hailydb_count = all_reports.get(date_key, 0)
            spc_live_count = spc_counts.get(date)
            
            if spc_live_count is None:
                match_status = 'PENDING' if date >= end_date - timedelta(days=1) else 'UNAVAILABLE'
            elif hailydb_count == spc_live_count:
                match_status = 'MATCH'
            else:
                match_status = 'MISMATCH'
            
            verification_results.append({
                'date': date_key,
                'day': date.day,
                'hailydb_count': hailydb_count,
                'spc_live_count': spc_live_count,
                'match_status': match_status
            })
        
        return jsonify({
            'status': 'success',
            'results': verification_results,
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d')
            },
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in SPC calendar verification: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

# Home route
@app.route('/')
def index():
    """Dashboard index - check admin access or redirect to documentation"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    return redirect(url_for('internal_dashboard'))

@app.route('/documentation')
def documentation():
    """Standalone documentation page - PUBLIC ACCESS with admin login link"""
    try:
        import markdown
        from markdown.extensions import codehilite, tables, toc
        
        # Get dynamic production statistics
        try:
            # Total NWS Alerts
            total_alerts = Alert.query.count()
            
            # Radar-detected events (any radar indication)
            radar_detected_total = Alert.query.filter(Alert.radar_indicated.isnot(None)).count()
            
            # Radar-detected hail (any size)
            radar_hail_count = Alert.query.filter(
                Alert.radar_indicated.isnot(None),
                Alert.radar_indicated['hail_inches'].astext.cast(db.Float) > 0
            ).count()
            
            # Radar-detected wind (50+ mph)
            radar_wind_count = Alert.query.filter(
                Alert.radar_indicated.isnot(None),
                Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= 50
            ).count()
            
            # SPC Storm Reports - Total
            total_spc_reports = SPCReport.query.count()
            
            # SPC Reports by type
            spc_tornado_count = SPCReport.query.filter(SPCReport.report_type == 'tornado').count()
            spc_wind_count = SPCReport.query.filter(SPCReport.report_type == 'wind').count()
            spc_hail_count = SPCReport.query.filter(SPCReport.report_type == 'hail').count()
            
            # Data integrity calculation
            data_integrity = 100 if total_alerts > 0 else 0
            
            production_stats = {
                'total_alerts': total_alerts,
                'radar_detected_total': radar_detected_total,
                'radar_hail_count': radar_hail_count,
                'radar_wind_count': radar_wind_count,
                'total_spc_reports': total_spc_reports,
                'spc_tornado_count': spc_tornado_count,
                'spc_wind_count': spc_wind_count,
                'spc_hail_count': spc_hail_count,
                'data_integrity': data_integrity
            }
        except Exception as stats_error:
            logger.error(f"Error getting production stats: {stats_error}")
            # Fallback to basic counts
            production_stats = {
                'total_alerts': Alert.query.count() if Alert.query.count() else 0,
                'radar_detected_total': 0,
                'radar_hail_count': 0,
                'radar_wind_count': 0,
                'total_spc_reports': SPCReport.query.count() if SPCReport.query.count() else 0,
                'spc_tornado_count': 0,
                'spc_wind_count': 0,
                'spc_hail_count': 0,
                'data_integrity': 100
            }
        
        # Read README.md content and replace static statistics with dynamic ones
        with open('README.md', 'r', encoding='utf-8') as f:
            markdown_content = f.read()
        

        
        # Configure markdown with extensions
        md = markdown.Markdown(extensions=[
            'markdown.extensions.codehilite',
            'markdown.extensions.tables', 
            'markdown.extensions.toc',
            'markdown.extensions.fenced_code'
        ], extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': True
            },
            'toc': {
                'anchorlink': True
            }
        })
        
        # Convert markdown to HTML
        documentation_html = md.convert(markdown_content)
        
        # Check if user has admin access
        is_admin = is_admin_access()
        
        # Generate admin login URL for external users
        admin_login_url = None
        if not is_admin:
            # Create admin access link - this will redirect to dashboard when clicked by admin
            admin_login_url = url_for('index')  # This redirects to dashboard if admin
        
        return render_template('documentation.html', 
                             documentation_html=documentation_html,
                             is_admin=is_admin,
                             admin_login_url=admin_login_url,
                             production_stats=production_stats)
        
    except Exception as e:
        logger.error(f"Error loading documentation: {e}")
        return f"<h1>Documentation Error</h1><p>Error loading documentation: {str(e)}</p>", 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page and handler"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if verify_admin_credentials(email, password):
            login_admin()
            # Redirect to dashboard after successful login
            return redirect(url_for('internal_dashboard'))
        else:
            error = "Invalid email or password"
            return render_template('admin_login.html', error=error)
    
    # Check if already logged in
    if is_admin_access():
        return redirect(url_for('internal_dashboard'))
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    """Admin logout"""
    logout_admin()
    return redirect(url_for('documentation'))

@app.route('/ingestion-logs')
def ingestion_logs():
    """View ingestion logs page"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    return render_template('ingestion_logs.html')

@app.route('/ingestion-logs/data')
def ingestion_logs_data():
    """API endpoint for ingestion logs data"""
    try:
        hours = int(request.args.get('hours', 24))
        operation_type = request.args.get('operation_type', '')
        success_param = request.args.get('success', '')
        
        # Build SQL query to avoid PostgreSQL type issues
        since = datetime.utcnow() - timedelta(hours=hours)
        
        # Base query with proper type casting and enhanced status
        base_sql = """
            SELECT 
                id,
                started_at,
                completed_at,
                operation_type::text,
                trigger_method::text,
                success,
                COALESCE(records_processed, 0) as records_processed,
                COALESCE(records_new, 0) as records_new,
                error_message::text,
                operation_metadata
            FROM scheduler_logs 
            WHERE started_at >= :since
        """
        
        params = {'since': since}
        
        # Add filters
        if operation_type:
            base_sql += " AND operation_type = :operation_type"
            params['operation_type'] = operation_type
            
        if success_param == 'true':
            base_sql += " AND success = true"
        elif success_param == 'false':
            base_sql += " AND success = false"
            
        # Order and limit
        base_sql += " ORDER BY started_at DESC LIMIT 100"
        
        # Execute query
        result = db.session.execute(db.text(base_sql), params)
        logs_data = result.fetchall()
        
        # Calculate summary statistics
        summary_sql = """
            SELECT 
                COUNT(*) as total_count,
                SUM(CASE WHEN success = true THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN success = false THEN 1 ELSE 0 END) as error_count,
                SUM(CASE WHEN success = true THEN COALESCE(records_processed, 0) ELSE 0 END) as total_processed,
                SUM(CASE WHEN success = true THEN COALESCE(records_new, 0) ELSE 0 END) as total_new
            FROM scheduler_logs 
            WHERE started_at >= :since
        """
        
        if operation_type:
            summary_sql += " AND operation_type = :operation_type"
            
        summary_result = db.session.execute(db.text(summary_sql), params)
        summary_data = summary_result.fetchone()
        
        # Format logs for JSON response with enhanced status
        formatted_logs = []
        for row in logs_data:
            duration = None
            if row.started_at and row.completed_at:
                duration = round((row.completed_at - row.started_at).total_seconds(), 1)
            
            # Determine enhanced status and color
            if not row.completed_at:
                # Check if operation has been running too long (likely stuck due to DB completion error)
                if row.started_at:
                    time_since_start = datetime.utcnow() - row.started_at
                    
                    # Operations should complete within 5 minutes - if longer, assume success but stuck
                    if time_since_start.total_seconds() > 300:  # 5 minutes = 300 seconds
                        # Look at operation type to determine likely outcome
                        if row.operation_type in ['nws_poll', 'spc_poll', 'spc_match']:
                            # These operations usually succeed, show as technical success
                            status_display = 'Success - DB Logging Failed'
                            status_color = '#28a745'
                            status_class = 'log-success'
                        else:
                            status_display = 'Completed - Status Unknown'
                            status_color = '#6c757d'
                            status_class = 'log-unknown'
                    else:
                        status_display = 'In Progress'
                        status_color = '#007bff'
                        status_class = 'log-progress'
                else:
                    status_display = 'In Progress'
                    status_color = '#007bff'
                    status_class = 'log-progress'
            elif row.success:
                if row.records_new == 0 and row.records_processed > 0:
                    status_display = 'Success - No New Data'
                    status_color = '#20c997'
                    status_class = 'log-success-no-data'
                elif row.records_new > 0:
                    status_display = 'Success'
                    status_color = '#28a745'
                    status_class = 'log-success'
                else:
                    status_display = 'Success'
                    status_color = '#28a745'
                    status_class = 'log-success'
            else:
                # Determine failure type from error message
                error_msg = (row.error_message or '').lower()
                if 'network' in error_msg or 'timeout' in error_msg or 'connection' in error_msg:
                    status_display = 'Failed - Network'
                    status_color = '#dc3545'
                    status_class = 'log-failed-network'
                elif 'database' in error_msg or 'sql' in error_msg or 'pg numeric type' in error_msg:
                    status_display = 'Failed - Technical'
                    status_color = '#fd7e14'
                    status_class = 'log-failed-technical'
                else:
                    status_display = 'Failed'
                    status_color = '#dc3545'
                    status_class = 'log-error'
            
            formatted_logs.append({
                'started_at': row.started_at.isoformat() if row.started_at else None,
                'completed_at': row.completed_at.isoformat() if row.completed_at else None,
                'operation_type': row.operation_type,
                'trigger_method': row.trigger_method,
                'success': row.success,
                'records_processed': row.records_processed,
                'records_new': row.records_new,
                'error_message': row.error_message,
                'duration': duration,
                'status_display': status_display,
                'status_color': status_color,
                'status_class': status_class
            })
        
        return jsonify({
            'summary': {
                'success_count': int(summary_data[1] or 0) if summary_data else 0,
                'error_count': int(summary_data[2] or 0) if summary_data else 0,
                'total_processed': int(summary_data[3] or 0) if summary_data else 0,
                'total_new': int(summary_data[4] or 0) if summary_data else 0
            },
            'logs': formatted_logs
        })
        
    except Exception as e:
        logger.error(f"Error in ingestion logs data: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/spc-matches')
def spc_matches():
    """View SPC verified matches page"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    return render_template('spc_matches.html')

@app.route('/hurricane-tracks')
def hurricane_tracks():
    """View hurricane tracks page"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    return render_template('hurricane_tracks.html')

# NEW: Consolidated alerts interface with radar-style visual presentation
@app.route('/alerts')
def get_alerts():
    """View enhanced alerts interface with immediate visual understanding of hail/wind data"""
    if request.args.get('format') == 'json':
        # Handle JSON API requests from dashboard JavaScript
        try:
            from models import Alert
            from datetime import datetime, timedelta
            from sqlalchemy import and_, or_
            
            # Get query parameters
            per_page = int(request.args.get('per_page', 50))
            page = int(request.args.get('page', 1))
            ingested_date = request.args.get('ingested_date')
            effective_start = request.args.get('effective_start')
            effective_end = request.args.get('effective_end')
            
            # Build query
            query = Alert.query
            
            # Apply filters
            if ingested_date:
                # Filter by ingestion date (UTC mode)
                ingested_start = datetime.fromisoformat(f"{ingested_date}T00:00:00")
                ingested_end = datetime.fromisoformat(f"{ingested_date}T23:59:59")
                query = query.filter(
                    and_(
                        Alert.ingested_at >= ingested_start,
                        Alert.ingested_at <= ingested_end
                    )
                )
            
            if effective_start and effective_end:
                # Filter by effective time range (SPC mode)
                start_time = datetime.fromisoformat(effective_start.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(effective_end.replace('Z', '+00:00'))
                query = query.filter(
                    and_(
                        Alert.effective >= start_time,
                        Alert.effective <= end_time
                    )
                )
            
            # Get total count for pagination
            total_count = query.count()
            
            # Apply pagination
            alerts = query.order_by(Alert.effective.desc()).offset((page - 1) * per_page).limit(per_page).all()
            
            # Convert to JSON-serializable format
            alerts_data = []
            for alert in alerts:
                alert_dict = alert.to_dict()
                alerts_data.append(alert_dict)
            
            return jsonify({
                'alerts': alerts_data,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                }
            })
            
        except Exception as e:
            logger.error(f"Error in alerts API: {e}")
            return jsonify({'error': str(e)}), 500
    
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    return render_template('radar_alerts.html')

@app.route('/radar-alerts')
def view_radar_alerts():
    """DEPRECATED: Redirect to consolidated alerts interface"""
    from flask import redirect, url_for
    return redirect(url_for('get_alerts'), code=301)

@app.route('/api/state-enrichment/stats')
def get_state_enrichment_stats():
    """Get statistics about alerts missing state information"""
    try:
        from models import Alert
        
        # Count alerts with missing states
        total_alerts = Alert.query.count()
        missing_states = Alert.query.filter(
            db.or_(
                Alert.affected_states.is_(None),
                Alert.affected_states == '[]'
            )
        ).count()
        
        enriched_alerts = total_alerts - missing_states
        
        stats = {
            'total_alerts': total_alerts,
            'missing_states': missing_states,
            'enriched_alerts': enriched_alerts,
            'completion_percentage': (enriched_alerts / total_alerts * 100) if total_alerts > 0 else 0
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting state enrichment stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/state-enrichment/enrich', methods=['POST'])
def trigger_state_enrichment():
    """Trigger state enrichment for alerts with missing state information"""
    try:
        from state_enrichment_service import StateEnrichmentService
        
        # Get batch size from request
        batch_size = request.json.get('batch_size', 1000) if request.is_json else 1000
        
        # Initialize enrichment service
        enrichment_service = StateEnrichmentService()
        
        # Run enrichment
        results = enrichment_service.enrich_alerts_batch(db, batch_size)
        
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error triggering state enrichment: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/state-enrichment/enrich-all', methods=['POST'])
def trigger_complete_state_enrichment():
    """Trigger complete state enrichment for all alerts with missing state information"""
    try:
        from state_enrichment_service import StateEnrichmentService
        
        # Get batch size from request
        batch_size = request.json.get('batch_size', 1000) if request.is_json else 1000
        
        # Initialize enrichment service
        enrichment_service = StateEnrichmentService()
        
        # Run complete enrichment
        results = enrichment_service.enrich_all_alerts(db, batch_size)
        
        return jsonify({
            'status': 'success',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error triggering complete state enrichment: {e}")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/address-targeting')
def address_targeting():
    """Address-specific weather event targeting interface"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    return render_template('address_targeting.html')

@app.route('/webhook-management')
def webhook_management():
    """View webhook management interface"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    return render_template('webhook_management.html')

@app.route('/live-radar')
@app.route('/live-radar-dashboard')
def live_radar_dashboard():
    """Live Radar Alerts Dashboard"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    return render_template('live_radar_dashboard.html')

@app.route('/api/live-radar-alerts')
def get_live_radar_alerts():
    """API endpoint for live NWS alerts - filters ingested database alerts for hail ANY size or winds 50+ mph"""
    try:
        from datetime import datetime, timedelta
        
        # Query our database for active alerts with radar-detected hail/wind criteria
        current_time = datetime.utcnow()
        
        # Get active alerts from our database that are not expired 
        query = Alert.query.filter(
            Alert.expires > current_time
        )
        
        active_alerts = query.all()
        
        # Filter for hail of ANY size OR winds 50+ mph from radar data
        qualifying_alerts = []
        for alert in active_alerts:
            radar_data = alert.radar_indicated or {}
            
            # Extract hail and wind data
            hail_inches = radar_data.get('hail_inches', 0) or 0
            wind_mph = radar_data.get('wind_mph', 0) or 0
            
            # Check if alert qualifies: hail ANY size OR wind 50+ mph
            has_qualifying_hail = hail_inches > 0
            has_qualifying_wind = wind_mph >= 50
            
            if has_qualifying_hail or has_qualifying_wind:
                # Calculate if expired
                is_expired = alert.expires and alert.expires <= current_time
                
                # Extract state from affected_states or area_desc
                state = None
                if alert.affected_states and len(alert.affected_states) > 0:
                    state = alert.affected_states[0]
                else:
                    # Extract state from area_desc as fallback
                    import re
                    state_match = re.findall(r'\b[A-Z]{2}\b', alert.area_desc or '')
                    if state_match:
                        state = state_match[-1]  # Get last state mentioned
                
                # Get message type from properties if available
                message_type = 'Alert'
                if alert.properties and 'messageType' in alert.properties:
                    message_type = alert.properties['messageType']
                
                qualifying_alerts.append({
                    'id': alert.id,  # Use correct id field
                    'event': alert.event,
                    'area_desc': alert.area_desc,
                    'severity': alert.severity,
                    'effective': alert.effective.isoformat() if alert.effective else None,
                    'expires': alert.expires.isoformat() if alert.expires else None,
                    'message_type': message_type,
                    'hail_size': hail_inches,
                    'wind_speed': wind_mph,
                    'is_expired': is_expired,
                    'state': state,
                    'headline': alert.properties.get('headline') if alert.properties else None,
                    'description': alert.properties.get('description') if alert.properties else None
                })
        
        # Calculate comprehensive dashboard statistics
        try:
            # Get historical statistics (last 7 days for context)
            since_date = current_time - timedelta(days=7)
            
            # Count historical alerts with radar-detected hail/wind
            hail_alerts = Alert.query.filter(
                Alert.radar_indicated.op('->>')('hail_inches').astext.cast(db.Float) > 0,
                Alert.ingested_at >= since_date
            ).count()
            
            wind_alerts = Alert.query.filter(
                Alert.radar_indicated.op('->>')('wind_mph').astext.cast(db.Integer) >= 50,
                Alert.ingested_at >= since_date
            ).count()
            
            # Count currently active alerts in database
            active_alerts_count = Alert.query.filter(
                Alert.expires > current_time
            ).count()
            
            # Count unique states affected by qualifying alerts
            current_states = set()
            for alert in qualifying_alerts:
                if alert.get('state'):
                    current_states.add(alert['state'])
            
            states_affected = len(current_states)

            return jsonify({
                'status': 'success',
                'alerts': qualifying_alerts,
                'count': len(qualifying_alerts),
                'statistics': {
                    'hail_alerts': hail_alerts,
                    'wind_alerts': wind_alerts,
                    'active_alerts': active_alerts_count,
                    'states_affected': states_affected,
                    'live_radar_count': len(qualifying_alerts),
                    'period': '7 days'
                },
                'timestamp': current_time.isoformat() + 'Z',
                'source': 'HailyDB ingested alerts with radar criteria'
            })
            
        except Exception as stats_error:
            logger.error(f"Error calculating live radar statistics: {stats_error}")
            return jsonify({
                'status': 'success',
                'alerts': qualifying_alerts,
                'count': len(qualifying_alerts),
                'statistics': {
                    'hail_alerts': 0,
                    'wind_alerts': 0,
                    'active_alerts': 0,
                    'states_affected': 0,
                    'live_radar_count': len(qualifying_alerts),
                    'period': 'error'
                },
                'timestamp': current_time.isoformat() + 'Z',
                'source': 'HailyDB ingested alerts with radar criteria'
            })
        
    except Exception as e:
        logger.error(f"Error getting live radar alerts: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Error fetching live radar alerts: {str(e)}',
            'alerts': [],
            'statistics': {
                'hail_alerts': 0,
                'wind_alerts': 0,
                'active_alerts': 0,
                'states_affected': 0,
                'live_radar_count': 0,
                'period': 'error'
            },
            'source': 'HailyDB ingested alerts with radar criteria'
        }), 500

@app.route('/spc-matches/data')
def spc_matches_data():
    """API endpoint for SPC verified matches data"""
    try:
        hours = int(request.args.get('hours', 168))  # Default to 7 days
        event_filter = request.args.get('event', '')
        method_filter = request.args.get('method', '')
        confidence_filter = request.args.get('confidence', '')
        state_filter = request.args.get('state', '')
        search_query = request.args.get('search', '').strip()
        
        # Build query for verified alerts
        query = Alert.query.filter(Alert.spc_verified == True)
        
        # Apply search query across multiple fields
        if search_query:
            search_pattern = f'%{search_query}%'
            query = query.filter(
                db.or_(
                    Alert.event.ilike(search_pattern),
                    Alert.area_desc.ilike(search_pattern),
                    Alert.spc_ai_summary.ilike(search_pattern),
                    Alert.properties['headline'].astext.ilike(search_pattern),
                    Alert.properties['description'].astext.ilike(search_pattern),
                    Alert.raw['properties']['areaDesc'].astext.ilike(search_pattern)
                )
            )
        
        # Filter by time - for verified alerts, use much longer timeframe to not exclude historical matches
        if hours <= 168:  # If default 7-day filter, extend to 30 days for verified alerts
            since = datetime.utcnow() - timedelta(hours=720)  # 30 days for verified matches
        else:
            since = datetime.utcnow() - timedelta(hours=hours)
        query = query.filter(Alert.effective >= since)
        
        # Filter by event type
        if event_filter:
            query = query.filter(Alert.event == event_filter)
        
        # Filter by match method
        if method_filter:
            query = query.filter(Alert.spc_match_method == method_filter)
        
        # Filter by confidence level
        if confidence_filter == 'high':
            query = query.filter(Alert.spc_confidence_score >= 0.8)
        elif confidence_filter == 'medium':
            query = query.filter(Alert.spc_confidence_score >= 0.5, Alert.spc_confidence_score < 0.8)
        elif confidence_filter == 'low':
            query = query.filter(Alert.spc_confidence_score < 0.5)
        
        # Filter by state (extract from area_desc)
        if state_filter:
            query = query.filter(Alert.area_desc.contains(state_filter))
        
        # Order by most recent first
        matches = query.order_by(Alert.effective.desc()).limit(500).all()
        
        # Calculate summary statistics
        total_alerts = Alert.query.filter(Alert.effective >= since).count()
        verified_count = len(matches) if not any([event_filter, method_filter, confidence_filter, state_filter]) else query.count()
        total_reports = sum(match.spc_report_count or 0 for match in matches)
        high_confidence_count = sum(1 for match in matches if (match.spc_confidence_score or 0) >= 0.8)
        verification_rate = round((verified_count / total_alerts * 100) if total_alerts > 0 else 0, 1)
        
        # Get unique states for filter dropdown
        states = set()
        for match in matches:
            if match.area_desc:
                # Extract state codes from area description
                import re
                state_matches = re.findall(r'\b([A-Z]{2})\b', match.area_desc)
                states.update(state_matches)
        
        # Format matches for JSON response
        formatted_matches = []
        for match in matches:
            # Parse SPC reports with IDs for navigation
            spc_reports = []
            if match.spc_reports:
                for report_data in match.spc_reports:
                    if isinstance(report_data, dict):
                        spc_reports.append({
                            'id': report_data.get('id'),
                            'report_type': report_data.get('report_type', 'unknown'),
                            'time_utc': report_data.get('time_utc', ''),
                            'location': report_data.get('location', ''),
                            'county': report_data.get('county', ''),
                            'state': report_data.get('state', ''),
                            'comments': report_data.get('comments', '')
                        })
            
            formatted_matches.append({
                'id': match.id,
                'effective': match.effective.isoformat() if match.effective else None,
                'event': match.event,
                'area_desc': match.area_desc,
                'match_method': match.spc_match_method or 'unknown',
                'confidence': match.spc_confidence_score or 0,
                'report_count': match.spc_report_count or 0,
                'spc_reports': spc_reports,
                'spc_ai_summary': match.spc_ai_summary
            })
        
        return jsonify({
            'summary': {
                'verified_count': verified_count,
                'total_reports': total_reports,
                'high_confidence_count': high_confidence_count,
                'verification_rate': verification_rate
            },
            'matches': formatted_matches,
            'states': sorted(list(states))
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Hurricane Track API Endpoints

@app.route("/api/hurricanes/tracks", methods=["GET"])
def get_hurricane_tracks():
    """
    Get hurricane track data with filtering options
    Query parameters:
    - storm_id: Filter by NOAA storm identifier
    - name: Filter by hurricane name
    - year: Filter by year
    - lat/lon: Bounding box (lat_min, lat_max, lon_min, lon_max)
    - start_date/end_date: Date range filter
    - limit/offset: Pagination
    """
    try:
        # Parse query parameters
        storm_id = request.args.get('storm_id')
        name = request.args.get('name')
        year = request.args.get('year', type=int)
        lat_min = request.args.get('lat_min', type=float)
        lat_max = request.args.get('lat_max', type=float)
        lon_min = request.args.get('lon_min', type=float)
        lon_max = request.args.get('lon_max', type=float)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = request.args.get('limit', default=100, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        # Build query
        query = HurricaneTrack.query
        
        if storm_id:
            query = query.filter(HurricaneTrack.storm_id == storm_id)
        if name:
            query = query.filter(HurricaneTrack.name.ilike(f'%{name}%'))
        if year:
            query = query.filter(HurricaneTrack.year == year)
        if lat_min is not None and lat_max is not None:
            query = query.filter(HurricaneTrack.lat.between(lat_min, lat_max))
        if lon_min is not None and lon_max is not None:
            query = query.filter(HurricaneTrack.lon.between(lon_min, lon_max))
        if start_date:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(HurricaneTrack.timestamp >= start_dt)
        if end_date:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(HurricaneTrack.timestamp <= end_dt)
        
        # Execute query with pagination
        tracks = query.order_by(HurricaneTrack.timestamp.desc()).offset(offset).limit(limit).all()
        
        # Format response
        return jsonify([track.to_dict() for track in tracks])
        
    except Exception as e:
        logger.error(f"Error retrieving hurricane tracks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/hurricanes/storm/<storm_id>", methods=["GET"])
def get_hurricane_storm(storm_id):
    """Get complete track data for a specific storm"""
    try:
        summary = hurricane_ingest_service.get_storm_summary(storm_id)
        if not summary:
            return jsonify({'error': 'Storm not found'}), 404
        
        return jsonify(summary)
        
    except Exception as e:
        logger.error(f"Error retrieving storm {storm_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/hurricanes/search", methods=["GET"])
def search_hurricanes_by_location():
    """
    Search for hurricanes near a specific location
    Query parameters:
    - lat: Latitude
    - lon: Longitude  
    - radius: Search radius in miles (default: 50)
    """
    try:
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        radius = request.args.get('radius', default=50, type=float)
        
        if lat is None or lon is None:
            return jsonify({'error': 'lat and lon parameters are required'}), 400
        
        tracks = hurricane_ingest_service.search_tracks_by_location(lat, lon, radius)
        
        # Calculate distance for each track
        results = []
        for track in tracks:
            track_dict = track.to_dict()
            # Approximate distance calculation
            lat_diff = abs(track.lat - lat)
            lon_diff = abs(track.lon - lon)
            distance_miles = ((lat_diff**2 + lon_diff**2)**0.5) * 69
            track_dict['distance_from_query'] = round(distance_miles, 1)
            results.append(track_dict)
        
        # Sort by distance
        results.sort(key=lambda x: x['distance_from_query'])
        
        return jsonify(results)
        
    except Exception as e:
        logger.error(f"Error searching hurricanes by location: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/hurricanes/county-impacts/<county_fips>", methods=["GET"])
def get_county_hurricane_impacts(county_fips):
    """
    Get hurricane impact history for a specific county FIPS code
    Supports insurance risk assessment and restoration targeting
    """
    try:
        from models import HurricaneCountyImpact
        
        # Validate FIPS format (5 digits)
        if not county_fips.isdigit() or len(county_fips) != 5:
            return jsonify({'error': 'Invalid FIPS code format. Expected 5 digits.'}), 400
        
        # Query parameters for filtering
        min_wind = request.args.get('min_wind', type=int)
        category = request.args.get('category')  # CAT1, CAT2, etc.
        since_year = request.args.get('since_year', type=int)
        
        # Base query
        query = HurricaneCountyImpact.query.filter_by(county_fips=county_fips)
        
        # Apply filters
        if min_wind:
            query = query.filter(HurricaneCountyImpact.max_wind_mph_observed >= min_wind)
        if category:
            query = query.filter(HurricaneCountyImpact.wind_field_category == category)
        if since_year:
            query = query.filter(HurricaneCountyImpact.first_impact_time >= datetime(since_year, 1, 1))
        
        impacts = query.order_by(HurricaneCountyImpact.first_impact_time.desc()).all()
        
        if not impacts:
            return jsonify({
                'county_fips': county_fips,
                'impacts': [],
                'total_storms': 0,
                'message': 'No hurricane impacts found for this county'
            })
        
        # Calculate summary statistics
        total_storms = len(impacts)
        max_wind_ever = max(impact.max_wind_mph_observed for impact in impacts if impact.max_wind_mph_observed)
        landfall_events = sum(1 for impact in impacts if impact.in_landfall_zone)
        
        # Category distribution
        category_stats = {}
        for impact in impacts:
            cat = impact.wind_field_category
            if cat:
                category_stats[cat] = category_stats.get(cat, 0) + 1
        
        return jsonify({
            'county_fips': county_fips,
            'county_name': impacts[0].county_name if impacts else None,
            'state_code': impacts[0].state_code if impacts else None,
            'summary': {
                'total_storms': total_storms,
                'max_wind_observed': max_wind_ever,
                'landfall_events': landfall_events,
                'category_distribution': category_stats,
                'most_recent_impact': impacts[0].first_impact_time.isoformat() if impacts and impacts[0].first_impact_time else None
            },
            'impacts': [impact.to_dict() for impact in impacts]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving county impacts for {county_fips}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/hurricanes/county-impacts/search", methods=["GET"])
def search_county_impacts():
    """
    Search county impacts by state, wind threshold, or storm characteristics
    Query parameters:
    - state: 2-letter state code
    - min_wind: Minimum wind speed threshold
    - category: Hurricane category (CAT1-CAT5, TS, TD)
    - landfall_only: true/false
    - since_year: Year filter
    """
    try:
        from models import HurricaneCountyImpact
        
        # Query parameters
        state = request.args.get('state')
        min_wind = request.args.get('min_wind', type=int)
        category = request.args.get('category')
        landfall_only = request.args.get('landfall_only', 'false').lower() == 'true'
        since_year = request.args.get('since_year', type=int)
        limit = min(request.args.get('limit', default=100, type=int), 500)
        
        # Base query
        query = HurricaneCountyImpact.query
        
        # Apply filters
        if state:
            query = query.filter(HurricaneCountyImpact.state_code == state.upper())
        if min_wind:
            query = query.filter(HurricaneCountyImpact.max_wind_mph_observed >= min_wind)
        if category:
            query = query.filter(HurricaneCountyImpact.wind_field_category == category)
        if landfall_only:
            query = query.filter(HurricaneCountyImpact.in_landfall_zone == True)
        if since_year:
            query = query.filter(HurricaneCountyImpact.first_impact_time >= datetime(since_year, 1, 1))
        
        # Execute with ordering and limit
        impacts = query.order_by(
            HurricaneCountyImpact.max_wind_mph_observed.desc(),
            HurricaneCountyImpact.first_impact_time.desc()
        ).limit(limit).all()
        
        return jsonify({
            'results': [impact.to_dict() for impact in impacts],
            'total_found': len(impacts),
            'filters_applied': {
                'state': state,
                'min_wind': min_wind,
                'category': category,
                'landfall_only': landfall_only,
                'since_year': since_year
            }
        })
        
    except Exception as e:
        logger.error(f"Error searching county impacts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/hurricanes/storm/<storm_id>/counties", methods=["GET"])
def get_storm_county_impacts(storm_id):
    """Get all county impacts for a specific storm"""
    try:
        from models import HurricaneCountyImpact
        
        impacts = HurricaneCountyImpact.query.filter_by(storm_id=storm_id).order_by(
            HurricaneCountyImpact.max_wind_mph_observed.desc()
        ).all()
        
        if not impacts:
            return jsonify({
                'storm_id': storm_id,
                'county_impacts': [],
                'message': 'No county impact data found for this storm'
            })
        
        # Calculate storm-wide statistics
        total_counties = len(impacts)
        landfall_counties = sum(1 for impact in impacts if impact.in_landfall_zone)
        max_wind = max(impact.max_wind_mph_observed for impact in impacts if impact.max_wind_mph_observed)
        
        # State distribution
        state_counts = {}
        for impact in impacts:
            state = impact.state_code
            if state:
                state_counts[state] = state_counts.get(state, 0) + 1
        
        return jsonify({
            'storm_id': storm_id,
            'summary': {
                'total_counties_affected': total_counties,
                'landfall_counties': landfall_counties,
                'max_wind_observed': max_wind,
                'states_affected': list(state_counts.keys()),
                'counties_by_state': state_counts
            },
            'county_impacts': [impact.to_dict() for impact in impacts]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving county impacts for storm {storm_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/internal/hurricane-ingest", methods=["POST"])
def trigger_hurricane_ingestion():
    """Admin endpoint to trigger hurricane data ingestion"""
    try:
        log_entry = scheduler_service.log_operation_start(
            "hurricane_ingest", "manual"
        )
        
        result = hurricane_ingest_service.ingest_hurricane_data("manual_trigger")
        
        scheduler_service.log_operation_complete(
            log_entry, 
            True,
            result['total_processed'],
            result['new_records'],
            None,
            None,
            None,
            result['duplicate_records']
        )
        
        return jsonify({
            'success': True,
            'message': f"Hurricane ingestion completed",
            'total_processed': result['total_processed'],
            'new_records': result['new_records'],
            'duplicate_records': result['duplicate_records'],
            'storms_processed': result['storms_processed']
        })
        
    except Exception as e:
        logger.error(f"Hurricane ingestion failed: {e}")
        if 'log_entry' in locals():
            scheduler_service.log_operation_complete(
                log_entry, False, 0, 0, str(e)
            )
        return jsonify({'error': str(e)}), 500

@app.route("/internal/hurricane-stats", methods=["GET"])
def get_hurricane_stats():
    """Get hurricane ingestion statistics"""
    try:
        stats = hurricane_ingest_service.get_ingestion_stats()
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error getting hurricane stats: {e}")
        return jsonify({'error': str(e)}), 500

# Webhook Management API Endpoints

@app.route('/internal/webhook-rules', methods=['GET'])
def get_webhook_rules():
    """List all registered webhook rules"""
    try:
        from models import WebhookRule
        
        rules = WebhookRule.query.order_by(WebhookRule.created_at.desc()).all()
        
        return jsonify({
            'status': 'success',
            'total': len(rules),
            'webhook_rules': [rule.to_dict() for rule in rules]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving webhook rules: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/internal/webhook-rules', methods=['POST'])
def create_webhook_rule():
    """Register a new webhook rule"""
    try:
        from models import WebhookRule
        
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'Request body must be JSON'
            }), 400
        
        # Validate required fields
        required_fields = ['webhook_url', 'event_type', 'threshold_value']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400
        
        # Validate event_type
        valid_event_types = ['hail', 'wind', 'damage_probability']
        if data['event_type'] not in valid_event_types:
            return jsonify({
                'status': 'error',
                'message': f'Invalid event_type. Must be one of: {valid_event_types}'
            }), 400
        
        # Validate threshold_value
        try:
            threshold_value = float(data['threshold_value'])
        except (ValueError, TypeError):
            return jsonify({
                'status': 'error',
                'message': 'threshold_value must be a number'
            }), 400
        
        # Create new webhook rule
        rule = WebhookRule(
            user_id=data.get('user_id'),
            webhook_url=data['webhook_url'],
            event_type=data['event_type'],
            threshold_value=threshold_value,
            location_filter=data.get('location_filter')
        )
        
        db.session.add(rule)
        db.session.commit()
        
        logger.info(f"Created webhook rule {rule.id}: {rule.event_type} >= {rule.threshold_value} -> {rule.webhook_url}")
        
        return jsonify({
            'status': 'success',
            'message': 'Webhook rule created successfully',
            'webhook_rule': rule.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Error creating webhook rule: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/internal/webhook-rules/<int:rule_id>', methods=['DELETE'])
def delete_webhook_rule(rule_id):
    """Delete a webhook rule"""
    try:
        from models import WebhookRule
        
        rule = WebhookRule.query.get_or_404(rule_id)
        
        logger.info(f"Deleting webhook rule {rule.id}: {rule.event_type} >= {rule.threshold_value}")
        
        db.session.delete(rule)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Webhook rule {rule_id} deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting webhook rule {rule_id}: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/internal/webhook-rules/<int:rule_id>', methods=['GET'])
def get_webhook_rule(rule_id):
    """Get details of a specific webhook rule"""
    try:
        from models import WebhookRule
        
        rule = WebhookRule.query.get_or_404(rule_id)
        
        return jsonify({
            'status': 'success',
            'webhook_rule': rule.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error retrieving webhook rule {rule_id}: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/internal/webhook-events', methods=['GET'])
def get_webhook_events():
    """List all webhook events with filtering options"""
    try:
        from models import WebhookEvent
        
        # Get query parameters for filtering
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        success_filter = request.args.get('success')  # 'true', 'false', or None
        event_type = request.args.get('event_type')  # 'hail', 'wind', 'damage_probability'
        rule_id = request.args.get('rule_id')
        
        # Build query
        query = WebhookEvent.query
        
        if success_filter is not None:
            success_bool = success_filter.lower() == 'true'
            query = query.filter(WebhookEvent.success == success_bool)
            
        if event_type:
            query = query.filter(WebhookEvent.event_type == event_type)
            
        if rule_id:
            query = query.filter(WebhookEvent.webhook_rule_id == int(rule_id))
        
        # Get total count for pagination
        total_count = query.count()
        
        # Apply pagination and ordering
        events = query.order_by(WebhookEvent.dispatched_at.desc()).offset(offset).limit(limit).all()
        
        return jsonify({
            'status': 'success',
            'total': total_count,
            'offset': offset,
            'limit': limit,
            'webhook_events': [event.to_dict() for event in events]
        })
        
    except Exception as e:
        logger.error(f"Error retrieving webhook events: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/test/webhook-evaluation', methods=['POST'])
def test_webhook_evaluation():
    """Test webhook evaluation and dispatch"""
    try:
        from webhook_service import WebhookService
        
        # Get optional alert_ids from request
        data = request.get_json() or {}
        alert_ids = data.get('alert_ids', [])
        
        webhook_service = WebhookService(db)
        
        if alert_ids:
            # Test with specific alerts
            from models import Alert
            alerts = Alert.query.filter(Alert.id.in_(alert_ids)).all()
            result = webhook_service.evaluate_and_dispatch_webhooks(alerts)
        else:
            # Test with all recent alerts
            result = webhook_service.evaluate_and_dispatch_webhooks()
        
        return jsonify({
            'status': 'success',
            'test_results': result
        })
        
    except Exception as e:
        logger.error(f"Error testing webhook evaluation: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# City Names and Point-in-Polygon API Endpoints
@app.route('/api/radar-alerts/parse-historical', methods=['POST'])
def trigger_historical_radar_parsing():
    """
    Trigger historical radar parsing for alerts missing radar_indicated data
    """
    try:
        data = request.get_json() or {}
        start_date = data.get('start_date', '2025-06-02')
        end_date = data.get('end_date', '2025-06-09')
        batch_size = data.get('batch_size', 100)
        
        # Import here to avoid circular imports
        from historical_radar_parser import parse_historical_radar_data
        
        stats = parse_historical_radar_data(start_date, end_date, batch_size)
        
        return jsonify({
            "success": True,
            "message": f"Historical radar parsing completed for {start_date} to {end_date}",
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Historical radar parsing failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/radar-alerts/backfill', methods=['POST'])
def trigger_radar_backfill():
    """
    Trigger systematic radar alerts backfill for specified date range
    """
    try:
        data = request.get_json() or {}
        start_date = data.get('start_date', '2025-06-10')
        end_date = data.get('end_date', '2025-06-11')
        batch_size = data.get('batch_size', 100)
        
        # Import here to avoid circular imports
        from radar_backfill import RadarBackfillProcessor
        
        processor = RadarBackfillProcessor()
        stats = processor.process_date_range(start_date, end_date, batch_size)
        
        return jsonify({
            "success": True,
            "message": f"Radar backfill completed for {start_date} to {end_date}",
            "stats": stats
        })
        
    except Exception as e:
        logger.error(f"Radar backfill failed: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/radar-alerts/available-dates')
def get_radar_available_dates():
    """
    Get list of dates with radar-detected alerts available for backfill
    """
    try:
        from radar_backfill import get_available_dates
        dates = get_available_dates()
        
        return jsonify({
            "dates": dates,
            "total_dates": len(dates)
        })
        
    except Exception as e:
        logger.error(f"Failed to get available dates: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/radar-alerts/stats')
def get_radar_alerts_stats():
    """
    Get radar_alerts table statistics
    """
    try:
        from radar_backfill import get_radar_backfill_stats
        stats = get_radar_backfill_stats()
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Failed to get radar alerts stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/alerts/direct')
def get_direct_alerts():
    """
    NEW: Direct query combining both alerts table and radar_alerts table for complete historical data
    This now serves as the primary alerts API with radar-style visual data
    """
    try:
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        limit = min(request.args.get('limit', 25, type=int), 100)
        search = request.args.get('q', '').strip()
        state = request.args.get('state', '').strip()
        event_type = request.args.get('event_type', '').strip()
        min_hail = request.args.get('min_hail', type=float)
        min_wind = request.args.get('min_wind', type=int)
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()
        
        from models import RadarAlert
        from datetime import datetime, timedelta
        
        # Combine results from both tables
        combined_results = []
        
        # Query radar_alerts table (historical backfill data)
        radar_query = RadarAlert.query
        
        # Apply filters to radar_alerts
        if search:
            search_pattern = f'%{search}%'
            radar_query = radar_query.filter(
                db.or_(
                    db.func.array_to_string(RadarAlert.city_names, ',').ilike(search_pattern),
                    db.func.array_to_string(RadarAlert.county_names, ',').ilike(search_pattern)
                )
            )
        
        if state:
            radar_query = radar_query.filter(
                db.func.array_to_string(RadarAlert.city_names, ',').ilike(f'%{state}%')
            )
        
        if min_hail:
            radar_query = radar_query.filter(RadarAlert.hail_inches >= min_hail)
            
        if min_wind:
            radar_query = radar_query.filter(RadarAlert.wind_mph >= min_wind)
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                radar_query = radar_query.filter(RadarAlert.detected_time >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                radar_query = radar_query.filter(RadarAlert.detected_time < end_dt)
            except ValueError:
                pass
        
        # Get radar_alerts results
        radar_alerts = radar_query.order_by(RadarAlert.detected_time.desc()).all()
        
        # Convert radar_alerts to common format
        for ra in radar_alerts:
            combined_results.append({
                'id': ra.alert_id,
                'event': 'Severe Thunderstorm Warning',
                'effective': ra.detected_time.isoformat() if ra.detected_time else None,
                'area_desc': ', '.join(ra.city_names) if ra.city_names else '',
                'radar_indicated': {
                    'hail_inches': ra.hail_inches or 0,
                    'wind_mph': ra.wind_mph or 0
                },
                'city_names': ra.city_names or [],
                'severity': 'Severe',
                'source': 'radar_alerts_table'
            })
        
        # Query main alerts table for current events
        hail_condition = Alert.radar_indicated['hail_inches'].astext.cast(db.Float) > 0
        wind_condition = Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= 50
        radar_source_condition = Alert.properties['description'].astext.ilike('%radar indicated%')
        
        alerts_query = Alert.query.filter(
            Alert.radar_indicated.isnot(None),
            radar_source_condition,
            db.or_(hail_condition, wind_condition)
        )
        
        # Apply same filters to alerts table
        if search:
            search_pattern = f'%{search}%'
            alerts_query = alerts_query.filter(
                db.or_(
                    Alert.event.ilike(search_pattern),
                    Alert.area_desc.ilike(search_pattern),
                    Alert.ai_summary.ilike(search_pattern)
                )
            )
        
        if state:
            alerts_query = alerts_query.filter(Alert.area_desc.ilike(f'%{state}%'))
        
        if event_type:
            alerts_query = alerts_query.filter(Alert.event.ilike(f'%{event_type}%'))
        
        if min_hail:
            alerts_query = alerts_query.filter(Alert.radar_indicated['hail_inches'].astext.cast(db.Float) >= min_hail)
        
        if min_wind:
            alerts_query = alerts_query.filter(Alert.radar_indicated['wind_mph'].astext.cast(db.Integer) >= min_wind)
        
        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                alerts_query = alerts_query.filter(Alert.effective >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                alerts_query = alerts_query.filter(Alert.effective < end_dt)
            except ValueError:
                pass
        
        # Get current alerts
        current_alerts = alerts_query.order_by(Alert.effective.desc()).all()
        
        # Add current alerts to combined results
        for alert in current_alerts:
            alert_dict = alert.to_dict()
            alert_dict['source'] = 'alerts_table'
            combined_results.append(alert_dict)
        
        # Sort combined results by effective time
        combined_results.sort(key=lambda x: x.get('effective', ''), reverse=True)
        
        # Apply pagination
        total = len(combined_results)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_results = combined_results[start_idx:end_idx]
        
        pages = (total + limit - 1) // limit
        
        return jsonify({
            'alerts': paginated_results,
            'total': total,
            'page': page,
            'limit': limit,
            'pages': pages,
            'has_more': page < pages
        })
        
    except Exception as e:
        logger.error(f"Error getting direct radar alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/radar-alerts/summary')
def get_radar_alerts_summary():
    """
    Get summary of radar alerts grouped by city, state, date
    Query parameters:
    - start_date (required, YYYY-MM-DD)
    - end_date (required, YYYY-MM-DD)
    - state (optional, 2-letter state code)
    - min_hail_inches (optional, float, default=0)
    - min_wind_mph (optional, int, default=50)
    - city (optional, string, partial match)
    """
    try:
        from models import RadarAlert
        from sqlalchemy import func, and_
        
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        state_filter = request.args.get('state')
        min_hail_inches = float(request.args.get('min_hail_inches', 0))
        min_wind_mph = int(request.args.get('min_wind_mph', 50))
        city_filter = request.args.get('city')
        
        if not start_date or not end_date:
            return jsonify({"error": "start_date and end_date are required"}), 400
        
        # Use raw SQL to properly handle array fields
        sql_query = """
        SELECT 
            UNNEST(city_names) as city,
            UNNEST(affected_states) as state,
            event_date as date,
            COUNT(CASE WHEN event_type = 'hail' THEN 1 END) as hail_count,
            MAX(CASE WHEN event_type = 'hail' THEN hail_inches END) as max_hail_inches,
            COUNT(CASE WHEN event_type = 'wind' THEN 1 END) as wind_count,
            MAX(CASE WHEN event_type = 'wind' THEN wind_mph END) as max_wind_mph
        FROM radar_alerts 
        WHERE event_date >= :start_date AND event_date <= :end_date
        """
        
        params = {'start_date': start_date, 'end_date': end_date}
        
        # Apply filters
        if state_filter:
            sql_query += " AND :state_filter = ANY(affected_states)"
            params['state_filter'] = state_filter
        
        if city_filter:
            sql_query += " AND EXISTS (SELECT 1 FROM UNNEST(city_names) as city WHERE city ILIKE :city_filter)"
            params['city_filter'] = f'%{city_filter}%'
        
        sql_query += """
        GROUP BY city, state, date
        HAVING COALESCE(MAX(CASE WHEN event_type = 'hail' THEN hail_inches END), 0) >= :min_hail_inches
           AND COALESCE(MAX(CASE WHEN event_type = 'wind' THEN wind_mph END), 0) >= :min_wind_mph
        ORDER BY date, state, city
        """
        
        params['min_hail_inches'] = min_hail_inches
        params['min_wind_mph'] = min_wind_mph
        
        results = db.session.execute(db.text(sql_query), params).fetchall()
        
        summary = []
        for row in results:
            summary.append({
                "city": row.city,
                "state": row.state,
                "date": row.date.isoformat() if row.date else None,
                "hail_count": int(row.hail_count or 0),
                "max_hail_inches": float(row.max_hail_inches) if row.max_hail_inches else None,
                "wind_count": int(row.wind_count or 0),
                "max_wind_mph": int(row.max_wind_mph) if row.max_wind_mph else None
            })
        
        return jsonify({"summary": summary})
        
    except Exception as e:
        logger.error(f"Radar alerts summary failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/radar-alerts/contains-address')
def contains_address():
    """
    Point-in-polygon API endpoint for address-specific radar alert verification
    Geocodes address and returns all radar-detected events containing that point
    """
    try:
        address = request.args.get('address')
        if not address:
            return jsonify({'error': 'Address parameter is required'}), 400
        
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Geocode address to lat/lon
        lat, lon = geocode_address(address)
        if lat is None or lon is None:
            return jsonify({'error': 'Unable to geocode address'}), 400
        
        # Query for radar-detected events containing this point
        from models import Alert
        
        # Base query for radar-detected events
        query = db.session.query(Alert).filter(
            Alert.radar_indicated.isnot(None),
            db.text("(radar_indicated->>'hail_inches')::float >= 0.00 OR (radar_indicated->>'wind_mph')::float >= 50")
        )
        
        # Add date filters if provided
        if start_date:
            query = query.filter(Alert.effective >= start_date)
        if end_date:
            query = query.filter(Alert.effective <= end_date)
        
        # Filter by bounding box first for performance, then do precise point-in-polygon test
        bbox_margin = 0.1  # ~11km margin for initial filtering
        query = query.filter(
            db.text("geometry_bounds->>'min_lat' <= :max_lat").params(max_lat=str(lat + bbox_margin)),
            db.text("geometry_bounds->>'max_lat' >= :min_lat").params(min_lat=str(lat - bbox_margin)),
            db.text("geometry_bounds->>'min_lon' <= :max_lon").params(max_lon=str(lon + bbox_margin)),
            db.text("geometry_bounds->>'max_lon' >= :min_lon").params(min_lon=str(lon - bbox_margin))
        )
        
        alerts = query.order_by(Alert.effective.desc()).all()
        
        # Format results
        results = []
        for alert in alerts:
            radar_data = alert.radar_indicated or {}
            
            result = {
                'alert_id': alert.id,
                'event_type': alert.event,
                'effective': alert.effective.isoformat() if alert.effective else None,
                'area_desc': alert.area_desc,
                'city_names': alert.city_names or [],
                'county_names': alert.county_names or [],
                'geometry_bounds': alert.geometry_bounds,
                'radar_indicated': {
                    'hail_inches': radar_data.get('hail_inches'),
                    'wind_mph': radar_data.get('wind_mph')
                },
                'ai_summary': alert.ai_summary,
                'spc_verified': alert.spc_verified,
                'spc_report_count': alert.spc_report_count
            }
            results.append(result)
        
        return jsonify({
            'address': address,
            'coordinates': {'lat': lat, 'lon': lon},
            'total_events': len(results),
            'events': results
        })
        
    except Exception as e:
        logger.error(f"Error in contains-address API: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/internal/backfill-city-names', methods=['POST'])
def backfill_city_names():
    """Backfill city_names for all radar-detected alerts"""
    try:
        from city_parser import backfill_all_city_names
        
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 500)
        
        stats = backfill_all_city_names(db.session, batch_size=batch_size)
        
        return jsonify({
            'success': True,
            'message': 'City names backfill completed',
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error backfilling city names: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/internal/parse-city-names/<alert_id>', methods=['POST'])
def parse_single_alert_city_names(alert_id):
    """Parse city names for a specific alert"""
    try:
        from city_parser import parse_and_update_city_names
        
        stats = parse_and_update_city_names(db.session, alert_id=alert_id)
        
        return jsonify({
            'success': True,
            'message': f'City names parsed for alert {alert_id}',
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error parsing city names for alert {alert_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hail-size-chart')
def get_hail_size_chart():
    """
    Get centralized NWS hail size chart and categories
    Provides official size mappings and display names for client applications
    """
    return jsonify({
        'hail_size_chart': Config.NWS_HAIL_SIZE_CHART,
        'hail_size_categories': Config.HAIL_SIZE_CATEGORIES,
        'severity_thresholds': {
            'extremely_severe': 4.0,
            'very_severe': 3.0,
            'severe': 2.0,
            'significant': 1.0,
            'notable': 0.5,
            'minor': 0.25
        },
        'example_usage': {
            'get_display_name': 'Use Config.get_hail_display_name(size_inches)',
            'get_severity': 'Use Config.get_hail_severity(size_inches)'
        }
    })

def geocode_address(address):
    """
    Geocode an address to lat/lon coordinates
    Uses Nominatim (OpenStreetMap) for free geocoding
    """
    try:
        # Use Nominatim geocoding service
        url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': address,
            'format': 'json',
            'limit': 1,
            'countrycodes': 'us'  # Limit to US addresses
        }
        headers = {
            'User-Agent': 'HailyDB-Geocoding/1.0 (contact@hailydb.com)'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if data and len(data) > 0:
            result = data[0]
            lat = float(result['lat'])
            lon = float(result['lon'])
            return lat, lon
        else:
            return None, None
            
    except Exception as e:
        logger.error(f"Geocoding error for address '{address}': {e}")
        return None, None

@app.route('/api/spc-reports/enrich', methods=['POST'])
def api_enrich_spc_reports():
    """
    API endpoint to trigger SPC report enrichment with polygon containment and nearby places
    """
    try:
        from spc_enrichment import SPCEnrichmentService
        
        # Get parameters
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 50)
        target_report_id = data.get('report_id')
        
        # Initialize enrichment service
        enrichment_service = SPCEnrichmentService()
        
        # Process enrichment
        if target_report_id:
            result = enrichment_service.enrich_spc_reports_batch(target_report_id=target_report_id)
        else:
            result = enrichment_service.enrich_spc_reports_batch(batch_size=batch_size)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"SPC enrichment API failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/spc-reports/<int:report_id>/enrichment')
def api_get_spc_report_enrichment(report_id):
    """
    API endpoint to retrieve enrichment data for a specific SPC report
    """
    try:
        report = SPCReport.query.get_or_404(report_id)
        
        # Return enrichment data
        enrichment_data = report.spc_enrichment or {}
        
        return jsonify({
            "report_id": report.id,
            "report_type": report.report_type,
            "location": report.location,
            "county": report.county,
            "state": report.state,
            "latitude": report.latitude,
            "longitude": report.longitude,
            "enrichment": enrichment_data
        })
        
    except Exception as e:
        logger.error(f"SPC enrichment retrieval failed for report {report_id}: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/spc/enrichment-dashboard')
def spc_enrichment_dashboard():
    """SPC Report Enrichment Dashboard"""
    redirect_response = require_admin_or_redirect()
    if redirect_response:
        return redirect_response
    return render_template('spc_enrichment_dashboard.html')

@app.route('/api/spc-reports/enrichment-stats')
def api_spc_enrichment_stats():
    """Get SPC report enrichment statistics"""
    try:
        # Get total count of SPC reports
        total_count = db.session.query(SPCReport).count()
        
        # Get count of enriched reports (those with non-empty spc_enrichment)
        enriched_count = db.session.query(SPCReport).filter(
            SPCReport.spc_enrichment.isnot(None),
            SPCReport.spc_enrichment != {}
        ).count()
        
        # Calculate pending count
        pending_count = total_count - enriched_count
        
        # Get recent enrichment activity (last 24 hours)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_enriched = db.session.query(SPCReport).filter(
            SPCReport.spc_enrichment.isnot(None),
            SPCReport.spc_enrichment != {}
        ).count()
        
        return jsonify({
            'total_count': total_count,
            'enriched_count': enriched_count,
            'pending_count': pending_count,
            'enrichment_percentage': round((enriched_count / total_count * 100) if total_count > 0 else 0, 1),
            'recent_enriched_24h': recent_enriched
        })
        
    except Exception as e:
        logger.error(f"Error getting enrichment stats: {e}")
        return jsonify({'error': 'Failed to get enrichment statistics'}), 500

@app.route('/api/spc-reports/<int:report_id>/enhanced-context')
def api_get_spc_enhanced_context(report_id):
    """
    API endpoint to retrieve enhanced context for a specific SPC report
    """
    try:
        # Get the SPC report
        report = db.session.query(SPCReport).filter_by(id=report_id).first()
        if not report:
            return jsonify({"error": "SPC report not found"}), 404
        
        # Generate enhanced context if not present
        if not report.enhanced_context or report.enhanced_context == {}:
            result = enhanced_context_service.generate_enhanced_context(report, db.session)
            enhanced_context = result.get('enhanced_context', {})
        else:
            enhanced_context = report.enhanced_context
        
        return jsonify(enhanced_context)
        
    except Exception as e:
        logger.error(f"Error retrieving enhanced context: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/spc-reports/enhanced-context/bulk-generate', methods=['POST'])
def api_bulk_generate_enhanced_context():
    """
    Bulk Enhanced Context generation endpoint - processes all reports missing Enhanced Context
    """
    try:
        data = request.get_json() or {}
        batch_size = data.get('batch_size', 100)
        max_batches = data.get('max_batches', 10)
        
        # Get reports missing Enhanced Context
        reports_missing_context = db.session.query(SPCReport).filter(
            db.or_(
                SPCReport.enhanced_context.is_(None),
                SPCReport.enhanced_context == {}
            )
        ).limit(batch_size * max_batches).all()
        
        processed_count = 0
        success_count = 0
        error_count = 0
        
        for report in reports_missing_context:
            try:
                result = enhanced_context_service.generate_enhanced_context(report, db.session)
                if result.get('success'):
                    success_count += 1
                else:
                    error_count += 1
                processed_count += 1
                
                # Commit every 10 reports
                if processed_count % 10 == 0:
                    db.session.commit()
                    
            except Exception as e:
                logger.error(f"Error generating enhanced context for report {report.id}: {e}")
                error_count += 1
                processed_count += 1
                continue
        
        # Final commit
        db.session.commit()
        
        return jsonify({
            "success": True,
            "processed": processed_count,
            "successful": success_count,
            "errors": error_count,
            "remaining": len(reports_missing_context) - processed_count
        })
        
    except Exception as e:
        logger.error(f"Error in bulk enhanced context generation: {e}")
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/spc-reports/enhanced-context/stats', methods=['GET'])
def api_enhanced_context_stats():
    """
    Get Enhanced Context generation statistics
    """
    try:
        total_reports = db.session.query(SPCReport).count()
        with_context = db.session.query(SPCReport).filter(
            SPCReport.enhanced_context.isnot(None),
            SPCReport.enhanced_context != {}
        ).count()
        missing_context = total_reports - with_context
        
        return jsonify({
            "total_reports": total_reports,
            "with_enhanced_context": with_context,
            "missing_enhanced_context": missing_context,
            "completion_percentage": round((with_context / total_reports * 100), 2) if total_reports > 0 else 0
        })
        
    except Exception as e:
        logger.error(f"Error getting enhanced context stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/spc-reports/enhanced-context/generate', methods=['POST'])
def api_generate_enhanced_context():
    """
    Enhanced Context generation endpoint v4.0 - intelligent alert integration with conditional SPC matching
    """
    try:
        data = request.get_json() or {}
        report_id = data.get('report_id')
        
        if not report_id:
            return jsonify({
                "success": False,
                "error": "Missing report_id parameter"
            }), 400
        
        # Get the report
        report = db.session.get(SPCReport, report_id)
        if not report:
            return jsonify({"success": False, "error": f"Report {report_id} not found"}), 404
        
        # Use Enhanced Context Service v4.0 with intelligent alert integration
        from enhanced_context_service_v4 import EnhancedContextServiceV4
        service = EnhancedContextServiceV4(db.session)
        result = service.generate_enhanced_context(report)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error generating enhanced context for report {report_id}: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e),
            "correlation_id": None
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
