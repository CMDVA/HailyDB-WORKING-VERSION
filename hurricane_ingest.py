"""
Hurricane Track Ingestion Service
Ingests historical hurricane track data from NOAA sources for HailyDB
Supports field intelligence for roof/property damage assessment
"""

import hashlib
import logging
import requests
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from models import HurricaneTrack
from app import db

logger = logging.getLogger(__name__)

class HurricaneIngestService:
    """
    Service for ingesting NOAA hurricane track data
    Handles deduplication, normalization, and storage
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'HailyDB-Hurricane-Ingestion/1.0 (contact@hailydb.com)'
        })
    
    def hash_track_row(self, storm_id: str, timestamp: datetime, lat: float, lon: float) -> str:
        """Generate SHA256 hash for track point deduplication"""
        row_string = f"{storm_id}-{timestamp.isoformat()}-{lat}-{lon}"
        return hashlib.sha256(row_string.encode()).hexdigest()
    
    def ingest_hurricane_data(self, data_source: str = "manual") -> Dict[str, Any]:
        """
        Main ingestion method for hurricane track data
        
        Args:
            data_source: Source identifier for logging
            
        Returns:
            Dictionary with ingestion statistics
        """
        logger.info(f"Starting hurricane track ingestion from {data_source}")
        
        stats = {
            'total_processed': 0,
            'new_records': 0,
            'duplicate_records': 0,
            'failed_records': 0,
            'storms_processed': 0,
            'errors': []
        }
        
        try:
            # For initial implementation, we'll use NOAA's Hurricane Database (HURDAT2)
            # This is a sample implementation - actual data source would be configured
            hurricane_data = self._fetch_noaa_hurdat2_data()
            
            if not hurricane_data:
                logger.warning("No hurricane data available from source")
                return stats
            
            # Process each storm in the dataset
            for storm_data in hurricane_data:
                try:
                    storm_stats = self._process_storm(storm_data)
                    stats['total_processed'] += storm_stats['processed']
                    stats['new_records'] += storm_stats['new']
                    stats['duplicate_records'] += storm_stats['duplicates']
                    stats['failed_records'] += storm_stats['failed']
                    stats['storms_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process storm {storm_data.get('storm_id', 'unknown')}: {e}")
                    stats['failed_records'] += 1
                    stats['errors'].append(str(e))
            
            self.db.session.commit()
            logger.info(f"Hurricane ingestion complete: {stats['new_records']} new tracks, {stats['duplicate_records']} duplicates")
            
        except Exception as e:
            logger.error(f"Hurricane ingestion failed: {e}")
            self.db.session.rollback()
            stats['errors'].append(str(e))
            
        return stats
    
    def _fetch_noaa_hurdat2_data(self) -> List[Dict[str, Any]]:
        """
        Fetch hurricane data from NOAA HURDAT2 database
        
        Returns:
            List of storm dictionaries with track data
        """
        # Sample implementation - replace with actual NOAA data source
        # This would typically fetch from:
        # https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2023-051124.txt
        
        sample_data = [
            {
                'storm_id': 'AL092022',
                'name': 'IAN',
                'year': 2022,
                'track_points': [
                    {
                        'timestamp': '2022-09-28T19:00:00Z',
                        'lat': 26.0,
                        'lon': -82.0,
                        'status': 'HU',
                        'wind_mph': 130,
                        'pressure_mb': 947,
                        'category': 'CAT4'
                    },
                    {
                        'timestamp': '2022-09-28T20:00:00Z',
                        'lat': 26.1,
                        'lon': -81.9,
                        'status': 'HU',
                        'wind_mph': 125,
                        'pressure_mb': 950,
                        'category': 'CAT4'
                    }
                ]
            }
        ]
        
        logger.info("Using sample hurricane data for demonstration")
        return sample_data
    
    def _process_storm(self, storm_data: Dict[str, Any]) -> Dict[str, int]:
        """
        Process a single storm's track data
        
        Args:
            storm_data: Dictionary containing storm information and track points
            
        Returns:
            Dictionary with processing statistics
        """
        stats = {'processed': 0, 'new': 0, 'duplicates': 0, 'failed': 0}
        
        storm_id = storm_data['storm_id']
        name = storm_data['name']
        year = storm_data['year']
        
        logger.debug(f"Processing storm {storm_id} ({name}) from {year}")
        
        for idx, point in enumerate(storm_data['track_points']):
            try:
                stats['processed'] += 1
                
                # Parse timestamp
                if isinstance(point['timestamp'], str):
                    timestamp = datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00'))
                else:
                    timestamp = point['timestamp']
                
                # Generate hash for deduplication
                row_hash = self.hash_track_row(
                    storm_id, timestamp, point['lat'], point['lon']
                )
                
                # Check if record already exists
                existing = HurricaneTrack.query.filter_by(row_hash=row_hash).first()
                if existing:
                    logger.debug(f"Duplicate track point skipped: {storm_id} at {timestamp}")
                    stats['duplicates'] += 1
                    continue
                
                # Create new track record
                track = HurricaneTrack(
                    storm_id=storm_id,
                    name=name,
                    year=year,
                    track_point_index=idx,
                    timestamp=timestamp,
                    lat=point['lat'],
                    lon=point['lon'],
                    category=point.get('category'),
                    wind_mph=point.get('wind_mph'),
                    pressure_mb=point.get('pressure_mb'),
                    status=point.get('status'),
                    raw_data=point,
                    row_hash=row_hash
                )
                
                self.db.session.add(track)
                stats['new'] += 1
                logger.debug(f"Added track point: {storm_id} at {timestamp}")
                
            except Exception as e:
                logger.error(f"Failed to process track point {idx} for storm {storm_id}: {e}")
                stats['failed'] += 1
        
        return stats
    
    def get_ingestion_stats(self) -> Dict[str, Any]:
        """Get hurricane track ingestion statistics"""
        try:
            total_tracks = HurricaneTrack.query.count()
            unique_storms = self.db.session.query(HurricaneTrack.storm_id).distinct().count()
            latest_ingestion = self.db.session.query(HurricaneTrack.ingested_at).order_by(
                HurricaneTrack.ingested_at.desc()
            ).first()
            
            years_range = self.db.session.query(
                db.func.min(HurricaneTrack.year),
                db.func.max(HurricaneTrack.year)
            ).first()
            
            return {
                'total_track_points': total_tracks,
                'unique_storms': unique_storms,
                'latest_ingestion': latest_ingestion[0].isoformat() if latest_ingestion and latest_ingestion[0] else None,
                'year_range': {
                    'min': years_range[0] if years_range[0] else None,
                    'max': years_range[1] if years_range[1] else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting hurricane ingestion stats: {e}")
            return {
                'total_track_points': 0,
                'unique_storms': 0,
                'latest_ingestion': None,
                'year_range': {'min': None, 'max': None}
            }
    
    def search_tracks_by_location(self, lat: float, lon: float, radius_miles: float = 50) -> List[HurricaneTrack]:
        """
        Search for hurricane tracks within a radius of a location
        
        Args:
            lat: Latitude of search center
            lon: Longitude of search center
            radius_miles: Search radius in miles
            
        Returns:
            List of HurricaneTrack objects within radius
        """
        # Approximate conversion: 1 degree ≈ 69 miles
        radius_degrees = radius_miles / 69.0
        
        tracks = HurricaneTrack.query.filter(
            HurricaneTrack.lat.between(lat - radius_degrees, lat + radius_degrees),
            HurricaneTrack.lon.between(lon - radius_degrees, lon + radius_degrees)
        ).order_by(HurricaneTrack.timestamp.desc()).all()
        
        return tracks
    
    def get_storm_summary(self, storm_id: str) -> Optional[Dict[str, Any]]:
        """
        Get summary information for a specific storm
        
        Args:
            storm_id: NOAA storm identifier
            
        Returns:
            Dictionary with storm summary or None if not found
        """
        tracks = HurricaneTrack.query.filter_by(storm_id=storm_id).order_by(
            HurricaneTrack.track_point_index
        ).all()
        
        if not tracks:
            return None
        
        # Calculate summary statistics
        max_winds = max(track.wind_mph for track in tracks if track.wind_mph)
        min_pressure = min(track.pressure_mb for track in tracks if track.pressure_mb)
        
        return {
            'storm_id': storm_id,
            'name': tracks[0].name,
            'year': tracks[0].year,
            'track_points': len(tracks),
            'max_winds_mph': max_winds,
            'min_pressure_mb': min_pressure,
            'duration_hours': (tracks[-1].timestamp - tracks[0].timestamp).total_seconds() / 3600,
            'start_time': tracks[0].timestamp.isoformat(),
            'end_time': tracks[-1].timestamp.isoformat(),
            'landfall_points': [
                track for track in tracks 
                if track.lat and track.lon and track.lat > 24 and track.lat < 50 and track.lon > -130 and track.lon < -60
            ]
        }