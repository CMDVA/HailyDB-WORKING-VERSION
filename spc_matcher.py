"""
Fixed SPC-NWS Alert Matching Service
Cross-references SPC storm reports with NWS alerts for verification
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, or_, func
from models import Alert, SPCReport, db
from match_summarizer import MatchSummarizer

logger = logging.getLogger(__name__)

class SPCMatchingService:
    """
    Service to match SPC reports with NWS alerts for verification
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.summarizer = MatchSummarizer()
        
        # Event correlation mapping
        self.event_correlations = {
            'tornado': ['Tornado Warning', 'Tornado Watch'],
            'wind': ['Severe Thunderstorm Warning', 'Severe Weather Statement', 'Significant Weather Advisory'],
            'hail': ['Severe Thunderstorm Warning', 'Severe Weather Statement', 'Significant Weather Advisory']
        }
        
        # Time window for matching (±2 hours as specified)
        self.time_window_hours = 2
        
        # Distance threshold for lat/lon fallback (25 miles as specified)
        self.distance_threshold_miles = 25
    
    def match_spc_reports_batch(self, limit: int = 100) -> Dict:
        """
        Match a batch of unverified alerts with SPC reports
        Returns statistics about matching process
        """
        # Get unverified alerts from last 48 hours for broader matching
        cutoff_time = datetime.utcnow() - timedelta(hours=48)
        
        unverified_alerts = Alert.query.filter(
            and_(
                or_(Alert.spc_verified == False, Alert.spc_verified.is_(None)),
                Alert.effective >= cutoff_time
            )
        ).limit(limit).all()
        
        logger.info(f"Processing {len(unverified_alerts)} unverified alerts for SPC matching")
        
        matched_count = 0
        updated_count = 0
        
        for alert in unverified_alerts:
            try:
                match_result = self.match_alert_with_spc(alert)
                if match_result['matched']:
                    matched_count += 1
                if match_result['updated']:
                    updated_count += 1
            except Exception as e:
                logger.error(f"Error matching alert {alert.id}: {e}")
        
        # Commit all changes at once
        try:
            self.db.commit()
        except Exception as e:
            logger.error(f"Error committing batch SPC matches: {e}")
            self.db.rollback()
        
        return {
            'processed': len(unverified_alerts),
            'matched': matched_count,
            'updated': updated_count
        }
    
    def match_alert_with_spc(self, alert: Alert) -> Dict:
        """
        Match a single alert with SPC reports
        Returns match result and updates alert if matches found
        """
        if not getattr(alert, 'effective', None):
            return {'matched': False, 'updated': False, 'reason': 'No effective time'}
        
        # Determine eligible SPC report types based on alert event
        eligible_types = self._get_eligible_spc_types(getattr(alert, 'event', '') or '')
        if not eligible_types:
            return {'matched': False, 'updated': False, 'reason': 'No eligible SPC types'}
        
        # Extract time window
        alert_effective = getattr(alert, 'effective')
        start_time = alert_effective - timedelta(hours=self.time_window_hours)
        end_time = alert_effective + timedelta(hours=self.time_window_hours)
        
        # Get report date(s) to search
        report_dates = self._get_report_dates_for_timerange(start_time, end_time)
        
        # Try county FIPS match first
        matches = self._find_county_matches(alert, eligible_types, report_dates, start_time, end_time)
        match_method = 'fips'
        confidence = 0.9
        
        # Fallback to lat/lon matching if no county matches
        if not matches:
            matches = self._find_proximity_matches(alert, eligible_types, report_dates, start_time, end_time)
            match_method = 'latlon'
            confidence = 0.7
        
        # No matches found
        if not matches:
            return {'matched': False, 'updated': False, 'reason': 'No matches found'}
        
        # Update alert with match results
        try:
            # Use proper SQLAlchemy updates instead of direct assignment
            setattr(alert, 'spc_verified', True)
            setattr(alert, 'spc_reports', [self._spc_report_to_dict(match) for match in matches])
            setattr(alert, 'spc_match_method', match_method)
            setattr(alert, 'spc_confidence_score', confidence)
            setattr(alert, 'spc_report_count', len(matches))
            
            # Generate AI summary for verified matches
            try:
                spc_reports_data = [self._spc_report_to_dict(match) for match in matches]
                ai_summary = self.summarizer.generate_match_summary(
                    alert=alert.to_dict(),
                    spc_reports=spc_reports_data
                )
                if ai_summary:
                    setattr(alert, 'spc_ai_summary', ai_summary)
                    logger.info(f"Generated AI summary for alert {alert.id}")
            except Exception as e:
                logger.warning(f"Failed to generate AI summary for alert {alert.id}: {e}")
            
            logger.info(f"Matched alert {alert.id} with {len(matches)} SPC reports via {match_method}")
            
            return {
                'matched': True,
                'updated': True,
                'match_count': len(matches),
                'method': match_method,
                'confidence': confidence
            }
        except Exception as e:
            logger.error(f"Error updating alert {alert.id} with SPC matches: {e}")
            return {'matched': False, 'updated': False, 'reason': f'Database error: {e}'}
            
    def _spc_report_to_dict(self, spc_report: SPCReport) -> Dict:
        """Convert SPC report to dictionary for JSON storage"""
        return {
            'id': spc_report.id,
            'report_date': spc_report.report_date.isoformat(),
            'report_type': spc_report.report_type,
            'time_utc': spc_report.time_utc,
            'location': spc_report.location,
            'county': spc_report.county,
            'state': spc_report.state,
            'latitude': spc_report.latitude,
            'longitude': spc_report.longitude,
            'comments': spc_report.comments,
            'magnitude': spc_report.magnitude
        }
    
    def _get_eligible_spc_types(self, alert_event: str) -> List[str]:
        """Determine which SPC report types are eligible for this alert event"""
        if not alert_event:
            return []
            
        eligible_types = []
        for spc_type, nws_events in self.event_correlations.items():
            if any(nws_event.lower() in alert_event.lower() for nws_event in nws_events):
                eligible_types.append(spc_type)
        
        return eligible_types
    
    def _get_report_dates_for_timerange(self, start_time: datetime, end_time: datetime) -> List:
        """Get all dates that need to be checked for SPC reports"""
        dates = []
        current_date = start_time.date()
        end_date = end_time.date()
        
        while current_date <= end_date:
            dates.append(current_date)
            current_date += timedelta(days=1)
            
        return dates
    
    def _find_county_matches(self, alert: Alert, eligible_types: List[str], 
                           report_dates: List, start_time: datetime, end_time: datetime) -> List[SPCReport]:
        """Find SPC reports matching by county/state"""
        # Get counties and states from alert
        alert_counties = alert.extract_counties()
        alert_states = alert.extract_states()
        
        if not alert_counties or not alert_states:
            return []
        
        # Query SPC reports in same counties
        matches = SPCReport.query.filter(
            and_(
                SPCReport.report_date.in_(report_dates),
                SPCReport.report_type.in_(eligible_types),
                SPCReport.state.in_(alert_states),
                SPCReport.county.in_(alert_counties)
            )
        ).all()
        
        # Filter by time if time_utc is available
        time_filtered_matches = []
        for match in matches:
            if self._is_time_match(match, alert, start_time, end_time):
                time_filtered_matches.append(match)
        
        return time_filtered_matches
    
    def _find_proximity_matches(self, alert: Alert, eligible_types: List[str],
                              report_dates: List, start_time: datetime, end_time: datetime) -> List[SPCReport]:
        """Find SPC reports matching by geographic proximity"""
        # Get alert centroid (simplified - use geometry if available)
        alert_lat, alert_lon = self._get_alert_centroid(alert)
        if not alert_lat or not alert_lon:
            return []
        
        # Query all SPC reports in the time/type range with coordinates
        candidates = SPCReport.query.filter(
            and_(
                SPCReport.report_date.in_(report_dates),
                SPCReport.report_type.in_(eligible_types),
                SPCReport.latitude.isnot(None),
                SPCReport.longitude.isnot(None)
            )
        ).all()
        
        # Filter by distance and time
        matches = []
        for candidate in candidates:
            distance = self._calculate_distance(
                alert_lat, alert_lon, candidate.latitude, candidate.longitude
            )
            
            if distance <= self.distance_threshold_miles:
                if self._is_time_match(candidate, alert, start_time, end_time):
                    matches.append(candidate)
        
        return matches
    
    def _get_alert_centroid(self, alert: Alert) -> Tuple[Optional[float], Optional[float]]:
        """Extract centroid coordinates from alert geometry or area description"""
        # Try geometry first
        alert_geometry = getattr(alert, 'geometry', None)
        if alert_geometry and isinstance(alert_geometry, dict):
            coordinates = alert_geometry.get('coordinates')
            if coordinates:
                # Handle different geometry types
                if alert_geometry.get('type') == 'Point':
                    return coordinates[1], coordinates[0]  # lat, lon
                elif alert_geometry.get('type') in ['Polygon', 'MultiPolygon']:
                    # Calculate centroid of polygon (simplified)
                    return self._calculate_polygon_centroid(coordinates)
        
        # Fallback: estimate from area description (very basic)
        return None, None
    
    def _calculate_polygon_centroid(self, coordinates) -> Tuple[Optional[float], Optional[float]]:
        """Calculate centroid of polygon coordinates (simplified)"""
        try:
            # For polygon: coordinates[0] is the outer ring
            if isinstance(coordinates, list) and len(coordinates) > 0:
                ring = coordinates[0] if isinstance(coordinates[0][0], list) else coordinates
                
                total_lat = sum(point[1] for point in ring)
                total_lon = sum(point[0] for point in ring)
                count = len(ring)
                
                return total_lat / count, total_lon / count
        except (IndexError, TypeError, ZeroDivisionError):
            pass
        
        return None, None
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles using Haversine formula"""
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in miles
        earth_radius_miles = 3959
        
        return earth_radius_miles * c
    
    def _is_time_match(self, spc_report: SPCReport, alert: Alert, 
                      start_time: datetime, end_time: datetime) -> bool:
        """Check if SPC report time falls within alert time window"""
        if not getattr(spc_report, 'time_utc', None) or not getattr(alert, 'effective', None):
            return True  # If no time data, assume match (location-based only)
        
        try:
            # Parse SPC time (HHMM format) and combine with report date
            spc_time_str = str(getattr(spc_report, 'time_utc')).zfill(4)  # Pad to 4 digits
            spc_hour = int(spc_time_str[:2])
            spc_minute = int(spc_time_str[2:])
            
            spc_datetime = datetime.combine(
                getattr(spc_report, 'report_date'),
                datetime.min.time().replace(hour=spc_hour, minute=spc_minute)
            )
            
            return start_time <= spc_datetime <= end_time
            
        except (ValueError, TypeError):
            # If time parsing fails, assume match
            return True
    
    def get_verification_stats(self) -> Dict:
        """Get statistics about SPC verification"""
        total_alerts = Alert.query.count()
        verified_alerts = Alert.query.filter(Alert.spc_verified == True).count()
        
        # Verification by method
        method_stats = self.db.query(
            Alert.spc_match_method,
            func.count(Alert.id).label('count')
        ).filter(Alert.spc_match_method.isnot(None)).group_by(Alert.spc_match_method).all()
        
        # Recent verification activity
        recent_verified = Alert.query.filter(
            and_(
                Alert.spc_verified == True,
                Alert.updated_at >= datetime.utcnow() - timedelta(hours=24)
            )
        ).count()
        
        return {
            'total_alerts': total_alerts,
            'verified_alerts': verified_alerts,
            'verification_rate': (verified_alerts / total_alerts * 100) if total_alerts > 0 else 0,
            'verification_methods': {row.spc_match_method: row.count for row in method_stats},
            'recent_24h_verified': recent_verified
        }