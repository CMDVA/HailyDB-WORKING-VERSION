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
        """Map hail size to official NWS threat level"""
        if hail_size >= 2.75:
            return "Extreme Threat"
        elif hail_size >= 1.75:
            return "High Threat"
        elif hail_size >= 1.0:
            return "Moderate Threat"
        elif hail_size >= 0.75:
            return "Low Threat"
        elif hail_size > 0:
            return "Very Low Threat"
        else:
            return "Non-Threatening"

    def _map_wind_threat_level(self, wind_speed: float) -> str:
        """Map wind speed to official NWS threat level"""
        if wind_speed >= 92:
            return "Extreme Threat"
        elif wind_speed >= 75:
            return "High Threat"
        elif wind_speed >= 58:
            return "Moderate Threat"
        elif wind_speed >= 39:
            return "Low Threat"
        elif wind_speed > 0:
            return "Very Low Threat"
        else:
            return "Non-Threatening"

    def _hail_effect_statement(self, hail_size: float) -> str:
        """Generate NWS-derived hail effect statement"""
        if hail_size >= 2.75:
            return "Giant hail (≥ 2.75\") is likely to cause major property damage including roof destruction, broken windows, and significant vehicle damage."
        elif hail_size >= 1.75:
            return "Very large hail (1.75\"–2.74\") may cause moderate to major damage to vehicles, roofs, and windows."
        elif hail_size >= 1.0:
            return "Large hail (1.0\"–1.74\") may cause minor to moderate damage including vehicle dents and roof impacts."
        elif hail_size >= 0.75:
            return "Hail near severe threshold (0.75\"–0.99\") may cause isolated minor damage to vehicles and vegetation."
        elif hail_size > 0:
            return "Small hail (< 0.75\") generally not expected to cause significant property damage."
        else:
            return "No hail reported."

    def _wind_effect_statement(self, wind_speed: int) -> str:
        """Generate NWS-derived wind effect statement"""
        if wind_speed >= 92:
            return "Violent wind gusts (≥ 92 mph) likely to cause major structural damage and widespread power outages."
        elif wind_speed >= 75:
            return "Very damaging wind gusts (75–91 mph) may cause moderate to major damage to structures, large trees, and power infrastructure."
        elif wind_speed >= 58:
            return "Damaging wind gusts (58–74 mph) may cause minor to moderate damage to roofs, trees, and vehicles."
        elif wind_speed >= 39:
            return "Strong wind gusts (39–57 mph) may cause minor damage to trees and unsecured structures."
        elif wind_speed > 0:
            return "Sub-severe wind gusts (< 39 mph) generally not expected to cause significant property damage."
        else:
            return "No wind reported."
    
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
            
            # Generate enhanced context for both verified and unverified reports
            # Unverified reports will get location-based enhanced context
            
            # Get verified alerts that match this report
            verified_alerts = self._get_verified_alerts_for_report(report_id)
            
            # Generate enhanced context (with or without verified alerts)
            enhanced_context = self._build_enhanced_context(report, verified_alerts)
            
            # Update the report with enhanced context
            report.enhanced_context = enhanced_context
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
                "multi_alert_summary": enhanced_summary,
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
        
        # Generate enhanced summary (handles both verified and unverified reports)
        multi_alert_summary = self._generate_enhanced_summary(
            report, verified_alerts, duration_minutes, counties_affected, 
            nws_office, location_context, radar_polygon_match
        )
        
        # Get location context
        location_context = self._get_location_context(report)
        
        # Generate polygon match status
        polygon_match_status = self._generate_polygon_match_status(verified_alerts, report)
        
        enhanced_context = {
            "multi_alert_summary": multi_alert_summary,
            "verified_alert_ids": [alert.id for alert in verified_alerts],
            "event_duration_minutes": duration_minutes,
            "counties_affected": sorted(list(counties_affected)),
            "avg_match_confidence": round(avg_confidence, 2),
            "nws_office": nws_office,
            "location_context": location_context,
            "polygon_match_status": polygon_match_status,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "alert_count": len(verified_alerts)
        }
        
        return enhanced_context
    
    def _extract_nws_office(self, verified_alerts: List) -> str:
        """Extract NWS office information from alerts"""
        for alert in verified_alerts:
            if alert.properties and isinstance(alert.properties, dict):
                # Try to extract from senderName in properties
                sender_name = alert.properties.get('senderName', '')
                if sender_name and "NWS" in sender_name:
                    return sender_name.replace("NWS ", "").strip()
                
                # Try to extract from sender
                sender = alert.properties.get('sender', '')
                if sender and "NWS" in sender:
                    return sender.replace("NWS ", "").strip()
        return "Unknown"
    
    def _generate_enhanced_summary(self, report, verified_alerts: List, 
                                 duration_minutes: int, counties_affected: set, nws_office: str,
                                 location_context: Dict[str, Any], radar_polygon_match: bool) -> str:
        """Generate AI-powered enhanced summary with conditional logic for verified/unverified reports"""
        try:
            # Prepare context for AI
            alert_details = []
            for alert in verified_alerts:
                alert_details.append({
                    "event": alert.event,
                    "effective": alert.effective.isoformat() if alert.effective else None,
                    "area": alert.area_desc,
                    "counties": alert.county_names
                })
            
            # Extract key location references for better context
            event_location = location_context.get('primary_location', report.location)
            major_city = location_context.get('nearest_major_city', '')
            major_city_distance = location_context.get('major_city_distance', '')
            nearby_places = location_context.get('nearby_places', [])
            
            # Build nearby places string with distances
            nearby_context = ""
            if nearby_places:
                closest_places = []
                for place in nearby_places[:3]:
                    name = place.get('name', '')
                    distance = place.get('distance_miles', 0)
                    if name and distance:
                        closest_places.append(f"{name} ({distance:.1f}mi)")
                if closest_places:
                    nearby_context = f"near {', '.join(closest_places)}"

            # Get radar polygon detection status from location context
            radar_polygon_match = location_context.get('radar_polygon_match', False)
            radar_event_type = 'storm activity' if radar_polygon_match else 'N/A'
            
            # Check if ANY verified alerts have radar confirmation (from polygon match status)
            verified_alerts_radar_confirmed = any(
                self._check_radar_confirmation(alert, report) for alert in verified_alerts
            )

            # Extract hail and wind magnitudes
            try:
                hail_size = float(report.magnitude) if report.report_type == "HAIL" and report.magnitude else 0.0
            except ValueError:
                hail_size = 0.0

            try:
                wind_speed = int(report.magnitude.replace(" MPH", "").replace("MPH", "").strip()) \
                    if report.report_type == "WIND" and report.magnitude else 0
            except (ValueError, AttributeError):
                wind_speed = 0

            # Map to NWS Threat Levels
            hail_threat_level = self._map_hail_threat_level(hail_size)
            wind_threat_level = self._map_wind_threat_level(wind_speed)

            # Include SPC comments if present, otherwise use NWS-derived effects
            if hasattr(report, 'comments') and report.comments and report.comments.strip():
                damage_statement = f"Reported Damage: {report.comments.strip()}"
            else:
                # Fallback to NWS-derived potential effects
                if report.report_type == "HAIL":
                    damage_statement = self._hail_effect_statement(hail_size)
                elif report.report_type == "WIND":
                    damage_statement = self._wind_effect_statement(wind_speed)
                else:
                    damage_statement = "No specific damage reports were received as of this summary."

            # Calculate direction from event to major city (if coordinates available)
            direction = ""
            if major_city and hasattr(report, 'latitude') and hasattr(report, 'longitude'):
                major_city_coords = location_context.get('major_city_coordinates', {})
                if major_city_coords and 'lat' in major_city_coords and 'lon' in major_city_coords:
                    direction = self._calculate_direction(
                        report.latitude, report.longitude, 
                        major_city_coords['lat'], major_city_coords['lon']
                    )

            # Generate conditional prompt based on whether we have verified alerts
            if verified_alerts and len(verified_alerts) > 0:
                # Multi-alert summary with verification context
                prompt = f"""You are a professional meteorological data analyst specializing in precise threat-level weather summaries aligned to official NWS guidance, designed for actionable intelligence in storm restoration, insurance, and public safety.

This is a HISTORICAL SPC STORM REPORT summary, not an active warning.

MANDATORY NWS Threat Classifications:
- HAIL: < 1.0" = Very Low Threat | 1.0"-1.74" = Low/Moderate Threat | 1.75"-2.74" = High Threat | ≥2.75" = Extreme Threat
- WIND: 39-57 mph = Low Threat | 58-74 mph = Moderate Threat | 75-91 mph = High Threat | ≥92 mph = Extreme Threat

SPC Historical Report:
- Type: {report.report_type}
- Location: {report.location}, {report.county}, {report.state}  
- Time: {report.time_utc}
- Hail Threat Level: {hail_threat_level}
- Wind Threat Level: {wind_threat_level}
- {damage_statement}

Location Context:
- Radar Detection: {'Detected' if radar_polygon_match else 'Not Detected'}
- Distance/Direction: {major_city_distance} {direction} of {major_city}
- Nearby Places: {nearby_context if nearby_context else 'Remote area'}

Verification: {len(verified_alerts)} NWS alerts over {duration_minutes} minutes

REQUIRED Format:
"At [location], [county] County, [state], [storm type] was reported. Radar-indicated [magnitude] places this event in the [threat level] category. [Damage status statement]. The event occurred [distance] [direction] of [major city] near [nearby places]."

Use ONLY the exact threat classifications provided. NEVER exaggerate beyond NWS scale."""
            else:
                # Location-only summary for unverified reports  
                prompt = f"""You are a professional meteorological data analyst specializing in precise threat-level weather summaries aligned to official NWS guidance.

This is a HISTORICAL SPC STORM REPORT summary, not an active warning.

MANDATORY NWS Threat Classifications:
- HAIL: < 1.0" = Very Low Threat | 1.0"-1.74" = Low/Moderate Threat | 1.75"-2.74" = High Threat | ≥2.75" = Extreme Threat  
- WIND: 39-57 mph = Low Threat | 58-74 mph = Moderate Threat | 75-91 mph = High Threat | ≥92 mph = Extreme Threat

SPC Historical Report:
- Type: {report.report_type}
- Location: {report.location}, {report.county}, {report.state}
- Time: {report.time_utc}  
- Hail Threat Level: {hail_threat_level}
- Wind Threat Level: {wind_threat_level}
- {damage_statement}
- Distance/Direction: {major_city_distance} {direction} of {major_city}
- Nearby Places: {nearby_context if nearby_context else 'Remote area'}

REQUIRED Format:
"At [location], [county] County, [state], [storm type] was reported. [Magnitude] places this event in the [threat level] category. [Damage status statement]. The event occurred [distance] [direction] of [major city] near [nearby places]."

Use ONLY the exact threat classifications provided. NEVER exaggerate beyond NWS scale."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a meteorological data analyst specializing in location-enhanced weather summaries. Create comprehensive summaries that make locations more recognizable and meaningful."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=250,
                temperature=0.2
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI summary: {e}")
            # Fallback summary
            return f"This {report.report_type} report in {report.county} County, {report.state} was validated by {len(verified_alerts)} NWS alerts spanning {duration_minutes} minutes across {len(counties_affected)} counties."
    

    
    def _get_location_context(self, report) -> Dict[str, Any]:
        """Get location context from existing enrichment data"""
        
        # Check if we have existing SPC enrichment data
        if hasattr(report, 'spc_enrichment') and report.spc_enrichment:
            try:
                existing_enrichment = json.loads(report.spc_enrichment) if isinstance(report.spc_enrichment, str) else report.spc_enrichment
                
                # Extract nearby places data from the actual Location Enrichment format
                nearby_places_data = existing_enrichment.get('nearby_places', [])
                
                # Extract structured Event Location and Nearest Major City
                event_location = None
                event_location_distance = ""
                nearest_major_city = "Unknown"
                major_city_distance = ""
                
                # Find Event Location (primary_location type)
                for place in nearby_places_data:
                    if place.get('type') == 'primary_location':
                        event_location = place.get('name', '')
                        distance = place.get('distance_miles', 0)
                        event_location_distance = f"{distance:.1f} miles away" if distance > 0 else "at coordinates"
                        break
                
                # Find Nearest Major City (nearest_city type)
                for place in nearby_places_data:
                    if place.get('type') == 'nearest_city':
                        nearest_major_city = place.get('name', '')
                        distance = place.get('distance_miles', 0)
                        major_city_distance = f"{distance:.1f} miles away" if distance > 0 else ""
                        break
                
                # Use the primary location from the report as fallback
                primary_location = f"{report.location}, {report.county} County, {report.state}"
                
                # Format nearby places for Enhanced Context (excluding primary_location and nearest_city)
                nearby_place_names = []
                for place in nearby_places_data:
                    place_name = place.get('name', '')
                    place_distance = place.get('distance_miles', 0)
                    place_type = place.get('type', '')
                    
                    if (place_name and place_distance and 
                        place_type not in ['primary_location', 'nearest_city']):
                        nearby_place_names.append({
                            'name': place_name,
                            'distance_miles': float(place_distance)
                        })
                
                # Get radar polygon match status
                radar_polygon_match = existing_enrichment.get('radar_polygon_match', False)
                
                location_context = {
                    'primary_location': primary_location,
                    'nearest_major_city': nearest_major_city,
                    'major_city_distance': major_city_distance,
                    'nearby_places': nearby_place_names,
                    'radar_polygon_match': radar_polygon_match
                }
                
                logger.info(f"Successfully extracted location context for report {report.id}: {len(nearby_place_names)} nearby places, radar match: {radar_polygon_match}")
                return location_context
                
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                logger.warning(f"Error parsing SPC enrichment for report {report.id}: {e}")
        
        # Fallback to basic location
        logger.info(f"Using fallback location context for report {report.id} - no enrichment data available")
        return {
            'primary_location': f"{report.county} County, {report.state}",
            'nearby_places': [],
            'nearest_major_city': 'Unknown',
            'major_city_distance': '',
            'radar_polygon_match': False
        }
    
    def _generate_location_context(self, report) -> Dict[str, Any]:
        """Generate location context using AI"""
        try:
            prompt = f"""Provide geographic context for this storm report location:

