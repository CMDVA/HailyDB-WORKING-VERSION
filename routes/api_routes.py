"""
API Routes Blueprint
Extracted from monolithic app.py for better organization
"""
from flask import Blueprint, request, jsonify
import logging
from datetime import datetime, timedelta

from models import db, Alert, SPCReport, RadarAlert, WebhookRule, WebhookEvent
from services.enhanced_context_service import EnhancedContextService
from utils.response_utils import success_response, error_response, handle_errors, paginated_response
from utils.config_utils import PaginationConfig

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')
enhanced_context_service = EnhancedContextService()

@api_bp.route('/alerts')
@handle_errors
def get_alerts():
    """Get recent alerts with optional filtering"""
    page = request.args.get('page', default=1, type=int)
    per_page = min(request.args.get('per_page', default=PaginationConfig.DEFAULT_PAGE_SIZE, type=int), 
                   PaginationConfig.API_MAX_PAGE_SIZE)
    
    state = request.args.get('state')
    category = request.args.get('category')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Alert.query
    
    if state:
        query = query.filter(Alert.areas.like(f'%{state}%'))
    if category:
        query = query.filter(Alert.category == category)
    if start_date:
        query = query.filter(Alert.effective >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.filter(Alert.effective <= datetime.fromisoformat(end_date))
    
    query = query.order_by(Alert.effective.desc())
    
    alerts = query.paginate(page=page, per_page=per_page, error_out=False)
    
    alert_data = []
    for alert in alerts.items:
        alert_dict = {
            'id': alert.id,
            'title': alert.title,
            'category': alert.category,
            'severity': alert.severity,
            'urgency': alert.urgency,
            'certainty': alert.certainty,
            'effective': alert.effective.isoformat() if alert.effective else None,
            'onset': alert.onset.isoformat() if alert.onset else None,
            'expires': alert.expires.isoformat() if alert.expires else None,
            'areas': alert.areas,
            'description': alert.description,
            'instruction': alert.instruction
        }
        alert_data.append(alert_dict)
    
    return paginated_response(
        data=alert_data,
        page=page,
        per_page=per_page,
        total=alerts.total
    )

@api_bp.route('/alerts/<alert_id>')
@handle_errors
def get_alert_detail(alert_id):
    """Get detailed information for a specific alert"""
    alert = Alert.query.get_or_404(alert_id)
    
    alert_data = {
        'id': alert.id,
        'title': alert.title,
        'category': alert.category,
        'severity': alert.severity,
        'urgency': alert.urgency,
        'certainty': alert.certainty,
        'effective': alert.effective.isoformat() if alert.effective else None,
        'onset': alert.onset.isoformat() if alert.onset else None,
        'expires': alert.expires.isoformat() if alert.expires else None,
        'areas': alert.areas,
        'description': alert.description,
        'instruction': alert.instruction,
        'geometry': alert.geometry,
        'radar_indicated': alert.radar_indicated,
        'hail_size_inches': alert.hail_size_inches,
        'wind_speed_mph': alert.wind_speed_mph,
        'city_names': alert.city_names
    }
    
    return success_response(alert_data)

@api_bp.route('/spc-reports/enhanced-context/generate', methods=['POST'])
@handle_errors
def generate_enhanced_context():
    """Generate Enhanced Context for SPC report with 6 geo data points"""
    data = request.get_json()
    report_id = data.get('report_id')
    
    if not report_id:
        return error_response("report_id is required", 400)
    
    report = SPCReport.query.get(report_id)
    if not report:
        return error_response("SPC report not found", 404)
    
    # Generate Enhanced Context
    enhanced_context = enhanced_context_service.generate_enhanced_context(report)
    
    # Update report with Enhanced Context
    report.enhanced_context = enhanced_context
    report.enhanced_context_version = enhanced_context["version"]
    report.enhanced_context_generated_at = datetime.utcnow()
    
    db.session.commit()
    
    return success_response({
        "enhanced_context": enhanced_context,
        "version": enhanced_context["version"],
        "correlation_id": None
    }, "Enhanced context generated successfully")

@api_bp.route('/spc-reports/<int:report_id>/enhanced-context')
@handle_errors
def get_spc_enhanced_context(report_id):
    """Get Enhanced Context for a specific SPC report"""
    report = SPCReport.query.get_or_404(report_id)
    
    if not report.enhanced_context:
        return error_response("Enhanced context not available for this report", 404)
    
    return success_response({
        "enhanced_context": report.enhanced_context,
        "version": report.enhanced_context_version,
        "generated_at": report.enhanced_context_generated_at.isoformat() if report.enhanced_context_generated_at else None
    })

@api_bp.route('/live-radar-alerts')
@handle_errors
def get_live_radar_alerts():
    """Get live radar alerts with state filtering"""
    state = request.args.get('state')
    severity_min = request.args.get('severity_min', type=int)
    limit = min(request.args.get('limit', default=100, type=int), PaginationConfig.API_MAX_PAGE_SIZE)
    
    query = Alert.query.filter(Alert.radar_indicated == True)
    
    if state:
        query = query.filter(Alert.areas.like(f'%{state}%'))
    
    if severity_min:
        if severity_min >= 58:
            query = query.filter(Alert.wind_speed_mph >= severity_min)
        elif severity_min >= 1:
            query = query.filter(Alert.hail_size_inches >= severity_min)
    
    # Get recent alerts only (last 24 hours)
    cutoff_time = datetime.utcnow() - timedelta(hours=24)
    query = query.filter(Alert.effective >= cutoff_time)
    
    alerts = query.order_by(Alert.effective.desc()).limit(limit).all()
    
    alert_data = []
    for alert in alerts:
        alert_dict = {
            'id': alert.id,
            'title': alert.title,
            'category': alert.category,
            'severity': alert.severity,
            'effective': alert.effective.isoformat() if alert.effective else None,
            'areas': alert.areas,
            'radar_indicated': alert.radar_indicated,
            'hail_size_inches': alert.hail_size_inches,
            'wind_speed_mph': alert.wind_speed_mph,
            'city_names': alert.city_names
        }
        alert_data.append(alert_dict)
    
    return success_response({
        "alerts": alert_data,
        "count": len(alert_data),
        "state_filter": state,
        "severity_filter": severity_min
    })

@api_bp.route('/radar-alerts/summary')
@handle_errors
def get_radar_alerts_summary():
    """Get summary of radar alerts grouped by location and date"""
    start_date = request.args.get('start_date', required=True)
    end_date = request.args.get('end_date', required=True)
    state = request.args.get('state')
    min_hail_inches = request.args.get('min_hail_inches', default=0, type=float)
    min_wind_mph = request.args.get('min_wind_mph', default=50, type=int)
    city = request.args.get('city')
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    except ValueError:
        return error_response("Invalid date format. Use YYYY-MM-DD", 400)
    
    query = RadarAlert.query.filter(
        RadarAlert.event_date >= start_dt.date(),
        RadarAlert.event_date <= end_dt.date()
    )
    
    if state:
        query = query.filter(RadarAlert.state == state.upper())
    if min_hail_inches > 0:
        query = query.filter(RadarAlert.hail_size_inches >= min_hail_inches)
    if min_wind_mph > 0:
        query = query.filter(RadarAlert.wind_speed_mph >= min_wind_mph)
    if city:
        query = query.filter(RadarAlert.city_names.like(f'%{city}%'))
    
    alerts = query.order_by(RadarAlert.event_date.desc(), RadarAlert.event_time.desc()).all()
    
    summary_data = []
    for alert in alerts:
        summary_data.append({
            'id': alert.id,
            'event_date': alert.event_date.isoformat(),
            'event_time': alert.event_time.strftime('%H:%M') if alert.event_time else None,
            'city_names': alert.city_names,
            'state': alert.state,
            'hail_size_inches': alert.hail_size_inches,
            'wind_speed_mph': alert.wind_speed_mph,
            'geometry': alert.geometry
        })
    
    return success_response({
        "alerts": summary_data,
        "count": len(summary_data),
        "filters": {
            "start_date": start_date,
            "end_date": end_date,
            "state": state,
            "min_hail_inches": min_hail_inches,
            "min_wind_mph": min_wind_mph,
            "city": city
        }
    })

@api_bp.route('/webhook-rules', methods=['GET'])
@handle_errors
def get_webhook_rules():
    """List all registered webhook rules"""
    rules = WebhookRule.query.all()
    
    rules_data = []
    for rule in rules:
        rules_data.append({
            'id': rule.id,
            'name': rule.name,
            'webhook_url': rule.webhook_url,
            'conditions': rule.conditions,
            'is_active': rule.is_active,
            'created_at': rule.created_at.isoformat() if rule.created_at else None
        })
    
    return success_response(rules_data)

@api_bp.route('/webhook-rules', methods=['POST'])
@handle_errors
def create_webhook_rule():
    """Create a new webhook rule"""
    data = request.get_json()
    
    required_fields = ['name', 'webhook_url', 'conditions']
    for field in required_fields:
        if field not in data:
            return error_response(f"Missing required field: {field}", 400)
    
    rule = WebhookRule(
        name=data['name'],
        webhook_url=data['webhook_url'],
        conditions=data['conditions'],
        is_active=data.get('is_active', True)
    )
    
    db.session.add(rule)
    db.session.commit()
    
    return success_response({
        'id': rule.id,
        'name': rule.name,
        'webhook_url': rule.webhook_url,
        'conditions': rule.conditions,
        'is_active': rule.is_active
    }, "Webhook rule created successfully", 201)

@api_bp.route('/webhook-events')
@handle_errors
def get_webhook_events():
    """List webhook events with filtering"""
    page = request.args.get('page', default=1, type=int)
    per_page = min(request.args.get('per_page', default=PaginationConfig.DEFAULT_PAGE_SIZE, type=int), 
                   PaginationConfig.API_MAX_PAGE_SIZE)
    
    rule_id = request.args.get('rule_id', type=int)
    status = request.args.get('status')
    
    query = WebhookEvent.query
    
    if rule_id:
        query = query.filter(WebhookEvent.webhook_rule_id == rule_id)
    if status:
        query = query.filter(WebhookEvent.status == status)
    
    events = query.order_by(WebhookEvent.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    events_data = []
    for event in events.items:
        events_data.append({
            'id': event.id,
            'webhook_rule_id': event.webhook_rule_id,
            'alert_id': event.alert_id,
            'status': event.status,
            'response_code': event.response_code,
            'created_at': event.created_at.isoformat() if event.created_at else None,
            'delivered_at': event.delivered_at.isoformat() if event.delivered_at else None
        })
    
    return paginated_response(
        data=events_data,
        page=page,
        per_page=per_page,
        total=events.total
    )