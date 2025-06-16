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
            
            for place_type in self.priority_place_types:
                url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                params = {
                    'location': f"{lat},{lon}",
                    'radius': radius_meters,
                    'type': place_type,
                    'key': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if data.get('results'):
                    # Get closest place of this type
                    closest_place = min(data['results'], key=lambda p: self._calculate_distance(
                        lat, lon, 
                        p['geometry']['location']['lat'], 
                        p['geometry']['location']['lng']
                    ))
                    
                    distance = self._calculate_distance(
                        lat, lon,
                        closest_place['geometry']['location']['lat'],
                        closest_place['geometry']['location']['lng']
                    )
                    
                    if distance <= radius_miles:
                        return PlaceResult(
                            name=closest_place['name'],
                            distance_miles=round(distance, 1),
                            lat=closest_place['geometry']['location']['lat'],
                            lon=closest_place['geometry']['location']['lng'],
                            place_type=place_type,
                            place_id=closest_place.get('place_id')
                        )
            
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
        Returns nearest CDP/town/city name with precise coordinates
        Filters out large geographical areas
        """
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'latlng': f"{lat},{lon}",
                'key': self.api_key,
                'result_type': 'locality|sublocality|neighborhood|administrative_area_level_3'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('results'):
                # Get the most specific place name
                for result in data['results']:
                    place_name = None
                    place_types = result.get('types', [])
                    
                    # Extract locality name from address components
                    for component in result['address_components']:
                        types = component['types']
                        if 'locality' in types:
                            place_name = component['long_name']
                            break
                        elif 'sublocality' in types:
                            place_name = component['long_name']
                            break
                        elif 'neighborhood' in types:
                            place_name = component['long_name']
                            break
                        elif 'administrative_area_level_3' in types:
                            place_name = component['long_name']
                            break
                    
                    # Check if this is a valid place name (not a large geographical area)
                    if place_name and self._is_valid_place_name(place_name, place_types):
                        place_lat = result['geometry']['location']['lat']
                        place_lon = result['geometry']['location']['lng']
                        distance = self._calculate_distance(lat, lon, place_lat, place_lon)
                        
                        return PlaceResult(
                            name=place_name,
                            distance_miles=round(distance, 1),
                            lat=place_lat,
                            lon=place_lon,
                            place_type='locality'
                        )
            
            return None
            
        except Exception as e:
            logger.error(f"Error in Google reverse geocoding: {e}")
            return None
    
    def find_nearest_major_city(self, lat: float, lon: float) -> Optional[PlaceResult]:
        """
        Find nearest major city for regional context (no distance limit)
        Uses direct geocoding for known major cities to bypass API radius limitations
        """
        try:
            # Pre-defined major cities with approximate coordinates for Wyoming region
            major_cities = [
                {'name': 'Gillette', 'lat': 44.2911, 'lon': -105.5022},
                {'name': 'Casper', 'lat': 42.8668, 'lon': -106.3131},
                {'name': 'Cheyenne', 'lat': 41.1400, 'lon': -104.8197},
                {'name': 'Laramie', 'lat': 41.3114, 'lon': -105.5911},
                {'name': 'Rock Springs', 'lat': 41.5875, 'lon': -109.2029},
                {'name': 'Sheridan', 'lat': 44.7972, 'lon': -106.9561},
                {'name': 'Buffalo', 'lat': 44.3483, 'lon': -106.6989},
                {'name': 'Cody', 'lat': 44.5263, 'lon': -109.0565},
                {'name': 'Rawlins', 'lat': 41.7911, 'lon': -107.2387},
                {'name': 'Riverton', 'lat': 43.0242, 'lon': -108.3801},
                # Major regional cities
                {'name': 'Billings', 'lat': 45.7833, 'lon': -108.5007},
                {'name': 'Rapid City', 'lat': 44.0805, 'lon': -103.2310},
                {'name': 'Denver', 'lat': 39.7392, 'lon': -104.9903},
                {'name': 'Salt Lake City', 'lat': 40.7608, 'lon': -111.8910}
            ]
            
            # Calculate distances to all major cities and find the closest
            city_distances = []
            for city in major_cities:
                distance = self._calculate_distance(lat, lon, city['lat'], city['lon'])
                city_distances.append({
                    'name': city['name'],
                    'distance': distance,
                    'lat': city['lat'],
                    'lon': city['lon']
                })
            
            # Return the closest major city
            if city_distances:
                closest_city = min(city_distances, key=lambda c: c['distance'])
                
                # Verify this city exists using Google Places to get exact coordinates
                try:
                    url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
                    params = {
                        'input': f"{closest_city['name']} city",
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
                    logger.warning(f"Could not verify coordinates for {closest_city['name']}: {geocode_error}")
                
                # Fallback to approximate coordinates if geocoding fails
                return PlaceResult(
                    name=closest_city['name'],
                    distance_miles=round(closest_city['distance'], 1),
                    lat=closest_city['lat'],
                    lon=closest_city['lon'],
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
            
            for place_type in search_types:
                url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
                params = {
                    'location': f"{lat},{lon}",
                    'radius': radius_meters,
                    'type': place_type,
                    'key': self.api_key
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                for result in data.get('results', [])[:5]:  # Limit results per type
                    place_name = result['name']
                    result_types = result.get('types', [])
                    
                    # Filter out large geographical areas
                    if not self._is_valid_place_name(place_name, result_types):
                        continue
                        
                    distance = self._calculate_distance(
                        lat, lon,
                        result['geometry']['location']['lat'],
                        result['geometry']['location']['lng']
                    )
                    
                    if distance <= radius_miles:
                        places.append(PlaceResult(
                            name=place_name,
                            distance_miles=round(distance, 1),
                            lat=result['geometry']['location']['lat'],
                            lon=result['geometry']['location']['lng'],
                            place_type=place_type
                        ))
            
            # Remove duplicates and sort by distance
            unique_places = {}
            for place in places:
                if place.name not in unique_places or place.distance_miles < unique_places[place.name].distance_miles:
                    unique_places[place.name] = place
            
            return sorted(unique_places.values(), key=lambda p: p.distance_miles)[:6]
            
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