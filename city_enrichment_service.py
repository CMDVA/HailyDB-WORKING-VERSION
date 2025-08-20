#!/usr/bin/env python3
"""
City Name Enrichment Service for HailyDB Phase 2
Standardizes city names from NWS alert area descriptions for enhanced location targeting
Critical for insurance and restoration industry address-level precision
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class LocationMatch:
    """Represents a matched location with confidence scoring"""
    city: str
    state: str
    confidence: float
    match_type: str  # 'direct', 'pattern', 'county_seat', 'populated_place'
    
class CityEnrichmentService:
    """
    Advanced city name extraction and standardization service
    
    Handles complex NWS area descriptions and extracts meaningful city names
    for insurance/restoration industry location targeting needs.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common directional patterns in NWS descriptions
        self.directional_patterns = [
            r'(\d+)\s+(N|S|E|W|NE|NW|SE|SW|NNE|NNW|SSE|SSW|ENE|ESE|WNW|WSW)\s+(.+)',
            r'(\d+)\s+miles?\s+(north|south|east|west|northeast|northwest|southeast|southwest)\s+of\s+(.+)',
            r'(.+?)\s+(\d+)\s+(N|S|E|W|NE|NW|SE|SW)\s',
        ]
        
        # Patterns for extracting cities from area descriptions
        self.city_extraction_patterns = [
            # "City, ST" format
            r'([A-Za-z\s]+),\s*([A-Z]{2})\b',
            # "including the cities of City1, City2 and City3"
            r'including\s+(?:the\s+)?(?:cities?|areas?|communities?)\s+of\s+([^.;]+)',
            # "near City" patterns
            r'near\s+([A-Za-z\s]+?)(?:\s*,|\s+in|\s+area|\.|$)',
            # "City area" or "City vicinity"
            r'([A-Za-z\s]+?)\s+(?:area|vicinity|region)(?:\s*,|\s+in|\.|$)',
        ]
        
        # Known non-city terms to filter out
        self.non_city_terms = {
            'county', 'parish', 'borough', 'area', 'vicinity', 'region', 'zone',
            'marine', 'coastal', 'offshore', 'inland', 'metro', 'metropolitan',
            'including', 'particularly', 'especially', 'mainly', 'portions',
            'northern', 'southern', 'eastern', 'western', 'central', 'upper', 'lower',
            'and', 'or', 'the', 'of', 'in', 'at', 'on', 'to', 'from', 'with'
        }
        
        # Known city name corrections for common misspellings or abbreviations
        self.city_corrections = {
            'st': 'Saint',
            'ft': 'Fort',
            'mt': 'Mount',
            'n': 'North',
            's': 'South',
            'e': 'East',
            'w': 'West',
        }
    
    def extract_cities_from_area_desc(self, area_desc: str) -> List[LocationMatch]:
        """
        Extract city names from NWS area description with confidence scoring
        
        Args:
            area_desc: NWS area description (e.g., "Carson, TX; Moore, TX")
            
        Returns:
            List of LocationMatch objects with city names and confidence scores
        """
        if not area_desc:
            return []
            
        locations = []
        
        # Primary extraction: County, State format
        primary_matches = self._extract_primary_locations(area_desc)
        locations.extend(primary_matches)
        
        # Secondary extraction: Directional references and city patterns
        secondary_matches = self._extract_secondary_locations(area_desc)
        locations.extend(secondary_matches)
        
        # Deduplication and ranking
        unique_locations = self._deduplicate_and_rank(locations)
        
        self.logger.debug(f"Extracted {len(unique_locations)} cities from: {area_desc[:100]}...")
        
        return unique_locations
    
    def _extract_primary_locations(self, area_desc: str) -> List[LocationMatch]:
        """Extract primary county/city names from standard NWS format"""
        locations = []
        
        # Split by semicolon for multiple areas
        areas = [area.strip() for area in area_desc.split(';')]
        
        for area in areas:
            # Standard "Location, ST" format
            match = re.match(r'^([^,]+),\s*([A-Z]{2})$', area.strip())
            if match:
                location_name = match.group(1).strip()
                state_code = match.group(2).strip()
                
                # For counties, try to extract city names
                if location_name.lower().endswith(' county') or location_name.lower().endswith(' parish'):
                    # This is a county - we'll handle this as a county seat lookup
                    county_name = location_name.replace(' County', '').replace(' Parish', '').strip()
                    
                    # Some counties share names with their county seats
                    potential_city = self._get_county_seat_or_major_city(county_name, state_code)
                    if potential_city:
                        locations.append(LocationMatch(
                            city=potential_city,
                            state=state_code,
                            confidence=0.7,  # Medium confidence for county seat inference
                            match_type='county_seat'
                        ))
                else:
                    # Clean location name as potential city
                    city_name = self._clean_location_name(location_name)
                    
                    if city_name and self._is_valid_city_name(city_name):
                        locations.append(LocationMatch(
                            city=city_name,
                            state=state_code,
                            confidence=0.9,  # High confidence for standard format
                            match_type='direct'
                        ))
            else:
                # Handle single location names without state codes (e.g., "Carson", "Hughes")
                # Try to infer this is a county name and look up county seat
                area_clean = area.strip()
                if area_clean and self._is_valid_city_name(area_clean):
                    # Try multiple state contexts - look for common county names
                    potential_cities = self._resolve_county_to_cities(area_clean)
                    for city, state, confidence in potential_cities:
                        locations.append(LocationMatch(
                            city=city,
                            state=state,
                            confidence=confidence,
                            match_type='county_inference'
                        ))
        
        return locations
    
    def _extract_secondary_locations(self, area_desc: str) -> List[LocationMatch]:
        """Extract cities from directional references and complex patterns"""
        locations = []
        
        # Look for directional patterns (e.g., "10 NNE Recluse")
        for pattern in self.directional_patterns:
            matches = re.finditer(pattern, area_desc, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 3:
                    potential_city = match.group(3).strip()
                    city_name = self._clean_location_name(potential_city)
                    
                    if city_name and self._is_valid_city_name(city_name):
                        # Extract state from context if possible
                        state = self._extract_state_from_context(area_desc)
                        
                        locations.append(LocationMatch(
                            city=city_name,
                            state=state or 'Unknown',
                            confidence=0.7,  # Medium confidence for directional references
                            match_type='pattern'
                        ))
        
        # Look for city extraction patterns
        for pattern in self.city_extraction_patterns:
            matches = re.finditer(pattern, area_desc, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 1:
                    city_list = match.group(1)
                    
                    # Handle lists like "City1, City2 and City3"
                    cities = re.split(r',|\sand\s|\sor\s', city_list)
                    
                    for city in cities:
                        city_name = self._clean_location_name(city.strip())
                        
                        if city_name and self._is_valid_city_name(city_name):
                            state = self._extract_state_from_context(area_desc)
                            
                            locations.append(LocationMatch(
                                city=city_name,
                                state=state or 'Unknown',
                                confidence=0.6,  # Lower confidence for extracted patterns
                                match_type='pattern'
                            ))
        
        return locations
    
    def _clean_location_name(self, location: str) -> str:
        """Clean and standardize location name"""
        if not location:
            return ''
            
        # Remove extra whitespace
        location = re.sub(r'\s+', ' ', location.strip())
        
        # Remove common non-city suffixes
        location = re.sub(r'\s+(County|Parish|Borough)$', '', location, flags=re.IGNORECASE)
        
        # Apply corrections for common abbreviations
        words = location.split()
        corrected_words = []
        
        for word in words:
            word_lower = word.lower()
            if word_lower in self.city_corrections:
                corrected_words.append(self.city_corrections[word_lower])
            else:
                corrected_words.append(word.title())
                
        return ' '.join(corrected_words)
    
    def _is_valid_city_name(self, name: str) -> bool:
        """Validate if a name could be a legitimate city name"""
        if not name or len(name) < 2:
            return False
            
        # Check against non-city terms
        name_lower = name.lower()
        if name_lower in self.non_city_terms:
            return False
            
        # Must contain at least one letter
        if not re.search(r'[A-Za-z]', name):
            return False
            
        # Reject obvious patterns
        if re.match(r'^\d+$', name):  # All numbers
            return False
            
        if len(name) > 50:  # Unreasonably long
            return False
            
        return True
    
    def _extract_state_from_context(self, area_desc: str) -> Optional[str]:
        """Extract state code from area description context"""
        # Look for state codes in the description
        state_match = re.search(r'\b([A-Z]{2})\b', area_desc)
        if state_match:
            return state_match.group(1)
        return None
    
    def _deduplicate_and_rank(self, locations: List[LocationMatch]) -> List[LocationMatch]:
        """Remove duplicates and rank by confidence"""
        # Group by city name (case-insensitive)
        location_groups = {}
        
        for location in locations:
            key = location.city.lower()
            if key not in location_groups:
                location_groups[key] = []
            location_groups[key].append(location)
        
        # Keep the highest confidence match for each city
        unique_locations = []
        for city_matches in location_groups.values():
            best_match = max(city_matches, key=lambda x: x.confidence)
            unique_locations.append(best_match)
        
        # Sort by confidence (highest first)
        unique_locations.sort(key=lambda x: x.confidence, reverse=True)
        
        return unique_locations
    
    def _get_county_seat_or_major_city(self, county_name: str, state_code: str) -> Optional[str]:
        """
        Get county seat or major city for a given county
        For common counties that share names with their seats
        """
        county_city_mapping = {
            # Texas
            'Harris': 'Houston',
            'Dallas': 'Dallas', 
            'Tarrant': 'Fort Worth',
            'Bexar': 'San Antonio',
            'Travis': 'Austin',
            'Collin': 'McKinney',
            'Denton': 'Denton',
            'Fort Bend': 'Richmond',
            
            # California
            'Los Angeles': 'Los Angeles',
            'San Diego': 'San Diego',
            'Orange': 'Santa Ana',
            'Riverside': 'Riverside',
            'San Bernardino': 'San Bernardino',
            'Alameda': 'Oakland',
            'Sacramento': 'Sacramento',
            'Contra Costa': 'Martinez',
            'Fresno': 'Fresno',
            'Kern': 'Bakersfield',
            
            # Florida
            'Miami Dade': 'Miami',
            'Broward': 'Fort Lauderdale',
            'Palm Beach': 'West Palm Beach',
            'Hillsborough': 'Tampa',
            'Orange': 'Orlando',
            'Pinellas': 'Clearwater',
            'Duval': 'Jacksonville',
            
            # New York
            'New York': 'New York',
            'Kings': 'Brooklyn',
            'Queens': 'Queens',
            'Bronx': 'Bronx',
            'Richmond': 'Staten Island',
            'Nassau': 'Mineola',
            'Suffolk': 'Riverhead',
            'Westchester': 'White Plains',
            'Erie': 'Buffalo',
            'Monroe': 'Rochester',
            
            # Other common counties
            'Cook': 'Chicago',  # IL
            'Maricopa': 'Phoenix',  # AZ
            'Clark': 'Las Vegas',  # NV
            'King': 'Seattle',  # WA
            'Wayne': 'Detroit',  # MI
            'Cuyahoga': 'Cleveland',  # OH
            'Fulton': 'Atlanta',  # GA
            'Jefferson': 'Birmingham',  # AL
        }
        
        # Direct mapping
        if county_name in county_city_mapping:
            return county_city_mapping[county_name]
        
        # If county name itself could be a city (many counties named after their seats)
        if self._is_valid_city_name(county_name):
            return county_name
            
        return None
    
    def _resolve_county_to_cities(self, location_name: str) -> List[Tuple[str, str, float]]:
        """
        Resolve a county name to potential cities across multiple states
        Returns list of (city, state, confidence) tuples
        """
        results = []
        
        # Extended county-to-city mapping with state information
        county_mappings = {
            # Texas counties
            'Carson': [('Panhandle', 'TX', 0.8)],  # Carson County, TX
            'Hughes': [('Hughes Springs', 'TX', 0.7)],  # Not a county, but a city
            'Hansford': [('Spearman', 'TX', 0.8)],  # Hansford County, TX
            'Ochiltree': [('Perryton', 'TX', 0.8)],  # Ochiltree County, TX
            'Moore': [('Dumas', 'TX', 0.8)],  # Moore County, TX
            'Dallas': [('Dallas', 'TX', 0.9)],
            'Harris': [('Houston', 'TX', 0.9)],
            'Travis': [('Austin', 'TX', 0.9)],
            'Tarrant': [('Fort Worth', 'TX', 0.9)],
            'Bexar': [('San Antonio', 'TX', 0.9)],
            
            # Oklahoma counties
            'McIntosh': [('Eufaula', 'OK', 0.8)],  # McIntosh County, OK
            'Tulsa': [('Tulsa', 'OK', 0.9)],
            'Oklahoma': [('Oklahoma City', 'OK', 0.9)],
            
            # Kansas counties
            'Sedgwick': [('Wichita', 'KS', 0.9)],
            'Johnson': [('Olathe', 'KS', 0.8)],
            'Wyandotte': [('Kansas City', 'KS', 0.8)],
            
            # Common county names that appear in multiple states
            'Washington': [
                ('Washington', 'PA', 0.6),
                ('Hagerstown', 'MD', 0.6),
                ('Fayetteville', 'AR', 0.6)
            ],
            'Jefferson': [
                ('Birmingham', 'AL', 0.6),
                ('Louisville', 'KY', 0.6),
                ('Jefferson City', 'MO', 0.6)
            ],
            'Franklin': [
                ('Columbus', 'OH', 0.6),
                ('Franklin', 'TN', 0.6)
            ],
            'Jackson': [
                ('Jackson', 'MS', 0.6),
                ('Jackson', 'TN', 0.6),
                ('Jackson', 'MI', 0.6)
            ]
        }
        
        # Check direct mapping
        if location_name in county_mappings:
            results.extend(county_mappings[location_name])
        
        # If it's a potential city name itself (many places have same name as county)
        if self._is_valid_city_name(location_name) and location_name not in county_mappings:
            # Default to treating as city name with unknown state
            results.append((location_name, 'Unknown', 0.5))
        
        return results
    
    def enrich_alert_with_cities(self, alert) -> List[str]:
        """
        Enrich an alert with standardized city names
        
        Args:
            alert: Alert model instance
            
        Returns:
            List of standardized city names
        """
        if not alert.area_desc:
            return []
            
        location_matches = self.extract_cities_from_area_desc(alert.area_desc)
        
        # Extract just the city names with high/medium confidence
        city_names = [
            match.city for match in location_matches 
            if match.confidence >= 0.5  # Only include confident matches
        ]
        
        self.logger.debug(f"Enriched alert {alert.id} with cities: {city_names}")
        
        return city_names

# Global service instance
city_enrichment_service = CityEnrichmentService()