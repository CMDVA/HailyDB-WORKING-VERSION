"""
Backfill Data Validation Framework
Ensures data quality and integrity for IEM historical weather alert backfill
"""

import logging
from datetime import datetime
from typing import Dict, List, Tuple
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)

class BackfillValidator:
    """
    Validates backfilled weather alert data quality and integrity
    """
    
    def __init__(self, db_session):
        self.db = db_session
        
    def validate_florida_pilot(self) -> Dict:
        """
        Run comprehensive validation on Florida pilot data
        """
        logger.info("Starting Florida pilot validation...")
        
        results = {
            'overall_success': True,
            'checks_passed': 0,
            'checks_failed': 0,
            'warnings': 0,
            'details': {}
        }
        
        # Run all validation checks
        checks = [
            ('data_counts', self._check_data_counts),
            ('geometry_validity', self._check_geometry_validity),
            ('vtec_key_integrity', self._check_vtec_key_integrity),
            ('temporal_coverage', self._check_temporal_coverage),
            ('spatial_coverage', self._check_spatial_coverage),
            ('data_source_consistency', self._check_data_source_consistency),
            ('sample_polygon_test', self._check_sample_polygon_queries)
        ]
        
        for check_name, check_func in checks:
            try:
                logger.info(f"Running check: {check_name}")
                check_result = check_func()
                results['details'][check_name] = check_result
                
                if check_result['status'] == 'pass':
                    results['checks_passed'] += 1
                elif check_result['status'] == 'fail':
                    results['checks_failed'] += 1
                    results['overall_success'] = False
                else:  # warning
                    results['warnings'] += 1
                    
            except Exception as e:
                logger.error(f"Check {check_name} failed with exception: {e}")
                results['details'][check_name] = {
                    'status': 'fail',
                    'message': f"Exception: {e}",
                    'details': {}
                }
                results['checks_failed'] += 1
                results['overall_success'] = False
        
        # Generate summary
        total_checks = len(checks)
        logger.info(f"Validation complete: {results['checks_passed']}/{total_checks} passed")
        if results['warnings']:
            logger.warning(f"Warnings: {results['warnings']}")
        if results['checks_failed']:
            logger.error(f"Failed checks: {results['checks_failed']}")
            
        return results
    
    def _check_data_counts(self) -> Dict:
        """Check record counts and consistency"""
        try:
            # Count IEM records
            iem_total = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts WHERE data_source = 'iem_watchwarn'
            """)).scalar()
            
            # Count by month for Florida pilot
            monthly_counts = self.db.execute(text("""
                SELECT 
                    EXTRACT(YEAR FROM effective) as year,
                    EXTRACT(MONTH FROM effective) as month,
                    COUNT(*) as count
                FROM alerts 
                WHERE data_source = 'iem_watchwarn'
                AND effective >= '2024-09-01' AND effective < '2024-11-01'
                GROUP BY EXTRACT(YEAR FROM effective), EXTRACT(MONTH FROM effective)
                ORDER BY year, month
            """)).fetchall()
            
            # Count with valid geometries
            geom_count = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts 
                WHERE data_source = 'iem_watchwarn' AND geom IS NOT NULL
            """)).scalar()
            
            details = {
                'total_iem_records': iem_total,
                'records_with_geometry': geom_count,
                'geometry_percentage': (geom_count / iem_total * 100) if iem_total > 0 else 0,
                'monthly_breakdown': [{'year': int(row[0]), 'month': int(row[1]), 'count': row[2]} 
                                    for row in monthly_counts]
            }
            
            # Determine status
            status = 'pass'
            message = f"Found {iem_total} IEM records, {geom_count} with geometries"
            
            if iem_total == 0:
                status = 'fail'
                message = "No IEM records found"
            elif geom_count < iem_total * 0.9:  # Less than 90% have geometries
                status = 'warning'
                message += f" (only {details['geometry_percentage']:.1f}% have geometries)"
            
            return {
                'status': status,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'status': 'fail',
                'message': f"Data count check failed: {e}",
                'details': {}
            }
    
    def _check_geometry_validity(self) -> Dict:
        """Check PostGIS geometry validity"""
        try:
            # Check valid geometries
            valid_geoms = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts 
                WHERE data_source = 'iem_watchwarn' 
                AND geom IS NOT NULL 
                AND ST_IsValid(geom) = true
            """)).scalar()
            
            # Check invalid geometries
            invalid_geoms = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts 
                WHERE data_source = 'iem_watchwarn' 
                AND geom IS NOT NULL 
                AND ST_IsValid(geom) = false
            """)).scalar()
            
            # Check geometry types
            geom_types = self.db.execute(text("""
                SELECT ST_GeometryType(geom), COUNT(*) 
                FROM alerts 
                WHERE data_source = 'iem_watchwarn' AND geom IS NOT NULL
                GROUP BY ST_GeometryType(geom)
                ORDER BY COUNT(*) DESC
            """)).fetchall()
            
            total_geoms = valid_geoms + invalid_geoms
            
            details = {
                'valid_geometries': valid_geoms,
                'invalid_geometries': invalid_geoms,
                'validity_percentage': (valid_geoms / total_geoms * 100) if total_geoms > 0 else 0,
                'geometry_types': [{'type': row[0], 'count': row[1]} for row in geom_types]
            }
            
            # Determine status
            if invalid_geoms == 0:
                status = 'pass'
                message = f"All {valid_geoms} geometries are valid"
            elif invalid_geoms < total_geoms * 0.05:  # Less than 5% invalid
                status = 'warning'
                message = f"{valid_geoms} valid, {invalid_geoms} invalid ({details['validity_percentage']:.1f}% valid)"
            else:
                status = 'fail'
                message = f"Too many invalid geometries: {invalid_geoms} of {total_geoms}"
            
            return {
                'status': status,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'status': 'fail',
                'message': f"Geometry validity check failed: {e}",
                'details': {}
            }
    
    def _check_vtec_key_integrity(self) -> Dict:
        """Check VTEC key format and uniqueness"""
        try:
            # Count records with VTEC keys
            vtec_count = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts 
                WHERE data_source = 'iem_watchwarn' AND vtec_key IS NOT NULL
            """)).scalar()
            
            # Check for duplicates
            duplicate_count = self.db.execute(text("""
                SELECT COUNT(*) FROM (
                    SELECT vtec_key FROM alerts 
                    WHERE data_source = 'iem_watchwarn' AND vtec_key IS NOT NULL
                    GROUP BY vtec_key HAVING COUNT(*) > 1
                ) duplicates
            """)).scalar()
            
            # Sample VTEC key formats
            sample_keys = self.db.execute(text("""
                SELECT vtec_key FROM alerts 
                WHERE data_source = 'iem_watchwarn' AND vtec_key IS NOT NULL
                LIMIT 5
            """)).fetchall()
            
            # Check VTEC key format (should be like "WFO-PHENOMSIG-YEAR-ETN")
            valid_format_count = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts 
                WHERE data_source = 'iem_watchwarn' 
                AND vtec_key ~ '^[A-Z]{3,4}-[A-Z]{2}[A-Z]-[0-9]{4}-[0-9]+$'
            """)).scalar()
            
            details = {
                'records_with_vtec': vtec_count,
                'duplicate_vtec_keys': duplicate_count,
                'valid_format_count': valid_format_count,
                'format_percentage': (valid_format_count / vtec_count * 100) if vtec_count > 0 else 0,
                'sample_keys': [row[0] for row in sample_keys]
            }
            
            # Determine status
            status = 'pass'
            message = f"{vtec_count} VTEC keys, {duplicate_count} duplicates"
            
            if duplicate_count > 0:
                status = 'fail'
                message += " (duplicates not allowed)"
            elif valid_format_count < vtec_count * 0.95:  # Less than 95% valid format
                status = 'warning'
                message += f" ({details['format_percentage']:.1f}% valid format)"
            
            return {
                'status': status,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'status': 'fail',
                'message': f"VTEC key check failed: {e}",
                'details': {}
            }
    
    def _check_temporal_coverage(self) -> Dict:
        """Check temporal coverage of backfilled data"""
        try:
            # Get date range
            date_range = self.db.execute(text("""
                SELECT 
                    MIN(effective)::date as min_date,
                    MAX(effective)::date as max_date,
                    COUNT(DISTINCT effective::date) as unique_dates
                FROM alerts 
                WHERE data_source = 'iem_watchwarn'
                AND effective IS NOT NULL
            """)).fetchone()
            
            # Expected coverage for Sep-Oct 2024
            expected_start = datetime(2024, 9, 1).date()
            expected_end = datetime(2024, 10, 31).date()
            expected_days = (expected_end - expected_start).days + 1
            
            details = {
                'min_date': str(date_range[0]) if date_range[0] else None,
                'max_date': str(date_range[1]) if date_range[1] else None,
                'unique_dates': date_range[2] if date_range[2] else 0,
                'expected_range': f"{expected_start} to {expected_end}",
                'expected_days': expected_days
            }
            
            # Determine status
            status = 'pass'
            message = f"Coverage: {details['min_date']} to {details['max_date']} ({details['unique_dates']} days)"
            
            if not date_range[0] or not date_range[1]:
                status = 'fail'
                message = "No temporal data found"
            elif date_range[0] > expected_start or date_range[1] < expected_end:
                status = 'warning'
                message += f" (expected {expected_start} to {expected_end})"
            
            return {
                'status': status,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'status': 'fail',
                'message': f"Temporal coverage check failed: {e}",
                'details': {}
            }
    
    def _check_spatial_coverage(self) -> Dict:
        """Check spatial coverage (should be Florida-focused)"""
        try:
            # Get bounding box of all geometries
            bbox = self.db.execute(text("""
                SELECT 
                    ST_XMin(ST_Extent(geom)) as min_lon,
                    ST_YMin(ST_Extent(geom)) as min_lat,
                    ST_XMax(ST_Extent(geom)) as max_lon,
                    ST_YMax(ST_Extent(geom)) as max_lat,
                    COUNT(*) as geom_count
                FROM alerts 
                WHERE data_source = 'iem_watchwarn' AND geom IS NOT NULL
            """)).fetchone()
            
            # Florida approximate bounds: -87.6 to -80.0 longitude, 24.5 to 31.0 latitude
            fl_bounds = {
                'min_lon': -87.6,
                'max_lon': -80.0,
                'min_lat': 24.5,
                'max_lat': 31.0
            }
            
            details = {
                'data_bbox': {
                    'min_lon': float(bbox[0]) if bbox[0] else None,
                    'min_lat': float(bbox[1]) if bbox[1] else None,
                    'max_lon': float(bbox[2]) if bbox[2] else None,
                    'max_lat': float(bbox[3]) if bbox[3] else None
                },
                'geometry_count': bbox[4] if bbox[4] else 0,
                'florida_bounds': fl_bounds
            }
            
            # Check if bounding box is reasonable for Florida
            status = 'pass'
            message = f"Spatial extent: {details['data_bbox']} ({details['geometry_count']} geometries)"
            
            if not bbox[0]:
                status = 'fail'
                message = "No spatial data found"
            else:
                # Check if data falls within reasonable Florida bounds (with some buffer)
                buffer = 2.0  # degrees
                if (bbox[0] < fl_bounds['min_lon'] - buffer or 
                    bbox[2] > fl_bounds['max_lon'] + buffer or
                    bbox[1] < fl_bounds['min_lat'] - buffer or 
                    bbox[3] > fl_bounds['max_lat'] + buffer):
                    status = 'warning'
                    message += " (outside expected Florida bounds)"
            
            return {
                'status': status,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'status': 'fail',
                'message': f"Spatial coverage check failed: {e}",
                'details': {}
            }
    
    def _check_data_source_consistency(self) -> Dict:
        """Check data source field consistency"""
        try:
            # Count by data source
            source_counts = self.db.execute(text("""
                SELECT data_source, COUNT(*) 
                FROM alerts 
                GROUP BY data_source 
                ORDER BY COUNT(*) DESC
            """)).fetchall()
            
            # Check for null data sources
            null_sources = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts WHERE data_source IS NULL
            """)).scalar()
            
            details = {
                'source_breakdown': [{'source': row[0] or 'NULL', 'count': row[1]} 
                                   for row in source_counts],
                'null_data_sources': null_sources
            }
            
            # Determine status
            status = 'pass'
            message = f"Data sources: {dict(source_counts)}"
            
            if null_sources > 0:
                status = 'warning'
                message += f" ({null_sources} records with null data_source)"
            
            return {
                'status': status,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'status': 'fail',
                'message': f"Data source consistency check failed: {e}",
                'details': {}
            }
    
    def _check_sample_polygon_queries(self) -> Dict:
        """Test sample point-in-polygon queries"""
        try:
            # Test points in Florida (major cities)
            test_points = [
                {'name': 'Miami', 'lon': -80.1918, 'lat': 25.7617},
                {'name': 'Orlando', 'lon': -81.3792, 'lat': 28.5383},
                {'name': 'Tampa', 'lon': -82.4572, 'lat': 27.9506},
                {'name': 'Jacksonville', 'lon': -81.6557, 'lat': 30.3322}
            ]
            
            query_results = []
            for point in test_points:
                count = self.db.execute(text("""
                    SELECT COUNT(*) FROM alerts 
                    WHERE data_source = 'iem_watchwarn'
                    AND geom IS NOT NULL
                    AND ST_Contains(geom, ST_Point(:lon, :lat))
                """), {'lon': point['lon'], 'lat': point['lat']}).scalar()
                
                query_results.append({
                    'location': point['name'],
                    'lon': point['lon'],
                    'lat': point['lat'],
                    'alert_count': count
                })
            
            # Test spatial index performance
            import time
            start_time = time.time()
            
            # Run a more complex spatial query
            complex_result = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts 
                WHERE data_source = 'iem_watchwarn'
                AND geom IS NOT NULL
                AND ST_Area(geom) > 0.01
                AND ST_IsValid(geom) = true
            """)).scalar()
            
            query_time = time.time() - start_time
            
            details = {
                'point_in_polygon_tests': query_results,
                'complex_query_result': complex_result,
                'query_performance_seconds': round(query_time, 3),
                'total_test_points': len(test_points)
            }
            
            # Determine status
            total_hits = sum(r['alert_count'] for r in query_results)
            status = 'pass'
            message = f"Spatial queries working, {total_hits} total point hits, {query_time:.3f}s query time"
            
            if query_time > 5.0:  # More than 5 seconds is concerning
                status = 'warning'
                message += " (slow query performance)"
            
            return {
                'status': status,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'status': 'fail',
                'message': f"Sample polygon query test failed: {e}",
                'details': {}
            }
    
    def generate_report(self, validation_results: Dict) -> str:
        """Generate a human-readable validation report"""
        report = []
        report.append("=" * 60)
        report.append("FLORIDA PILOT BACKFILL VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall status
        overall = "✅ PASS" if validation_results['overall_success'] else "❌ FAIL"
        report.append(f"Overall Status: {overall}")
        report.append(f"Checks Passed: {validation_results['checks_passed']}")
        report.append(f"Checks Failed: {validation_results['checks_failed']}")
        report.append(f"Warnings: {validation_results['warnings']}")
        report.append("")
        
        # Detailed results
        for check_name, result in validation_results['details'].items():
            status_emoji = {'pass': '✅', 'warning': '⚠️', 'fail': '❌'}
            emoji = status_emoji.get(result['status'], '❓')
            
            report.append(f"{emoji} {check_name.replace('_', ' ').title()}")
            report.append(f"   Status: {result['status'].upper()}")
            report.append(f"   Message: {result['message']}")
            
            # Add key details
            if 'details' in result and result['details']:
                details = result['details']
                if 'total_iem_records' in details:
                    report.append(f"   Records: {details['total_iem_records']}")
                if 'valid_geometries' in details:
                    report.append(f"   Valid geometries: {details['valid_geometries']}")
                if 'unique_dates' in details:
                    report.append(f"   Date coverage: {details['unique_dates']} days")
            
            report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)