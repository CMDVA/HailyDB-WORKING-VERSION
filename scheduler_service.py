"""
Scheduler Service for HailyDB v2.0 Core Upgrade
Provides operation logging and error recovery for autonomous ingestion
"""
import logging
from datetime import datetime
from typing import Dict, Optional
from app import db
from models import SchedulerLog

logger = logging.getLogger(__name__)

class SchedulerService:
    """
    Service to log and track all ingestion operations
    Maintains audit trail for autonomous system monitoring
    """
    
    def __init__(self, db):
        self.db = db
    
    def log_operation_start(self, operation_type: str, trigger_method: str = "manual", 
                          metadata: Optional[Dict] = None) -> SchedulerLog:
        """
        Start logging an operation
        Returns the log entry for completion tracking
        """
        try:
            log_entry = SchedulerLog(
                operation_type=operation_type,
                trigger_method=trigger_method,
                started_at=datetime.utcnow(),
                operation_metadata=metadata or {}
            )
            
            self.db.session.add(log_entry)
            self.db.session.commit()
            
            logger.info(f"Started operation {operation_type} (trigger: {trigger_method})")
            return log_entry
            
        except Exception as e:
            logger.error(f"Failed to log operation start: {e}")
            self.db.session.rollback()
            raise
    
    def log_operation_complete(self, log_entry: SchedulerLog, success: bool,
                             records_processed: int = 0, records_new: int = 0,
                             error_message: str = None, error_details: dict = None,
                             failed_alert_ids: list = None, duplicate_count: int = 0,
                             http_status_code: int = None, api_response_size: int = None,
                             processing_duration: float = None):
        """
        Complete an operation log entry with PostgreSQL workaround
        """
        # Extract operation type before accessing log_entry object
        operation_type = None
        log_id = None
        
        try:
            # Get basic info we need before potential SQLAlchemy issues
            operation_type = log_entry.operation_type if hasattr(log_entry, 'operation_type') else 'unknown'
            
            # Use direct SQL execution to bypass type conversion issues
            self.db.session.execute(
                "UPDATE scheduler_logs SET completed_at = CURRENT_TIMESTAMP, success = :success, "
                "records_processed = :processed, records_new = :new_records, error_message = :error "
                "WHERE started_at = (SELECT MAX(started_at) FROM scheduler_logs WHERE operation_type = :op_type AND completed_at IS NULL)",
                {
                    'success': success,
                    'processed': records_processed or 0,
                    'new_records': records_new or 0,
                    'error': error_message,
                    'op_type': operation_type
                }
            )
            self.db.session.commit()
            
            status = "SUCCESS" if success else "FAILED"
            details = f"(processed: {records_processed or 0}, new: {records_new or 0})"
            
            logger.info(f"Completed operation {operation_type}: {status} {details}")
            
        except Exception as e:
            logger.error(f"Operation completion failed: {e}")
            # Final fallback - just log the completion without database update
            status = "SUCCESS" if success else "FAILED"
            details = f"(processed: {records_processed or 0}, new: {records_new or 0})"
            logger.info(f"Operation {operation_type or 'unknown'} completed in memory: {status} {details}")
            
            # Try to at least mark it as completed
            try:
                self.db.session.execute(
                    f"UPDATE scheduler_logs SET completed_at = CURRENT_TIMESTAMP WHERE operation_type = '{operation_type}' AND completed_at IS NULL"
                )
                self.db.session.commit()
            except:
                pass  # Ignore final fallback errors
    
    def _determine_detailed_status(self, success: bool, records_processed: int, 
                                 records_new: int, error_message: str = None) -> str:
        """Determine detailed status based on operation results"""
        if not success:
            if error_message:
                if 'network' in error_message.lower() or 'timeout' in error_message.lower():
                    return 'failed_network'
                elif 'database' in error_message.lower() or 'sql' in error_message.lower():
                    return 'failed_technical'
                else:
                    return 'failed_data'
            return 'failed_unknown'
        
        # Success cases
        if records_new == 0 and records_processed > 0:
            return 'success_no_new_data'
        elif records_new > 0:
            return 'success_with_new_data'
        else:
            return 'success_empty'
    
    def get_recent_operations(self, hours: int = 24, operation_type: str = None) -> list:
        """
        Get recent operation logs for monitoring
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        query = SchedulerLog.query.filter(SchedulerLog.started_at >= cutoff)
        
        if operation_type:
            query = query.filter(SchedulerLog.operation_type == operation_type)
        
        return query.order_by(SchedulerLog.started_at.desc()).all()
    
    def get_operation_stats(self) -> Dict:
        """
        Get operation statistics for health monitoring
        """
        from datetime import timedelta
        
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        
        recent_logs = SchedulerLog.query.filter(
            SchedulerLog.started_at >= cutoff_24h
        ).all()
        
        stats = {
            'total_operations_24h': len(recent_logs),
            'successful_operations_24h': len([log for log in recent_logs if log.success]),
            'failed_operations_24h': len([log for log in recent_logs if not log.success]),
            'operations_by_type': {},
            'last_successful_operations': {}
        }
        
        # Group by operation type
        for log in recent_logs:
            op_type = log.operation_type
            if op_type not in stats['operations_by_type']:
                stats['operations_by_type'][op_type] = {'total': 0, 'successful': 0, 'failed': 0}
            
            stats['operations_by_type'][op_type]['total'] += 1
            if log.success:
                stats['operations_by_type'][op_type]['successful'] += 1
            else:
                stats['operations_by_type'][op_type]['failed'] += 1
        
        # Last successful operation for each type
        for op_type in ['nws_poll', 'spc_poll', 'spc_match', 'ai_enrich']:
            try:
                last_success = SchedulerLog.query.filter(
                    SchedulerLog.operation_type == op_type,
                    SchedulerLog.success == True
                ).order_by(SchedulerLog.completed_at.desc()).first()
                
                if last_success and last_success.completed_at:
                    stats['last_successful_operations'][op_type] = last_success.completed_at.isoformat()
            except Exception as e:
                logger.warning(f"Could not fetch last operation for {op_type}: {e}")
                continue
        
        return stats
    
    def cleanup_old_logs(self, days_to_keep: int = 30):
        """
        Clean up old operation logs to prevent database bloat
        """
        from datetime import timedelta
        
        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
        
        deleted_count = SchedulerLog.query.filter(
            SchedulerLog.started_at < cutoff
        ).delete()
        
        self.db.session.commit()
        logger.info(f"Cleaned up {deleted_count} old scheduler logs (older than {days_to_keep} days)")
        
        return deleted_count