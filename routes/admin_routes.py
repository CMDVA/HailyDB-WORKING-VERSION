"""
Admin Routes Blueprint
Internal management and monitoring endpoints
"""
from flask import Blueprint, request, jsonify, render_template
import logging
from datetime import datetime, timedelta

from models import db, Alert, SPCReport, IngestionLog, WebhookRule
from services.enhanced_context_service import EnhancedContextService
from utils.response_utils import success_response, error_response, handle_errors
from utils.config_utils import PaginationConfig

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/internal')
enhanced_context_service = EnhancedContextService()

@admin_bp.route('/status')
@handle_errors
def internal_status():
    """Health status endpoint - comprehensive system diagnostics"""
    try:
        # Database connectivity check
        db.session.execute('SELECT 1')
        db_status = "healthy"
        
        # Recent alert counts
        recent_alerts = Alert.query.filter(
            Alert.effective >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        # SPC report counts
        spc_reports_today = SPCReport.query.filter(
            SPCReport.report_date == datetime.utcnow().date()
        ).count()
        
        # Enhanced context coverage
        enhanced_reports = SPCReport.query.filter(
            SPCReport.enhanced_context.isnot(None)
        ).count()
        
        total_reports = SPCReport.query.count()
        
        # Recent ingestion logs
        recent_logs = IngestionLog.query.filter(
            IngestionLog.start_time >= datetime.utcnow() - timedelta(hours=6)
        ).order_by(IngestionLog.start_time.desc()).limit(10).all()
        
        log_data = []
        for log in recent_logs:
            log_data.append({
                'operation_type': log.operation_type,
                'status': log.status,
                'start_time': log.start_time.isoformat() if log.start_time else None,
                'end_time': log.end_time.isoformat() if log.end_time else None,
                'records_processed': log.records_processed,
                'errors_count': log.errors_count
            })
        
        status_data = {
            'database': db_status,
            'alerts_24h': recent_alerts,
            'spc_reports_today': spc_reports_today,
            'enhanced_context_coverage': {
                'enhanced': enhanced_reports,
                'total': total_reports,
                'percentage': round((enhanced_reports / total_reports * 100) if total_reports > 0 else 0, 1)
            },
            'recent_operations': log_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return success_response(status_data)
        
    except Exception as e:
        logger.exception("Health check failed")
        return error_response(f"System health check failed: {str(e)}", 503)

@admin_bp.route('/dashboard')
def internal_dashboard():
    """Admin dashboard"""
    return render_template('internal_dashboard.html')

@admin_bp.route('/metrics')
@handle_errors
def internal_metrics():
    """Alert metrics"""
    try:
        # Alert category breakdown
        alert_stats = db.session.query(
            Alert.category,
            db.func.count(Alert.id).label('count')
        ).group_by(Alert.category).all()
        
        category_data = {stat[0]: stat[1] for stat in alert_stats}
        
        # Severity breakdown
        severity_stats = db.session.query(
            Alert.severity,
            db.func.count(Alert.id).label('count')
        ).group_by(Alert.severity).all()
        
        severity_data = {stat[0]: stat[1] for stat in severity_stats}
        
        # Recent activity (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_activity = db.session.query(
            db.func.date(Alert.effective).label('date'),
            db.func.count(Alert.id).label('count')
        ).filter(Alert.effective >= week_ago).group_by(
            db.func.date(Alert.effective)
        ).order_by(db.func.date(Alert.effective)).all()
        
        activity_data = [
            {
                'date': str(stat[0]),
                'count': stat[1]
            } for stat in recent_activity
        ]
        
        return success_response({
            'categories': category_data,
            'severities': severity_data,
            'recent_activity': activity_data,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.exception("Error generating metrics")
        return error_response(f"Error generating metrics: {str(e)}")

@admin_bp.route('/enhanced-context/backfill', methods=['POST'])
@handle_errors
def enhanced_context_backfill():
    """Trigger Enhanced Context backfill for all SPC reports"""
    try:
        batch_size = request.json.get('batch_size', 100) if request.is_json else 100
        
        # Get reports without Enhanced Context
        reports_query = SPCReport.query.filter(
            SPCReport.enhanced_context.is_(None)
        ).limit(batch_size)
        
        reports = reports_query.all()
        
        if not reports:
            return success_response({
                'processed': 0,
                'message': 'No reports requiring Enhanced Context generation'
            })
        
        processed_count = 0
        error_count = 0
        
        for report in reports:
            try:
                enhanced_context = enhanced_context_service.generate_enhanced_context(report)
                
                report.enhanced_context = enhanced_context
                report.enhanced_context_version = enhanced_context["version"]
                report.enhanced_context_generated_at = datetime.utcnow()
                
                processed_count += 1
                
                # Commit in batches
                if processed_count % 10 == 0:
                    db.session.commit()
                    
            except Exception as e:
                logger.error(f"Error processing report {report.id}: {e}")
                error_count += 1
                continue
        
        # Final commit
        db.session.commit()
        
        return success_response({
            'processed': processed_count,
            'errors': error_count,
            'batch_size': batch_size,
            'message': f'Enhanced Context backfill completed: {processed_count} reports processed'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.exception("Enhanced Context backfill failed")
        return error_response(f"Backfill failed: {str(e)}")

@admin_bp.route('/ingestion-logs')
@handle_errors
def ingestion_logs():
    """View ingestion logs page"""
    return render_template('ingestion_logs.html')

@admin_bp.route('/ingestion-logs/data')
@handle_errors
def ingestion_logs_data():
    """API endpoint for ingestion logs data"""
    page = request.args.get('page', default=1, type=int)
    per_page = min(request.args.get('per_page', default=PaginationConfig.DEFAULT_PAGE_SIZE, type=int), 
                   PaginationConfig.MAX_PAGE_SIZE)
    
    operation_type = request.args.get('operation_type')
    status = request.args.get('status')
    
    query = IngestionLog.query
    
    if operation_type:
        query = query.filter(IngestionLog.operation_type == operation_type)
    if status:
        query = query.filter(IngestionLog.status == status)
    
    logs = query.order_by(IngestionLog.start_time.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    logs_data = []
    for log in logs.items:
        logs_data.append({
            'id': log.id,
            'operation_type': log.operation_type,
            'status': log.status,
            'start_time': log.start_time.isoformat() if log.start_time else None,
            'end_time': log.end_time.isoformat() if log.end_time else None,
            'records_processed': log.records_processed,
            'errors_count': log.errors_count,
            'error_message': log.error_message,
            'metadata': log.metadata
        })
    
    return success_response({
        'logs': logs_data,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': logs.total,
            'pages': logs.pages
        }
    })

@admin_bp.route('/enrichment/stats')
@handle_errors
def get_enrichment_stats():
    """Get enrichment statistics including priority alert coverage"""
    try:
        # Enhanced Context coverage by report type
        context_stats = db.session.query(
            SPCReport.report_type,
            db.func.count(SPCReport.id).label('total'),
            db.func.sum(
                db.case([(SPCReport.enhanced_context.isnot(None), 1)], else_=0)
            ).label('enhanced')
        ).group_by(SPCReport.report_type).all()
        
        coverage_data = []
        for stat in context_stats:
            total = stat[1]
            enhanced = stat[2] or 0
            coverage_data.append({
                'report_type': stat[0],
                'total': total,
                'enhanced': enhanced,
                'percentage': round((enhanced / total * 100) if total > 0 else 0, 1)
            })
        
        # Recent enrichment activity
        recent_enhanced = SPCReport.query.filter(
            SPCReport.enhanced_context_generated_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        return success_response({
            'coverage_by_type': coverage_data,
            'recent_24h': recent_enhanced,
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.exception("Error generating enrichment stats")
        return error_response(f"Error generating enrichment stats: {str(e)}")

@admin_bp.route('/webhook-management')
def webhook_management():
    """View webhook management interface"""
    return render_template('webhook_management.html')

@admin_bp.route('/spc/verification/<date_str>')
@handle_errors
def spc_verification_date(date_str):
    """Get SPC verification data for a specific date"""
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get SPC reports for the date
        reports = SPCReport.query.filter(
            SPCReport.report_date == target_date
        ).all()
        
        # Count by type
        report_counts = {}
        enhanced_counts = {}
        
        for report in reports:
            report_type = report.report_type
            report_counts[report_type] = report_counts.get(report_type, 0) + 1
            
            if report.enhanced_context:
                enhanced_counts[report_type] = enhanced_counts.get(report_type, 0) + 1
        
        verification_data = {
            'date': date_str,
            'total_reports': len(reports),
            'report_counts': report_counts,
            'enhanced_counts': enhanced_counts,
            'reports': [
                {
                    'id': report.id,
                    'report_type': report.report_type,
                    'location': report.location,
                    'magnitude': report.magnitude,
                    'has_enhanced_context': bool(report.enhanced_context)
                } for report in reports[:50]  # Limit for display
            ]
        }
        
        return success_response(verification_data)
        
    except ValueError:
        return error_response("Invalid date format. Use YYYY-MM-DD", 400)
    except Exception as e:
        logger.exception(f"Error getting SPC verification for {date_str}")
        return error_response(f"Error retrieving verification data: {str(e)}")