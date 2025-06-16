"""
Web Interface Routes Blueprint
User-facing web pages and templates
"""
from flask import Blueprint, render_template, request, redirect, url_for
import logging
from datetime import datetime, timedelta

from models import db, Alert, SPCReport, RadarAlert
from utils.response_utils import handle_errors
from utils.config_utils import PaginationConfig

logger = logging.getLogger(__name__)

web_bp = Blueprint('web', __name__)

@web_bp.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@web_bp.route('/spc-reports')
@handle_errors
def view_spc_reports():
    """View SPC reports in web interface with search functionality"""
    page = request.args.get('page', default=1, type=int)
    per_page = min(request.args.get('per_page', default=PaginationConfig.DEFAULT_PAGE_SIZE, type=int), 
                   PaginationConfig.MAX_PAGE_SIZE)
    
    report_type = request.args.get('type')
    state = request.args.get('state')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = SPCReport.query
    
    if report_type:
        query = query.filter(SPCReport.report_type == report_type.upper())
    if state:
        query = query.filter(SPCReport.state == state.upper())
    if start_date:
        query = query.filter(SPCReport.report_date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(SPCReport.report_date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    reports = query.order_by(SPCReport.report_date.desc(), SPCReport.report_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('spc_reports.html', 
                         reports=reports,
                         report_type=report_type,
                         state=state,
                         start_date=start_date,
                         end_date=end_date)

@web_bp.route('/spc-reports/<int:report_id>')
@handle_errors
def view_spc_report_detail(report_id):
    """View detailed information for a specific SPC report"""
    report = SPCReport.query.get_or_404(report_id)
    return render_template('spc_report_detail.html', report=report)

@web_bp.route('/radar-alerts')
@handle_errors
def view_radar_alerts():
    """View radar-detected alerts interface"""
    page = request.args.get('page', default=1, type=int)
    per_page = min(request.args.get('per_page', default=PaginationConfig.DEFAULT_PAGE_SIZE, type=int), 
                   PaginationConfig.MAX_PAGE_SIZE)
    
    state = request.args.get('state')
    min_hail = request.args.get('min_hail', type=float)
    min_wind = request.args.get('min_wind', type=int)
    
    query = RadarAlert.query
    
    if state:
        query = query.filter(RadarAlert.state == state.upper())
    if min_hail:
        query = query.filter(RadarAlert.hail_size_inches >= min_hail)
    if min_wind:
        query = query.filter(RadarAlert.wind_speed_mph >= min_wind)
    
    # Default to recent alerts (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    query = query.filter(RadarAlert.event_date >= week_ago.date())
    
    alerts = query.order_by(RadarAlert.event_date.desc(), RadarAlert.event_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('radar_alerts.html',
                         alerts=alerts,
                         state=state,
                         min_hail=min_hail,
                         min_wind=min_wind)

@web_bp.route('/live-radar-dashboard')
@handle_errors
def live_radar_dashboard():
    """Live Radar Alerts Dashboard"""
    return render_template('live_radar_dashboard.html')

@web_bp.route('/spc-matches')
@handle_errors
def spc_matches():
    """View SPC verified matches page"""
    return render_template('spc_matches.html')

@web_bp.route('/hurricane-tracks')
@handle_errors
def hurricane_tracks():
    """View hurricane tracks page"""
    return render_template('hurricane_tracks.html')

@web_bp.route('/address-targeting')
@handle_errors
def address_targeting():
    """Address-specific weather event targeting interface"""
    return render_template('address_targeting.html')

@web_bp.route('/spc-enrichment-dashboard')
@handle_errors
def spc_enrichment_dashboard():
    """SPC Report Enrichment Dashboard"""
    return render_template('spc_enrichment_dashboard.html')