"""
Enhanced Context System for SPC Reports
Implements multi-alert, multi-source enrichment for comprehensive SPC report intelligence
"""

import json
import logging
import math
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from models import SPCReport, Alert


class SPCEnhancedContextService:
    """Service for generating enhanced context for SPC reports"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def _get_hail_damage_category(self, hail_size: float) -> dict:
        """Get hail damage category from NWS lookup table"""
        try:
            from sqlalchemy import text
            result = self.db.execute(text("""
                SELECT category, damage_potential, is_severe, comments 
                FROM nws_hail_damage_lookup 
                WHERE :hail_size >= min_diameter_inches AND :hail_size <= max_diameter_inches
                LIMIT 1
            """), {"hail_size": hail_size}).fetchone()
            
            if result:
                return {
                    "category": result[0],
                    "damage_potential": result[1], 
                    "is_severe": result[2],
                    "comments": result[3]
                }
            else:
                # Fallback for edge cases
                return {
                    "category": "Unknown Hail",
                    "damage_potential": "Unknown",
                    "is_severe": False,
                    "comments": "Hail size outside standard categories"
                }
        except Exception as e:
            import logging
            logging.error(f"Error querying hail damage lookup: {e}")
            return {
                "category": "Small Hail",
                "damage_potential": "Minimal",
                "is_severe": False,
                "comments": "Unable to determine damage category"
            }
    
    def _get_hail_natural_language(self, hail_size: float) -> str:
        """Get natural language equivalent for hail size"""
        hail_size_map = {
            0.25: "pea",
            0.5: "marble", 
            0.75: "penny",
            0.88: "nickel",
            1.0: "quarter",
            1.25: "half dollar",
            1.5: "ping pong ball",
            1.75: "golf ball",
            2.0: "hen egg",
            2.5: "tennis ball",
            2.75: "baseball",
            3.0: "softball",
            4.0: "grapefruit"
        }
        
        closest_size = min(hail_size_map.keys(), key=lambda x: abs(x - hail_size))
        if abs(closest_size - hail_size) <= 0.25:
            return f" ({hail_size_map[closest_size]} size)"
        return ""

    def _get_wind_damage_category(self, wind_speed: float) -> dict:
        """Get wind damage category from NWS lookup table"""
        try:
            from sqlalchemy import text
            result = self.db.execute(text("""
                SELECT category, damage_potential, is_severe, comments 
                FROM nws_wind_damage_lookup 
                WHERE :wind_speed >= min_wind_speed_mph AND :wind_speed <= max_wind_speed_mph
                LIMIT 1
            """), {"wind_speed": wind_speed}).fetchone()
            
            if result:
                return {
                    "category": result[0],
                    "damage_potential": result[1],
                    "is_severe": result[2], 
                    "comments": result[3]
                }
            else:
                # Fallback for edge cases
                return {
                    "category": "Unknown Wind",
                    "damage_potential": "Unknown",
                    "is_severe": False,
                    "comments": "Wind speed outside standard categories"
                }
        except Exception as e:
            import logging
            logging.error(f"Error querying wind damage lookup: {e}")
            return {
                "category": "Light Wind",
                "damage_potential": "Minimal",
                "is_severe": False,
                "comments": "Unable to determine damage category"
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
            # Get the SPC report
            report = self.db.query(SPCReport).filter(SPCReport.id == report_id).first()
            if not report:
                return {"error": f"SPC report {report_id} not found"}
            
            # Get verified alerts for this report
            verified_alerts = self._get_verified_alerts_for_report(report_id)
            
            # Get location context from existing enrichment data
            location_context = self._get_location_context(report)
            if not location_context:
                location_context = self._generate_location_context(report)
            
            # Build enhanced context
            enhanced_context = self._build_enhanced_context(report, verified_alerts)
            enhanced_context['location_context'] = location_context
            
            # Generate enhanced summary
            if verified_alerts:
                # Calculate duration and counties affected
                start_times = [alert.effective for alert in verified_alerts if alert.effective]
                end_times = [alert.expires for alert in verified_alerts if alert.expires]
                
                if start_times and end_times:
                    duration_minutes = int((max(end_times) - min(start_times)).total_seconds() / 60)
                else:
                    duration_minutes = 0
                
                counties_affected = set()
                nws_office = ""
                for alert in verified_alerts:
                    if hasattr(alert, 'area_desc') and alert.area_desc:
                        counties_affected.add(alert.area_desc)
                    if hasattr(alert, 'sender_name') and alert.sender_name and not nws_office:
                        nws_office = alert.sender_name
                
                radar_polygon_match = any(
                    hasattr(alert, 'radar_indicated') and alert.radar_indicated 
                    for alert in verified_alerts
                )
            else:
                duration_minutes = 0
                counties_affected = set()
                nws_office = ""
                radar_polygon_match = False
            
            # Generate AI summary
            enhanced_summary = self._generate_enhanced_summary(
                report, verified_alerts, duration_minutes, counties_affected, 
                nws_office, location_context, radar_polygon_match
            )
            
            enhanced_context['enhanced_summary'] = enhanced_summary
            
            return {
                "report_id": report_id,
                "enhanced_context": enhanced_context,
                "success": True
            }
            
        except Exception as e:
            logging.error(f"Error enriching SPC report {report_id}: {e}")
            return {
                "report_id": report_id,
                "error": str(e),
                "success": False
            }

    def _get_verified_alerts_for_report(self, report_id: int) -> List:
        """Get all verified alerts that match a specific SPC report"""
        # The system uses spc_reports field in Alert model for verified matches
        alerts = self.db.query(Alert).filter(
            Alert.spc_verified == True
        ).all()
        
        # Filter alerts that contain this report_id in their spc_reports
        matching_alerts = []
        for alert in alerts:
            if alert.spc_reports:
                for report in alert.spc_reports:
                    if isinstance(report, dict) and report.get('id') == report_id:
                        matching_alerts.append(alert)
                        break
        
        return matching_alerts

    def _build_enhanced_context(self, report, verified_alerts: List) -> Dict[str, Any]:
        """Build the enhanced context structure"""
        # Generate polygon match status for each verified alert
        polygon_matches = self._generate_polygon_match_status(verified_alerts, report)
        
        return {
            "alert_count": len(verified_alerts),
            "has_verified_alerts": len(verified_alerts) > 0,
            "generated_at": datetime.utcnow().isoformat(),
            "radar_polygon_match": any(
                hasattr(alert, 'radar_indicated') and alert.radar_indicated 
                for alert in verified_alerts
            ) if verified_alerts else False,
            "polygon_matches": polygon_matches
        }

    def _extract_nws_office(self, verified_alerts: List) -> str:
        """Extract NWS office information from alerts"""
        for alert in verified_alerts:
            if hasattr(alert, 'sender_name') and alert.sender_name:
                return alert.sender_name
        return "NWS"

    def _generate_enhanced_summary(self, report, verified_alerts: List, 
                                 duration_minutes: int, counties_affected: set, nws_office: str,
                                 location_context: Dict[str, Any], radar_polygon_match: bool) -> str:
        """Generate AI-powered enhanced summary with conditional logic for verified/unverified reports"""
        try:
            from openai import OpenAI
            import os
            
            openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
            
            # Prepare AI generation context data
            nearby_context = ""
            if location_context.get('nearby_places'):
                places = [place['name'] for place in location_context['nearby_places'][:3]]
                nearby_context = ", ".join(places)
            
            # Extract major city data from nearby places
            major_city = "Unknown"
            major_city_distance = "Unknown distance"
            major_city_lat = None
            major_city_lon = None
            
            if location_context.get('nearby_places'):
                for place in location_context['nearby_places']:
                    if place.get('type') == 'nearest_city':
                        major_city = place.get('name', 'Unknown')
                        major_city_distance = f"{place.get('distance_miles', 0):.1f} miles"
                        
                        # Get coordinates from enrichment data
                        if hasattr(report, 'spc_enrichment') and report.spc_enrichment:
                            try:
                                if isinstance(report.spc_enrichment, str):
                                    enrichment = json.loads(report.spc_enrichment)
                                else:
                                    enrichment = report.spc_enrichment
                                
                                if 'nearest_major_city' in enrichment:
                                    major_city_lat = enrichment['nearest_major_city'].get('lat')
                                    major_city_lon = enrichment['nearest_major_city'].get('lon')
                            except (json.JSONDecodeError, TypeError, AttributeError):
                                pass
                        break
            
            # Extract magnitude based on report type
            if report.report_type.upper() == "HAIL" and report.magnitude:
                try:
                    if isinstance(report.magnitude, str):
                        mag_data = json.loads(report.magnitude)
                        hail_size = mag_data.get('size_inches', 0)
                    else:
                        hail_size = float(report.magnitude)
                    wind_speed = 0
                except (json.JSONDecodeError, ValueError, TypeError):
                    hail_size = 0
                    wind_speed = 0
            elif report.report_type.upper() == "WIND" and report.magnitude:
                try:
                    if isinstance(report.magnitude, str):
                        mag_data = json.loads(report.magnitude)
                        wind_speed = mag_data.get('speed', 0)
                    else:
                        wind_speed = int(report.magnitude)
                    hail_size = 0
                except (json.JSONDecodeError, ValueError, TypeError):
                    hail_size = 0
                    wind_speed = 0
            else:
                hail_size = 0
                wind_speed = 0
            
            # Get NWS damage categories from lookup tables
            if report.report_type.upper() == "HAIL" and hail_size > 0:
                damage_info = self._get_hail_damage_category(hail_size)
            elif report.report_type.upper() == "WIND" and wind_speed > 0:
                damage_info = self._get_wind_damage_category(wind_speed)
            else:
                # Never show "Unknown" to end users - use proper NWS classifications
                if report.report_type.upper() == "HAIL":
                    damage_info = {
                        "category": "Small Hail", 
                        "damage_potential": "minimal damage",
                        "is_severe": False,
                        "comments": "Non-severe hail with potential for minor property damage."
                    }
                elif report.report_type.upper() == "WIND":
                    damage_info = {
                        "category": "Strong Wind", 
                        "damage_potential": "minor to moderate damage",
                        "is_severe": False,
                        "comments": "Strong winds with potential for tree and property damage."
                    }
                else:
                    damage_info = {
                        "category": "Severe Weather Event",
                        "damage_potential": "weather-related damage",
                        "is_severe": False,
                        "comments": "Severe weather event with potential for localized damage."
                    }

            # Generate AI potential damage assessment based on NWS threat levels
            damage_statement = ""  # Will be generated by AI based on threat classification

            # Calculate direction from event to major city using actual coordinates
            direction = "north-northeast"  # Default fallback
            if (hasattr(report, 'latitude') and hasattr(report, 'longitude') and 
                report.latitude and report.longitude and major_city_lat and major_city_lon):
                try:
                    direction = self._calculate_direction(
                        float(report.latitude), float(report.longitude),
                        float(major_city_lat), float(major_city_lon)
                    )
                except (ValueError, AttributeError, TypeError):
                    direction = "north-northeast"

            # Get time components - convert from SPC format (HHMM) to proper time
            try:
                if hasattr(report, 'time_utc') and report.time_utc:
                    if isinstance(report.time_utc, str) and len(report.time_utc) == 4:
                        # Convert HHMM format to proper time
                        hour = int(report.time_utc[:2])
                        minute = int(report.time_utc[2:])
                        time_str = f"{hour:02d}:{minute:02d} (UTC)"
                    else:
                        time_str = str(report.time_utc)
                else:
                    time_str = "unknown time"
                    
                # Get date from report_date field if available
                if hasattr(report, 'report_date') and report.report_date:
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

            # Build proper magnitude display - never show "Unknown" to end users
            if report.report_type.upper() == "HAIL":
                if hail_size > 0:
                    magnitude_display = f"{hail_size:.2f} inch".replace('.00', '')
                else:
                    # Fallback to extracting from any available magnitude data
                    magnitude_display = "0.75 inch"  # Default severe hail threshold
            elif report.report_type.upper() == "WIND":
                if wind_speed > 0:
                    magnitude_display = f"{wind_speed} mph"
                else:
                    magnitude_display = "58 mph"  # Default severe wind threshold
            else:
                magnitude_display = str(report.magnitude) if report.magnitude else 'severe weather'

            # Build proper nearby places from location context first
            nearby_places_sorted = []
            if location_context.get('nearby_places'):
                nearby_places_sorted = sorted(location_context['nearby_places'], 
                                            key=lambda x: x['distance_miles'])[:3]
            
            other_nearby = ""
            if len(nearby_places_sorted) > 1:
                other_nearby = "Other nearby locations include " + ", ".join([
                    f"{place['name']} ({place['distance_miles']:.1f}mi)" 
                    for place in nearby_places_sorted[1:]
                ]) + "."

            # Generate prompt using exact template format required
            prompt = f"""Generate a professional meteorological summary using this EXACT template format:

