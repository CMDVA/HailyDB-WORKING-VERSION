"""
Enhanced Context System for SPC Reports
Implements multi-alert, multi-source enrichment for comprehensive SPC report intelligence
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import openai
import os

from app import db
from config import Config
from google_places_service import GooglePlacesService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

class SPCEnhancedContextService:
    """Service for generating enhanced context for SPC reports"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def _map_hail_threat_level(self, hail_size: float) -> str:
        """Map hail size to NWS official classification for historical reports"""
        if hail_size >= 2.75:
            return "Giant Hail - Hail larger than 2 3/4 inch (larger than baseballs, such as the size of grapefruit or softballs) causing major damage"
        elif hail_size >= 1.75:
            return "Very Large Hail - Hail from 1 3/4 inch to 2 3/4 inch in diameter (from the size of golf balls to baseballs) causing moderate damage"
        elif hail_size >= 1.0:
            return "Large Hail - Hail from 1 inch to 1 3/4 inch in diameter (from the size of quarters to golf balls) causing minor damage"
        else:
            return "Small Hail - Hail less than 1 inch in diameter (from the size of peas to nickels)"
    
    def _get_hail_natural_language(self, hail_size: float) -> str:
        """Get natural language equivalent for hail size"""
        hail_size_map = {
            0.25: 'pea', 0.5: 'peanut', 0.75: 'penny',
            0.88: 'nickel', 1.0: 'quarter', 1.25: 'half dollar',
            1.5: 'ping pong ball', 1.75: 'golf ball', 2.0: 'egg',
            2.5: 'tennis ball', 2.75: 'baseball', 3.0: 'large apple',
            4.0: 'softball', 4.5: 'grapefruit'
        }
        
        # Find closest match
        closest_size = min(hail_size_map.keys(), key=lambda x: abs(x - hail_size))
        if abs(closest_size - hail_size) <= 0.25:
            return f" ({hail_size_map[closest_size]} size)"
        return ""

    def _map_wind_threat_level(self, wind_speed: float) -> str:
        """Map wind speed to NWS official classification for historical reports"""
        if wind_speed >= 92:
            return "Violent Wind Gusts - Severe thunderstorm wind gusts greater than 92 mph (80 knots or greater) causing major damage"
        elif wind_speed >= 75:
            return "Very Damaging Wind Gusts - Severe thunderstorm wind gusts between 75 mph and 91 mph (between 65 knots and 79 knots) causing moderate damage"
        elif wind_speed >= 58:
            return "Damaging Wind Gusts - Severe thunderstorm wind gusts between 58 mph and 74 mph (between 50 knots and 64 knots) causing minor damage"
        elif wind_speed >= 39:
            return "Strong Wind Gusts - Thunderstorm wind gusts between 39 mph and 57 mph (between 34 knots and 49 knots)"
        else:
            return "Light Wind Gusts"

    def _get_location_context(self, report) -> Dict[str, Any]:
        """Get complete location hierarchy using Google Places API"""
        try:
            # Initialize Google Places service
            places_service = GooglePlacesService()
            
            # Get complete location hierarchy using Google Places API
            location_data = places_service.get_nearby_places(
                lat=float(report.latitude), 
                lon=float(report.longitude), 
                radius_miles=25
            )
            
            # Return structured location context with full hierarchy
            return {
                "event_location": location_data.get('event_location'),
                "nearest_major_city": location_data.get('nearest_major_city'),
                "nearby_places": location_data.get('nearby_places', [])
            }
            
        except Exception as e:
            logger.error(f"Error getting location context: {e}")
            return {
                "event_location": {"name": report.location, "distance_miles": 0},
                "nearest_major_city": {"name": "Unknown", "distance_miles": 0},
                "nearby_places": []
            }
    
    def enrich_spc_report(self, report_id: int) -> Dict[str, Any]:
        """
        Generate enhanced context for a specific SPC report
        
        Args:
            report_id: SPC report ID
            
        Returns:
            Enhanced context dictionary
        """
        try:
            # Import models here to avoid circular imports
            from models import SPCReport, Alert, RadarAlert
            
            # Get the SPC report
            report = self.db.query(SPCReport).filter_by(id=report_id).first()
            if not report:
                raise ValueError(f"SPC report {report_id} not found")
            
            # Get verified alerts that match this report
            verified_alerts = self._get_verified_alerts_for_report(report_id)
            
            # Generate enhanced context (with or without verified alerts)
            enhanced_context = self._build_enhanced_context(report, verified_alerts)
            
            # Update the report with enhanced context
            report.enhanced_context = enhanced_context
            report.enhanced_context_version = "v2.0"
            report.enhanced_context_generated_at = datetime.utcnow()
            self.db.commit()
            
            logger.info(f"Enhanced context generated for SPC report {report_id}")
            return enhanced_context
            
        except Exception as e:
            logger.error(f"Error enriching SPC report {report_id}: {e}")
            self.db.rollback()
            raise
    
    def _get_verified_alerts_for_report(self, report_id: int) -> List:
        """Get all verified alerts that match a specific SPC report"""
        
        # Query alerts that contain the report_id in their spc_reports JSONB field
        query = text("""
            SELECT DISTINCT a.id
            FROM alerts a, jsonb_array_elements(a.spc_reports) AS report_element
            WHERE a.spc_reports IS NOT NULL
            AND (report_element->>'id')::int = :report_id
            AND a.spc_confidence_score >= 0.8
        """)
        
        result = self.db.execute(query, {"report_id": report_id})
        alert_ids = [row[0] for row in result.fetchall()]
        
        if not alert_ids:
            return []
        
        # Get full alert objects
        from models import Alert
        alerts = self.db.query(Alert).filter(Alert.id.in_(alert_ids)).order_by(Alert.effective).all()
        return alerts
    
    def _build_enhanced_context(self, report, verified_alerts: List) -> Dict[str, Any]:
        """Build the enhanced context structure"""
        
        # Always get location context regardless of verified alerts
        location_context = self._get_location_context(report)
        
        # Handle case with no verified alerts but still provide location enrichment
        if not verified_alerts:
            # Use the consolidated Enhanced Summary function with empty verified alerts list
            enhanced_summary = self._generate_enhanced_summary(
                report, [], 0, set(), "Unknown", location_context, False
            )
            return {
                "alert_count": 0,
                "enhanced_summary": enhanced_summary,
                "location_context": location_context,
                "generated_at": datetime.utcnow().isoformat(),
                "has_verified_alerts": False
            }
        
        # Calculate event duration
        if len(verified_alerts) > 1:
            start_time = min(alert.effective for alert in verified_alerts if alert.effective)
            end_time = max(alert.expires for alert in verified_alerts if alert.expires)
            if start_time and end_time:
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
            else:
                duration_minutes = 0
        else:
            duration_minutes = 0
        
        # Extract counties affected
        counties_affected = set()
        for alert in verified_alerts:
            if alert.county_names:
                try:
                    # Handle both list and string formats
                    if isinstance(alert.county_names, list):
                        # Filter out any non-string items
                        for county in alert.county_names:
                            if isinstance(county, str):
                                counties_affected.add(county)
                    elif isinstance(alert.county_names, str):
                        counties_affected.add(alert.county_names)
                    else:
                        logger.warning(f"Unexpected county_names type: {type(alert.county_names)} - {alert.county_names}")
                except Exception as e:
                    logger.error(f"Error processing county_names for alert {alert.id}: {e}")
                    continue
        
        # Calculate average match confidence
        confidences = [alert.spc_confidence_score for alert in verified_alerts if alert.spc_confidence_score]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Extract NWS office
        nws_office = self._extract_nws_office(verified_alerts)
        
        # Check if any alerts have radar polygon containment
        radar_polygon_match = any(getattr(alert, 'radar_polygon_contains_report', False) for alert in verified_alerts)
        
        # Generate enhanced summary
        enhanced_summary = self._generate_enhanced_summary(
            report, verified_alerts, duration_minutes, counties_affected, 
            nws_office, location_context, radar_polygon_match
        )
        
        return {
            "alert_count": len(verified_alerts),
            "enhanced_summary": enhanced_summary,
            "location_context": location_context,
            "duration_minutes": duration_minutes,
            "counties_affected": list(counties_affected),
            "avg_confidence": round(avg_confidence, 2),
            "nws_office": nws_office,
            "radar_confirmed": radar_polygon_match,
            "generated_at": datetime.utcnow().isoformat(),
            "has_verified_alerts": True
        }

    def _generate_enhanced_summary(self, report, verified_alerts, duration_minutes, counties_affected, nws_office, location_context, radar_polygon_match):
        """Generate enhanced summary using your specific OpenAI prompt methodology"""
        
        try:
            # Extract magnitude with proper handling for 'UNK' values
            magnitude_value = None
            if report.magnitude:
                try:
                    if str(report.magnitude).upper() == 'UNK':
                        magnitude_value = None
                    else:
                        magnitude_value = float(report.magnitude)
                except (ValueError, TypeError):
                    magnitude_value = None
            
            # Determine values based on report type
            if report.report_type.upper() == 'HAIL':
                hail_size = magnitude_value if magnitude_value else 0.75
                hail_threat_level = self._map_hail_threat_level(hail_size)
                wind_threat_level = ""
                damage_statement = f"Hail can cause dents to vehicles, cracked windows, damage to roofing materials, siding, and gutters. Personal property left exposed is vulnerable to damage."
            elif report.report_type.upper() == 'WIND':
                wind_speed = magnitude_value if magnitude_value else 60
                hail_threat_level = ""
                wind_threat_level = self._map_wind_threat_level(wind_speed)
                damage_statement = f"Wind gusts can cause damage to trees, power lines, and structures. Mobile homes and high-profile vehicles are particularly vulnerable."
            else:
                hail_size = wind_speed = 0
                hail_threat_level = wind_threat_level = "Unknown threat level"
                damage_statement = ""
            
            # Get location context data
            event_location = location_context.get('event_location', {})
            major_city_data = location_context.get('nearest_major_city', {})
            nearby_places = location_context.get('nearby_places', [])
            
            # Use event location as primary reference
            if event_location and event_location.get('name'):
                primary_location = event_location['name']
                primary_distance = event_location.get('distance_miles', 0)
            else:
                primary_location = report.location
                primary_distance = 0
            
            # Get major city reference
            major_city = major_city_data.get('name', 'Unknown City')
            major_city_distance = f"{major_city_data.get('distance_miles', 0):.1f} miles"
            
            # Create nearby context string
            nearby_context = ""
            if nearby_places:
                nearby_list = [f"{place['name']} ({place.get('distance_miles', 0):.1f}mi)" for place in nearby_places[:3]]
                nearby_context = ", ".join(nearby_list)
            
            # Calculate direction (simplified - you may want to enhance this)
            direction = "northeast"  # Placeholder - implement proper direction calculation
            
            # Get time and date strings
            try:
                if hasattr(report, 'time_utc') and report.time_utc:
                    if isinstance(report.time_utc, str) and len(report.time_utc) == 4:
                        hour = int(report.time_utc[:2])
                        minute = int(report.time_utc[2:])
                        time_str = f"{hour:02d}:{minute:02d} (UTC)"
                    else:
                        time_str = str(report.time_utc)
                else:
                    time_str = "unknown time"
                    
                if hasattr(report, 'report_date') and report.report_date:
                    from datetime import datetime
                    if isinstance(report.report_date, str):
                        date_obj = datetime.strptime(report.report_date, '%Y-%m-%d')
                        date_str = date_obj.strftime('%B %d, %Y')
                    else:
                        date_str = report.report_date.strftime('%B %d, %Y')
                else:
                    date_str = "unknown date"
            except (ValueError, AttributeError):
                time_str = str(report.time_utc) if hasattr(report, 'time_utc') else "unknown time"
                date_str = str(report.spc_date) if hasattr(report, 'spc_date') else "unknown date"
            
            # Add natural language hail size if applicable
            hail_natural_lang = ""
            if report.report_type.upper() == 'HAIL':
                hail_natural_lang = self._get_hail_natural_language(hail_size)
            
            # Generate template-based summary following your exact format
            if report.report_type.upper() == 'HAIL':
                summary = (f"{hail_size:.2f} inch hail{hail_natural_lang} struck {primary_location}. "
                          f"{hail_threat_level}. {damage_statement} "
                          f"Approximately {major_city_distance} from {major_city}. "
                          f"Nearby locations include {nearby_context}.")
            else:
                summary = (f"{wind_speed:.0f} mph wind struck {primary_location}. "
                          f"{wind_threat_level}. {damage_statement} "
                          f"Approximately {major_city_distance} from {major_city}. "
                          f"Nearby locations include {nearby_context}.")
            
            return summary.replace('.00', '').replace('  ', ' ')
            
        except Exception as e:
            logger.error(f"Error generating enhanced summary: {e}")
            return f"Storm event reported at {report.location}, {report.county} County, {report.state}."

    def _extract_nws_office(self, verified_alerts):
        """Extract NWS office from verified alerts"""
        offices = set()
        for alert in verified_alerts:
            if hasattr(alert, 'sender_name') and alert.sender_name:
                # Extract office code from sender name (e.g., "NWS Topeka KS" -> "TOP")
                if 'NWS' in alert.sender_name:
                    parts = alert.sender_name.split()
                    if len(parts) >= 3:
                        offices.add(parts[1])  # City name
        return list(offices)[0] if offices else "Unknown"

