"""
Enhanced Context System v2.0 for SPC Reports
Production-grade implementation with transaction isolation, versioning, and modular pipeline
"""

import json
import logging
import math
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import SPCReport, Alert

# Version tracking for Enhanced Context generation
ENHANCED_CONTEXT_VERSION = "v2.0"


class SPCEnhancedContextService:
    """Production-grade service for generating enhanced context for SPC reports"""
    
    def __init__(self, db_session: Session):
        """Initialize service with database session"""
        self.db = db_session
        self.logger = logging.getLogger(__name__)
        
    def _build_prompt_context(self, report, location_context, duration_minutes, counties_affected, nws_office, radar_polygon_match):
        """Prepare structured prompt context"""
        report_type = report.report_type.upper()

        # Extract magnitude with proper JSON handling and UNK value handling
        magnitude_value = None
        if report.magnitude:
            if isinstance(report.magnitude, dict):
                # Handle JSON magnitude data
                if report_type == "HAIL" and 'size_inches' in report.magnitude:
                    magnitude_value = report.magnitude['size_inches']
                elif report_type == "WIND" and 'speed' in report.magnitude:
                    magnitude_value = report.magnitude['speed']
                else:
                    # Try common keys
                    magnitude_value = report.magnitude.get('speed') or report.magnitude.get('size_inches') or report.magnitude.get('value')
            else:
                # Handle string/numeric magnitude values, including 'UNK'
                try:
                    if str(report.magnitude).upper() == 'UNK':
                        magnitude_value = None
                    else:
                        magnitude_value = float(report.magnitude)
                except (ValueError, TypeError):
                    magnitude_value = None
        
        # Format magnitude display
        if report_type == "HAIL":
            magnitude_display = f"{magnitude_value:.2f} inch".replace('.00', '') if magnitude_value else "0.75 inch"
        elif report_type == "WIND":
            magnitude_display = f"{int(magnitude_value)} mph" if magnitude_value else "58 mph"
        else:
            magnitude_display = str(magnitude_value) if magnitude_value else 'severe weather'

        # Time formatting
        if hasattr(report, 'time_utc') and report.time_utc:
            if isinstance(report.time_utc, str) and len(report.time_utc) == 4:
                hour = int(report.time_utc[:2])
                minute = int(report.time_utc[2:])
                time_str = f"{hour:02d}:{minute:02d} (UTC)"
            else:
                time_str = str(report.time_utc)
        else:
            time_str = "unknown time"

        # Date formatting
        if hasattr(report, 'report_date') and report.report_date:
            if isinstance(report.report_date, str):
                date_obj = datetime.strptime(report.report_date, '%Y-%m-%d')
                date_str = date_obj.strftime('%B %d, %Y')
            else:
                date_str = report.report_date.strftime('%B %d, %Y')
        else:
            date_str = "unknown date"

        # Extract location hierarchy from Google Places data
        event_location = ""
        nearest_major_city = ""
        nearby_places_text = ""
        
        # Use event location as primary location (smallest nearby place)
        if location_context.get('event_location') and location_context['event_location'].get('name'):
            event_location = location_context['event_location']['name']
        
        # Add nearest major city with distance
        if location_context.get('nearest_major_city') and location_context['nearest_major_city'].get('name'):
            major_city = location_context['nearest_major_city']
            distance = major_city.get('distance_miles', 0)
            nearest_major_city = f"approximately {distance:.0f} miles from {major_city['name']}"
        
        # Build nearby places context
        if location_context.get('nearby_places'):
            nearby_sorted = sorted([
                place for place in location_context['nearby_places'] 
                if place.get('distance_miles', 0) <= 50
            ], key=lambda x: x.get('distance_miles', 0))[:3]
            
            if nearby_sorted:
                nearby_places_text = "Nearby locations include " + ", ".join([
                    f"{place['name']} ({place['distance_miles']:.1f}mi)"
                    for place in nearby_sorted
                ]) + "."

        # Damage assessment
        if report_type == "HAIL" and report.magnitude:
            damage_info = self._get_hail_damage_category(float(report.magnitude))
        elif report_type == "WIND" and report.magnitude:
            damage_info = self._get_wind_damage_category(float(report.magnitude))
        else:
            damage_info = {
                "category": "Severe Weather Event",
                "damage_potential": "weather-related damage",
                "is_severe": False,
                "comments": "Severe weather event with potential for localized damage."
            }

        return {
            "report_type": report_type,
            "magnitude_display": magnitude_display,
            "location": report.location,
            "county": report.county,
            "state": report.state,
            "time_str": time_str,
            "date_str": date_str,
            "event_location": event_location,
            "nearest_major_city": nearest_major_city,
            "nearby_places_text": nearby_places_text,
            "damage_info": damage_info
        }

    def _build_prompt(self, context):
        """Build plain text prompt from structured context"""
        location_text = ""
        if context['event_location']:
            location_text = f"in {context['event_location']}"
        elif context['location']:
            location_text = f"in {context['location']}"
        else:
            location_text = f"in {context['county']} County, {context['state']}"
            
        nearby_context = ""
        if context['nearest_major_city']:
            nearby_context += f" {context['nearest_major_city']}."
        if context['nearby_places_text']:
            nearby_context += f" {context['nearby_places_text']}"
            
        return f"""Generate a professional meteorological summary for this severe weather event.

EVENT DATA:
- Event Type: {context['report_type']}
- Magnitude: {context['magnitude_display']}
- Primary Location: {context['event_location'] or context['location']}
- Regional Context: {context['nearest_major_city']}
- Nearby Places: {context['nearby_places_text']}
- Time: {context['time_str']} on {context['date_str']}
- Damage Assessment: {context['damage_info']['category']} - {context['damage_info']['damage_potential']}

REQUIREMENTS:
1. Start with "[magnitude] [event type] struck [primary location]"
2. Add regional context using nearest major city with distance
3. Include nearby places for additional context
4. Use professional NWS meteorological terminology
5. Keep summary concise and factual
6. Format: "[magnitude] [event type] struck [primary location]. [damage assessment]. [regional context]"
"""

    def _call_openai(self, prompt_text, template_summary, correlation_id=None):
        """Call OpenAI with retry logic and correlation tracking"""
        from openai import OpenAI
        import os
        
        openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        max_retries = 3
        retry_delay = 1
        
        if not correlation_id:
            correlation_id = str(uuid.uuid4())[:8]

        for attempt in range(max_retries):
            try:
                self.logger.info(f"[{correlation_id}] OpenAI attempt {attempt + 1}/{max_retries}")
                
                response = openai_client.chat.completions.create(
                    model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                    messages=[
                        {"role": "system", "content": prompt_text},
                        {"role": "user", "content": f"Generate the enhanced summary using this template: {template_summary}"}
                    ],
                    max_tokens=300,
                    temperature=0.1,
                    timeout=30
                )
                
                if response and response.choices:
                    content = response.choices[0].message.content
                    if content:
                        self.logger.info(f"[{correlation_id}] OpenAI success on attempt {attempt + 1}")
                        return content.strip()
                
                self.logger.warning(f"[{correlation_id}] Empty response from OpenAI on attempt {attempt + 1}")
                
            except Exception as e:
                self.logger.warning(f"[{correlation_id}] OpenAI API attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    self.logger.error(f"[{correlation_id}] All OpenAI attempts failed")
                    return None
                time.sleep(retry_delay * (2 ** attempt))

        return None

    def _parse_ai_response(self, ai_response, fallback, correlation_id=None):
        """Clean AI response or fallback"""
        if ai_response:
            return ai_response
        else:
            if correlation_id:
                self.logger.warning(f"[{correlation_id}] Using fallback template")
            return fallback

    def _get_hail_damage_category(self, size_inches):
        """Get hail damage category based on size"""
        if size_inches >= 4.0:
            return {
                "category": "Destructive Hail",
                "damage_potential": "extensive property damage",
                "is_severe": True,
                "comments": "Large hail capable of causing significant structural damage to vehicles and buildings."
            }
        elif size_inches >= 2.0:
            return {
                "category": "Damaging Hail",
                "damage_potential": "moderate property damage",
                "is_severe": True,
                "comments": "Large hail capable of denting vehicles and damaging roofing materials."
            }
        elif size_inches >= 1.0:
            return {
                "category": "Severe Hail",
                "damage_potential": "minor to moderate property damage",
                "is_severe": True,
                "comments": "Quarter-size or larger hail that meets severe thunderstorm criteria."
            }
        else:
            return {
                "category": "Small Hail",
                "damage_potential": "minimal damage",
                "is_severe": False,
                "comments": "Sub-severe hail with limited damage potential."
            }

    def _get_wind_damage_category(self, speed_mph):
        """Get wind damage category based on speed"""
        if speed_mph >= 75:
            return {
                "category": "Destructive Winds",
                "damage_potential": "extensive structural damage",
                "is_severe": True,
                "comments": "Extreme winds capable of causing widespread damage to structures and vegetation."
            }
        elif speed_mph >= 58:
            return {
                "category": "Severe Winds",
                "damage_potential": "structural damage",
                "is_severe": True,
                "comments": "Severe thunderstorm winds meeting NWS criteria for warnings."
            }
        else:
            return {
                "category": "Strong Winds",
                "damage_potential": "minor damage",
                "is_severe": False,
                "comments": "Strong winds below severe thunderstorm thresholds."
            }

    def _generate_enhanced_summary(self, report, verified_alerts, duration_minutes, counties_affected, nws_office, location_context, radar_polygon_match):
        """Orchestrate full enhanced summary pipeline with correlation tracking"""
        correlation_id = str(uuid.uuid4())[:8]
        
        try:
            self.logger.info(f"[{correlation_id}] Starting enhanced summary for report {report.id}")
            
            # Build structured context
            context = self._build_prompt_context(report, location_context, duration_minutes, counties_affected, nws_office, radar_polygon_match)

            # Build prompt text
            prompt_text = self._build_prompt(context)

            # Build template summary with location hierarchy
            primary_loc = context['event_location'] or context['location'] or f"{context['county']} County"
            regional_context = ""
            if context['nearest_major_city']:
                regional_context = f" {context['nearest_major_city']}."
            if context['nearby_places_text']:
                regional_context += f" {context['nearby_places_text']}"
            
            template_summary = f"{context['magnitude_display']} {context['report_type'].lower()} struck {primary_loc}. {context['damage_info']['damage_potential'].capitalize()}.{regional_context}"

            # Call OpenAI
            ai_response = self._call_openai(prompt_text, template_summary, correlation_id)

            # Parse response
            result = self._parse_ai_response(ai_response, template_summary, correlation_id)
            
            self.logger.info(f"[{correlation_id}] Enhanced summary completed for report {report.id}")
            return result

        except Exception as e:
            self.logger.error(f"[{correlation_id}] Error generating AI summary for report {report.id}: {e}")
            return f"This {report.report_type.lower()} report was documented in {report.county} County, {report.state} by the Storm Prediction Center."

    def enrich_spc_report(self, report_id: int) -> Dict[str, Any]:
        """Generate enhanced context for a single SPC report with transaction isolation"""
        correlation_id = str(uuid.uuid4())[:8]
        
        try:
            self.logger.info(f"[{correlation_id}] Starting enrichment for report {report_id}")
            
            # Get the report
            report = self.db.query(SPCReport).filter(SPCReport.id == report_id).first()
            if not report:
                return {"success": False, "error": f"Report {report_id} not found"}

            # Check if already has current version
            if (report.enhanced_context_version == ENHANCED_CONTEXT_VERSION and 
                report.enhanced_context_generated_at and
                report.enhanced_context):
                self.logger.info(f"[{correlation_id}] Report {report_id} already has current version {ENHANCED_CONTEXT_VERSION}")
                return {"success": True, "message": "Already has current version", "enhanced_context": report.enhanced_context}

            # Generate Enhanced Context directly from SPC report data (no verification required)
            # This ensures ALL SPC reports get Enhanced Context, not just verified ones
            
            # Use SPC report data directly
            duration_minutes = 0  # SPC reports are point-in-time events
            counties_affected = {report.county} if report.county else set()
            nws_office = "Storm Prediction Center"  # SPC is the authoritative source
            radar_polygon_match = False  # SPC reports are ground truth, not radar-dependent

            # Get location context
            location_context = self._get_location_context(report)

            # Generate enhanced summary (no verification required)
            enhanced_summary = self._generate_enhanced_summary(
                report, [], duration_minutes, counties_affected, 
                nws_office, location_context, radar_polygon_match
            )

            # Prepare enhanced context data
            enhanced_context = {
                "enhanced_summary": enhanced_summary,
                "spc_report_type": report.report_type,
                "duration_minutes": duration_minutes,
                "counties_affected": list(counties_affected),
                "nws_office": nws_office,
                "radar_polygon_match": radar_polygon_match,
                "location_context": location_context,
                "generation_metadata": {
                    "correlation_id": correlation_id,
                    "generated_at": datetime.utcnow().isoformat(),
                    "version": ENHANCED_CONTEXT_VERSION
                }
            }

            # Use transaction isolation for safe writes
            try:
                with self.db.begin():
                    report.enhanced_context = enhanced_context
                    report.enhanced_context_version = ENHANCED_CONTEXT_VERSION
                    report.enhanced_context_generated_at = datetime.utcnow()
                    
                self.logger.info(f"[{correlation_id}] Successfully enriched report {report_id} with version {ENHANCED_CONTEXT_VERSION}")
                
                return {
                    "success": True,
                    "enhanced_context": enhanced_context,
                    "correlation_id": correlation_id
                }
                
            except Exception as db_error:
                self.db.rollback()
                self.logger.error(f"[{correlation_id}] Database error enriching report {report_id}: {db_error}")
                return {"success": False, "error": f"Database error: {db_error}"}

        except Exception as e:
            self.logger.error(f"[{correlation_id}] Error enriching report {report_id}: {e}")
            return {"success": False, "error": str(e)}

    def generate_enhanced_context_batch(self, limit: int = 50) -> Dict[str, Any]:
        """Generate enhanced context for reports without current version"""
        correlation_id = str(uuid.uuid4())[:8]
        
        try:
            self.logger.info(f"[{correlation_id}] Starting batch enhanced context generation (limit: {limit})")
            
            # Find reports that need enhanced context (ALL reports, not just verified)
            reports_needing_context = self.db.query(SPCReport).filter(
                (SPCReport.enhanced_context_version != ENHANCED_CONTEXT_VERSION) |
                (SPCReport.enhanced_context_version.is_(None))
            ).limit(limit).all()

            if not reports_needing_context:
                self.logger.info(f"[{correlation_id}] No reports need enhanced context generation")
                return {"success": True, "processed": 0, "message": "No reports need processing"}

            enriched_count = 0
            error_count = 0
            errors = []

            for report in reports_needing_context:
                try:
                    result = self.enrich_spc_report(report.id)
                    if result.get('success'):
                        enriched_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Report {report.id}: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    error_count += 1
                    errors.append(f"Report {report.id}: {str(e)}")
                    self.logger.error(f"[{correlation_id}] Error processing report {report.id}: {e}")

            self.logger.info(f"[{correlation_id}] Batch processing complete: {enriched_count} enriched, {error_count} errors")
            
            return {
                "success": True,
                "processed": enriched_count,
                "errors": error_count,
                "error_details": errors[:10],  # Limit error details
                "correlation_id": correlation_id
            }

        except Exception as e:
            self.logger.error(f"[{correlation_id}] Error in batch processing: {e}")
            return {"success": False, "error": str(e)}

    def _find_verified_alerts_for_report(self, report):
        """Find verified alerts that match this SPC report"""
        # This would implement the existing logic for finding matched alerts
        # For now, return empty list - this needs to be implemented based on existing matching logic
        return []

    def _calculate_alert_duration(self, alerts):
        """Calculate duration span of alerts in minutes"""
        if not alerts:
            return 0
        # Implementation needed based on alert structure
        return 60  # Placeholder

    def _get_affected_counties(self, alerts):
        """Get set of counties affected by alerts"""
        counties = set()
        for alert in alerts:
            if hasattr(alert, 'counties') and alert.counties:
                counties.update(alert.counties)
        return counties

    def _get_issuing_office(self, alerts):
        """Get the NWS office that issued the alerts"""
        if alerts and hasattr(alerts[0], 'nws_office'):
            return alerts[0].nws_office
        return "Unknown NWS Office"

    def _get_location_context(self, report):
        """Get location context for the report using Google Places API"""
        try:
            from google_places_service import GooglePlacesService
            
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
            self.logger.error(f"Error getting location context: {e}")
            # Fallback to basic location info
            return {
                "event_location": None,
                "nearest_major_city": None,
                "nearby_places": []
            }


def create_enhanced_context_service(db_session: Session) -> SPCEnhancedContextService:
    """Factory function to create Enhanced Context service"""
    return SPCEnhancedContextService(db_session)