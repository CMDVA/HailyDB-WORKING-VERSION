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
            
            # Generate comprehensive Enhanced Context summary
            enhanced_summary = self._generate_summary(
                report, magnitude_value, location_data
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
                         location_data: Dict[str, Any]) -> str:
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
        
        return enhanced_summary
    
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