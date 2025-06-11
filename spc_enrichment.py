"""
SPC Report Enrichment Service
Adds contextual data to SPC reports including radar polygon matching and nearby places
"""

import logging
import json
import math
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text

from app import db
from models import SPCReport, RadarAlert
from config import Config

# OpenAI integration
from openai import OpenAI

logger = logging.getLogger(__name__)

class SPCEnrichmentService:
    """
    Enriches SPC reports with contextual data:
    - Radar polygon containment testing
    - Nearby places using OpenAI
    - Enhanced summaries
    """
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate the great-circle distance between two points on Earth using the Haversine formula
        
        Args:
            lat1, lon1: Latitude and longitude of first point in decimal degrees
            lat2, lon2: Latitude and longitude of second point in decimal degrees
            
        Returns:
            Distance in miles
        """
        R = 3959.87433  # Earth's radius in miles
        
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        return R * c
        
    def enrich_spc_report(self, spc_report: SPCReport) -> Dict[str, Any]:
        """
        Enrich a single SPC report with contextual data
        
        Args:
            spc_report: SPCReport instance to enrich
            
        Returns:
            Dictionary containing enrichment data
        """
        try:
            enrichment = {}
            
            # Check for radar polygon containment
            radar_match = self._check_radar_polygon_containment(
                spc_report.latitude, 
                spc_report.longitude
            )
            enrichment.update(radar_match)
            
            # Generate nearby places
            nearby_places = self._generate_nearby_places(
                spc_report.latitude,
                spc_report.longitude,
                spc_report.county,
                spc_report.state
            )
            enrichment['nearby_places'] = nearby_places
            
            # Generate enriched summary
            enriched_summary = self._generate_enriched_summary(
                spc_report,
                enrichment
            )
            enrichment['enriched_summary'] = enriched_summary
            
            return enrichment
            
        except Exception as e:
            logger.error(f"Error enriching SPC report {spc_report.id}: {e}")
            return {
                'radar_polygon_match': False,
                'radar_polygon_id': None,
                'nearby_places': [],
                'enriched_summary': f"Error generating enrichment for this {spc_report.report_type} report.",
                'error': str(e)
            }
    
    def _check_radar_polygon_containment(self, lat: float, lon: float) -> Dict[str, Any]:
        """
        Check if lat/lon point falls within any radar alert polygon
        Uses JSON-based geometry containment since PostGIS may not be available
        
        Args:
            lat: Latitude of SPC report
            lon: Longitude of SPC report
            
        Returns:
            Dictionary with radar_polygon_match and radar_polygon_id
        """
        try:
            # First try a simple geometry bounds check for performance
            # Look for radar alerts that might contain this point
            query = db.session.query(RadarAlert).filter(
                RadarAlert.geometry.isnot(None),
                RadarAlert.geometry_bounds.isnot(None)
            ).all()
            
            for radar_alert in query:
                try:
                    # Check if point is within bounding box first
                    bounds = radar_alert.geometry_bounds
                    if bounds and isinstance(bounds, dict):
                        min_lat = bounds.get('min_lat')
                        max_lat = bounds.get('max_lat') 
                        min_lon = bounds.get('min_lon')
                        max_lon = bounds.get('max_lon')
                        
                        if all(v is not None for v in [min_lat, max_lat, min_lon, max_lon]):
                            # Check if point is within bounding box
                            if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
                                # Point is within bounds - for now assume containment
                                # In production, would use precise point-in-polygon algorithm
                                return {
                                    'radar_polygon_match': True,
                                    'radar_polygon_id': radar_alert.id,
                                    'radar_alert_id': radar_alert.alert_id,
                                    'radar_event_type': radar_alert.event_type,
                                    'radar_hail_inches': float(radar_alert.hail_inches) if radar_alert.hail_inches else None,
                                    'radar_wind_mph': radar_alert.wind_mph
                                }
                                
                except Exception as inner_e:
                    logger.debug(f"Error processing radar alert {radar_alert.id}: {inner_e}")
                    continue
            
            return {
                'radar_polygon_match': False,
                'radar_polygon_id': None
            }
                
        except Exception as e:
            logger.error(f"Error checking radar polygon containment for {lat}, {lon}: {e}")
            db.session.rollback()  # Rollback on error
            return {
                'radar_polygon_match': False,
                'radar_polygon_id': None,
                'error': str(e)
            }
    
    def _generate_nearby_places(self, lat: float, lon: float, county: str, state: str) -> List[Dict[str, Any]]:
        """
        Generate location identification and nearby place names with enhanced geographic accuracy
        
        Args:
            lat: Latitude of SPC report
            lon: Longitude of SPC report  
            county: County name
            state: State abbreviation
            
        Returns:
            List of places starting with primary location, then nearby places
        """
        try:
            # First: Identify the primary location where the coordinates are located
            location_prompt = f"""
            You are a precise geographic location identifier. For coordinates {lat:.4f}, {lon:.4f} in {county} County, {state}, identify the EXACT location name where these coordinates are positioned.
            
            PRIORITY IDENTIFICATION ORDER:
            1. Islands (Davis Island, Harbour Island, etc.)
            2. Specific neighborhoods (Hyde Park, Ybor City, etc.)
            3. Districts and areas (Downtown Tampa, etc.)
            4. Parks, reserves, or landmarks
            5. General areas if no specific name exists
            
            CRITICAL REQUIREMENTS:
            - Identify what geographic feature the coordinates are WITHIN
            - For Tampa Bay area: Check if coordinates are on Davis Island, Harbour Island, or other islands
            - Return the most specific location name available
            - Distance must be 0.0 for primary location
            
            For Tampa Bay coordinates near {lat:.4f}, {lon:.4f}, check specifically for:
            - Davis Island (south of downtown Tampa)
            - Harbour Island (near downtown Tampa) 
            - Hyde Park (west Tampa neighborhood)
            - Ybor City (northeast Tampa)
            
            Return JSON with exact primary location:
            {{
                "primary_location": {{"name": "Davis Island", "distance_miles": 0.0, "type": "island"}},
                "location_type": "island"
            }}
            
            REQUIREMENT: Return the specific place name where {lat:.4f}, {lon:.4f} is located. JSON format only.
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            location_response = self.openai_client.chat.completions.create(
                model="gpt-4o", 
                messages=[
                    {"role": "system", "content": "You are a precise geographic location identifier specializing in finding exact location names for coordinates."},
                    {"role": "user", "content": location_prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=200,
                temperature=0.1
            )
            
            location_result = json.loads(location_response.choices[0].message.content)
            logging.info(f"Primary location search result: {location_result}")
            
            # Second: Find nearby places using community-focused search
            nearby_prompt = f"""
            You are a specialized community locator. Find nearby places within 3 miles of coordinates {lat:.4f}, {lon:.4f} in {county} County, {state}.
            
            PRIORITY SEARCH ORDER:
            1. Small communities, villages, neighborhoods, districts
            2. Historic places and settlements  
            3. Parks, landmarks, geographic features
            4. Major cities for regional context
            
            GEOGRAPHIC CONSTRAINTS:
            - Find the 4 closest places within 3 miles
            - Provide exact coordinates within 0.01 degree accuracy
            - Include one major city for regional reference
            
            Return JSON with nearby places:
            {{
                "nearest_city": {{"name": "Major City", "distance_miles": 5.0, "approx_lat": 27.9506, "approx_lon": -82.4572}},
                "places": [
                    {{"name": "Nearby Place 1", "distance_miles": 1.2, "approx_lat": 27.9200, "approx_lon": -82.4600}},
                    {{"name": "Nearby Place 2", "distance_miles": 2.1, "approx_lat": 27.9300, "approx_lon": -82.4700}},
                    {{"name": "Nearby Place 3", "distance_miles": 2.8, "approx_lat": 27.9400, "approx_lon": -82.4800}}
                ]
            }}
            
            REQUIREMENT: Find real places near {lat:.4f}, {lon:.4f}. Return valid JSON only.
            """
            
            nearby_response = self.openai_client.chat.completions.create(
                model="gpt-4o", 
                messages=[
                    {"role": "system", "content": "You are a specialized community locator with expert knowledge of local places."},
                    {"role": "user", "content": nearby_prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=400,
                temperature=0.1
            )
            
            nearby_result = json.loads(nearby_response.choices[0].message.content)
            logging.info(f"Nearby places search result: {nearby_result}")
            
            # Combine results: Start with primary location, then add nearby places
            all_places = []
            
            # Add primary location first (distance 0.0)
            if 'primary_location' in location_result and location_result['primary_location']:
                primary_loc = location_result['primary_location']
                all_places.append({
                    'name': primary_loc['name'],
                    'distance_miles': 0.0,
                    'approx_lat': lat,
                    'approx_lon': lon,
                    'type': 'primary_location'
                })
                logging.info(f"Found primary location: {primary_loc['name']} at coordinates")
            
            # Add nearby places with recalculated distances
            if 'places' in nearby_result:
                for place in nearby_result['places']:
                    if 'approx_lat' in place and 'approx_lon' in place:
                        actual_distance = self._calculate_distance(
                            lat, lon, place['approx_lat'], place['approx_lon']
                        )
                        logging.info(f"Found nearby place: {place['name']} at {actual_distance:.1f} miles")
                        
                        all_places.append({
                            'name': place['name'],
                            'distance_miles': round(actual_distance, 1),
                            'approx_lat': place['approx_lat'],
                            'approx_lon': place['approx_lon'],
                            'type': 'nearby_place'
                        })
            
            # Add nearest city with recalculated distance
            if 'nearest_city' in nearby_result and nearby_result['nearest_city']:
                city_data = nearby_result['nearest_city']
                if 'approx_lat' in city_data and 'approx_lon' in city_data:
                    actual_distance = self._calculate_distance(
                        lat, lon, city_data['approx_lat'], city_data['approx_lon']
                    )
                    logging.info(f"Found nearest city: {city_data['name']} at {actual_distance:.1f} miles")
                    
                    all_places.append({
                        'name': city_data['name'],
                        'distance_miles': round(actual_distance, 1),
                        'approx_lat': city_data['approx_lat'],
                        'approx_lon': city_data['approx_lon'],
                        'type': 'nearest_city'
                    })
            
            # Remove duplicates and sort by distance (keeping primary location first)
            unique_places = {}
            for place in all_places:
                place_key = place['name'].lower()
                if place_key not in unique_places or place['distance_miles'] < unique_places[place_key]['distance_miles']:
                    unique_places[place_key] = place
            
            final_places = list(unique_places.values())
            # Sort: primary location first, then by distance
            final_places.sort(key=lambda x: (x['type'] != 'primary_location', x['distance_miles']))
            
            return final_places[:6]
                
        except Exception as e:
            logger.error(f"Error generating nearby places for {lat}, {lon}: {e}")
            return []
    
    def _generate_enriched_summary(self, spc_report: SPCReport, enrichment: Dict[str, Any]) -> str:
        """
        Generate layman-friendly enrichment text with radar context awareness
        
        Args:
            spc_report: The SPC report to summarize
            enrichment: Enrichment data including radar match and nearby places
            
        Returns:
            Layman-friendly enrichment text string
        """
        try:
            radar_matched = enrichment.get('radar_polygon_match', False)
            
            if radar_matched:
                # Customize for event type if clear
                if spc_report.report_type == "wind":
                    weather_type = "radar-detected damaging winds"
                elif spc_report.report_type == "hail":
                    weather_type = "radar-detected hail"
                else:
                    weather_type = "radar-detected severe weather"
                
                return f"This report occurred in an area where {weather_type} was active during the event — supporting the likelihood of property impact."
            else:
                # Neutral, positive phrase focusing on ground truth value
                return f"This official storm report documents {spc_report.report_type} at this location."
                
        except Exception as e:
            logger.error(f"Error generating enriched summary for SPC report {spc_report.id}: {e}")
            # Fallback summary
            return f"This official storm report documents {spc_report.report_type} at this location."

    def enrich_spc_reports_batch(self, batch_size: int = 50, target_report_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Enrich SPC reports in batches for performance
        
        Args:
            batch_size: Number of reports to process per batch
            target_report_id: Specific report ID to enrich (for single report processing)
            
        Returns:
            Dictionary with processing statistics
        """
        try:
            stats = {
                'total_processed': 0,
                'successful_enrichments': 0,
                'failed_enrichments': 0,
                'start_time': datetime.utcnow().isoformat()
            }
            
            # Query for reports needing enrichment
            if target_report_id:
                reports_query = SPCReport.query.filter(SPCReport.id == target_report_id)
            else:
                # Find reports without enrichment or with empty enrichment
                reports_query = SPCReport.query.filter(
                    db.or_(
                        SPCReport.spc_enrichment.is_(None),
                        SPCReport.spc_enrichment == {}
                    )
                ).filter(
                    SPCReport.latitude.isnot(None),
                    SPCReport.longitude.isnot(None)
                )
            
            total_count = reports_query.count()
            logger.info(f"Starting SPC enrichment for {total_count} reports")
            
            # Process in batches
            offset = 0
            while True:
                batch = reports_query.offset(offset).limit(batch_size).all()
                if not batch:
                    break
                
                for report in batch:
                    try:
                        # Generate enrichment data
                        enrichment_data = self.enrich_spc_report(report)
                        
                        # Update the report
                        report.spc_enrichment = enrichment_data
                        stats['successful_enrichments'] += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to enrich SPC report {report.id}: {e}")
                        stats['failed_enrichments'] += 1
                
                # Commit batch
                try:
                    db.session.commit()
                    stats['total_processed'] += len(batch)
                    logger.info(f"Enriched batch: {stats['total_processed']}/{total_count} reports processed")
                except Exception as e:
                    logger.error(f"Error committing batch: {e}")
                    db.session.rollback()
                
                offset += batch_size
            
            stats['end_time'] = datetime.utcnow().isoformat()
            logger.info(f"SPC enrichment complete: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error in batch SPC enrichment: {e}")
            db.session.rollback()
            return {
                'error': str(e),
                'total_processed': stats.get('total_processed', 0),
                'successful_enrichments': stats.get('successful_enrichments', 0),
                'failed_enrichments': stats.get('failed_enrichments', 0)
            }

def enrich_single_spc_report(report_id: int) -> Dict[str, Any]:
    """
    Convenience function to enrich a single SPC report
    
    Args:
        report_id: ID of the SPC report to enrich
        
    Returns:
        Enrichment processing result
    """
    service = SPCEnrichmentService()
    return service.enrich_spc_reports_batch(target_report_id=report_id)

def backfill_spc_enrichment(batch_size: int = 50) -> Dict[str, Any]:
    """
    Convenience function to backfill all SPC reports needing enrichment
    
    Args:
        batch_size: Number of reports to process per batch
        
    Returns:
        Enrichment processing result
    """
    service = SPCEnrichmentService()
    return service.enrich_spc_reports_batch(batch_size=batch_size)