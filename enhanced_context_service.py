"""
Enhanced Context Service for HailyDB v2.0
Handles SPC report enrichment with comprehensive location context and AI-powered summaries
Separated from app.py for better code organization and maintainability
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from google_places_service import GooglePlacesService

logger = logging.getLogger(__name__)

class EnhancedContextService:
    """
    Service class for generating Enhanced Context summaries for SPC reports
    Provides comprehensive location enrichment with 6 geo data points
    """
    
    def __init__(self):
        self.places_service = GooglePlacesService()
    
    def generate_enhanced_context(self, report, db_session: Session) -> Dict[str, Any]:
        """
        Generate comprehensive Enhanced Context for an SPC report
        
        Args:
            report: SPCReport database object
            db_session: Database session for transactions
            
        Returns:
            Dictionary containing enhanced context data
        """
        try:
            # Extract magnitude value from JSON with UNK handling
            magnitude_value = self._extract_magnitude(report)
            
            # Get Google Places location context
            location_context = self.places_service.enrich_location(
                lat=float(report.latitude) if report.latitude else 0,
                lon=float(report.longitude) if report.longitude else 0
            )
            
            # Build comprehensive location context with 6 geo data points
            location_data = self._build_location_context(report, location_context)
            
            # Get damage probability assessment
            damage_probability = self._assess_damage_probability(report, magnitude_value)
            
            # Check for verified NWS warnings during report time
            verified_warnings = self._check_verified_warnings(report, db_session)
            
            # Generate comprehensive Enhanced Context summary
            enhanced_summary = self._generate_summary(
                report, magnitude_value, location_data, damage_probability, verified_warnings
            )
            
            # Store enhanced context in the database
            enhanced_context = {
                "enhanced_summary": enhanced_summary,
                "location_context": location_context,
                "generated_at": datetime.utcnow().isoformat(),
                "version": "v2.0"
            }
            
            # Save to database with proper transaction handling
            report.enhanced_context = enhanced_context
            report.enhanced_context_version = "v2.0"
            report.enhanced_context_generated_at = datetime.utcnow()
            db_session.commit()
            
            logger.info(f"Enhanced context generated for report {report.id}")
            
            return {
                "success": True,
                "report_id": report.id,
                "enhanced_context": enhanced_context,
                "message": "Enhanced context generated successfully",
                "version": "v2.0"
            }
            
        except Exception as e:
            logger.error(f"Error generating enhanced context for report {report.id}: {str(e)}")
            db_session.rollback()
            raise e
    
    def _extract_magnitude(self, report) -> Optional[float]:
        """Extract and validate magnitude value from report data"""
        magnitude_value = None
        
        if report.magnitude:
            if isinstance(report.magnitude, dict):
                if report.report_type.upper() == "WIND" and 'speed' in report.magnitude:
                    magnitude_value = report.magnitude['speed']
                elif report.report_type.upper() == "HAIL" and 'size_inches' in report.magnitude:
                    magnitude_value = report.magnitude['size_inches']
            else:
                magnitude_value = report.magnitude
        
        # Filter out UNK values
        if magnitude_value and str(magnitude_value).upper() == 'UNK':
            magnitude_value = None
            
        return magnitude_value
    
    def _build_location_context(self, report, location_context: Dict) -> Dict[str, Any]:
        """Build comprehensive location context with directional data"""
        location_data = {
            'event_location': None,
            'event_distance': None,
            'event_direction': "",
            'nearest_major_city': None,
            'major_city_distance': None,
            'major_city_direction': "",
            'nearby_places_text': ""
        }
        
        if not location_context or not location_context.get('nearby_places'):
            return location_data
            
        nearby_places = location_context['nearby_places']
        
        # Extract event location (primary_location)
        for place in nearby_places:
            if place.get('type') == 'primary_location':
                location_data['event_location'] = place.get('name')
                location_data['event_distance'] = place.get('distance_miles')
                
                # Calculate direction FROM event coordinates TO the location
                if (report.latitude and report.longitude and 
                    place.get('approx_lat') and place.get('approx_lon')):
                    location_data['event_direction'] = self._calculate_direction(
                        float(report.latitude), float(report.longitude),
                        float(place['approx_lat']), float(place['approx_lon'])
                    )
                break
        
        # Extract nearest major city with direction
        for place in nearby_places:
            if place.get('type') == 'nearest_city':
                location_data['nearest_major_city'] = place.get('name')
                location_data['major_city_distance'] = place.get('distance_miles')
                
                # Calculate direction FROM event coordinates TO major city
                if (report.latitude and report.longitude and 
                    place.get('approx_lat') and place.get('approx_lon')):
                    location_data['major_city_direction'] = self._calculate_direction(
                        float(report.latitude), float(report.longitude),
                        float(place['approx_lat']), float(place['approx_lon'])
                    )
                break
        
        # Build nearby places text (closest 2-3 places)
        nearby_place_items = []
        for place in nearby_places:
            if place.get('type') == 'nearby_place' and len(nearby_place_items) < 3:
                name = place.get('name')
                distance = place.get('distance_miles')
                if name and distance:
                    nearby_place_items.append(f"{name} ({distance:.1f} mi)")
        
        if nearby_place_items:
            location_data['nearby_places_text'] = f". Nearby places include {', '.join(nearby_place_items)}"
            
        return location_data
    
    def _calculate_direction(self, from_lat: float, from_lon: float, 
                           to_lat: float, to_lon: float) -> str:
        """Calculate cardinal direction from one point to another"""
        lat_diff = from_lat - to_lat
        lon_diff = from_lon - to_lon
        
        if abs(lat_diff) > abs(lon_diff):
            return "north" if lat_diff > 0 else "south"
        else:
            return "east" if lon_diff > 0 else "west"
    
    def _generate_summary(self, report, magnitude_value: Optional[float], 
                         location_data: Dict[str, Any], damage_probability: Dict[str, Any],
                         verified_warnings: List[Dict[str, Any]]) -> str:
        """Generate comprehensive Enhanced Context summary with 6 geo data points"""
        enhanced_summary = f"On {report.report_date}, a {report.report_type.lower()} event occurred"
        
        # Add magnitude information
        if magnitude_value:
            try:
                mag_val = float(magnitude_value)
                if report.report_type.upper() == "HAIL":
                    enhanced_summary += f" with {mag_val:.2f}\" hail"
                elif report.report_type.upper() == "WIND":
                    enhanced_summary += f" with {int(mag_val)} mph winds"
            except (ValueError, TypeError):
                pass
        
        # Build comprehensive location context using the 6 geo data points
        location_text = f" at {report.location}"
        
        if location_data['event_location'] and location_data['event_distance']:
            if location_data['event_direction']:
                location_text += f", located {location_data['event_direction']} {location_data['event_distance']:.1f} miles from {location_data['event_location']}"
            else:
                location_text += f", located {location_data['event_distance']:.1f} miles from {location_data['event_location']}"
        
        if location_data['nearest_major_city'] and location_data['major_city_distance']:
            if location_data['major_city_direction']:
                location_text += f", or {location_data['major_city_direction']} {location_data['major_city_distance']:.1f} miles from {location_data['nearest_major_city']}"
            else:
                location_text += f", or {location_data['major_city_distance']:.1f} miles from {location_data['nearest_major_city']}"
        
        enhanced_summary += location_text + location_data['nearby_places_text'] + "."
        
        # Add SPC Comments if available
        if hasattr(report, 'comments') and report.comments and report.comments.strip():
            enhanced_summary += f" SPC Notes: {report.comments.strip()}"
        
        # Add damage probability assessment
        if damage_probability and damage_probability.get('assessment'):
            enhanced_summary += f" {damage_probability['assessment']}"
        
        # Add verified warnings information
        if verified_warnings:
            warning_text = f" Verified Reports: {len(verified_warnings)} active NWS warning(s) during this event"
            enhanced_summary += warning_text
        
        return enhanced_summary
    
    def _assess_damage_probability(self, report, magnitude_value: Optional[float]) -> Dict[str, Any]:
        """
        Assess damage probability based on NWS damage classification tables
        Returns professional damage assessment based on magnitude
        """
        if not magnitude_value:
            return {}
        
        try:
            mag_val = float(magnitude_value)
            
            if report.report_type.upper() == "HAIL":
                return self._assess_hail_damage(mag_val)
            elif report.report_type.upper() == "WIND":
                return self._assess_wind_damage(mag_val)
        except (ValueError, TypeError):
            pass
        
        return {}
    
    def _assess_hail_damage(self, size_inches: float) -> Dict[str, Any]:
        """Assess hail damage probability based on NWS damage classification"""
        # NWS Hail Damage Classification Table
        if size_inches >= 4.5:  # Grapefruit+
            return {
                "assessment": "Damage Potential: Severe structural damage likely to roofs, vehicles, and crops. Major property damage expected.",
                "category": "Severe",
                "probability": "High"
            }
        elif size_inches >= 2.75:  # Baseball+
            return {
                "assessment": "Damage Potential: Significant damage likely to roofs, vehicles, and agriculture. Extensive property damage probable.",
                "category": "Significant",
                "probability": "High"
            }
        elif size_inches >= 1.75:  # Golf Ball+
            return {
                "assessment": "Damage Potential: Moderate to severe damage expected to vehicles, roofs, and crops. Property damage likely.",
                "category": "Moderate-Severe",
                "probability": "Moderate-High"
            }
        elif size_inches >= 1.0:  # Quarter+
            return {
                "assessment": "Damage Potential: Minor to moderate damage possible to vehicles and crops. Some property damage expected.",
                "category": "Minor-Moderate",
                "probability": "Moderate"
            }
        elif size_inches >= 0.75:  # Penny+
            return {
                "assessment": "Damage Potential: Minor damage possible to crops and sensitive surfaces. Vehicle dents possible.",
                "category": "Minor",
                "probability": "Low-Moderate"
            }
        else:  # Smaller hail
            return {
                "assessment": "Damage Potential: Minimal damage expected. Possible minor crop or garden damage.",
                "category": "Minimal",
                "probability": "Low"
            }
    
    def _assess_wind_damage(self, speed_mph: float) -> Dict[str, Any]:
        """Assess wind damage probability based on Enhanced Fujita Scale"""
        # Enhanced Fujita Scale Wind Damage Classification
        if speed_mph >= 200:  # EF5
            return {
                "assessment": "Damage Potential: Catastrophic destruction. Well-built structures leveled, automobiles thrown significant distances.",
                "category": "Catastrophic",
                "probability": "Extreme"
            }
        elif speed_mph >= 166:  # EF4
            return {
                "assessment": "Damage Potential: Devastating structural damage. Well-constructed homes severely damaged or destroyed.",
                "category": "Devastating",
                "probability": "Extreme"
            }
        elif speed_mph >= 136:  # EF3
            return {
                "assessment": "Damage Potential: Severe structural damage. Roofs and walls torn from well-constructed buildings.",
                "category": "Severe",
                "probability": "High"
            }
        elif speed_mph >= 111:  # EF2
            return {
                "assessment": "Damage Potential: Considerable structural damage. Mobile homes destroyed, large trees snapped.",
                "category": "Considerable",
                "probability": "High"
            }
        elif speed_mph >= 86:  # EF1
            return {
                "assessment": "Damage Potential: Moderate structural damage. Roof damage, mobile homes overturned, trees uprooted.",
                "category": "Moderate",
                "probability": "Moderate-High"
            }
        elif speed_mph >= 65:  # EF0
            return {
                "assessment": "Damage Potential: Light structural damage. Peeling roof surfaces, broken branches, shallow-rooted trees pushed over.",
                "category": "Light",
                "probability": "Moderate"
            }
        elif speed_mph >= 58:  # Severe threshold
            return {
                "assessment": "Damage Potential: Minor structural damage. Tree limbs broken, loose outdoor objects become projectiles.",
                "category": "Minor",
                "probability": "Low-Moderate"
            }
        else:
            return {
                "assessment": "Damage Potential: Minimal damage expected. Possible minor debris movement.",
                "category": "Minimal",
                "probability": "Low"
            }
    
    def _check_verified_warnings(self, report, db_session: Session) -> List[Dict[str, Any]]:
        """
        Check for active NWS warnings during the report time
        Returns list of concurrent NWS warnings for verification
        """
        try:
            # Import here to avoid circular import
            from models import Alert
            from datetime import datetime, timedelta
            
            # Convert report date and time to datetime object
            report_datetime = self._parse_report_datetime(report)
            if not report_datetime:
                return []
            
            # Search for alerts within ±30 minutes of the report time
            time_window_start = report_datetime - timedelta(minutes=30)
            time_window_end = report_datetime + timedelta(minutes=30)
            
            # Query for severe weather warnings in the same area during the time window
            warnings = db_session.query(Alert).filter(
                Alert.sent >= time_window_start,
                Alert.sent <= time_window_end,
                Alert.event.in_([
                    'Severe Thunderstorm Warning',
                    'Tornado Warning',
                    'Severe Weather Statement'
                ])
            ).all()
            
            # Filter warnings that overlap with report location
            verified_warnings = []
            for warning in warnings:
                if self._check_location_overlap(report, warning):
                    verified_warnings.append({
                        'id': warning.id,
                        'event': warning.event,
                        'sent': warning.sent.isoformat(),
                        'headline': warning.headline or '',
                        'description': warning.description[:100] + '...' if warning.description and len(warning.description) > 100 else warning.description
                    })
            
            return verified_warnings[:3]  # Limit to 3 most relevant warnings
            
        except Exception as e:
            logger.warning(f"Error checking verified warnings for report {report.id}: {str(e)}")
            return []
    
    def _parse_report_datetime(self, report) -> Optional[datetime]:
        """Parse SPC report date and time into datetime object"""
        try:
            # SPC reports have date and time fields
            report_date = report.report_date
            report_time = report.report_time if hasattr(report, 'report_time') and report.report_time else "1200"
            
            # Parse date (YYYY-MM-DD format)
            if isinstance(report_date, str):
                date_obj = datetime.strptime(report_date, '%Y-%m-%d').date()
            else:
                date_obj = report_date
            
            # Parse time (HHMM format)
            if isinstance(report_time, str) and len(report_time) >= 4:
                hour = int(report_time[:2])
                minute = int(report_time[2:4])
            else:
                hour = 12  # Default to noon if time is missing
                minute = 0
            
            return datetime.combine(date_obj, datetime.min.time().replace(hour=hour, minute=minute))
            
        except Exception as e:
            logger.warning(f"Error parsing report datetime: {str(e)}")
            return None
    
    def _check_location_overlap(self, report, warning) -> bool:
        """Check if report location overlaps with warning area"""
        try:
            # Simple distance-based check for now
            if not (report.latitude and report.longitude and warning.latitude and warning.longitude):
                return False
            
            # Calculate distance between report and warning center
            from geopy.distance import geodesic
            report_point = (float(report.latitude), float(report.longitude))
            warning_point = (float(warning.latitude), float(warning.longitude))
            
            distance_miles = geodesic(report_point, warning_point).miles
            
            # Consider overlap if within 25 miles
            return distance_miles <= 25.0
            
        except Exception as e:
            logger.warning(f"Error checking location overlap: {str(e)}")
            return False
    
    def bulk_generate_enhanced_context(self, report_ids: List[int], 
                                     db_session: Session) -> Dict[str, Any]:
        """
        Generate Enhanced Context for multiple reports in batch
        
        Args:
            report_ids: List of SPC report IDs to process
            db_session: Database session
            
        Returns:
            Dictionary with batch processing results
        """
        from models import SPCReport
        
        results = {
            'total_processed': 0,
            'successful_enrichments': 0,
            'failed_enrichments': 0,
            'start_time': datetime.utcnow().isoformat(),
            'errors': []
        }
        
        for report_id in report_ids:
            try:
                report = db_session.get(SPCReport, report_id)
                if not report:
                    results['failed_enrichments'] += 1
                    results['errors'].append(f"Report {report_id} not found")
                    continue
                
                self.generate_enhanced_context(report, db_session)
                results['successful_enrichments'] += 1
                
            except Exception as e:
                results['failed_enrichments'] += 1
                results['errors'].append(f"Report {report_id}: {str(e)}")
                logger.error(f"Failed to generate enhanced context for report {report_id}: {e}")
            
            results['total_processed'] += 1
        
        results['end_time'] = datetime.utcnow().isoformat()
        
        logger.info(f"Batch Enhanced Context generation complete: {results['successful_enrichments']}/{results['total_processed']} successful")
        
        return results

# Global service instance
enhanced_context_service = EnhancedContextService()