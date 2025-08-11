"""
Enhanced Context Service v4.0 - Intelligent Alert Integration
Redesigned to intelligently integrate rich NWS alert data with SPC verification
Avoids duplication with Confirmed Warning Reports and handles conditional logic
"""

import logging
import math
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

class EnhancedContextServiceV4:
    """Enhanced Context generation with intelligent alert data integration"""
    
    def __init__(self, db_session: Optional[Session]):
        self.db_session = db_session
        self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
        # Comprehensive cities database (same as v3)
        self.COMPREHENSIVE_CITIES = [
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
            {'name': 'Independence, KS', 'lat': 37.2264, 'lon': -95.7080, 'population': 9000},
            {'name': 'Winfield, KS', 'lat': 37.2403, 'lon': -97.0000, 'population': 12000},
            {'name': 'Coffeyville, KS', 'lat': 37.0373, 'lon': -95.6169, 'population': 10000},
            {'name': 'Chanute, KS', 'lat': 37.6781, 'lon': -95.4594, 'population': 9000},
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
            {'name': 'Arkansas City, KS', 'lat': 37.0625, 'lon': -97.0364, 'population': 12000},
            {'name': 'Parsons, KS', 'lat': 37.3403, 'lon': -95.2608, 'population': 10000},
            {'name': 'Abilene, KS', 'lat': 38.9172, 'lon': -97.2142, 'population': 7000},
            
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
            {'name': 'Scottsbluff, NE', 'lat': 41.8661, 'lon': -103.6672, 'population': 15000},
            
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
            {'name': 'Boulder, CO', 'lat': 40.0150, 'lon': -105.2705, 'population': 108000},
            {'name': 'Greeley, CO', 'lat': 40.4233, 'lon': -104.7091, 'population': 108000},
            {'name': 'Longmont, CO', 'lat': 40.1672, 'lon': -105.1019, 'population': 98000},
            {'name': 'Loveland, CO', 'lat': 40.3978, 'lon': -105.0750, 'population': 76000},
            {'name': 'Grand Junction, CO', 'lat': 39.0639, 'lon': -108.5506, 'population': 65000},
            
            # Additional regional cities for better coverage
            {'name': 'Oklahoma City, OK', 'lat': 35.4676, 'lon': -97.5164, 'population': 695000},
            {'name': 'Tulsa, OK', 'lat': 36.1540, 'lon': -95.9928, 'population': 413000},
            {'name': 'Des Moines, IA', 'lat': 41.5868, 'lon': -93.6250, 'population': 215000},
            {'name': 'Cedar Rapids, IA', 'lat': 41.9778, 'lon': -91.6656, 'population': 133000},
            {'name': 'Sioux Falls, SD', 'lat': 43.5446, 'lon': -96.7311, 'population': 192000},
            {'name': 'Fargo, ND', 'lat': 46.8772, 'lon': -96.7898, 'population': 125000},
            {'name': 'Minneapolis, MN', 'lat': 44.9778, 'lon': -93.2650, 'population': 429000},
            {'name': 'St. Paul, MN', 'lat': 44.9537, 'lon': -93.0900, 'population': 308000}
        ]

    def generate_enhanced_context(self, report) -> Dict[str, Any]:
        """Generate intelligent enhanced context with conditional SPC integration"""
        try:
            logger.info(f"Generating enhanced context v4.0 for SPC report {report.id}")
            
            # Get location data
            location_data = self._get_comprehensive_location_data(report)
            
            # Check if report has verified alerts (SPC match)
            has_verified_alerts = self._has_verified_alerts(report)
            
            # Get alert data if available
            alert_data = self._get_alert_context(report) if has_verified_alerts else None
            
            # Get SPC-specific data
            spc_data = self._get_spc_context(report)
            
            # Generate intelligent summary based on available data
            enhanced_summary = self._generate_intelligent_summary(
                report, location_data, alert_data, spc_data, has_verified_alerts
            )
            
            result = {
                'version': 'v4.0',
                'generated_at': datetime.now().isoformat(),
                'enhanced_summary': enhanced_summary,
                'location_context': location_data,
                'alert_integration': alert_data is not None,
                'spc_verified': has_verified_alerts
            }
            
            logger.info(f"Enhanced context v4.0 generated successfully for report {report.id}")
            return result
            
        except Exception as e:
            logger.error(f"Enhanced context generation failed for report {report.id}: {str(e)}")
            raise

    def _has_verified_alerts(self, report) -> bool:
        """Check if report has verified alerts (indicating SPC match)"""
        try:
            # Check if there are any verified alerts linked to this report
            from models import Alert
            if not self.db_session:
                return False
            
            # Try to find alerts that have SPC verification 
            # Since the relationship structure may vary, check multiple approaches
            try:
                # Method 1: Check if alert has spc_verified flag and references this report
                verified_count = self.db_session.query(Alert).filter(
                    Alert.spc_verified == True,
                    Alert.spc_reports.contains([{'id': report.id}])
                ).count()
                
                if verified_count > 0:
                    return True
                    
                # Method 2: Check if there are any verified alerts in the same timeframe/location
                # This is a fallback for reports that should have verification but relationships aren't set
                import datetime
                if hasattr(report, 'report_date') and report.report_date:
                    time_window = datetime.timedelta(hours=2)
                    start_time = report.report_date - time_window
                    end_time = report.report_date + time_window
                    
                    nearby_verified = self.db_session.query(Alert).filter(
                        Alert.effective.between(start_time, end_time),
                        Alert.spc_verified == True
                    ).count()
                    
                    return nearby_verified > 0
                
                return False
                
            except Exception as e:
                logger.error(f"Error checking verified alerts status: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Error checking verified alerts for report {report.id}: {str(e)}")
            return False

    def _get_alert_context(self, report) -> Optional[Dict[str, Any]]:
        """Extract rich context data from verified alerts"""
        try:
            from models import Alert
            if not self.db_session:
                return None
                
            # Get the first verified alert linked to this report
            alert = self.db_session.query(Alert).filter(
                Alert.spc_verified == True,
                Alert.spc_reports.contains([{'id': report.id}])
            ).first()
            
            if not alert:
                return None
                
            # Build alert context with safely checked attributes
            alert_context = {
                'event_type': getattr(alert, 'event', 'Unknown'),
                'affected_areas': getattr(alert, 'area_desc', ''),
                'affected_states': getattr(alert, 'affected_states', []),
                'alert_timing': {
                    'effective': alert.effective.isoformat() if hasattr(alert, 'effective') and alert.effective else None,
                    'expires': alert.expires.isoformat() if hasattr(alert, 'expires') and alert.expires else None
                }
            }
            
            # Add optional fields if they exist
            if hasattr(alert, 'severity'):
                alert_context['severity'] = alert.severity
            if hasattr(alert, 'certainty'):
                alert_context['certainty'] = alert.certainty
            if hasattr(alert, 'status'):
                alert_context['status'] = alert.status
            if hasattr(alert, 'response'):
                alert_context['response'] = alert.response
            
            # Extract technical details
            if alert.properties:
                props = alert.properties
                alert_context.update({
                    'hazards': props.get('hazard', []),
                    'vtec_code': props.get('vtec', ''),
                    'wmo_id': props.get('wmoId', ''),
                    'awips_id': props.get('awipsId', ''),
                    'distribution_channels': props.get('distributionChannels', []),
                    'geocodes': props.get('geocode', {}),
                    'affected_zones': props.get('affectedZones', [])
                })
            
            # Extract radar-detected parameters if available
            if hasattr(alert, 'radar_indicated') and alert.radar_indicated:
                radar_data = alert.radar_indicated
                alert_context['radar_detected'] = {
                    'hail_size': radar_data.get('hail_inches'),
                    'wind_speed': radar_data.get('wind_mph'),
                    'storm_motion': radar_data.get('storm_motion'),
                    'hazard_description': radar_data.get('hazard_text', '')
                }
            
            return alert_context
            
        except Exception as e:
            logger.error(f"Error extracting alert context for report {report.id}: {str(e)}")
            return None

    def _get_spc_context(self, report) -> Dict[str, Any]:
        """Extract SPC report context data"""
        spc_context = {
            'event_date': report.report_date.strftime('%Y-%m-%d %H:%M UTC') if report.report_date else None,
            'event_type': report.report_type or report.event_type,
            'location_description': report.location,
            'magnitude': None,
            'comments': None
        }
        
        # Extract magnitude
        if hasattr(report, 'magnitude') and report.magnitude:
            try:
                mag_data = report.magnitude
                if isinstance(mag_data, dict):
                    if report.report_type and 'HAIL' in report.report_type.upper():
                        spc_context['magnitude'] = {
                            'type': 'hail',
                            'size_inches': mag_data.get('size_inches'),
                            'description': f"{mag_data.get('size_inches', 0):.2f}\" hail"
                        }
                    elif report.report_type and 'WIND' in report.report_type.upper():
                        spc_context['magnitude'] = {
                            'type': 'wind',
                            'speed_mph': mag_data.get('speed_mph'),
                            'description': f"{mag_data.get('speed_mph', 0)} mph winds"
                        }
            except (ValueError, TypeError, AttributeError):
                pass
        
        # Extract meaningful comments (avoid empty or placeholder comments)
        if hasattr(report, 'comments') and report.comments:
            comments = str(report.comments).strip()
            # Filter out meaningless comments like "(ICT)", "(OUN)", empty strings, etc.
            if (comments and len(comments) > 5 and 
                not (comments.startswith('(') and comments.endswith(')') and len(comments) <= 6) and
                not comments.upper() in ['(ICT)', '(OUN)', '(SGF)', '(TOP)', '(DDC)', '(GLD)', '(EAX)']):
                spc_context['comments'] = comments
        
        return spc_context

    def _generate_intelligent_summary(self, report, location_data: Dict[str, Any], 
                                    alert_data: Optional[Dict[str, Any]], 
                                    spc_data: Dict[str, Any], 
                                    has_verified_alerts: bool) -> str:
        """Generate intelligent summary with conditional logic and rich data integration"""
        
        # Start with event description
        event_date = spc_data.get('event_date', 'Unknown date')
        event_type = spc_data.get('event_type', 'severe weather event')
        
        if has_verified_alerts and alert_data:
            # SPC-verified event - focus on verification and technical details
            summary = self._build_verified_event_summary(alert_data, spc_data, location_data)
        else:
            # Non-verified SPC report - focus on location and magnitude
            summary = self._build_standard_event_summary(spc_data, location_data)
        
        return summary

    def _build_verified_event_summary(self, alert_data: Dict[str, Any], 
                                    spc_data: Dict[str, Any], 
                                    location_data: Dict[str, Any]) -> str:
        """Build summary for SPC-verified events with rich alert integration"""
        
        # Start with verification context
        event_date = spc_data.get('event_date', 'Unknown date')
        alert_type = alert_data.get('event_type', 'severe weather alert')
        severity = alert_data.get('severity', 'severe')
        certainty = alert_data.get('certainty', 'observed')
        
        summary = f"On {event_date}, this SPC report verified a {alert_type.lower()} "
        
        # Add severity and certainty context
        if severity and certainty:
            summary += f"({severity.lower()} severity, {certainty.lower()}) "
        
        # Add location with SPC precision
        location_desc = self._format_location_description(location_data, detailed=True)
        if location_desc:
            summary += f"that occurred {location_desc}"
        
        # Add technical verification details
        radar_data = alert_data.get('radar_detected', {})
        spc_magnitude = spc_data.get('magnitude', {})
        
        if radar_data and spc_magnitude:
            summary += f". The National Weather Service initially detected "
            
            # Add radar parameters
            radar_params = []
            if radar_data.get('hail_size'):
                radar_params.append(f"{radar_data['hail_size']:.2f}\" hail")
            if radar_data.get('wind_speed'):
                radar_params.append(f"{radar_data['wind_speed']} mph winds")
            
            if radar_params:
                summary += f"{' and '.join(radar_params)} via radar, "
            
            # Add SPC verification
            summary += f"which SPC verified as {spc_magnitude.get('description', 'severe weather')}"
        
        # Add affected areas with technical precision
        affected_areas = alert_data.get('affected_areas', '')
        if affected_areas:
            # Extract county information
            counties = self._extract_counties_from_description(affected_areas)
            if counties:
                summary += f", affecting {', '.join(counties[:3])} " + ("counties" if len(counties) > 1 else "county")
        
        # Add technical alert details
        vtec_code = alert_data.get('vtec_code', '')
        awips_id = alert_data.get('awips_id', '')
        if vtec_code or awips_id:
            summary += f". Technical identifiers: "
            tech_details = []
            if vtec_code:
                tech_details.append(f"VTEC {vtec_code}")
            if awips_id:
                tech_details.append(f"AWIPS {awips_id}")
            summary += ", ".join(tech_details)
        
        # Add meaningful SPC comments if available
        spc_comments = spc_data.get('comments')
        if spc_comments:
            summary += f". Field observations: {spc_comments}"
        
        return summary

    def _build_standard_event_summary(self, spc_data: Dict[str, Any], 
                                    location_data: Dict[str, Any]) -> str:
        """Build summary for standard SPC reports (non-verified)"""
        
        event_date = spc_data.get('event_date', 'Unknown date')
        event_type = spc_data.get('event_type', 'severe weather event')
        
        summary = f"On {event_date}, a {event_type.lower()} event occurred"
        
        # Add magnitude if available
        magnitude = spc_data.get('magnitude', {})
        if magnitude and magnitude.get('description'):
            summary += f" with {magnitude['description']}"
        
        # Add location
        location_desc = self._format_location_description(location_data, detailed=False)
        if location_desc:
            summary += f" {location_desc}"
        
        # Add meaningful comments
        comments = spc_data.get('comments')
        if comments:
            summary += f". SPC notes: {comments}"
        
        return summary

    def _format_location_description(self, location_data: Dict[str, Any], detailed: bool = False) -> str:
        """Format location description with conditional detail level"""
        location_parts = []
        
        # Primary location
        spc_location = location_data.get('spc_location', '')
        event_location = location_data.get('event_location')
        event_distance = location_data.get('event_distance')
        event_direction = location_data.get('event_direction')
        
        if event_location and event_distance is not None:
            if event_direction and spc_location:
                location_parts.append(f"{event_direction} {event_distance:.1f} miles from {event_location} ({spc_location})")
            elif spc_location:
                location_parts.append(f"{event_distance:.1f} miles from {event_location} ({spc_location})")
            else:
                location_parts.append(f"{event_distance:.1f} miles from {event_location}")
        elif spc_location:
            location_parts.append(f"near {spc_location}")
        
        # Major city reference
        major_city = location_data.get('nearest_major_city')
        major_distance = location_data.get('major_city_distance')
        major_direction = location_data.get('major_city_direction')
        
        if major_city and major_distance is not None and detailed:
            if major_direction:
                location_parts.append(f"{major_direction} {major_distance:.1f} miles from {major_city}")
            else:
                location_parts.append(f"{major_distance:.1f} miles from {major_city}")
        
        if location_parts:
            return "located " + (", or " if len(location_parts) > 1 else "").join(location_parts)
        return ""

    def _extract_counties_from_description(self, area_desc: str) -> List[str]:
        """Extract county names from area description"""
        if not area_desc:
            return []
        
        import re
        counties = []
        # Split by semicolon and extract county names
        areas = area_desc.split(';')
        
        for area in areas:
            area = area.strip()
            # Match pattern "County Name, ST"
            county_match = re.match(r'^([^,]+),\s*([A-Z]{2})$', area)
            if county_match:
                county_name = county_match.group(1).strip()
                # Remove " County" suffix if present
                county_name = re.sub(r'\s+County$', '', county_name)
                counties.append(county_name)
        
        return counties

    def _get_comprehensive_location_data(self, report) -> Dict[str, Any]:
        """Get comprehensive location data (reuse from v3 with enhancements)"""
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
        """Calculate distance between two points using Haversine formula"""
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