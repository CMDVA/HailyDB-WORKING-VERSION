import os
import logging
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import atexit

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

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://localhost/nws_alerts")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the app with the extension
db.init_app(app)

# Add custom Jinja2 filters
@app.template_filter('number_format')
def number_format(value):
    """Format numbers with commas for thousands"""
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value

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
    
    # Initialize autonomous scheduler
    from autonomous_scheduler import AutonomousScheduler
    autonomous_scheduler = AutonomousScheduler(db)

# API Routes
@app.route('/alerts')
def get_alerts():
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

@app.route('/alerts/<alert_id>')
def get_alert(alert_id):
    """Get single enriched alert"""
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

@app.route('/alerts/summary')
def get_alerts_summary():
    """Get recent alert summaries with AI-generated content and verification summaries"""
    # Get alerts with either AI summaries or SPC verification summaries
    alerts = Alert.query.filter(
        (Alert.ai_summary.isnot(None)) | (Alert.spc_ai_summary.isnot(None))
    ).order_by(Alert.ingested_at.desc()).limit(20).all()
    
    summaries = []
    for alert in alerts:
        summary_data = {
            'id': alert.id,
            'event': alert.event,
            'severity': alert.severity,
            'area_desc': alert.area_desc,
            'effective': alert.effective.isoformat() if alert.effective else None,
            'expires': alert.expires.isoformat() if alert.expires else None,
            'ai_summary': alert.ai_summary,
            'ai_tags': alert.ai_tags,
            'spc_verified': alert.spc_verified,
            'spc_verification_summary': alert.spc_ai_summary,
            'spc_confidence_score': alert.spc_confidence_score,
            'spc_report_count': alert.spc_report_count
        }
        
        # Add verification status for quick filtering
        if alert.spc_verified and alert.spc_ai_summary:
            summary_data['verification_status'] = 'verified_with_ai_summary'
        elif alert.spc_verified:
            summary_data['verification_status'] = 'verified'
        elif alert.ai_summary:
            summary_data['verification_status'] = 'ai_summary_only'
        else:
            summary_data['verification_status'] = 'basic'
            
        summaries.append(summary_data)
    
    if request.args.get('format') == 'json':
        return jsonify({
            'summaries': summaries,
            'total_count': len(summaries),
            'verified_count': len([s for s in summaries if s['spc_verified']]),
            'ai_summary_count': len([s for s in summaries if s['spc_verification_summary']])
        })
    
    return render_template('summaries.html', summaries=summaries)

@app.route('/api/alerts/by-state/<state>')
def get_alerts_by_state(state):
    """Get alerts for a specific state"""
    query = Alert.query.filter(
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
        'total_alerts': len(alerts),
        'alerts': [alert.to_dict() for alert in alerts]
    })

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

@app.route('/spc/reports/<int:report_id>')
def view_spc_report_detail(report_id):
    """View detailed information for a specific SPC report"""
    try:
        report = SPCReport.query.get_or_404(report_id)
        return render_template('spc_report_detail.html', report=report)
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

@app.route('/internal/dashboard')
def internal_dashboard():
    """Admin dashboard"""
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
                
                # Count total data rows (subtract 3 for headers)
                lines = response.text.strip().split('\n')
                total_lines = len(lines)
                spc_live_count = max(0, total_lines - 3)
                
                match_status = 'MATCH' if hailydb_count == spc_live_count else 'MISMATCH'
                
                verification_results.append({
                    'date': check_date.strftime('%Y-%m-%d'),
                    'hailydb_count': hailydb_count,
                    'spc_live_count': spc_live_count,
                    'match_status': match_status
                })
                
            except requests.RequestException:
                # SPC file not available for this date - always show for reference
                verification_results.append({
                    'date': check_date.strftime('%Y-%m-%d'),
                    'hailydb_count': hailydb_count,
                    'spc_live_count': None,
                    'match_status': 'PENDING' if check_date == today else 'UNKNOWN'
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
    return redirect(url_for('internal_dashboard'))

@app.route('/ingestion-logs')
def ingestion_logs():
    """View ingestion logs page"""
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
    return render_template('spc_matches.html')

@app.route('/hurricane-tracks')
def hurricane_tracks():
    """View hurricane tracks page"""
    return render_template('hurricane_tracks.html')

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
        
        # Filter by time
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
            # Parse SPC reports
            spc_reports = []
            if match.spc_reports:
                for report in match.spc_reports:
                    spc_reports.append({
                        'report_type': report.get('report_type', 'unknown'),
                        'time_utc': report.get('time_utc', ''),
                        'location': report.get('location', ''),
                        'county': report.get('county', ''),
                        'state': report.get('state', ''),
                        'comments': report.get('comments', '')
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

@app.route("/api/hurricanes/storms/<storm_id>", methods=["GET"])
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

if __name__ == '__main__':
    with app.app_context():
        init_scheduler()
    app.run(host='0.0.0.0', port=5000, debug=True)
