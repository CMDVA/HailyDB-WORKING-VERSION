"""
Enhanced Context Service for SPC Report Enrichment
Extracts Enhanced Context generation from monolithic app.py
Implements 6 geo data points format with Google Places integration
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from google_places_service import GooglePlacesService
from utils.config_utils import HailSizeConfig

logger = logging.getLogger(__name__)

class EnhancedContextService:
    """
    Service for generating Enhanced Context summaries for SPC reports
    Implements the 6 geo data points format with Google Places enrichment
    """
    
    def __init__(self):
        self.google_places = GooglePlacesService()
    
    def generate_enhanced_context(self, report) -> Dict[str, Any]:
        """
        Generate Enhanced Context with 6 geo data points format
        
        Args:
            report: SPCReport database object
            
        Returns:
            Dictionary containing enhanced context data
        """
        try:
            # Extract magnitude value
            magnitude_value = report.magnitude
            
            # Handle magnitude display based on report type
            if report.report_type.upper() == "HAIL":
                magnitude_display = self._format_hail_magnitude(magnitude_value)
            elif report.report_type.upper() == "WIND":
                magnitude_display = self._format_wind_magnitude(magnitude_value)
            else:
                magnitude_display = str(magnitude_value) if magnitude_value and str(magnitude_value).upper() != 'UNK' else "unknown magnitude"
            
            # Get Google Places location context
            location_context = self.google_places.enrich_location(
                lat=float(report.latitude) if report.latitude else 0,
                lon=float(report.longitude) if report.longitude else 0
            )
            
            # Build 6 geo data points
            geo_data = self._extract_geo_data_points(report, location_context)
            
            # Generate Enhanced Context summary
            enhanced_summary = self._generate_summary(report, magnitude_display, geo_data)
            
            return {
                "enhanced_summary": enhanced_summary,
                "location_context": location_context,
                "generated_at": datetime.utcnow().isoformat(),
                "version": "v3.0"
            }
            
        except Exception as e:
            logger.exception(f"Error generating enhanced context for report {report.id}: {e}")
            raise
    
    def _format_hail_magnitude(self, magnitude_value) -> str:
        """Format hail magnitude with display name"""
        try:
            numeric_magnitude = float(magnitude_value) if magnitude_value else 0
            if numeric_magnitude > 0:
                display_name = HailSizeConfig.get_hail_display_name(numeric_magnitude)
                return f"{display_name} ({numeric_magnitude} inches)"
            else:
                return "unknown size"
        except (ValueError, TypeError):
            return "unknown size"
    
    def _format_wind_magnitude(self, magnitude_value) -> str:
        """Format wind magnitude"""
        try:
            numeric_magnitude = float(magnitude_value) if magnitude_value else 0
            if numeric_magnitude > 0:
                return f"{int(numeric_magnitude)} mph"
            else:
                return "unknown speed"
        except (ValueError, TypeError):
            return "unknown speed"
    
    def _extract_geo_data_points(self, report, location_context) -> Dict[str, Any]:
        """
        Extract 6 geo data points from location context
        
        Returns:
            Dictionary with event_location, event_distance, event_direction,
            nearest_major_city, major_city_distance, major_city_direction, nearby_places_text
        """
        geo_data = {
            "event_location": None,
            "event_distance": None,
            "event_direction": "",
            "nearest_major_city": None,
            "major_city_distance": None,
            "major_city_direction": "",
            "nearby_places_text": ""
        }
        
        if not location_context or not location_context.get('nearby_places'):
            return geo_data
        
        nearby_places = location_context['nearby_places']
        
        # Extract event location (primary_location)
        for place in nearby_places:
            if place.get('type') == 'primary_location':
                geo_data["event_location"] = place.get('name')
                geo_data["event_distance"] = place.get('distance_miles')
                
                # Calculate direction FROM event coordinates TO the location
                if report.latitude and report.longitude and place.get('approx_lat') and place.get('approx_lon'):
                    lat_diff = float(report.latitude) - float(place['approx_lat'])
                    lon_diff = float(report.longitude) - float(place['approx_lon'])
                    
                    if abs(lat_diff) > abs(lon_diff):
                        geo_data["event_direction"] = "north" if lat_diff > 0 else "south"
                    else:
                        geo_data["event_direction"] = "east" if lon_diff > 0 else "west"
                break
        
        # Extract nearest major city with direction
        for place in nearby_places:
            if place.get('type') == 'nearest_city':
                geo_data["nearest_major_city"] = place.get('name')
                geo_data["major_city_distance"] = place.get('distance_miles')
                
                # Calculate direction FROM event coordinates TO major city
                if report.latitude and report.longitude and place.get('approx_lat') and place.get('approx_lon'):
                    lat_diff = float(report.latitude) - float(place['approx_lat'])
                    lon_diff = float(report.longitude) - float(place['approx_lon'])
                    
                    if abs(lat_diff) > abs(lon_diff):
                        geo_data["major_city_direction"] = "north" if lat_diff > 0 else "south"
                    else:
                        geo_data["major_city_direction"] = "east" if lon_diff > 0 else "west"
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
            geo_data["nearby_places_text"] = f". Nearby places include {', '.join(nearby_place_items)}"
        
        return geo_data
    
    def _generate_summary(self, report, magnitude_display: str, geo_data: Dict[str, Any]) -> str:
        """
        Generate Enhanced Context summary with 6 geo data points format
        """
        # Build location text with 6 geo data points format
        location_text = self._build_location_text(report, geo_data)
        
        # Get damage description based on report type and magnitude
        damage_desc = self._get_damage_description(report, magnitude_display)
        
        # Generate final summary
        if report.report_type.upper() == "WIND":
            return f"On {report.report_date}, damaging winds reached {magnitude_display} {location_text}. {damage_desc}"
        elif report.report_type.upper() == "HAIL":
            return f"On {report.report_date}, hail measuring {magnitude_display} struck {location_text}. {damage_desc}"
        else:
            return f"On {report.report_date}, {report.report_type.lower()} event occurred {location_text}."
    
    def _build_location_text(self, report, geo_data: Dict[str, Any]) -> str:
        """Build location text with 6 geo data points format"""
        if (geo_data["event_location"] and geo_data["event_distance"] and 
            geo_data["event_direction"] and geo_data["nearest_major_city"] and 
            geo_data["major_city_distance"] and geo_data["major_city_direction"]):
            
            return (f"located {geo_data['event_direction']} {geo_data['event_distance']} miles from "
                   f"{geo_data['event_location']} ({report.location}), or "
                   f"{geo_data['major_city_direction']} {geo_data['major_city_distance']:.1f} miles from "
                   f"{geo_data['nearest_major_city']}{geo_data['nearby_places_text']}")
        elif geo_data["event_location"]:
            return f"at {geo_data['event_location']} ({report.location}){geo_data['nearby_places_text']}"
        else:
            return f"at {report.location}{geo_data['nearby_places_text']}"
    
    def _get_damage_description(self, report, magnitude_display: str) -> str:
        """Get damage description based on report type and magnitude"""
        try:
            numeric_magnitude = float(report.magnitude) if report.magnitude else 0
        except (ValueError, TypeError):
            numeric_magnitude = 0
        
        if report.report_type.upper() == "WIND" and numeric_magnitude > 0:
            if numeric_magnitude >= 74:
                return "Capable of causing significant structural damage to buildings and vehicles."
            elif numeric_magnitude >= 58:
                return "Strong enough to damage roofs, break windows, and down large trees."
            else:
                return "Sufficient to cause minor property damage and tree limb breakage."
        elif report.report_type.upper() == "HAIL" and numeric_magnitude > 0:
            if numeric_magnitude >= 2.0:
                return "Large enough to cause severe vehicle damage and roof penetration."
            elif numeric_magnitude >= 1.0:
                return "Size sufficient to damage vehicles and cause roof impacts."
            else:
                return "Small hail capable of minor vehicle and property damage."
        else:
            return "Event details available in original report."