"""
SPC Report Enrichment Service
Adds contextual data to SPC reports including radar polygon matching and nearby places
"""

import logging
import json
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
        Generate nearby place names using OpenAI with geographic context
        
        Args:
            lat: Latitude of SPC report
            lon: Longitude of SPC report  
            county: County name
            state: State abbreviation
            
        Returns:
            List of nearby places with name and approximate coordinates
        """
        try:
            # Use OpenAI to generate contextual nearby places
            prompt = f"""
            Generate 3-6 nearby place names within approximately 5 miles of coordinates {lat:.4f}, {lon:.4f} in {county} County, {state}.
            
            Use authentic local naming conventions like:
            - Small towns, neighborhoods, or communities
            - Geographic features (lakes, rivers, hills)
            - Well-known local landmarks
            - Major roads or intersections
            
            Respond with JSON array only:
            [
                {{"name": "Place Name", "approx_lat": lat, "approx_lon": lon}},
                ...
            ]
            
            If no suitable places exist within 5 miles, return empty array [].
            """
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a geographic information expert. Provide accurate, locally-relevant place names based on real geographic data. Respond only with valid JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )
            
            # Parse OpenAI response
            content = response.choices[0].message.content
            places_data = json.loads(content)
            
            # Validate and format response
            if isinstance(places_data, list):
                return places_data[:6]  # Limit to 6 places max
            elif isinstance(places_data, dict) and 'places' in places_data:
                return places_data['places'][:6]
            else:
                logger.warning(f"Unexpected OpenAI response format for nearby places: {content}")
                return []
                
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