def enrich_spc_report(report_id: int, db_session: Session) -> Dict[str, Any]:
    """
    Public function to enrich a single SPC report
    """
    service = SPCEnhancedContextService(db_session)
    return service.enrich_spc_report(report_id)

def bulk_enrich_spc_reports(limit: int = 50, db_session: Session = None) -> Dict[str, Any]:
    """
    Enrich multiple SPC reports without enhanced context
    """
    if not db_session:
        db_session = db.session
        
    try:
        from models import SPCReport
        
        # Get reports without enhanced context
        reports = db_session.query(SPCReport).filter(
            (SPCReport.enhanced_context.is_(None)) |
            (SPCReport.enhanced_context_version != "v2.0") |
            (SPCReport.enhanced_context_generated_at.is_(None))
        ).limit(limit).all()
        
        if not reports:
            return {"message": "No reports need enrichment", "processed": 0}
        
        service = SPCEnhancedContextService(db_session)
        processed = 0
        errors = []
        
        for report in reports:
            try:
                service.enrich_spc_report(report.id)
                processed += 1
                logger.info(f"Enriched SPC report {report.id}")
            except Exception as e:
                errors.append(f"Report {report.id}: {str(e)}")
                logger.error(f"Failed to enrich report {report.id}: {e}")
                continue
        
        return {
            "message": f"Processed {processed} reports",
            "processed": processed,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Error in bulk enrichment: {e}")
        raise