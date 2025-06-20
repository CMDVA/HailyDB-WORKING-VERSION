"""
Enhanced Context Service v3.0 - 6 Geo Data Points Format
Implements proper location hierarchy using free regional database
Format: located [direction] [distance] miles from [event location] ([SPC location]), or [direction] [distance] from [major city]. Nearby places [closest (mi), second (mi), third (mi)]
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

class EnhancedContextServiceV3:
    """Enhanced Context generation with proper 6 geo data points format"""
    
    COMPREHENSIVE_CITIES = [
        # Kansas
        {'name': 'Wichita, KS', 'lat': 37.6872, 'lon': -97.3301, 'population': 389000},
        {'name': 'Overland Park, KS', 'lat': 38.9822, 'lon': -94.6708, 'population': 195000},
        {'name': 'Kansas City, KS', 'lat': 39.1142, 'lon': -94.6275, 'population': 153000},
        {'name': 'Olathe, KS', 'lat': 38.8814, 'lon': -94.8191, 'population': 140000},
        {'name': 'Topeka, KS', 'lat': 39.0473, 'lon': -95.6890, 'population': 125000},
        {'name': 'Lawrence, KS', 'lat': 38.9717, 'lon': -95.2353, 'population': 95000},
        {'name': 'Shawnee, KS', 'lat': 39.0228, 'lon': -94.7202, 'population': 65000},
        {'name': 'Manhattan, KS', 'lat': 39.1836, 'lon': -96.5717, 'population': 55000},
        {'name': 'Lenexa, KS', 'lat': 38.9536, 'lon': -94.7336, 'population': 55000},
        {'name': 'Salina, KS', 'lat': 38.8403, 'lon': -97.6114, 'population': 47000},
        {'name': 'Hutchinson, KS', 'lat': 38.0608, 'lon': -97.9297, 'population': 41000},
        {'name': 'Leavenworth, KS', 'lat': 39.3111, 'lon': -94.9225, 'population': 36000},
        {'name': 'Leawood, KS', 'lat': 38.9167, 'lon': -94.6169, 'population': 35000},
        {'name': 'Dodge City, KS', 'lat': 37.7653, 'lon': -100.0171, 'population': 27000},
        {'name': 'Garden City, KS', 'lat': 37.9717, 'lon': -100.8728, 'population': 26000},
        {'name': 'Emporia, KS', 'lat': 38.4039, 'lon': -96.1817, 'population': 25000},
        {'name': 'Junction City, KS', 'lat': 39.0292, 'lon': -96.8317, 'population': 23000},
        {'name': 'Derby, KS', 'lat': 37.5450, 'lon': -97.2692, 'population': 23000},
        {'name': 'Liberal, KS', 'lat': 37.0431, 'lon': -100.9210, 'population': 19000},
        {'name': 'Hays, KS', 'lat': 38.8792, 'lon': -99.3267, 'population': 21000},
        {'name': 'Great Bend, KS', 'lat': 38.3642, 'lon': -98.8648, 'population': 15000},
        {'name': 'McPherson, KS', 'lat': 38.3706, 'lon': -97.6645, 'population': 13000},
        {'name': 'El Dorado, KS', 'lat': 37.8181, 'lon': -96.8564, 'population': 13000},
        {'name': 'Newton, KS', 'lat': 38.0467, 'lon': -97.3450, 'population': 19000},
        {'name': 'Pittsburg, KS', 'lat': 37.4108, 'lon': -94.7041, 'population': 20000},
        {'name': 'Chanute, KS', 'lat': 37.6781, 'lon': -95.4594, 'population': 9000},
        {'name': 'Coffeyville, KS', 'lat': 37.0373, 'lon': -95.6169, 'population': 10000},
        {'name': 'Independence, KS', 'lat': 37.2264, 'lon': -95.7080, 'population': 9000},
        {'name': 'Winfield, KS', 'lat': 37.2403, 'lon': -97.0000, 'population': 12000},
        {'name': 'Arkansas City, KS', 'lat': 37.0625, 'lon': -97.0364, 'population': 12000},
        {'name': 'Parsons, KS', 'lat': 37.3403, 'lon': -95.2608, 'population': 10000},
        {'name': 'Abilene, KS', 'lat': 38.9172, 'lon': -97.2142, 'population': 7000},
        {'name': 'Colby, KS', 'lat': 39.3906, 'lon': -101.0546, 'population': 5000},
        {'name': 'Scott City, KS', 'lat': 38.4731, 'lon': -100.9065, 'population': 4000},
        {'name': 'Goodland, KS', 'lat': 39.3481, 'lon': -101.7112, 'population': 4500},
        
        # Nebraska  
        {'name': 'Omaha, NE', 'lat': 41.2565, 'lon': -95.9345, 'population': 486000},
        {'name': 'Lincoln, NE', 'lat': 40.8136, 'lon': -96.7026, 'population': 295000},
        {'name': 'Bellevue, NE', 'lat': 41.1370, 'lon': -95.9145, 'population': 53000},
        {'name': 'Grand Island, NE', 'lat': 40.9264, 'lon': -98.3420, 'population': 52000},
        {'name': 'Kearney, NE', 'lat': 40.6994, 'lon': -99.0817, 'population': 33000},
        {'name': 'Fremont, NE', 'lat': 41.4333, 'lon': -96.4981, 'population': 26000},
        {'name': 'Hastings, NE', 'lat': 40.5861, 'lon': -98.3887, 'population': 25000},
        {'name': 'North Platte, NE', 'lat': 41.1239, 'lon': -100.7654, 'population': 24000},
        {'name': 'Norfolk, NE', 'lat': 42.0331, 'lon': -97.4170, 'population': 24000},
        {'name': 'Columbus, NE', 'lat': 41.4297, 'lon': -97.3675, 'population': 23000},
        {'name': 'Papillion, NE', 'lat': 41.1544, 'lon': -96.0422, 'population': 24000},
        {'name': 'La Vista, NE', 'lat': 41.1833, 'lon': -96.0264, 'population': 17000},
        {'name': 'Scottsbluff, NE', 'lat': 41.8661, 'lon': -103.6672, 'population': 15000},
        {'name': 'Beatrice, NE', 'lat': 40.2681, 'lon': -96.7470, 'population': 12000},
        {'name': 'South Sioux City, NE', 'lat': 42.4586, 'lon': -96.4131, 'population': 13000},
        {'name': 'York, NE', 'lat': 40.8675, 'lon': -97.5920, 'population': 8000},
        {'name': 'McCook, NE', 'lat': 40.2006, 'lon': -100.6254, 'population': 7500},
        {'name': 'Sidney, NE', 'lat': 41.1428, 'lon': -103.0093, 'population': 6500},
        {'name': 'Alliance, NE', 'lat': 42.0997, 'lon': -102.8718, 'population': 8000},
        {'name': 'Chadron, NE', 'lat': 42.8306, 'lon': -103.0010, 'population': 5500},
        {'name': 'Valentine, NE', 'lat': 42.8722, 'lon': -100.5493, 'population': 2700},
        {'name': 'Broken Bow, NE', 'lat': 41.4028, 'lon': -99.6376, 'population': 3600},
        {'name': 'Holdrege, NE', 'lat': 40.4406, 'lon': -99.3709, 'population': 5500},
        {'name': 'Lexington, NE', 'lat': 40.7806, 'lon': -99.7418, 'population': 10000},
        {'name': 'Ogallala, NE', 'lat': 41.1281, 'lon': -101.7193, 'population': 4500},
        
        # Colorado
        {'name': 'Denver, CO', 'lat': 39.7392, 'lon': -104.9903, 'population': 715000},
        {'name': 'Colorado Springs, CO', 'lat': 38.8339, 'lon': -104.8214, 'population': 478000},
        {'name': 'Aurora, CO', 'lat': 39.7294, 'lon': -104.8319, 'population': 379000},
        {'name': 'Fort Collins, CO', 'lat': 40.5853, 'lon': -105.0844, 'population': 170000},
        {'name': 'Lakewood, CO', 'lat': 39.7047, 'lon': -105.0814, 'population': 155000},
        {'name': 'Thornton, CO', 'lat': 39.8681, 'lon': -104.9719, 'population': 141000},
        {'name': 'Arvada, CO', 'lat': 39.8028, 'lon': -105.0875, 'population': 121000},
        {'name': 'Westminster, CO', 'lat': 39.8367, 'lon': -105.0372, 'population': 114000},
        {'name': 'Pueblo, CO', 'lat': 38.2544, 'lon': -104.6091, 'population': 111000},
        {'name': 'Centennial, CO', 'lat': 39.5807, 'lon': -104.8761, 'population': 108000},
        {'name': 'Boulder, CO', 'lat': 40.0150, 'lon': -105.2705, 'population': 108000},
        {'name': 'Greeley, CO', 'lat': 40.4233, 'lon': -104.7091, 'population': 108000},
        {'name': 'Longmont, CO', 'lat': 40.1672, 'lon': -105.1019, 'population': 98000},
        {'name': 'Loveland, CO', 'lat': 40.3978, 'lon': -105.0750, 'population': 76000},
        {'name': 'Grand Junction, CO', 'lat': 39.0639, 'lon': -108.5506, 'population': 65000},
        {'name': 'Broomfield, CO', 'lat': 39.9205, 'lon': -105.0866, 'population': 70000},
        {'name': 'Castle Rock, CO', 'lat': 39.3722, 'lon': -104.8561, 'population': 65000},
        {'name': 'Commerce City, CO', 'lat': 39.8083, 'lon': -104.9339, 'population': 62000},
        {'name': 'Parker, CO', 'lat': 39.5186, 'lon': -104.7614, 'population': 58000},
        {'name': 'Littleton, CO', 'lat': 39.6133, 'lon': -105.0167, 'population': 46000},
        {'name': 'Northglenn, CO', 'lat': 39.8961, 'lon': -104.9811, 'population': 38000},
        {'name': 'Englewood, CO', 'lat': 39.6478, 'lon': -104.9875, 'population': 33000},
        {'name': 'Wheat Ridge, CO', 'lat': 39.7661, 'lon': -105.0772, 'population': 31000},
        {'name': 'Fort Morgan, CO', 'lat': 40.2536, 'lon': -103.7978, 'population': 11000},
        {'name': 'Sterling, CO', 'lat': 40.6253, 'lon': -103.2077, 'population': 14000},
        {'name': 'Burlington, CO', 'lat': 39.3031, 'lon': -102.2693, 'population': 3000},
        {'name': 'Limon, CO', 'lat': 39.2631, 'lon': -103.6921, 'population': 2000},
        {'name': 'Yuma, CO', 'lat': 40.1231, 'lon': -102.7243, 'population': 3500},
        
        # Additional regional cities for better coverage
        {'name': 'Oklahoma City, OK', 'lat': 35.4676, 'lon': -97.5164, 'population': 695000},
        {'name': 'Tulsa, OK', 'lat': 36.1540, 'lon': -95.9928, 'population': 413000},
        {'name': 'Des Moines, IA', 'lat': 41.5868, 'lon': -93.6250, 'population': 215000},
        {'name': 'Cedar Rapids, IA', 'lat': 41.9778, 'lon': -91.6656, 'population': 133000},
        {'name': 'Sioux Falls, SD', 'lat': 43.5446, 'lon': -96.7311, 'population': 192000},
        {'name': 'Rapid City, SD', 'lat': 44.0805, 'lon': -103.2310, 'population': 78000},
        {'name': 'Fargo, ND', 'lat': 46.8772, 'lon': -96.7898, 'population': 125000},
        {'name': 'Bismarck, ND', 'lat': 46.8083, 'lon': -100.7837, 'population': 73000},
        {'name': 'Minneapolis, MN', 'lat': 44.9778, 'lon': -93.2650, 'population': 429000},
        {'name': 'St. Paul, MN', 'lat': 44.9537, 'lon': -93.0900, 'population': 308000},
        {'name': 'Rochester, MN', 'lat': 44.0121, 'lon': -92.4802, 'population': 118000},
        {'name': 'Duluth, MN', 'lat': 46.7867, 'lon': -92.1005, 'population': 86000},
        {'name': 'St. Cloud, MN', 'lat': 45.5608, 'lon': -94.1622, 'population': 68000},
        {'name': 'Kansas City, MO', 'lat': 39.0997, 'lon': -94.5786, 'population': 495000},
        {'name': 'St. Louis, MO', 'lat': 38.6270, 'lon': -90.1994, 'population': 301000},
    ]
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    def generate_enhanced_context(self, report_id: int) -> Dict[str, Any]:
        """Generate Enhanced Context with proper 6 geo data points format"""
        try:
            from models import SPCReport
            
            report = self.db.query(SPCReport).filter(SPCReport.id == report_id).first()
            if not report:
                return {"success": False, "error": "Report not found"}
            
            # Get location data with 6 geo data points
            location_data = self._get_comprehensive_location_data(report)
            
            # Get magnitude and damage assessment
            magnitude_value = self._extract_magnitude_value(report)
            damage_assessment = self._get_damage_probability(report, magnitude_value)
            
            # Generate Enhanced Context summary with proper format
            enhanced_summary = self._generate_6_point_summary(
                report, magnitude_value, location_data, damage_assessment
            )
            
            # Build context structure
            enhanced_context = {
                "version": "v3.0",
                "generated_at": datetime.utcnow().isoformat(),
                "enhanced_summary": enhanced_summary,
                "location_context": {
                    "event_location": location_data.get('event_location'),
                    "nearest_major_city": location_data.get('nearest_major_city'),
                    "nearby_places": location_data.get('nearby_places', [])
                }
            }
            
            # Update database
            report.enhanced_context = enhanced_context
            report.enhanced_context_version = "v3.0"
            report.enhanced_context_generated_at = datetime.utcnow()
            self.db.commit()
            
            return {
                "success": True,
                "report_id": report_id,
                "version": "v3.0",
                "enhanced_context": enhanced_context
            }
            
        except Exception as e:
            logger.error(f"Error generating Enhanced Context for report {report_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_comprehensive_location_data(self, report) -> Dict[str, Any]:
        """Get comprehensive location data for 6 geo data points format"""
        location_data = {
            'event_location': None,
            'event_distance': None, 
            'event_direction': None,
            'nearest_major_city': None,
            'major_city_distance': None,
            'major_city_direction': None,
            'nearby_places': [],
            'spc_location': None
        }
        
        # Extract coordinates
        try:
            lat = float(report.latitude) if report.latitude else None
            lon = float(report.longitude) if report.longitude else None
            if not lat or not lon:
                return location_data
        except (ValueError, TypeError):
            return location_data
        
        # Preserve SPC location
        if hasattr(report, 'location') and report.location:
            location_data['spc_location'] = str(report.location).strip()
        
        # Find all nearby cities sorted by distance
        all_cities = []
        for city in self.COMPREHENSIVE_CITIES:
            distance = self._calculate_distance(lat, lon, city['lat'], city['lon'])
            all_cities.append({
                'name': city['name'],
                'distance_miles': distance,
                'population': city['population'],
                'lat': city['lat'],
                'lon': city['lon']
            })
        
        # Sort by distance
        all_cities.sort(key=lambda x: x['distance_miles'])
        
        # Find event location (closest city under 30 miles)
        for city in all_cities:
            if city['distance_miles'] <= 30:
                location_data['event_location'] = city['name']
                location_data['event_distance'] = city['distance_miles']
                location_data['event_direction'] = self._calculate_direction(
                    lat, lon, city['lat'], city['lon']
                )
                break
        
        # Find major city (largest population over 50k, or closest if none found)
        major_city = None
        for city in all_cities:
            if city['population'] >= 50000:
                major_city = city
                break
        
        if not major_city and all_cities:
            major_city = all_cities[0]  # Use closest city as fallback
        
        if major_city:
            location_data['nearest_major_city'] = major_city['name']
            location_data['major_city_distance'] = major_city['distance_miles']
            location_data['major_city_direction'] = self._calculate_direction(
                lat, lon, major_city['lat'], major_city['lon']
            )
        
        # Build nearby places list (excluding event location and major city)
        event_name = location_data.get('event_location', '')
        major_name = location_data.get('nearest_major_city', '')
        
        nearby_places = []
        for city in all_cities[:10]:  # Take closest 10 cities
            if (city['name'] != event_name and city['name'] != major_name and
                city['distance_miles'] <= 100):
                nearby_places.append({
                    'name': city['name'],
                    'distance_miles': city['distance_miles'],
                    'type': 'nearby_place'
                })
        
        location_data['nearby_places'] = nearby_places[:3]  # Limit to 3
        
        return location_data
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in miles"""
        R = 3959  # Earth's radius in miles
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = (math.sin(dlat/2)**2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def _calculate_direction(self, from_lat: float, from_lon: float, 
                           to_lat: float, to_lon: float) -> str:
        """Calculate cardinal direction from one point to another"""
        lat_diff = to_lat - from_lat
        lon_diff = to_lon - from_lon
        
        if abs(lat_diff) > abs(lon_diff):
            return "north" if lat_diff > 0 else "south"
        else:
            return "east" if lon_diff > 0 else "west"
    
    def _extract_magnitude_value(self, report) -> Optional[float]:
        """Extract magnitude value from report"""
        try:
            if hasattr(report, 'magnitude') and report.magnitude:
                mag_data = report.magnitude
                if isinstance(mag_data, dict):
                    if report.report_type and report.report_type.upper() == 'HAIL':
                        return float(mag_data.get('size_inches', 0))
                    elif report.report_type and report.report_type.upper() == 'WIND':
                        return float(mag_data.get('speed_mph', 0))
            return None
        except (ValueError, TypeError, AttributeError):
            return None
    
    def _get_damage_probability(self, report, magnitude_value: Optional[float]) -> Dict[str, Any]:
        """Get damage assessment based on magnitude"""
        if not magnitude_value:
            return {}
        
        try:
            event_type = report.report_type.upper() if report.report_type else ""
            
            if event_type == "HAIL":
                if magnitude_value >= 2.0:
                    return {"assessment": "Large hail likely caused significant damage to vehicles, roofing materials, siding, and outdoor equipment."}
                elif magnitude_value >= 1.0:
                    return {"assessment": "Hail likely caused dents to vehicles, cracked windows, damage to roofing materials, siding, and gutters."}
                else:
                    return {"assessment": "Small hail likely caused minor damage to crops and vegetation."}
            
            elif event_type == "WIND":
                if magnitude_value >= 75:
                    return {"assessment": "Severe winds likely caused structural damage, downed large trees, and widespread power outages."}
                elif magnitude_value >= 58:
                    return {"assessment": "Severe winds likely caused tree damage and power outages in the area."}
                else:
                    return {"assessment": "Strong winds likely caused minor tree damage and scattered power outages."}
            
            return {}
            
        except (AttributeError, TypeError):
            return {}
    
    def _generate_6_point_summary(self, report, magnitude_value: Optional[float], 
                                 location_data: Dict[str, Any], damage_assessment: Dict[str, Any]) -> str:
        """Generate Enhanced Context summary with 6 geo data points format"""
        
        # Base event information
        try:
            event_date = report.report_date.strftime('%Y-%m-%d') if report.report_date else "Unknown date"
            event_type = report.report_type.lower() if report.report_type else "weather event"
        except (AttributeError, TypeError):
            event_date = "Unknown date"
            event_type = "weather event"
        
        summary = f"On {event_date}, a {event_type} event"
        
        # Add magnitude
        if magnitude_value:
            try:
                if event_type.upper() == "HAIL":
                    summary += f" with {magnitude_value:.2f}\" hail occurred"
                elif event_type.upper() == "WIND":
                    summary += f" with {int(magnitude_value)} mph winds occurred"
                else:
                    summary += " occurred"
            except (ValueError, TypeError):
                summary += " occurred"
        else:
            summary += " occurred"
        
        # IMPLEMENT 6 GEO DATA POINTS FORMAT
        # Format: located [direction] [distance] miles from [event location] ([SPC location]), or [direction] [distance] from [major city]. Nearby places [closest (mi), second (mi), third (mi)]
        
        spc_location = location_data.get('spc_location', '')
        
        # Add event location with SPC preservation
        if (location_data.get('event_location') and 
            location_data.get('event_distance') is not None):
            
            direction = location_data.get('event_direction', '')
            distance = location_data['event_distance']
            event_loc = location_data['event_location']
            
            if direction and spc_location:
                summary += f" located {direction} {distance:.1f} miles from {event_loc} ({spc_location})"
            elif spc_location:
                summary += f" located {distance:.1f} miles from {event_loc} ({spc_location})"
            elif direction:
                summary += f" located {direction} {distance:.1f} miles from {event_loc}"
            else:
                summary += f" located {distance:.1f} miles from {event_loc}"
        elif spc_location:
            summary += f" at {spc_location}"
        
        # Add major city
        if (location_data.get('nearest_major_city') and 
            location_data.get('major_city_distance') is not None):
            
            city_direction = location_data.get('major_city_direction', '')
            city_distance = location_data['major_city_distance']
            major_city = location_data['nearest_major_city']
            
            if city_direction:
                summary += f", or {city_direction} {city_distance:.1f} miles from {major_city}"
            else:
                summary += f", or {city_distance:.1f} miles from {major_city}"
        
        # Add nearby places
        nearby_places = location_data.get('nearby_places', [])
        if nearby_places:
            place_items = []
            for place in nearby_places[:3]:
                name = place.get('name', '')
                distance = place.get('distance_miles', 0)
                if name and distance:
                    place_items.append(f"{name} ({distance:.1f} mi)")
            
            if place_items:
                summary += f". Nearby places include {', '.join(place_items)}"
        
        # Add SPC comments
        try:
            if hasattr(report, 'comments') and report.comments:
                comments = str(report.comments).strip()
                if comments:
                    summary += f". SPC Notes: {comments}"
        except (AttributeError, TypeError):
            pass
        
        # Add damage assessment
        if damage_assessment.get('assessment'):
            summary += f" {damage_assessment['assessment']}"
        
        return summary