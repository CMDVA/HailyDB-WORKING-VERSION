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
from google_places_service import GooglePlacesService

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
        self.google_places = GooglePlacesService()
    
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
            
            # Generate nearby places using Google Places API
            spc_reference_city = self._extract_spc_reference_city(
                spc_report.location if hasattr(spc_report, 'location') else None
            ) if hasattr(spc_report, 'location') else None
            
            google_places_data = self.google_places.enrich_location(
                spc_report.latitude,
                spc_report.longitude,
                spc_reference_city
            )
            enrichment.update(google_places_data)
            
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
    
    def _extract_spc_reference_city(self, location: str) -> Optional[str]:
        """
        Extract the reference city from SPC location field (e.g., "10 NNE Recluse" -> "Recluse")
        
        Args:
            location: SPC location field text
            
        Returns:
            Reference city name or None if not found
        """
        if not location:
            return None
            
        # Common SPC location patterns: "10 NNE Recluse", "5 S Dallas", "2 E Los Angeles"
        import re
        
        # Pattern to match: optional distance + direction + city name
        # Examples: "10 NNE Recluse", "5 S Dallas", "2 E Los Angeles", "Dallas"
        patterns = [
            r'\d+\s+[NSEW]{1,3}\s+(.+)$',  # "10 NNE Recluse" -> "Recluse"
            r'\d+\s+[NSEW]{1,3}\s+(.+?)\s*$',  # Handle trailing spaces
            r'^(.+)$'  # Fallback to entire location if no distance/direction
        ]
        
        for pattern in patterns:
            match = re.search(pattern, location.strip(), re.IGNORECASE)
            if match:
                city = match.group(1).strip()
                # Filter out obvious non-city patterns
                if len(city) > 1 and not city.isdigit():
                    return city
                    
        return None


    
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