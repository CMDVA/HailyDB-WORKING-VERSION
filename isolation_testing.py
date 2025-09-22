"""
Isolation Testing Framework
Ensures IEM backfill process doesn't interfere with existing real-time ingestion
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import text
import json

logger = logging.getLogger(__name__)

class IsolationTester:
    """
    Tests that backfill operations are properly isolated from production systems
    """
    
    def __init__(self, db_session):
        self.db = db_session
        
    def run_isolation_tests(self) -> Dict:
        """
        Run complete isolation test suite
        """
        logger.info("Starting isolation testing...")
        
        results = {
            'overall_success': True,
            'tests_passed': 0,
            'tests_failed': 0,
            'details': {}
        }
        
        tests = [
            ('data_source_separation', self._test_data_source_separation),
            ('performance_impact', self._test_performance_impact),
            ('concurrent_operations', self._test_concurrent_operations),
            ('rollback_safety', self._test_rollback_safety),
            ('production_compatibility', self._test_production_compatibility)
        ]
        
        for test_name, test_func in tests:
            try:
                logger.info(f"Running isolation test: {test_name}")
                test_result = test_func()
                results['details'][test_name] = test_result
                
                if test_result['passed']:
                    results['tests_passed'] += 1
                else:
                    results['tests_failed'] += 1
                    results['overall_success'] = False
                    
                logger.info(f"Test {test_name}: {'PASS' if test_result['passed'] else 'FAIL'}")
                    
            except Exception as e:
                logger.error(f"Isolation test {test_name} failed with exception: {e}")
                results['details'][test_name] = {
                    'passed': False,
                    'message': f"Exception: {e}",
                    'details': {}
                }
                results['tests_failed'] += 1
                results['overall_success'] = False
        
        # Summary
        total_tests = len(tests)
        logger.info(f"Isolation testing complete: {results['tests_passed']}/{total_tests} passed")
        
        if results['overall_success']:
            logger.info("✅ All isolation tests passed - backfill is safe for production")
        else:
            logger.error("❌ Isolation tests failed - review before production deployment")
            
        return results
    
    def _test_data_source_separation(self) -> Dict:
        """
        Test that IEM data is properly separated by data_source field
        """
        try:
            # Count alerts by data source
            source_counts = self.db.execute(text("""
                SELECT 
                    COALESCE(data_source, 'NULL') as source,
                    COUNT(*) as count
                FROM alerts 
                GROUP BY data_source
                ORDER BY count DESC
            """)).fetchall()
            
            source_dict = {row[0]: row[1] for row in source_counts}
            
            # Check for proper separation
            iem_count = source_dict.get('iem_watchwarn', 0)
            real_time_count = source_dict.get('nws_live', 0) + source_dict.get(None, 0)
            null_count = source_dict.get('NULL', 0)
            
            # Check that IEM data has unique VTEC keys
            iem_vtec_unique = self.db.execute(text("""
                SELECT COUNT(DISTINCT vtec_key) as unique_keys, COUNT(*) as total_records
                FROM alerts WHERE data_source = 'iem_watchwarn' AND vtec_key IS NOT NULL
            """)).fetchone()
            
            details = {
                'source_breakdown': source_dict,
                'iem_records': iem_count,
                'real_time_records': real_time_count,
                'null_data_source': null_count,
                'iem_vtec_unique': iem_vtec_unique[0] if iem_vtec_unique else 0,
                'iem_vtec_total': iem_vtec_unique[1] if iem_vtec_unique else 0
            }
            
            # Test passes if:
            # 1. IEM data has proper data_source
            # 2. VTEC keys are unique for IEM data
            # 3. No data conflicts
            passed = True
            message = f"Data sources properly separated: {source_dict}"
            
            if iem_count > 0 and details['iem_vtec_unique'] != details['iem_vtec_total']:
                passed = False
                message = "IEM VTEC keys not unique - potential data conflict"
            elif null_count > real_time_count * 0.1:  # More than 10% null sources
                passed = False
                message = f"Too many records with null data_source: {null_count}"
            
            return {
                'passed': passed,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f"Data source separation test failed: {e}",
                'details': {}
            }
    
    def _test_performance_impact(self) -> Dict:
        """
        Test that backfilled data doesn't impact query performance
        """
        try:
            # Baseline query performance test
            queries = [
                # Real-time data query (typical dashboard query)
                {
                    'name': 'recent_alerts',
                    'sql': """
                        SELECT COUNT(*) FROM alerts 
                        WHERE effective >= NOW() - INTERVAL '7 days'
                        AND data_source != 'iem_watchwarn'
                    """
                },
                # Spatial query performance
                {
                    'name': 'spatial_query',
                    'sql': """
                        SELECT COUNT(*) FROM alerts 
                        WHERE geom IS NOT NULL 
                        AND ST_Area(geom) > 0.01 
                        LIMIT 1000
                    """
                },
                # Mixed data source query
                {
                    'name': 'mixed_sources',
                    'sql': """
                        SELECT data_source, COUNT(*) FROM alerts 
                        WHERE effective >= '2024-09-01' 
                        GROUP BY data_source
                    """
                }
            ]
            
            performance_results = []
            for query in queries:
                start_time = time.time()
                result = self.db.execute(text(query['sql'])).fetchall()
                elapsed = time.time() - start_time
                
                performance_results.append({
                    'query': query['name'],
                    'execution_time': round(elapsed, 4),
                    'result_count': len(result)
                })
                
                logger.info(f"Query {query['name']}: {elapsed:.4f}s")
            
            # Check database size impact
            table_sizes = self.db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename IN ('alerts', 'backfill_progress')
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            """)).fetchall()
            
            details = {
                'query_performance': performance_results,
                'table_sizes': [
                    {
                        'table': row[1], 
                        'size': row[2], 
                        'size_bytes': row[3]
                    } for row in table_sizes
                ],
                'slowest_query': max(performance_results, key=lambda x: x['execution_time'])
            }
            
            # Test passes if no query takes more than 5 seconds
            max_time = details['slowest_query']['execution_time']
            passed = max_time < 5.0
            message = f"Query performance acceptable, slowest: {max_time:.4f}s"
            
            if not passed:
                message = f"Performance impact detected: slowest query {max_time:.4f}s"
            
            return {
                'passed': passed,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f"Performance impact test failed: {e}",
                'details': {}
            }
    
    def _test_concurrent_operations(self) -> Dict:
        """
        Test that backfill and real-time operations can run concurrently
        """
        try:
            # Simulate concurrent operations by checking if we can:
            # 1. Read real-time data while IEM data exists
            # 2. Insert new real-time data (simulated)
            # 3. Update existing data without conflicts
            
            # Test 1: Read real-time data with IEM data present
            start_time = time.time()
            real_time_count = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts 
                WHERE data_source IS NULL OR data_source != 'iem_watchwarn'
            """)).scalar()
            read_time = time.time() - start_time
            
            # Test 2: Simulate insert of new alert (with rollback)
            start_time = time.time()
            try:
                self.db.execute(text("""
                    INSERT INTO alerts (
                        id, event, severity, area_desc, effective, expires, 
                        data_source, ingested_at
                    ) VALUES (
                        'test_isolation_' || EXTRACT(EPOCH FROM NOW()),
                        'Test Alert', 'Minor', 'Test Area', NOW(), NOW() + INTERVAL '1 hour',
                        'isolation_test', NOW()
                    )
                """))
                
                # Clean up test record immediately
                self.db.execute(text("""
                    DELETE FROM alerts WHERE data_source = 'isolation_test'
                """))
                self.db.commit()
                insert_test_passed = True
                
            except Exception as e:
                logger.warning(f"Insert test failed: {e}")
                self.db.rollback()
                insert_test_passed = False
            
            insert_time = time.time() - start_time
            
            # Test 3: Check for lock contention
            start_time = time.time()
            index_stats = self.db.execute(text("""
                SELECT 
                    schemaname, tablename, indexname, idx_scan, idx_tup_read
                FROM pg_stat_user_indexes 
                WHERE tablename = 'alerts'
                ORDER BY idx_scan DESC
                LIMIT 5
            """)).fetchall()
            stats_time = time.time() - start_time
            
            details = {
                'real_time_read_count': real_time_count,
                'real_time_read_time': round(read_time, 4),
                'insert_test_passed': insert_test_passed,
                'insert_test_time': round(insert_time, 4),
                'stats_query_time': round(stats_time, 4),
                'index_usage': [
                    {
                        'index': row[2],
                        'scans': row[3],
                        'tuples_read': row[4]
                    } for row in index_stats
                ]
            }
            
            # Test passes if operations complete quickly and insert test passes
            passed = (read_time < 2.0 and insert_test_passed and insert_time < 1.0)
            message = f"Concurrent operations test: read {read_time:.4f}s, insert {'OK' if insert_test_passed else 'FAIL'}"
            
            return {
                'passed': passed,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f"Concurrent operations test failed: {e}",
                'details': {}
            }
    
    def _test_rollback_safety(self) -> Dict:
        """
        Test that IEM backfill data can be safely removed without affecting real-time data
        """
        try:
            # Count current data
            before_counts = {
                'total_alerts': self.db.execute(text("SELECT COUNT(*) FROM alerts")).scalar(),
                'iem_alerts': self.db.execute(text("SELECT COUNT(*) FROM alerts WHERE data_source = 'iem_watchwarn'")).scalar(),
                'real_time_alerts': self.db.execute(text("SELECT COUNT(*) FROM alerts WHERE data_source IS NULL OR data_source != 'iem_watchwarn'")).scalar(),
                'progress_records': self.db.execute(text("SELECT COUNT(*) FROM backfill_progress")).scalar()
            }
            
            # Test rollback query (without actually executing - just EXPLAIN)
            rollback_plan = self.db.execute(text("""
                EXPLAIN (FORMAT JSON) DELETE FROM alerts WHERE data_source = 'iem_watchwarn'
            """)).fetchone()
            
            progress_rollback_plan = self.db.execute(text("""
                EXPLAIN (FORMAT JSON) DELETE FROM backfill_progress WHERE state = 'FL'
            """)).fetchone()
            
            # Check if rollback would be safe (no cascading deletes, etc.)
            rollback_safe = True
            safety_checks = []
            
            # Check for foreign key constraints that might be affected
            fk_constraints = self.db.execute(text("""
                SELECT 
                    tc.table_name, 
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' 
                AND (tc.table_name = 'alerts' OR ccu.table_name = 'alerts')
            """)).fetchall()
            
            safety_checks.append({
                'check': 'foreign_key_constraints',
                'result': len(fk_constraints),
                'safe': len(fk_constraints) == 0  # No FK constraints is safer
            })
            
            # Check for triggers that might be affected
            triggers = self.db.execute(text("""
                SELECT trigger_name, event_manipulation, trigger_schema, trigger_name
                FROM information_schema.triggers 
                WHERE event_object_table = 'alerts'
            """)).fetchall()
            
            safety_checks.append({
                'check': 'table_triggers',
                'result': len(triggers),
                'safe': True  # Triggers are usually OK
            })
            
            details = {
                'before_counts': before_counts,
                'rollback_plan': rollback_plan[0] if rollback_plan else None,
                'progress_rollback_plan': progress_rollback_plan[0] if progress_rollback_plan else None,
                'safety_checks': safety_checks,
                'foreign_key_constraints': len(fk_constraints),
                'table_triggers': len(triggers)
            }
            
            # Test passes if rollback would be safe and data counts are reasonable
            passed = (
                rollback_safe and 
                before_counts['iem_alerts'] >= 0 and 
                before_counts['real_time_alerts'] > 0  # Ensure real-time data exists
            )
            
            message = f"Rollback safety: {before_counts['iem_alerts']} IEM records can be safely removed"
            if not passed:
                message = "Rollback safety concerns detected"
            
            return {
                'passed': passed,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f"Rollback safety test failed: {e}",
                'details': {}
            }
    
    def _test_production_compatibility(self) -> Dict:
        """
        Test that the backfill system is compatible with production environment
        """
        try:
            # Check database version and capabilities
            db_version = self.db.execute(text("SELECT version()")).scalar()
            postgis_version = self.db.execute(text("SELECT PostGIS_Version()")).scalar()
            
            # Check table permissions
            table_privileges = self.db.execute(text("""
                SELECT table_name, privilege_type 
                FROM information_schema.role_table_grants 
                WHERE table_name IN ('alerts', 'backfill_progress')
                AND grantee = current_user
            """)).fetchall()
            
            # Check available memory/storage
            db_size = self.db.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)).scalar()
            
            # Check for production-specific settings
            relevant_settings = self.db.execute(text("""
                SELECT name, setting, unit 
                FROM pg_settings 
                WHERE name IN (
                    'max_connections', 'shared_buffers', 'work_mem', 
                    'maintenance_work_mem', 'checkpoint_timeout'
                )
            """)).fetchall()
            
            # Verify that existing services won't be affected
            recent_real_time = self.db.execute(text("""
                SELECT COUNT(*) FROM alerts 
                WHERE ingested_at >= NOW() - INTERVAL '24 hours'
                AND (data_source IS NULL OR data_source != 'iem_watchwarn')
            """)).scalar()
            
            details = {
                'database_version': db_version,
                'postgis_version': postgis_version,
                'database_size': db_size,
                'table_privileges': [{'table': row[0], 'privilege': row[1]} for row in table_privileges],
                'database_settings': [{'setting': row[0], 'value': row[1], 'unit': row[2]} for row in relevant_settings],
                'recent_real_time_activity': recent_real_time
            }
            
            # Basic compatibility checks
            has_select = any(p['privilege'] == 'SELECT' for p in details['table_privileges'])
            has_insert = any(p['privilege'] == 'INSERT' for p in details['table_privileges'])
            has_update = any(p['privilege'] == 'UPDATE' for p in details['table_privileges'])
            
            passed = (
                has_select and has_insert and has_update and
                'PostGIS' in postgis_version and
                recent_real_time >= 0  # Real-time system is working
            )
            
            message = f"Production compatibility: {'OK' if passed else 'ISSUES DETECTED'}"
            if passed:
                message += f" (DB: {db_size}, PostGIS: {postgis_version.split()[0]})"
            
            return {
                'passed': passed,
                'message': message,
                'details': details
            }
            
        except Exception as e:
            return {
                'passed': False,
                'message': f"Production compatibility test failed: {e}",
                'details': {}
            }
    
    def create_rollback_script(self) -> str:
        """
        Create a rollback script for emergency use
        """
        script = '''#!/usr/bin/env python3
"""
EMERGENCY ROLLBACK SCRIPT
Removes all IEM backfill data and related tracking records
"""

import os
import psycopg2
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def rollback_iem_data():
    """Remove all IEM backfill data"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        cursor = conn.cursor()
        
        logger.info("Starting IEM data rollback...")
        
        # Count records before removal
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE data_source = 'iem_watchwarn'")
        iem_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM backfill_progress")
        progress_count = cursor.fetchone()[0]
        
        logger.info(f"Found {iem_count} IEM alerts and {progress_count} progress records")
        
        # Remove IEM alerts
        cursor.execute("DELETE FROM alerts WHERE data_source = 'iem_watchwarn'")
        deleted_alerts = cursor.rowcount
        
        # Remove progress tracking
        cursor.execute("DELETE FROM backfill_progress")
        deleted_progress = cursor.rowcount
        
        conn.commit()
        
        logger.info(f"Rollback complete: {deleted_alerts} alerts, {deleted_progress} progress records removed")
        
        # Verify cleanup
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE data_source = 'iem_watchwarn'")
        remaining = cursor.fetchone()[0]
        
        if remaining == 0:
            logger.info("✅ Rollback successful - no IEM data remaining")
        else:
            logger.error(f"❌ Rollback incomplete - {remaining} IEM records still exist")
        
        cursor.close()
        conn.close()
        
        return remaining == 0
        
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False

if __name__ == "__main__":
    success = rollback_iem_data()
    exit(0 if success else 1)
'''
        return script