Location: {report.location}
County: {report.county}
State: {report.state}
Coordinates: {report.lat}, {report.lon}

Provide a JSON response with:
1. primary_location: Main location description
2. nearby_places: Array of nearby towns/cities with approximate coordinates
3. geographic_features: Array of notable geographic features (rivers, mountains, etc.)

Focus on locations that would be relevant for insurance, restoration, or emergency management."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a geographic analyst. Provide location context in JSON format."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=300,
                temperature=0.3
            )
            
            context = json.loads(response.choices[0].message.content)
            return context
            
        except Exception as e:
            logger.error(f"Error generating location context: {e}")
            return {
                "primary_location": f"{report.location}, {report.county} County, {report.state}",
                "nearby_places": [],
                "geographic_features": []
            }
    
    def _generate_polygon_match_status(self, verified_alerts: List, report) -> List[Dict[str, Any]]:
        """Generate polygon match status for each verified alert"""
        polygon_status = []
        
        for alert in verified_alerts:
            # Check if polygon is present
            polygon_present = bool(alert.geometry)
            
            # Check radar confirmation
            radar_confirmed = self._check_radar_confirmation(alert, report)
            
            polygon_status.append({
                "alert_id": alert.id,
                "polygon_present": polygon_present,
                "radar_confirmed": radar_confirmed,
                "event_type": alert.event,
                "effective_time": alert.effective.isoformat() if alert.effective else None
            })
        
        return polygon_status
    
    def _check_radar_confirmation(self, alert, report) -> bool:
        """Check if alert has radar confirmation from polygon match status"""
        # Check if this alert has radar-indicated data (wind/hail measurements)
        if hasattr(alert, 'radar_indicated') and alert.radar_indicated:
            try:
                radar_data = json.loads(alert.radar_indicated) if isinstance(alert.radar_indicated, str) else alert.radar_indicated
                # If alert has wind or hail measurements, it's radar-confirmed
                return radar_data and (radar_data.get('wind_mph', 0) > 0 or radar_data.get('hail_inches', 0) > 0)
            except:
                pass
        return False
    
    def _calculate_direction(self, lat1: float, lon1: float, lat2: float, lon2: float) -> str:
        """Calculate cardinal direction from point 1 to point 2"""
        import math
        
        try:
            # Convert to radians
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            lon_diff = math.radians(lon2 - lon1)
            
            # Calculate bearing
            y = math.sin(lon_diff) * math.cos(lat2_rad)
            x = math.cos(lat1_rad) * math.sin(lat2_rad) - \
                math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(lon_diff)
            
            bearing = math.atan2(y, x)
            bearing = math.degrees(bearing)
            bearing = (bearing + 360) % 360
            
            # Convert to cardinal direction
            directions = [
                "north", "northeast", "east", "southeast",
                "south", "southwest", "west", "northwest"
            ]
            index = int((bearing + 22.5) / 45) % 8
            return directions[index]
            
        except Exception as e:
            logger.warning(f"Could not calculate direction: {e}")
            return ""
    
    def enrich_all_reports(self, batch_size: int = 50, unenriched_only: bool = True) -> Dict[str, int]:
        """Enrich ALL SPC reports with enhanced context (verified and unverified)"""
        try:
            # Import here to avoid circular imports
            from models import SPCReport
            from sqlalchemy import or_
            
            # Get all SPC reports that need enrichment
            if unenriched_only:
                # Only enrich reports without enhanced_context or with empty enhanced_context
                query = self.db.query(SPCReport).filter(
                    or_(
                        SPCReport.enhanced_context.is_(None),
                        SPCReport.enhanced_context == {}
                    )
                )
            else:
                # Enrich all reports (re-enrichment)
                query = self.db.query(SPCReport)
            
            all_reports = query.all()
            
            total_reports = len(all_reports)
            processed = 0
            successful = 0
            failed = 0
            
            logger.info(f"Starting enhanced context generation for {total_reports} SPC reports")
            
            for i in range(0, total_reports, batch_size):
                batch = all_reports[i:i+batch_size]
                
                for report in batch:
                    try:
                        enhanced_context = self.enrich_spc_report(report.id)
                        if enhanced_context:
                            successful += 1
                        processed += 1
                        
                        if processed % 10 == 0:
                            logger.info(f"Processed {processed}/{total_reports} reports")
                            
                    except Exception as e:
                        logger.error(f"Failed to enrich report {report.id}: {e}")
                        failed += 1
                        processed += 1
                
                # Commit batch
                try:
                    self.db.commit()
                except Exception as e:
                    logger.error(f"Error committing batch: {e}")
                    self.db.rollback()
            
            results = {
                "total_reports": total_reports,
                "processed": processed,
                "successful": successful,
                "failed": failed
            }
            
            logger.info(f"Enrichment complete: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error in bulk enrichment: {e}")
            self.db.rollback()
            raise

def enrich_spc_report_context(report_id: int) -> Dict[str, Any]:
    """Standalone function to enrich a single SPC report"""
    service = SPCEnhancedContextService(db.session)
    return service.enrich_spc_report(report_id)

def enrich_all_spc_reports() -> Dict[str, int]:
    """Standalone function to enrich all SPC reports"""
    service = SPCEnhancedContextService(db.session)
    return service.enrich_all_reports()