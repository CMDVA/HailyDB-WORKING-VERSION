"""
IEM Backfill Service for HailyDB
Downloads and processes historical NWS watch/warn/advisory alerts from Iowa Environmental Mesonet
"""

import os
import logging
import requests
import time
import zipfile
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from io import BytesIO
import pyshp
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import unary_union
import json

from models import db

logger = logging.getLogger(__name__)

class IemBackfillService:
    """
    Service for downloading and processing historical NWS alerts from IEM
    Focuses on Florida pilot: Sep-Oct 2024
    """
    
    def __init__(self, db_session):
        self.db = db_session
        self.base_url = "https://mesonet.agron.iastate.edu/cgi-bin/request/gis/watchwarn.py"
        self.headers = {
            'User-Agent': 'HailyDB-IEM-Backfill/1.0 (contact@hailydb.com)',
            'Accept': 'application/zip'
        }
        # Throttling settings per PRD requirements
        self.max_concurrent = 2
        self.retry_delay = 5  # seconds
        self.max_retries = 3
        
    def get_florida_url(self, start_date: str, end_date: str) -> str:
        """
        Build IEM URL for Florida data within date range
        Format: YYYY-MM-DDTHH:MM:SSZ
        """
        params = {
            'location_group': 'states',
            'states': 'FL',
            'sts': f'{start_date}T00:00Z',
            'ets': f'{end_date}T23:59Z',
            'accept': 'shapefile',
            'limit1': 'yes',  # Reduce payload as per PRD
            'limitps': 'yes'   # Limit polygon size
        }
        
        # Build URL with parameters
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        url = f"{self.base_url}?{param_str}"
        
        logger.info(f"Built IEM URL: {url}")
        return url
    
    def download_shapefile(self, url: str) -> Optional[bytes]:
        """
        Download shapefile ZIP from IEM with retry logic
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Downloading shapefile (attempt {attempt + 1}/{self.max_retries})")
                
                response = requests.get(url, headers=self.headers, timeout=60)
                response.raise_for_status()
                
                if response.status_code == 429:
                    # Rate limited, use exponential backoff
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait_time} seconds (attempt {attempt + 1})")
                    time.sleep(wait_time)
                    continue
                
                if len(response.content) < 100:
                    logger.warning("Received suspiciously small file, might be empty")
                    return None
                
                logger.info(f"Downloaded {len(response.content)} bytes")
                return response.content
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Download attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    # Exponential backoff for all request exceptions
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying in {wait_time} seconds (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error("All download attempts failed after exponential backoff")
                    return None
        
        return None
    
    def parse_shapefile(self, zip_data: bytes) -> List[Dict]:
        """
        Extract and parse shapefile from ZIP data
        Returns list of alert records with geometries and attributes
        """
        alerts = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Securely extract ZIP file with path traversal protection
                with zipfile.ZipFile(BytesIO(zip_data)) as zip_file:
                    self._safe_extract_zip(zip_file, temp_dir)
                
                # Find the .shp file
                shp_file = None
                for file in os.listdir(temp_dir):
                    if file.endswith('.shp'):
                        shp_file = os.path.join(temp_dir, file)
                        break
                
                if not shp_file:
                    logger.error("No .shp file found in ZIP")
                    return alerts
                
                # Parse shapefile with pyshp
                sf = pyshp.Reader(shp_file)
                
                # Get field names from shapefile
                field_names = [field[0] for field in sf.fields[1:]]  # Skip deletion flag
                logger.info(f"Shapefile fields: {field_names}")
                
                # Process each shape record
                for shape_record in sf.shapeRecords():
                    try:
                        # Extract attributes
                        attributes = dict(zip(field_names, shape_record.record))
                        
                        # Extract geometry
                        geom = shape_record.shape
                        if not geom.parts:
                            logger.warning("Shape with no parts, skipping")
                            continue
                        
                        # Convert to Shapely geometry
                        shapely_geom = self._pyshp_to_shapely(geom)
                        if not shapely_geom:
                            continue
                        
                        # Convert to GeoJSON
                        geojson = mapping(shapely_geom)
                        
                        alert_record = {
                            'attributes': attributes,
                            'geometry': geojson,
                            'original_geom': geom  # Keep original for debugging
                        }
                        
                        alerts.append(alert_record)
                        
                    except Exception as e:
                        logger.error(f"Error processing shape record: {e}")
                        continue
                
                logger.info(f"Parsed {len(alerts)} alert records from shapefile")
                return alerts
                
            except Exception as e:
                logger.error(f"Error parsing shapefile: {e}")
                return alerts
    
    def _pyshp_to_shapely(self, pyshp_shape) -> Optional[object]:
        """
        Convert pyshp shape to Shapely geometry
        """
        try:
            # Convert pyshp shape to GeoJSON-like structure
            if pyshp_shape.shapeType == pyshp.POLYGON:
                # Handle polygon with potential holes
                if len(pyshp_shape.parts) == 1:
                    # Simple polygon
                    coords = list(pyshp_shape.points)
                    if len(coords) < 3:
                        return None
                    
                    # Close polygon if not closed
                    if coords[0] != coords[-1]:
                        coords.append(coords[0])
                    
                    return Polygon(coords)
                else:
                    # Polygon with holes or MultiPolygon
                    polygons = []
                    parts = list(pyshp_shape.parts) + [len(pyshp_shape.points)]
                    
                    for i in range(len(parts) - 1):
                        start = parts[i]
                        end = parts[i + 1]
                        ring_coords = pyshp_shape.points[start:end]
                        
                        if len(ring_coords) < 3:
                            continue
                        
                        # Close ring if not closed
                        if ring_coords[0] != ring_coords[-1]:
                            ring_coords.append(ring_coords[0])
                        
                        polygons.append(Polygon(ring_coords))
                    
                    if len(polygons) == 1:
                        return polygons[0]
                    elif len(polygons) > 1:
                        return MultiPolygon(polygons)
            
            return None
            
        except Exception as e:
            logger.error(f"Error converting pyshp to Shapely: {e}")
            return None
    
    def build_vtec_key(self, attributes: Dict) -> Optional[str]:
        """
        Build VTEC key from IEM attributes
        Format: {wfo}-{phenom}{sig}-{year}-{etn}
        """
        try:
            wfo = attributes.get('WFO', '').strip()
            phenom = attributes.get('PHENOM', '').strip()
            sig = attributes.get('SIG', '').strip()
            etn = attributes.get('ETN', '')
            issued = attributes.get('ISSUED')
            
            if not all([wfo, phenom, sig, etn]):
                logger.warning(f"Missing VTEC components: WFO={wfo}, PHENOM={phenom}, SIG={sig}, ETN={etn}")
                return None
            
            # Extract year from issued time
            year = None
            if issued:
                try:
                    # Parse various date formats
                    if isinstance(issued, str):
                        # Try ISO format first
                        if 'T' in issued:
                            dt = datetime.fromisoformat(issued.replace('Z', '+00:00'))
                        else:
                            # Try other common formats
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y%m%d %H:%M', '%Y-%m-%d']:
                                try:
                                    dt = datetime.strptime(issued, fmt)
                                    break
                                except ValueError:
                                    continue
                            else:
                                logger.warning(f"Could not parse issued time: {issued}")
                                dt = datetime.utcnow()  # Fallback to current year
                        
                        year = dt.year
                    
                except Exception as e:
                    logger.warning(f"Error parsing issued time {issued}: {e}")
                    year = datetime.utcnow().year
            else:
                year = datetime.utcnow().year
            
            vtec_key = f"{wfo}-{phenom}{sig}-{year}-{etn}"
            logger.debug(f"Built VTEC key: {vtec_key}")
            
            return vtec_key
            
        except Exception as e:
            logger.error(f"Error building VTEC key: {e}")
            return None
    
    def record_progress(self, state: str, year: int, month: int, step: str, 
                       records_processed: int = 0, records_inserted: int = 0, 
                       records_updated: int = 0, error_message: str = None,
                       metadata: Dict = None):
        """
        Record progress in backfill_progress table
        """
        try:
            from sqlalchemy import text
            
            # Upsert progress record
            query = text("""
                INSERT INTO backfill_progress 
                (state, year, month, step, completed_at, records_processed, 
                 records_inserted, records_updated, error_message, metadata)
                VALUES (:state, :year, :month, :step, :completed_at, :records_processed,
                        :records_inserted, :records_updated, :error_message, :metadata)
                ON CONFLICT (state, year, month, step) DO UPDATE SET
                    completed_at = EXCLUDED.completed_at,
                    records_processed = EXCLUDED.records_processed,
                    records_inserted = EXCLUDED.records_inserted,
                    records_updated = EXCLUDED.records_updated,
                    error_message = EXCLUDED.error_message,
                    metadata = EXCLUDED.metadata
            """)
            
            self.db.execute(query, {
                'state': state,
                'year': year,
                'month': month,
                'step': step,
                'completed_at': datetime.utcnow() if not error_message else None,
                'records_processed': records_processed,
                'records_inserted': records_inserted,
                'records_updated': records_updated,
                'error_message': error_message,
                'metadata': json.dumps(metadata or {})
            })
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error recording progress: {e}")
    
    def process_florida_month(self, year: int, month: int) -> Dict:
        """
        Process one month of Florida data
        Returns summary statistics
        """
        logger.info(f"Processing Florida data for {year}-{month:02d}")
        
        # Build date range for the month
        start_date = f"{year}-{month:02d}-01"
        if month == 12:
            end_date = f"{year + 1}-01-01"
        else:
            end_date = f"{year}-{month + 1:02d}-01"
        
        stats = {
            'records_processed': 0,
            'records_inserted': 0,
            'records_updated': 0,
            'errors': []
        }
        
        try:
            # Record start of download
            self.record_progress('FL', year, month, 'shapefile_download')
            
            # Download shapefile
            url = self.get_florida_url(start_date, end_date)
            zip_data = self.download_shapefile(url)
            
            if not zip_data:
                error_msg = "Failed to download shapefile"
                self.record_progress('FL', year, month, 'shapefile_download', 
                                   error_message=error_msg)
                stats['errors'].append(error_msg)
                return stats
            
            # Record start of parsing
            self.record_progress('FL', year, month, 'parsing')
            
            # Parse shapefile
            alerts = self.parse_shapefile(zip_data)
            stats['records_processed'] = len(alerts)
            
            if not alerts:
                logger.info(f"No alerts found for {year}-{month:02d}")
                self.record_progress('FL', year, month, 'completed', 
                                   records_processed=0)
                return stats
            
            # Record start of database operations
            self.record_progress('FL', year, month, 'database_insert')
            
            # Process alerts in batches with progress checkpoints
            batch_size = 50  # Process in smaller batches for better progress tracking
            inserted = 0
            updated = 0
            
            for i in range(0, len(alerts), batch_size):
                batch = alerts[i:i + batch_size]
                batch_start = i + 1
                batch_end = min(i + batch_size, len(alerts))
                
                logger.info(f"Processing batch {batch_start}-{batch_end} of {len(alerts)} alerts")
                
                # Record batch progress
                self.record_progress('FL', year, month, 'processing_batch', 
                                   records_processed=batch_end,
                                   metadata={'batch_start': batch_start, 'batch_end': batch_end})
                
                batch_inserted = 0
                batch_updated = 0
                
                for alert_record in batch:
                    try:
                        result = self.upsert_alert(alert_record)
                        if result == 'inserted':
                            inserted += 1
                            batch_inserted += 1
                        elif result == 'updated':
                            updated += 1
                            batch_updated += 1
                    except Exception as e:
                        error_msg = f"Error upserting alert: {e}"
                        stats['errors'].append(error_msg)
                        logger.error(error_msg)
                        continue
                
                # Log batch completion
                logger.info(f"Completed batch {batch_start}-{batch_end}: {batch_inserted} inserted, {batch_updated} updated")
                
                # Small pause between batches to prevent overwhelming the database
                if i + batch_size < len(alerts):
                    time.sleep(0.1)  # 100ms pause
            
            stats['records_inserted'] = inserted
            stats['records_updated'] = updated
            
            # Record completion
            self.record_progress('FL', year, month, 'completed',
                               records_processed=len(alerts),
                               records_inserted=inserted,
                               records_updated=updated)
            
            logger.info(f"Completed {year}-{month:02d}: {inserted} inserted, {updated} updated")
            
        except Exception as e:
            error_msg = f"Error processing month {year}-{month:02d}: {e}"
            self.record_progress('FL', year, month, 'failed', error_message=error_msg)
            stats['errors'].append(error_msg)
            logger.error(error_msg)
        
        return stats
    
    def upsert_alert(self, alert_record: Dict) -> str:
        """
        Insert or update alert in database
        Returns 'inserted', 'updated', or 'skipped'
        """
        try:
            attributes = alert_record['attributes']
            geometry = alert_record['geometry']
            
            # Build VTEC key
            vtec_key = self.build_vtec_key(attributes)
            if not vtec_key:
                logger.warning("Could not build VTEC key, skipping alert")
                return 'skipped'
            
            # Extract core NWS fields
            event = attributes.get('PHENOM', 'Unknown')  # Will map to proper event names
            severity = attributes.get('SIG', 'Unknown')
            area_desc = attributes.get('AREA_DESC', '')
            
            # Parse timestamps
            effective = self._parse_timestamp(attributes.get('ISSUED'))
            expires = self._parse_timestamp(attributes.get('EXPIRED'))
            
            from sqlalchemy import text
            
            # Use PostGIS with SRID=4326, ST_MakeValid for geometry repair, and proper conflict resolution
            query = text("""
                INSERT INTO alerts (
                    id, event, severity, area_desc, effective, expires, sent,
                    geometry, properties, geom, vtec_key, data_source,
                    ingested_at, updated_at
                ) VALUES (
                    :vtec_key, :event, :severity, :area_desc, :effective, :expires, :effective,
                    :geometry_json, :properties, 
                    ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(:geometry_str), 4326)),
                    :vtec_key, 'iem_watchwarn', NOW(), NOW()
                )
                ON CONFLICT (id) DO UPDATE SET
                    event = EXCLUDED.event,
                    severity = EXCLUDED.severity,
                    area_desc = EXCLUDED.area_desc,
                    effective = EXCLUDED.effective,
                    expires = EXCLUDED.expires,
                    geometry = EXCLUDED.geometry,
                    properties = EXCLUDED.properties,
                    geom = ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(EXCLUDED.properties->>'geometry'), 4326)),
                    data_source = EXCLUDED.data_source,
                    updated_at = NOW()
                WHERE alerts.data_source = 'iem_watchwarn' OR alerts.data_source IS NULL
                RETURNING (xmax = 0) AS inserted
            """)
            
            result = self.db.execute(query, {
                'vtec_key': vtec_key,
                'event': event,
                'severity': severity,
                'area_desc': area_desc,
                'effective': effective,
                'expires': expires,
                'geometry_json': json.dumps(geometry),
                'geometry_str': json.dumps(geometry),
                'properties': json.dumps(attributes)
            })
            
            row = result.fetchone()
            was_inserted = row[0] if row else True
            
            self.db.commit()
            
            return 'inserted' if was_inserted else 'updated'
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error upserting alert: {e}")
            raise
    
    def _parse_timestamp(self, timestamp_str) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        if not timestamp_str:
            return None
        
        try:
            # Try ISO format first
            if isinstance(timestamp_str, str):
                if 'T' in timestamp_str:
                    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                
                # Try other formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y%m%d %H:%M', '%Y-%m-%d']:
                    try:
                        return datetime.strptime(timestamp_str, fmt)
                    except ValueError:
                        continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not parse timestamp {timestamp_str}: {e}")
            return None
    
    def _safe_extract_zip(self, zip_file: zipfile.ZipFile, extract_to: str):
        """
        Safely extract ZIP file with path traversal protection
        """
        for member in zip_file.infolist():
            # Get the file path and normalize it
            file_path = member.filename
            
            # Security checks
            if self._is_safe_path(file_path, extract_to):
                try:
                    # Extract individual file
                    zip_file.extract(member, extract_to)
                    logger.debug(f"Extracted safe file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to extract {file_path}: {e}")
                    continue
            else:
                logger.warning(f"Blocked unsafe path in ZIP: {file_path}")
    
    def _is_safe_path(self, file_path: str, extract_to: str) -> bool:
        """
        Check if file path is safe for extraction (prevents path traversal)
        """
        # Normalize the paths
        extract_to = os.path.abspath(extract_to)
        full_path = os.path.abspath(os.path.join(extract_to, file_path))
        
        # Security checks
        # 1. Must be within the extraction directory
        if not full_path.startswith(extract_to):
            return False
        
        # 2. No suspicious path components
        path_parts = file_path.split('/')
        for part in path_parts:
            if part in ['..', '.', ''] or part.startswith('.'):
                return False
        
        # 3. No absolute paths
        if os.path.isabs(file_path):
            return False
        
        # 4. Reasonable filename (no control characters)
        if any(ord(c) < 32 for c in file_path):
            return False
        
        # 5. File extension whitelist for shapefiles
        allowed_extensions = ['.shp', '.shx', '.dbf', '.prj', '.cpg', '.xml']
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext and file_ext not in allowed_extensions:
            logger.debug(f"Ignoring non-shapefile: {file_path}")
            return False
        
        return True