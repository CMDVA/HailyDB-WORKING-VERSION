"""
Google Places API Service for Accurate Location Enrichment
Replaces OpenAI geocoding with precise Google Maps data
"""

import logging
import requests
import math
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PlaceResult:
    name: str
    distance_miles: float
    lat: float
    lon: float
    place_type: str
    place_id: str = None

class GooglePlacesService:
    """
    Accurate location enrichment using Google Places API
    Implements 3-tier fallback architecture for precise distance calculations
    """
    
    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_PLACES_API_KEY not found in environment")
        
        # Priority place types for Event Location search
        self.priority_place_types = [
            'school',
            'hospital', 
            'fire_station',
            'library',
            'park',
            'city_hall',
            'police',
            'post_office',
            'community_center',
            'university'
        ]
        
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate precise distance using Haversine formula
        """
        R = 3959.87433  # Earth's radius in miles
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
    
    def find_event_location(self, lat: float, lon: float, radius_miles: float = 5) -> Optional[PlaceResult]:
        """
        Phase 1: Find Event Location using Google Places Nearby Search
        Prioritizes public places within 5 miles
        """
        try:
            # Convert miles to meters for Google API
            radius_meters = int(radius_miles * 1609.34)
            
            # GOOGLE API DISABLED - COST TOO HIGH
            # for place_type in self.priority_place_types:
            #     url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            #     params = {
            #         'location': f"{lat},{lon}",
            #         'radius': radius_meters,
            #         'type': place_type,
            #         'key': self.api_key
            #     }
            #     
            #     response = requests.get(url, params=params, timeout=10)
            #     response.raise_for_status()
            #     data = response.json()
            #     
            #         # Get closest place of this type
            #         closest_place = min(data['results'], key=lambda p: self._calculate_distance(
            #             lat, lon, 
            #             p['geometry']['location']['lat'], 
            #             p['geometry']['location']['lng']
            #         ))
            #         
            #         distance = self._calculate_distance(
            #             lat, lon,
            #             closest_place['geometry']['location']['lat'],
            #             closest_place['geometry']['location']['lng']
            #         )
            #         
            #         if distance <= radius_miles:
            #             return PlaceResult(
            #                 name=closest_place['name'],
            #                 distance_miles=round(distance, 1),
            #                 lat=closest_place['geometry']['location']['lat'],
            #                 lon=closest_place['geometry']['location']['lng'],
            #                 place_type=place_type,
            #                 place_id=closest_place.get('place_id')
            #             )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Google Places nearby search: {e}")
            return None
    
    def _is_valid_place_name(self, place_name: str, place_types: List[str]) -> bool:
        """
        Filter out large geographical areas like national parks, grasslands, forests
        Focus on smaller, more specific locations
        """
        # Exclude large geographical areas
        excluded_keywords = [
            'national park', 'national grassland', 'national forest', 'national monument',
            'state park', 'wilderness area', 'recreation area', 'wildlife refuge',
            'grassland', 'forest', 'basin', 'desert', 'mountain range', 'mountains',
            'prairie', 'plains', 'valley', 'canyon', 'ridge', 'butte', 'mesa'
        ]
        
        place_name_lower = place_name.lower()
        for keyword in excluded_keywords:
            if keyword in place_name_lower:
                return False
                
        # Exclude certain place types that tend to be large areas
        excluded_types = [
            'natural_feature', 'park', 'establishment'
        ]
        
        # If the place has only excluded types, filter it out
        if place_types and all(ptype in excluded_types for ptype in place_types):
            return False
            
        return True

    def find_nearest_place_by_geocoding(self, lat: float, lon: float) -> Optional[PlaceResult]:
        """
        Phase 2: Fallback to Google Reverse Geocoding
        DISABLED - Using free alternative instead of expensive Google API
        """
        # GOOGLE API DISABLED - COST TOO HIGH - USING FREE ALTERNATIVE
        return None
    
    def _find_comprehensive_regional_cities(self, lat: float, lon: float) -> List[Dict]:
        """
        Comprehensive regional city database covering all major metropolitan areas
        Addresses the Pelican Rapids/Fargo issue by including detailed regional coverage
        """
        # Comprehensive city database with population-based significance
        regional_cities = [
            # Minnesota - Upper Midwest
            {'name': 'Minneapolis', 'state': 'MN', 'lat': 45.9537, 'lon': -93.0900, 'pop': 429606},
            {'name': 'Saint Paul', 'state': 'MN', 'lat': 44.9537, 'lon': -93.0900, 'pop': 308096},
            {'name': 'Duluth', 'state': 'MN', 'lat': 46.7867, 'lon': -92.1005, 'pop': 85884},
            {'name': 'Rochester', 'state': 'MN', 'lat': 44.0121, 'lon': -92.4802, 'pop': 118935},
            {'name': 'Moorhead', 'state': 'MN', 'lat': 46.8739, 'lon': -96.7678, 'pop': 44505},
            {'name': 'Detroit Lakes', 'state': 'MN', 'lat': 46.8172, 'lon': -95.8453, 'pop': 9869},
            {'name': 'Brainerd', 'state': 'MN', 'lat': 46.3580, 'lon': -94.2008, 'pop': 13590},
            {'name': 'Fergus Falls', 'state': 'MN', 'lat': 46.2830, 'lon': -96.0777, 'pop': 13471},
            {'name': 'Alexandria', 'state': 'MN', 'lat': 45.8855, 'lon': -95.3775, 'pop': 13070},
            {'name': 'Willmar', 'state': 'MN', 'lat': 45.1219, 'lon': -95.0434, 'pop': 21015},

            # North Dakota - Key Regional Centers
            {'name': 'Fargo', 'state': 'ND', 'lat': 46.8772, 'lon': -96.7898, 'pop': 125990},
            {'name': 'Bismarck', 'state': 'ND', 'lat': 46.8083, 'lon': -100.7837, 'pop': 73529},
            {'name': 'Grand Forks', 'state': 'ND', 'lat': 47.9253, 'lon': -97.0329, 'pop': 56588},
            {'name': 'Minot', 'state': 'ND', 'lat': 48.2330, 'lon': -101.2960, 'pop': 48743},
            {'name': 'West Fargo', 'state': 'ND', 'lat': 46.8747, 'lon': -96.9003, 'pop': 38626},

            # South Dakota - Regional Cities
            {'name': 'Sioux Falls', 'state': 'SD', 'lat': 43.5460, 'lon': -96.7313, 'pop': 192517},
            {'name': 'Rapid City', 'state': 'SD', 'lat': 44.0805, 'lon': -103.2310, 'pop': 74703},
            {'name': 'Aberdeen', 'state': 'SD', 'lat': 45.4647, 'lon': -98.4865, 'pop': 28495},

            # Wisconsin - Upper Midwest Coverage
            {'name': 'Milwaukee', 'state': 'WI', 'lat': 43.0389, 'lon': -87.9065, 'pop': 577222},
            {'name': 'Madison', 'state': 'WI', 'lat': 43.0731, 'lon': -89.4012, 'pop': 269840},
            {'name': 'Green Bay', 'state': 'WI', 'lat': 44.5133, 'lon': -88.0133, 'pop': 107395},
            {'name': 'Eau Claire', 'state': 'WI', 'lat': 44.8113, 'lon': -91.4985, 'pop': 69421},

            # Iowa - Regional Coverage
            {'name': 'Des Moines', 'state': 'IA', 'lat': 41.5868, 'lon': -93.6250, 'pop': 214133},
            {'name': 'Cedar Rapids', 'state': 'IA', 'lat': 41.9778, 'lon': -91.6656, 'pop': 137710},
            {'name': 'Davenport', 'state': 'IA', 'lat': 41.5236, 'lon': -90.5776, 'pop': 101724},

            # Wyoming - Original Coverage Area
            {'name': 'Cheyenne', 'state': 'WY', 'lat': 41.1400, 'lon': -104.8197, 'pop': 65132},
            {'name': 'Casper', 'state': 'WY', 'lat': 42.8668, 'lon': -106.3131, 'pop': 59038},
            {'name': 'Laramie', 'state': 'WY', 'lat': 41.3114, 'lon': -105.5911, 'pop': 31407},
            {'name': 'Gillette', 'state': 'WY', 'lat': 44.2911, 'lon': -105.5022, 'pop': 33403},
            {'name': 'Rock Springs', 'state': 'WY', 'lat': 41.5875, 'lon': -109.2029, 'pop': 23526},
            {'name': 'Sheridan', 'state': 'WY', 'lat': 44.7972, 'lon': -106.9561, 'pop': 18737},
            {'name': 'Buffalo', 'state': 'WY', 'lat': 44.3483, 'lon': -106.6989, 'pop': 4415},
            {'name': 'Cody', 'state': 'WY', 'lat': 44.5263, 'lon': -109.0565, 'pop': 10028},

            # Montana - Regional Coverage
            {'name': 'Billings', 'state': 'MT', 'lat': 45.7833, 'lon': -108.5007, 'pop': 117116},
            {'name': 'Missoula', 'state': 'MT', 'lat': 46.8721, 'lon': -113.9940, 'pop': 75516},
            {'name': 'Great Falls', 'state': 'MT', 'lat': 47.5053, 'lon': -111.3008, 'pop': 60442},
            {'name': 'Bozeman', 'state': 'MT', 'lat': 45.6770, 'lon': -111.0429, 'pop': 53293},

            # Colorado - Regional Coverage
            {'name': 'Denver', 'state': 'CO', 'lat': 39.7392, 'lon': -104.9903, 'pop': 715522},
            {'name': 'Colorado Springs', 'state': 'CO', 'lat': 38.8339, 'lon': -104.8214, 'pop': 478961},
            {'name': 'Fort Collins', 'state': 'CO', 'lat': 40.5853, 'lon': -105.0844, 'pop': 169810},

            # Utah - Regional Coverage
            {'name': 'Salt Lake City', 'state': 'UT', 'lat': 40.7608, 'lon': -111.8910, 'pop': 200567},

            # Nebraska - Regional Coverage
            {'name': 'Omaha', 'state': 'NE', 'lat': 41.2565, 'lon': -95.9345, 'pop': 486051},
            {'name': 'Lincoln', 'state': 'NE', 'lat': 40.8136, 'lon': -96.7026, 'pop': 295178},
        ]

        # Calculate distances and filter
        cities_with_distance = []
        for city in regional_cities:
            distance = self._calculate_distance(lat, lon, city['lat'], city['lon'])
            cities_with_distance.append({
                'name': f"{city['name']}, {city['state']}",
                'distance': distance,
                'lat': city['lat'],
                'lon': city['lon'],
                'population': city['pop']
            })

        return sorted(cities_with_distance, key=lambda c: c['distance'])

    def _get_geonames_location_context(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Get comprehensive location context using GeoNames APIs
        Returns streets, intersections, and neighborhood information
        """
        context = {
            'nearby_streets': [],
            'nearest_intersection': None,
            'neighborhood': None
        }
        
        try:
            # Find nearby streets
            streets_url = "http://api.geonames.org/findNearbyStreetsJSON"
            streets_params = {'lat': lat, 'lng': lon, 'maxRows': 5}
            
            streets_response = requests.get(streets_url, params=streets_params, timeout=10)
            if streets_response.status_code == 200:
                streets_data = streets_response.json()
                if 'streetSegment' in streets_data:
                    for street in streets_data['streetSegment'][:3]:
                        distance = self._calculate_distance(
                            lat, lon, 
                            float(street['lat']), 
                            float(street['lng'])
                        )
                        context['nearby_streets'].append({
                            'name': street.get('name', 'Unnamed Street'),
                            'distance_miles': round(distance, 2)
                        })
            
            # Find nearest intersection
            intersection_url = "http://api.geonames.org/findNearestIntersectionJSON"
            intersection_params = {'lat': lat, 'lng': lon}
            
            intersection_response = requests.get(intersection_url, params=intersection_params, timeout=10)
            if intersection_response.status_code == 200:
                intersection_data = intersection_response.json()
                if 'intersection' in intersection_data:
                    intersection = intersection_data['intersection']
                    distance = self._calculate_distance(
                        lat, lon,
                        float(intersection['lat']),
                        float(intersection['lng'])
                    )
                    context['nearest_intersection'] = {
                        'street1': intersection.get('street1', ''),
                        'street2': intersection.get('street2', ''),
                        'distance_miles': round(distance, 2)
                    }
            
            # Find neighborhood
            neighborhood_url = "http://api.geonames.org/neighbourhoodJSON"
            neighborhood_params = {'lat': lat, 'lng': lon}
            
            neighborhood_response = requests.get(neighborhood_url, params=neighborhood_params, timeout=10)
            if neighborhood_response.status_code == 200:
                neighborhood_data = neighborhood_response.json()
                if 'neighbourhood' in neighborhood_data:
                    neighborhood = neighborhood_data['neighbourhood']
                    context['neighborhood'] = {
                        'name': neighborhood.get('name', ''),
                        'city': neighborhood.get('city', ''),
                        'adminName1': neighborhood.get('adminName1', '')
                    }
            
        except Exception as e:
            logger.warning(f"Error getting GeoNames location context: {e}")
        
        return context

    def find_nearest_major_city(self, lat: float, lon: float) -> Optional[PlaceResult]:
        """
        Find nearest major city using comprehensive regional database
        Prioritizes cities under 100 miles with population-based significance
        """
        try:
            # Get all cities sorted by distance
            regional_cities = self._find_comprehensive_regional_cities(lat, lon)
            
            if regional_cities:
                # Filter for suitable cities within 100 miles (population 5,000+ or under 50 miles)
                suitable_cities = []
                for city in regional_cities:
                    if (city['distance'] <= 100 and 
                        (city['population'] >= 5000 or city['distance'] <= 50)):
                        suitable_cities.append(city)
                
                # If we found suitable cities, use the closest
                if suitable_cities:
                    closest = suitable_cities[0]
                    
                    # Verify coordinates with Google Places for accuracy (optional enhancement)
                    try:
                        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
                        params = {
                            'input': closest['name'],
                            'inputtype': 'textquery',
                            'fields': 'name,geometry',
                            'key': self.api_key
                        }
                        
                        response = requests.get(url, params=params, timeout=10)
                        response.raise_for_status()
                        data = response.json()
                        
                        if data.get('candidates') and len(data['candidates']) > 0:
                            candidate = data['candidates'][0]
                            exact_distance = self._calculate_distance(
                                lat, lon,
                                candidate['geometry']['location']['lat'],
                                candidate['geometry']['location']['lng']
                            )
                            
                            return PlaceResult(
                                name=candidate['name'],
                                distance_miles=round(exact_distance, 1),
                                lat=candidate['geometry']['location']['lat'],
                                lon=candidate['geometry']['location']['lng'],
                                place_type='major_city'
                            )
                    except Exception as geocode_error:
                        logger.warning(f"Could not verify coordinates with Google Places for {closest['name']}: {geocode_error}")
                    
                    # Use regional database coordinates
                    return PlaceResult(
                        name=closest['name'],
                        distance_miles=round(closest['distance'], 1),
                        lat=closest['lat'],
                        lon=closest['lon'],
                        place_type='major_city'
                    )
                
                # If no suitable cities under 100 miles, use the closest available
                closest_any = regional_cities[0]
                return PlaceResult(
                    name=closest_any['name'],
                    distance_miles=round(closest_any['distance'], 1),
                    lat=closest_any['lat'],
                    lon=closest_any['lon'],
                    place_type='major_city'
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding major city: {e}")
            return None
    
    def get_nearby_places(self, lat: float, lon: float, radius_miles: float = 25) -> Dict[str, Any]:
        """
        Get nearby places using Google Places API for Enhanced Context generation
        Returns structured location context expected by Enhanced Context system
        """
        try:
            # Phase 1: Find event location (smallest nearby place)
            event_location = self.find_nearest_place_by_geocoding(lat, lon)
            
            # Phase 2: Find nearest major city
            nearest_major_city = self.find_nearest_major_city(lat, lon)
            
            # Phase 3: Find other nearby places
            nearby_places_list = []
            
            # Convert miles to meters for Google API
            radius_meters = int(radius_miles * 1609.34)
            
            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                'location': f"{lat},{lon}",
                'radius': radius_meters,
                'key': self.api_key,
                'type': 'establishment'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results'):
                for place in data['results'][:20]:  # Get more results to filter
                    place_types = place.get('types', [])
                    place_name = place['name']
                    
                    # Filter out restaurants, food establishments, and chain stores
                    excluded_types = [
                        'restaurant', 'food', 'meal_takeaway', 'meal_delivery',
                        'bakery', 'cafe', 'bar', 'liquor_store', 'convenience_store',
                        'gas_station', 'atm', 'store', 'supermarket', 'grocery_or_supermarket'
                    ]
                    
                    # Filter out common chain names
                    excluded_names = [
                        'subway', 'mcdonalds', 'burger king', 'pizza', 'kfc', 'taco bell',
                        'walmart', 'target', 'cvs', 'walgreens', 'shell', 'exxon', 'bp'
                    ]
                    
                    # Skip if it's a restaurant or excluded establishment
                    if any(ptype in excluded_types for ptype in place_types):
                        continue
                    
                    if any(name.lower() in place_name.lower() for name in excluded_names):
                        continue
                    
                    place_lat = place['geometry']['location']['lat']
                    place_lon = place['geometry']['location']['lng']
                    distance = self._calculate_distance(lat, lon, place_lat, place_lon)
                    
                    # Only include establishments that are meaningful for location context
                    preferred_types = [
                        'school', 'hospital', 'library', 'park', 'church', 'cemetery',
                        'fire_station', 'police', 'post_office', 'city_hall', 'courthouse',
                        'university', 'museum', 'point_of_interest', 'establishment'
                    ]
                    
                    if any(ptype in preferred_types for ptype in place_types) or len(place_types) == 0:
                        nearby_places_list.append({
                            'name': place['name'],
                            'distance_miles': round(distance, 1),
                            'type': 'establishment',
                            'lat': place_lat,
                            'lon': place_lon
                        })
                
                # Limit to top 10 after filtering
                nearby_places_list = nearby_places_list[:10]
            
            # Sort by distance
            nearby_places_list = sorted(nearby_places_list, key=lambda x: x['distance_miles'])
            
            # Structure response for Enhanced Context
            return {
                'event_location': {
                    'name': event_location.name if event_location else None,
                    'distance_miles': event_location.distance_miles if event_location else 0
                } if event_location else None,
                'nearest_major_city': {
                    'name': nearest_major_city.name if nearest_major_city else None,
                    'distance_miles': nearest_major_city.distance_miles if nearest_major_city else 0
                } if nearest_major_city else None,
                'nearby_places': nearby_places_list
            }
            
        except Exception as e:
            logger.error(f"Error getting nearby places: {e}")
            return {
                'event_location': None,
                'nearest_major_city': None,
                'nearby_places': []
            }

    def find_other_nearby_places(self, lat: float, lon: float, radius_miles: float = 15) -> List[PlaceResult]:
        """
        Phase 3: Find other nearby places within 15 miles
        """
        places = []
        
        try:
            radius_meters = int(radius_miles * 1609.34)
            
            # Search for various place types
            search_types = ['locality', 'sublocality', 'natural_feature', 'park', 'point_of_interest']
            
            # GOOGLE API DISABLED - COST TOO HIGH - USING FREE ALTERNATIVE
            # for place_type in search_types:
            #     url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            #     params = {
            #         'location': f"{lat},{lon}",
            #         'radius': radius_meters,
            #         'type': place_type,
            #         'key': self.api_key
            #     }
            #     
            #     response = requests.get(url, params=params, timeout=10)
            #     response.raise_for_status()
            #     data = response.json()
            #         place_name = result['name']
            #         result_types = result.get('types', [])
            #         if not self._is_valid_place_name(place_name, result_types):
            #             continue
            #         distance = self._calculate_distance(lat, lon, result['geometry']['location']['lat'], result['geometry']['location']['lng'])
            #         if distance <= radius_miles:
            #             places.append(PlaceResult(name=place_name, distance_miles=round(distance, 1), lat=result['geometry']['location']['lat'], lon=result['geometry']['location']['lng'], place_type=place_type))
            
            # USING FREE ALTERNATIVE INSTEAD OF EXPENSIVE GOOGLE API
            return []
            
        except Exception as e:
            logger.error(f"Error finding nearby places: {e}")
            return []
    
    def enrich_location(self, lat: float, lon: float, spc_reference_city: str = None) -> Dict[str, Any]:
        """
        Complete location enrichment using 3-tier Google Places architecture
        """
        enrichment = {
            'nearby_places': []
        }
        
        logger.info(f"Starting Google Places enrichment for {lat:.4f}, {lon:.4f}")
        
        # Phase 1: Find ALL potential event locations and select the closest
        event_location_candidates = []
        
        # Try public places first
        public_place = self.find_event_location(lat, lon)
        if public_place:
            event_location_candidates.append(public_place)
        
        # Try reverse geocoding
        geocoded_place = self.find_nearest_place_by_geocoding(lat, lon)
        if geocoded_place:
            event_location_candidates.append(geocoded_place)
        
        # Get other nearby places for additional candidates
        other_places = self.find_other_nearby_places(lat, lon, radius_miles=5)  # Only within 5 miles for event location
        event_location_candidates.extend(other_places)
        
        # Select the closest candidate as Event Location
        if event_location_candidates:
            event_location = min(event_location_candidates, key=lambda p: p.distance_miles)
            enrichment['nearby_places'].append({
                'name': event_location.name,
                'distance_miles': event_location.distance_miles,
                'approx_lat': event_location.lat,
                'approx_lon': event_location.lon,
                'type': 'primary_location'
            })
            logger.info(f"Event Location: {event_location.name} at {event_location.distance_miles} miles")
        
        # Phase 2: Nearest Major City (no distance limit)
        major_city = self.find_nearest_major_city(lat, lon)
        if major_city:
            enrichment['nearby_places'].append({
                'name': major_city.name,
                'distance_miles': major_city.distance_miles,
                'approx_lat': major_city.lat,
                'approx_lon': major_city.lon,
                'type': 'nearest_city'
            })
            logger.info(f"Nearest Major City: {major_city.name} at {major_city.distance_miles} miles")
        
        # Phase 3: Other Nearby Places (within 15 miles) - exclude already selected places
        other_places = self.find_other_nearby_places(lat, lon)
        existing_names = [p['name'] for p in enrichment['nearby_places']]
        
        for place in other_places:
            if place.name not in existing_names:
                enrichment['nearby_places'].append({
                    'name': place.name,
                    'distance_miles': place.distance_miles,
                    'approx_lat': place.lat,
                    'approx_lon': place.lon,
                    'type': 'nearby_place'
                })
                logger.info(f"Nearby Place: {place.name} at {place.distance_miles} miles")
        
        return enrichment