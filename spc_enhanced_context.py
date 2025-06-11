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

from models import SPCReport, Alert, RadarAlert, db
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
    
    def enrich_spc_report(self, report_id: int) -> Dict[str, Any]:
        """
        Generate enhanced context for a specific SPC report
        
        Args:
            report_id: SPC report ID
            
        Returns:
            Enhanced context dictionary
        """
        try:
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
    
    def _get_verified_alerts_for_report(self, report_id: int) -> List[Alert]:
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
        alerts = self.db.query(Alert).filter(Alert.id.in_(alert_ids)).order_by(Alert.effective).all()
        return alerts
    
    def _build_enhanced_context(self, report: SPCReport, verified_alerts: List[Alert]) -> Dict[str, Any]:
        """Build the enhanced context structure"""
        
        # Always get location context regardless of verified alerts
        location_context = self._get_location_context(report)
        
        # Handle case with no verified alerts but still provide location enrichment
        if not verified_alerts:
            return {
                "alert_count": 0,
                "multi_alert_summary": self._generate_location_only_summary(report, location_context),
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
        
        # Generate multi-alert summary
        multi_alert_summary = self._generate_multi_alert_summary(
            report, verified_alerts, duration_minutes, counties_affected, nws_office
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
    
    def _extract_nws_office(self, verified_alerts: List[Alert]) -> str:
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
    
    def _generate_multi_alert_summary(self, report: SPCReport, verified_alerts: List[Alert], 
                                    duration_minutes: int, counties_affected: set, nws_office: str) -> str:
        """Generate AI-powered enhanced summary with location context"""
        try:
            # Get location context for enhanced summary
            location_context = self._get_location_context(report)
            
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

            # Check for radar polygon detection at SPC point location
            radar_polygon_match = False
            radar_event_type = 'N/A'
            
            # Check location enrichment for point-in-polygon radar detection
            if hasattr(report, 'spc_enrichment') and report.spc_enrichment:
                try:
                    enrichment_data = json.loads(report.spc_enrichment) if isinstance(report.spc_enrichment, str) else report.spc_enrichment
                    radar_polygon_match = enrichment_data.get('radar_polygon_match', False)
                    if radar_polygon_match:
                        radar_event_type = 'storm activity'
                except:
                    pass
            
            # Check if ANY verified alerts have radar confirmation (from polygon match status)
            verified_alerts_radar_confirmed = any(
                self._check_radar_confirmation(alert, report) for alert in verified_alerts
            )

            prompt = f"""Generate a professional 2-3 sentence enhanced summary for this SPC storm report.

SPC Report Details:
- Type: {report.report_type}
- Location: {report.location}, {report.county}, {report.state}
- Time: {report.time_utc}
- Magnitude: {report.magnitude if hasattr(report, 'magnitude') else 'N/A'}
- Verified Alerts Radar Confirmation: {'Yes' if verified_alerts_radar_confirmed else 'No'}

Location Context:
- Nearest Major City: {major_city} ({major_city_distance} away)
- Nearby Places: {nearby_context if nearby_context else 'None found nearby'}

Radar Detection:
- Radar Detection at this Location: {'Yes' if radar_polygon_match else 'No'}
- Radar Event Type (if matched): {radar_event_type if radar_polygon_match else 'N/A'}

Verified Alerts Summary:
- Total Verified NWS Alerts: {len(verified_alerts)} spanning {duration_minutes} minutes
- Counties Affected: {', '.join(sorted(counties_affected))}
- NWS Office(s): {nws_office}

Instructions:
Write a clear and professional summary that:
1. Begins with the SPC Report Location: "{report.location}, {report.county}, {report.state}".
2. References the Nearest Major City and distance.
3. Mentions notable Nearby Places if available.
4. Clearly states whether the location was confirmed as within a Radar-detected storm area. 
   - If Radar Detection = Yes, use layman terms like "Radar-confirmed storm area was present".
   - If Radar Detection = No, say "No Radar-confirmed storm area was detected at this location".
5. Emphasizes the number of Verified NWS Alerts, duration, and geographic coverage.
6. Optionally includes the NWS Office name to provide source credibility.
7. Write for a broad audience — use plain language, avoid technical jargon like 'polygon', 'lat/lon', or 'point-in-polygon'.
8. If ANY Verified Alerts were Radar Confirmed (Verified Alerts Radar Confirmation == Yes), clearly state that radar-confirmed storm activity was present in this area, even if the SPC point itself was not inside a radar polygon.
9. If Verified Alerts Radar Confirmation == No, do not mention radar in the summary.

CRITICAL:
- Follow the above instructions strictly.
- Do not hallucinate additional historical data.
- Use only the provided inputs — do not speculate.
- Be consistent — users will compare multiple SPC Reports and expect uniform structure."""

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
    
    def _generate_location_only_summary(self, report: SPCReport, location_context: Dict[str, Any]) -> str:
        """Generate location-enriched summary for reports without verified alerts"""
        try:
            # Extract key location references for better context
            event_location = location_context.get('primary_location', report.location)
            major_city = location_context.get('nearest_major_city', 'Unknown')
            major_city_distance = location_context.get('major_city_distance', '')
            nearby_places = location_context.get('nearby_places', [])
            
            # Build nearby places string with distances for location-only summary
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

            prompt = f"""Generate a location-enhanced summary for this SPC storm report:

SPC Report Details:
- Type: {report.report_type}
- Location: {report.location}, {report.county}, {report.state}
- Time: {report.time_utc}
- Magnitude: {report.magnitude if hasattr(report, 'magnitude') else 'N/A'}
- Comments: {report.comments}

Location Context (USE THIS DATA):
- Nearest Major City: {major_city} ({major_city_distance} away)
- Nearby Places: {nearby_context if nearby_context else 'None within close proximity'}

Create a 1-2 sentence enhanced summary that:
1. Starts with the SPC report location: "{report.location}, {report.county}, {report.state}"
2. Reference the nearest major city: "{major_city}" at "{major_city_distance}" away when available
3. Include nearby places when available: {nearby_context}
4. Describes the SPC report type and measurement clearly
5. Makes the location meaningful and accessible to readers

CRITICAL: Use the provided location data exactly as given. Do not add historical context or speculation."""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a meteorological data analyst specializing in location-enhanced weather summaries. Create clear, location-focused summaries that make storm reports more accessible."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.2
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating location-only summary: {e}")
            # Fallback with location context
            location_ref = location_context.get('primary_location', f"{report.location}, {report.county}, {report.state}")
            return f"This {report.report_type} report occurred at {location_ref} at {report.time_utc}."
    
    def _get_location_context(self, report: SPCReport) -> Dict[str, Any]:
        """Get location context from existing enrichment data"""
        
        # Check if we have existing SPC enrichment data
        if hasattr(report, 'spc_enrichment') and report.spc_enrichment:
            try:
                existing_enrichment = json.loads(report.spc_enrichment) if isinstance(report.spc_enrichment, str) else report.spc_enrichment
                
                # Extract nearby places data
                nearby_places = existing_enrichment.get('nearby_places', [])
                
                # Find primary location (distance = 0.0) and nearest city
                primary_location = f"{report.location}, {report.county}"
                nearest_major_city = ""
                major_city_distance = ""
                nearby_place_names = []
                
                for place in nearby_places:
                    place_type = place.get('type', '')
                    place_name = place.get('name', '')
                    distance_miles = place.get('distance_miles', 0)
                    
                    if place_type == 'primary_location' and distance_miles == 0.0:
                        primary_location = place_name
                    elif place_type == 'nearest_city':
                        nearest_major_city = place_name
                        major_city_distance = f"{distance_miles:.1f} miles"
                    elif place_type == 'nearby_place' and distance_miles <= 10.0:
                        nearby_place_names.append({
                            'name': place_name,
                            'distance_miles': distance_miles
                        })
                
                location_context = {
                    'primary_location': primary_location,
                    'nearest_major_city': nearest_major_city,
                    'major_city_distance': major_city_distance,
                    'nearby_places': nearby_place_names,
                    'geographic_features': []
                }
                
                return location_context
                
            except (json.JSONDecodeError, KeyError, AttributeError) as e:
                logger.warning(f"Error parsing SPC enrichment for report {report.id}: {e}")
        
        # Fallback to basic location
        return {
            'primary_location': f"{report.location}, {report.county}, {report.state}",
            'nearby_places': [],
            'geographic_features': [],
            'nearest_major_city': 'Unknown'
        }
    
    def _generate_location_context(self, report: SPCReport) -> Dict[str, Any]:
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
    
    def _generate_polygon_match_status(self, verified_alerts: List[Alert], report: SPCReport) -> List[Dict[str, Any]]:
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
    
    def _check_radar_confirmation(self, alert: Alert, report: SPCReport) -> bool:
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
    
    def enrich_all_reports(self, batch_size: int = 50, unenriched_only: bool = True) -> Dict[str, int]:
        """Enrich ALL SPC reports with enhanced context (verified and unverified)"""
        try:
            # Get all SPC reports that need enrichment
            if unenriched_only:
                # Only enrich reports without enhanced_context or with empty enhanced_context
                query = self.db.query(SPCReport).filter(
                    db.or_(
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