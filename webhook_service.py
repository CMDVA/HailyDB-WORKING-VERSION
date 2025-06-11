import json
import logging
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
from models import WebhookRule, Alert, SPCReport, SchedulerLog, db

logger = logging.getLogger(__name__)

class WebhookService:
    """
    Webhook dispatch service for real-time alert notifications
    Evaluates conditions and dispatches HTTP POST requests with retry logic
    """
    
    def __init__(self, db):
        self.db = db
        
    def evaluate_and_dispatch_webhooks(self, alerts: List[Alert] = None) -> Dict:
        """
        Evaluate webhook conditions and dispatch notifications
        Can be called with specific alerts or evaluate all recent alerts
        """
        try:
            # Get all active webhook rules
            webhook_rules = WebhookRule.query.all()
            
            if not webhook_rules:
                logger.debug("No webhook rules registered")
                return {'dispatched': 0, 'failed': 0, 'rules_evaluated': 0}
            
            # If no specific alerts provided, get recent alerts from last hour
            if alerts is None:
                from datetime import timedelta
                one_hour_ago = datetime.utcnow() - timedelta(hours=1)
                alerts = Alert.query.filter(
                    Alert.ingested_at >= one_hour_ago
                ).all()
            
            dispatched = 0
            failed = 0
            rules_evaluated = len(webhook_rules)
            
            logger.info(f"Evaluating {rules_evaluated} webhook rules against {len(alerts)} alerts")
            
            # Evaluate each webhook rule against each alert
            for rule in webhook_rules:
                for alert in alerts:
                    if self._evaluate_webhook_condition(rule, alert):
                        success = self._dispatch_webhook(rule, alert)
                        if success:
                            dispatched += 1
                        else:
                            failed += 1
            
            logger.info(f"Webhook evaluation complete: {dispatched} dispatched, {failed} failed")
            
            return {
                'dispatched': dispatched,
                'failed': failed,
                'rules_evaluated': rules_evaluated,
                'alerts_processed': len(alerts)
            }
            
        except Exception as e:
            logger.error(f"Error during webhook evaluation: {e}")
            return {'dispatched': 0, 'failed': 1, 'rules_evaluated': 0, 'error': str(e)}
    
    def _evaluate_webhook_condition(self, rule: WebhookRule, alert: Alert) -> bool:
        """
        Evaluate if a webhook rule condition is met for a specific alert
        """
        try:
            # Check location filter first
            if rule.location_filter:
                if not self._location_matches(rule.location_filter, alert):
                    return False
            
            # Evaluate based on event type
            if rule.event_type == 'hail':
                return self._evaluate_hail_condition(rule, alert)
            elif rule.event_type == 'wind':
                return self._evaluate_wind_condition(rule, alert)
            elif rule.event_type == 'damage_probability':
                return self._evaluate_damage_probability_condition(rule, alert)
            else:
                logger.warning(f"Unknown webhook event type: {rule.event_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error evaluating webhook condition for rule {rule.id}: {e}")
            return False
    
    def _evaluate_hail_condition(self, rule: WebhookRule, alert: Alert) -> bool:
        """Evaluate hail threshold condition - capture ALL hail if threshold is 0"""
        # Check radar-indicated hail first
        if alert.radar_indicated and 'hail_inches' in alert.radar_indicated:
            hail_size = alert.radar_indicated['hail_inches']
            if hail_size and hail_size > 0:  # Any hail size if threshold is 0
                if rule.threshold_value == 0 or hail_size >= rule.threshold_value:
                    logger.debug(f"Hail condition met: radar-indicated {hail_size}\" (threshold: {rule.threshold_value}\")")
                    return True
        
        # Check SPC-verified hail
        if alert.spc_verified and alert.spc_reports:
            for report in alert.spc_reports:
                if report.get('report_type') == 'hail' and report.get('magnitude', {}).get('size'):
                    spc_hail_size = report['magnitude']['size']
                    if rule.threshold_value == 0 or spc_hail_size >= rule.threshold_value:
                        logger.debug(f"Hail condition met: SPC-verified {spc_hail_size}\" (threshold: {rule.threshold_value}\")")
                        return True
        
        return False
    
    def _evaluate_wind_condition(self, rule: WebhookRule, alert: Alert) -> bool:
        """Evaluate wind threshold condition"""
        # Check radar-indicated wind first
        if alert.radar_indicated and 'wind_mph' in alert.radar_indicated:
            wind_speed = alert.radar_indicated['wind_mph']
            if wind_speed and wind_speed >= rule.threshold_value:
                logger.debug(f"Wind condition met: radar-indicated {wind_speed} mph >= {rule.threshold_value} mph")
                return True
        
        # Check SPC-verified wind
        if alert.spc_verified and alert.spc_reports:
            for report in alert.spc_reports:
                if report.get('report_type') == 'wind' and report.get('magnitude', {}).get('speed'):
                    spc_wind_speed = report['magnitude']['speed']
                    if spc_wind_speed >= rule.threshold_value:
                        logger.debug(f"Wind condition met: SPC-verified {spc_wind_speed} mph >= {rule.threshold_value} mph")
                        return True
        
        return False
    
    def _evaluate_damage_probability_condition(self, rule: WebhookRule, alert: Alert) -> bool:
        """Evaluate damage probability threshold condition"""
        # Placeholder for future damage probability model
        # For now, return False since this feature is not yet implemented
        logger.debug("Damage probability evaluation not yet implemented")
        return False
    
    def _location_matches(self, location_filter: str, alert: Alert) -> bool:
        """
        Check if alert location matches the webhook location filter
        Supports state codes, county names, and partial matching
        """
        if not location_filter or not alert.area_desc:
            return True
        
        # Normalize for comparison
        filter_lower = location_filter.lower()
        area_lower = alert.area_desc.lower()
        
        # Direct substring match
        if filter_lower in area_lower:
            return True
        
        # State code matching (e.g., "TX" matches "Dallas, TX")
        if len(location_filter) == 2 and location_filter.upper() in alert.area_desc:
            return True
        
        # County name matching
        if ',' in alert.area_desc:
            counties = [county.strip() for county in alert.area_desc.split(',')]
            for county in counties:
                if filter_lower in county.lower():
                    return True
        
        return False
    
    def _dispatch_webhook(self, rule: WebhookRule, alert: Alert) -> bool:
        """
        Dispatch webhook with retry logic and exponential backoff
        """
        # Determine source and value based on what triggered the condition
        source, value = self._get_trigger_source_and_value(rule, alert)
        
        payload = {
            'event_type': rule.event_type,
            'location': alert.area_desc,
            'value': value,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'source': source,
            'alert_id': alert.id,
            'alert_event': alert.event,
            'effective_time': alert.effective.isoformat() if alert.effective else None,
            'expires_time': alert.expires.isoformat() if alert.expires else None
        }
        
        # Retry logic with exponential backoff (up to 3 attempts)
        max_retries = 3
        base_delay = 1  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Dispatching webhook (attempt {attempt + 1}/{max_retries}) to {rule.webhook_url}")
                
                response = requests.post(
                    rule.webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=10
                )
                
                if 200 <= response.status_code < 300:
                    logger.info(f"Webhook dispatched successfully to {rule.webhook_url}: {response.status_code}")
                    self._log_webhook_dispatch(rule, alert, True, payload, response.status_code)
                    return True
                else:
                    logger.warning(f"Webhook dispatch failed with status {response.status_code}: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Webhook dispatch attempt {attempt + 1} failed: {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                time.sleep(delay)
        
        # All retries failed
        logger.error(f"Webhook dispatch failed after {max_retries} attempts to {rule.webhook_url}")
        self._log_webhook_dispatch(rule, alert, False, payload)
        return False
    
    def _get_trigger_source_and_value(self, rule: WebhookRule, alert: Alert) -> tuple:
        """
        Determine what triggered the webhook and get the actual value
        Returns (source, value) tuple
        """
        if rule.event_type == 'hail':
            # Check radar-indicated first
            if alert.radar_indicated and 'hail_inches' in alert.radar_indicated:
                hail_size = alert.radar_indicated['hail_inches']
                if hail_size and hail_size >= rule.threshold_value:
                    return ('Radar Indicated', hail_size)
            
            # Check SPC-verified
            if alert.spc_verified and alert.spc_reports:
                for report in alert.spc_reports:
                    if report.get('report_type') == 'hail' and report.get('magnitude', {}).get('size'):
                        spc_hail_size = report['magnitude']['size']
                        if spc_hail_size >= rule.threshold_value:
                            return ('SPC', spc_hail_size)
        
        elif rule.event_type == 'wind':
            # Check radar-indicated first
            if alert.radar_indicated and 'wind_mph' in alert.radar_indicated:
                wind_speed = alert.radar_indicated['wind_mph']
                if wind_speed and wind_speed >= rule.threshold_value:
                    return ('Radar Indicated', wind_speed)
            
            # Check SPC-verified
            if alert.spc_verified and alert.spc_reports:
                for report in alert.spc_reports:
                    if report.get('report_type') == 'wind' and report.get('magnitude', {}).get('speed'):
                        spc_wind_speed = report['magnitude']['speed']
                        if spc_wind_speed >= rule.threshold_value:
                            return ('SPC', spc_wind_speed)
        
        elif rule.event_type == 'damage_probability':
            # Placeholder for future damage probability model
            return ('HailyDB Probability Model', 0.0)
        
        return ('Unknown', 0.0)
    
    def _log_webhook_dispatch(self, rule: WebhookRule, alert: Alert, success: bool, payload: Dict, status_code: int = None):
        """
        Log webhook dispatch attempt to scheduler_logs
        """
        try:
            operation_metadata = {
                'webhook_rule_id': rule.id,
                'webhook_url': rule.webhook_url,
                'event_type': rule.event_type,
                'threshold_value': rule.threshold_value,
                'location_filter': rule.location_filter,
                'alert_id': alert.id,
                'payload': payload,
                'http_status_code': status_code
            }
            
            error_message = None if success else f"Webhook dispatch failed to {rule.webhook_url}"
            
            log_entry = SchedulerLog(
                operation_type='webhook_dispatch',
                trigger_method='internal_timer',
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                success=success,
                records_processed=1,
                records_new=1 if success else 0,
                error_message=error_message,
                operation_metadata=operation_metadata,
                http_status_code=status_code
            )
            
            self.db.session.add(log_entry)
            self.db.session.commit()
            
        except Exception as e:
            logger.error(f"Failed to log webhook dispatch: {e}")
            # Don't raise - webhook logging failure shouldn't break the webhook system