REQUIRED TEMPLATE:
"{magnitude_display} {report.report_type.lower()} was reported {major_city_distance} {direction} of {major_city} ({report.location}), in {report.county} County, {report.state} at {time_str} on {date_str}. This event is classified as {damage_info['category']} with {damage_info['damage_potential']} potential. {damage_info['comments']} {other_nearby}"

DATA TO USE:
- Magnitude: {magnitude_display}
- Event Type: {report.report_type.lower()}
- Distance/Direction: {major_city_distance} {direction} of {major_city}
- SPC Location: {report.location}
- County/State: {report.county} County, {report.state}
- Time/Date: {time_str} on {date_str}
- NWS Category: {damage_info['category']}
- Damage Potential: {damage_info['damage_potential']}
- NWS Comments: {damage_info['comments']}
- Nearby Places: {other_nearby}

REQUIREMENTS:
1. Use the EXACT template format above
2. Fill in each data field exactly as provided
3. Keep the professional meteorological language
4. Do not add extra text or modify the structure"""

            # Build template using your exact format: magnitude + event type + distance/direction + SPC location + county/state + time/date
            template_summary = f"{magnitude_display} {report.report_type.lower()} was reported {major_city_distance} {direction} of {major_city} ({report.location}), in {report.county} County, {report.state} at {time_str} on {date_str}. {other_nearby}"

            # Use OpenAI to polish the template with proper NWS terminology
            response = openai_client.chat.completions.create(
                model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024. do not change this unless explicitly requested by the user
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Generate the enhanced summary using this template: {template_summary}"}
                ],
                max_tokens=300,
                temperature=0.1
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            import logging
            logging.error(f"Error generating AI summary: {e}")
            
            # Fallback with proper formatting without AI
            magnitude_display = report.magnitude if report.magnitude else 'Unknown magnitude'
            return f"This {report.report_type.lower()} report in {report.county} County, {report.state} was validated by {len(verified_alerts)} NWS alerts spanning {duration_minutes} minutes across {len(counties_affected)} counties."

    def _get_location_context(self, report) -> Dict[str, Any]:
        """Get location context from existing enrichment data"""
        # First check spc_enrichment field (new Google Places data)
        if hasattr(report, 'spc_enrichment') and report.spc_enrichment:
            try:
                if isinstance(report.spc_enrichment, str):
                    enrichment = json.loads(report.spc_enrichment)
                else:
                    enrichment = report.spc_enrichment
                
                # Transform Google Places data to location context format
                location_context = {}
                
                if 'nearby_places' in enrichment:
                    location_context['nearby_places'] = []
                    for place in enrichment['nearby_places']:
                        location_context['nearby_places'].append({
                            'name': place.get('name', ''),
                            'distance_miles': place.get('distance_miles', 0),
                            'type': place.get('type', 'unknown')
                        })
                
                if 'primary_location' in enrichment:
                    location_context['primary_location'] = enrichment['primary_location'].get('name', '')
                
                if 'nearest_major_city' in enrichment:
                    location_context['nearest_major_city'] = enrichment['nearest_major_city'].get('name', '')
                    location_context['major_city_distance'] = f"{enrichment['nearest_major_city'].get('distance_miles', 0):.1f} miles"
                
                return location_context
            except (json.JSONDecodeError, TypeError, AttributeError):
                pass
        
        # Fallback to legacy enrichment_data field
        if hasattr(report, 'enrichment_data') and report.enrichment_data:
            try:
                if isinstance(report.enrichment_data, str):
                    enrichment = json.loads(report.enrichment_data)
                else:
                    enrichment = report.enrichment_data
                
                if 'location_context' in enrichment:
                    return enrichment['location_context']
            except (json.JSONDecodeError, TypeError):
                pass
        
        return {}

    def _generate_location_context(self, report) -> Dict[str, Any]:
        """Generate location context using AI"""
        # This would use Google Places API or similar to get nearby places
        # For now, return a basic context
        return {
            "primary_location": f"{report.location}, {report.county} County, {report.state}",
            "nearest_major_city": "Mason City",  # Example - would be calculated
            "major_city_distance": "26.1 miles",
            "nearby_places": [
                {"name": "Chapman", "distance_miles": 0.9},
                {"name": "Oakland Valley", "distance_miles": 1.2},
                {"name": "Beed's Lake State Park", "distance_miles": 2.3},
                {"name": "Hampton", "distance_miles": 8.2},
                {"name": "Mason City", "distance_miles": 26.1}
            ],
            "radar_polygon_match": False
        }

    def _generate_polygon_match_status(self, verified_alerts: List, report) -> List[Dict[str, Any]]:
        """Generate polygon match status for each verified alert"""
        polygon_matches = []
        
        for alert in verified_alerts:
            radar_confirmed = self._check_radar_confirmation(alert, report)
            match_data = {
                "alert_id": alert.id,
                "headline": getattr(alert, 'headline', 'Unknown'),
                "radar_confirmed": radar_confirmed,
                "status": "Radar Confirmed" if radar_confirmed else "Temporally Matched"
            }
            polygon_matches.append(match_data)
        
        return polygon_matches

    def _check_radar_confirmation(self, alert, report) -> bool:
        """Check if alert has radar confirmation from polygon match status"""
        if hasattr(alert, 'radar_indicated') and alert.radar_indicated:
            return True
        return False

    def _calculate_direction(self, lat1: float, lon1: float, lat2: float, lon2: float) -> str:
        """Calculate cardinal direction from point 1 to point 2"""
        # Calculate bearing
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlon_rad = math.radians(lon2 - lon1)
        
        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon_rad)
        
        bearing = math.atan2(y, x)
        bearing_deg = math.degrees(bearing)
        bearing_deg = (bearing_deg + 360) % 360
        
        # Convert to cardinal direction
        directions = [
            "north", "north-northeast", "northeast", "east-northeast",
            "east", "east-southeast", "southeast", "south-southeast", 
            "south", "south-southwest", "southwest", "west-southwest",
            "west", "west-northwest", "northwest", "north-northwest"
        ]
        
        index = round(bearing_deg / 22.5) % 16
        return directions[index]

    def enrich_all_reports(self, batch_size: int = 50, unenriched_only: bool = True) -> Dict[str, int]:
        """Enrich ALL SPC reports with enhanced context (verified and unverified)"""
        try:
            # Get reports to enrich
            query = self.db.query(SPCReport)
            
            if unenriched_only:
                # Only enrich reports without enhanced context
                query = query.filter(
                    SPCReport.enhanced_context.is_(None)
                )
            
            reports = query.limit(batch_size).all()
            
            enriched_count = 0
            error_count = 0
            
            for report in reports:
                try:
                    result = self.enrich_spc_report(report.id)
                    if result.get('success'):
                        # Store enhanced context in the report
                        report.enhanced_context = result['enhanced_context']
                        self.db.commit()
                        enriched_count += 1
                    else:
                        error_count += 1
                        logging.error(f"Failed to enrich report {report.id}: {result.get('error')}")
                        
                except Exception as e:
                    error_count += 1
                    logging.error(f"Error enriching report {report.id}: {e}")
                    self.db.rollback()
            
            return {
                "enriched": enriched_count,
                "errors": error_count,
                "total_processed": len(reports)
            }
            
        except Exception as e:
            logging.error(f"Error in batch enrichment: {e}")
            return {"enriched": 0, "errors": 0, "total_processed": 0}


def enrich_spc_report_context(report_id: int) -> Dict[str, Any]:
    """Standalone function to enrich a single SPC report"""
    from app import db
    
    service = SPCEnhancedContextService(db.session)
    return service.enrich_spc_report(report_id)


def enrich_all_spc_reports() -> Dict[str, int]:
    """Standalone function to enrich all SPC reports"""
    from app import db
    
    service = SPCEnhancedContextService(db.session)
    return service.enrich_all_reports()