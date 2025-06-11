"""
City Name Parser for HailyDB
Extracts city names from NWS area_desc fields for radar-detected events
"""

import re
from typing import List, Set
from sqlalchemy.orm import Session
from models import Alert
import logging

logger = logging.getLogger(__name__)

class CityNameParser:
    """
    Parses city names from NWS area_desc field patterns
    Handles various formats like "City, ST", "County, ST", multi-city strings
    """
    
    def __init__(self):
        # Common county suffixes to identify county names vs city names
        self.county_suffixes = {
            'county', 'co', 'parish', 'borough', 'census area', 'city and borough', 'municipality'
        }
        
        # Direction indicators that are part of location names
        self.directions = {
            'north', 'northern', 'south', 'southern', 'east', 'eastern', 
            'west', 'western', 'central', 'upper', 'lower', 'northeast', 
            'northwest', 'southeast', 'southwest'
        }
        
        # Common prefixes that indicate geographic areas
        self.area_prefixes = {
            'lake', 'mount', 'mt', 'point', 'cape', 'fort', 'st', 'saint'
        }
    
    def parse_area_desc(self, area_desc: str) -> List[str]:
        """
        Parse area_desc field to extract city names
        
        Args:
            area_desc: NWS area description string
            
        Returns:
            List of extracted city/location names
        """
        if not area_desc:
            return []
            
        city_names = set()
        
        # Split by semicolons and commas to handle multiple areas
        areas = re.split(r'[;,]', area_desc)
        
        for area in areas:
            area = area.strip()
            if not area:
                continue
                
            extracted = self._extract_from_area(area)
            city_names.update(extracted)
        
        # Filter out obvious non-city names and sort
        filtered_cities = []
        for city in city_names:
            if self._is_valid_city_name(city):
                filtered_cities.append(city)
        
        return sorted(list(set(filtered_cities)))
    
    def _extract_from_area(self, area: str) -> Set[str]:
        """Extract city names from a single area string"""
        cities = set()
        
        # Remove state codes (2-letter codes at end)
        area_clean = re.sub(r'\s+[A-Z]{2}$', '', area.strip())
        
        # Pattern 1: "City, ST" or "City"
        # Pattern 2: "Direction City" (e.g., "Eastern Clay")
        # Pattern 3: "City County" where we want the city part
        
        # Handle direction + location patterns (e.g., "Eastern Clay", "Western Putnam")
        direction_match = re.match(r'^(North|Northern|South|Southern|East|Eastern|West|Western|Central|Upper|Lower|Northeast|Northwest|Southeast|Southwest)\s+(.+)$', area_clean, re.IGNORECASE)
        if direction_match:
            direction = direction_match.group(1)
            location = direction_match.group(2)
            
            # Check if location is a county
            if self._is_county_name(location):
                # For "Eastern Clay County", extract "Clay"
                county_base = self._remove_county_suffix(location)
                if county_base:
                    cities.add(f"{direction} {county_base}")
            else:
                # For "Eastern City", keep as is
                cities.add(f"{direction} {location}")
            
            return cities
        
        # Handle simple cases
        if not self._is_county_name(area_clean):
            # Not a county, likely a city
            cities.add(area_clean)
        else:
            # It's a county, extract the base name
            county_base = self._remove_county_suffix(area_clean)
            if county_base:
                cities.add(county_base)
        
        return cities
    
    def _is_county_name(self, name: str) -> bool:
        """Check if a name appears to be a county"""
        name_lower = name.lower()
        return any(suffix in name_lower for suffix in self.county_suffixes)
    
    def _remove_county_suffix(self, name: str) -> str:
        """Remove county suffixes to get base name"""
        name_clean = name.strip()
        
        # Remove common county suffixes
        for suffix in self.county_suffixes:
            pattern = rf'\s+{re.escape(suffix)}$'
            name_clean = re.sub(pattern, '', name_clean, flags=re.IGNORECASE)
        
        return name_clean.strip()
    
    def _is_valid_city_name(self, name: str) -> bool:
        """Filter out invalid city names"""
        if not name or len(name.strip()) < 2:
            return False
            
        name = name.strip()
        
        # Skip single letters or numbers
        if len(name) == 1 or name.isdigit():
            return False
            
        # Skip common non-city patterns
        skip_patterns = [
            r'^\d+\s*(n|s|e|w|ne|nw|se|sw|north|south|east|west)',  # "5 N", "10 SW"
            r'coastal waters',
            r'offshore waters',
            r'nm$',  # nautical miles
            r'extending from',
            r'out \d+',
        ]
        
        for pattern in skip_patterns:
            if re.search(pattern, name.lower()):
                return False
        
        return True

def parse_and_update_city_names(db: Session, alert_id: str = None, batch_size: int = 100) -> dict:
    """
    Parse and update city_names for alerts with radar_indicated data
    
    Args:
        db: Database session
        alert_id: Optional specific alert ID to update
        batch_size: Number of alerts to process in each batch
        
    Returns:
        Dictionary with update statistics
    """
    parser = CityNameParser()
    stats = {
        'processed': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0
    }
    
    try:
        # Build query for alerts with radar data
        query = db.query(Alert).filter(Alert.radar_indicated.isnot(None))
        
        if alert_id:
            query = query.filter(Alert.id == alert_id)
        else:
            # Only process alerts without city_names or with empty city_names
            # Use raw SQL to handle ARRAY column properly
            query = query.filter(
                db.text("(city_names IS NULL OR array_length(city_names, 1) IS NULL)")
            )
        
        alerts = query.limit(batch_size).all()
        
        for alert in alerts:
            stats['processed'] += 1
            
            try:
                if not alert.area_desc:
                    stats['skipped'] += 1
                    continue
                
                # Parse city names
                city_names = parser.parse_area_desc(alert.area_desc)
                
                # Update alert
                alert.city_names = city_names
                stats['updated'] += 1
                
                logger.debug(f"Updated alert {alert.id}: {alert.area_desc} -> {city_names}")
                
            except Exception as e:
                logger.error(f"Failed to parse city names for alert {alert.id}: {e}")
                stats['failed'] += 1
        
        # Commit changes
        db.commit()
        logger.info(f"City name parsing complete: {stats}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"City name parsing failed: {e}")
        raise
    
    return stats

def backfill_all_city_names(db: Session, batch_size: int = 500) -> dict:
    """
    Backfill city_names for all radar-detected alerts
    """
    total_stats = {
        'processed': 0,
        'updated': 0,
        'failed': 0,
        'skipped': 0,
        'batches': 0
    }
    
    while True:
        batch_stats = parse_and_update_city_names(db, batch_size=batch_size)
        
        total_stats['processed'] += batch_stats['processed']
        total_stats['updated'] += batch_stats['updated']
        total_stats['failed'] += batch_stats['failed']
        total_stats['skipped'] += batch_stats['skipped']
        total_stats['batches'] += 1
        
        logger.info(f"Batch {total_stats['batches']} complete: {batch_stats}")
        
        # If we processed fewer than batch_size, we're done
        if batch_stats['processed'] < batch_size:
            break
    
    logger.info(f"Backfill complete: {total_stats}")
    return total_stats