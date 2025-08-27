#!/usr/bin/env python3
"""
Copy Development to Production - Direct database export/import
Export complete development database and import to production
"""

import os
import subprocess
import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def export_development_database():
    """Export complete development database to SQL file"""
    try:
        db_url = os.environ.get('DATABASE_URL')
        logger.info("Exporting complete development database...")
        
        # Export using pg_dump with data and schema
        export_cmd = f'pg_dump "{db_url}" > production_import.sql'
        result = subprocess.run(export_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Check file size
            file_size = subprocess.run('ls -lh production_import.sql', shell=True, capture_output=True, text=True)
            logger.info(f"✅ Database export complete: {file_size.stdout.strip()}")
            
            # Count lines
            line_count = subprocess.run('wc -l production_import.sql', shell=True, capture_output=True, text=True)
            logger.info(f"Export contains: {line_count.stdout.strip()}")
            
            return True
        else:
            logger.error(f"Export failed: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Database export failed: {e}")
        return False

def create_production_restore_script():
    """Create script to restore database in production"""
    script_content = '''#!/bin/bash
# Production Database Restore Script
echo "Starting production database restore..."

# Drop and recreate all tables
psql "$DATABASE_URL" -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Import complete database
psql "$DATABASE_URL" < production_import.sql

echo "Production restore complete"

# Verify import
psql "$DATABASE_URL" -c "SELECT COUNT(*) as total_alerts FROM alerts;"
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM alerts WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';"
'''
    
    try:
        with open('production_restore.sh', 'w') as f:
            f.write(script_content)
        
        # Make executable
        subprocess.run('chmod +x production_restore.sh', shell=True)
        logger.info("✅ Production restore script created")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create restore script: {e}")
        return False

def verify_development_data():
    """Verify development database has complete data"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor() as cursor:
            # Check alerts
            cursor.execute("SELECT COUNT(*) FROM alerts;")
            alert_count = cursor.fetchone()[0]
            
            # Check target alert
            cursor.execute("""
                SELECT COUNT(*) FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            target_present = cursor.fetchone()[0]
            
            # Check SPC reports
            try:
                cursor.execute("SELECT COUNT(*) FROM spc_reports;")
                spc_count = cursor.fetchone()[0]
            except:
                spc_count = 0
            
            # Check tables
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY tablename;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
        conn.close()
        
        logger.info("Development database contains:")
        logger.info(f"  Alerts: {alert_count:,}")
        logger.info(f"  SPC Reports: {spc_count:,}")
        logger.info(f"  Target Alert: {'✅ Present' if target_present else '❌ Missing'}")
        logger.info(f"  Tables: {len(tables)} ({', '.join(tables[:5])}...)")
        
        return alert_count > 0 and target_present > 0
        
    except Exception as e:
        logger.error(f"Development verification failed: {e}")
        return False

def create_direct_sql_import():
    """Create SQL file that can be executed directly in production"""
    try:
        logger.info("Creating direct SQL import file...")
        
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor() as cursor:
            # Get target alert data
            cursor.execute("""
                SELECT id, event, severity, area_desc, effective, expires, sent, 
                       geometry, properties, radar_indicated, fips_codes, county_names,
                       geometry_type, coordinate_count, affected_states, geometry_bounds
                FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            target_alert = cursor.fetchone()
        
        conn.close()
        
        if target_alert:
            # Create SQL insert statement
            sql_content = f"""
-- Direct Production Import - Target Alert
DELETE FROM alerts WHERE id = '{target_alert[0]}';

INSERT INTO alerts (
    id, event, severity, area_desc, effective, expires, sent, 
    geometry, properties, radar_indicated, fips_codes, county_names,
    geometry_type, coordinate_count, affected_states, geometry_bounds,
    ingested_at, updated_at
) VALUES (
    '{target_alert[0]}',
    '{target_alert[1]}',
    '{target_alert[2]}', 
    '{target_alert[3]}',
    '{target_alert[4]}',
    '{target_alert[5]}',
    '{target_alert[6]}',
    '{target_alert[7]}',
    '{target_alert[8]}',
    '{target_alert[9]}',
    '{target_alert[10]}',
    '{target_alert[11]}',
    '{target_alert[12]}',
    '{target_alert[13]}',
    '{target_alert[14]}',
    '{target_alert[15]}',
    NOW(),
    NOW()
);

-- Verify insert
SELECT 'Target alert inserted:', COUNT(*) FROM alerts WHERE id = '{target_alert[0]}';
"""
            
            with open('direct_production_insert.sql', 'w') as f:
                f.write(sql_content)
            
            logger.info("✅ Direct SQL import file created")
            return True
        else:
            logger.error("Target alert not found in development")
            return False
            
    except Exception as e:
        logger.error(f"Failed to create direct SQL import: {e}")
        return False

def main():
    """Execute complete development to production copy"""
    logger.info("🚀 Copying development database TO production")
    
    # Step 1: Verify development has data
    if not verify_development_data():
        logger.error("Development database verification failed")
        return False
    
    # Step 2: Export development database
    if not export_development_database():
        logger.error("Database export failed")
        return False
    
    # Step 3: Create restore scripts
    if not create_production_restore_script():
        logger.error("Restore script creation failed")
        return False
    
    # Step 4: Create direct SQL import
    if not create_direct_sql_import():
        logger.error("Direct SQL creation failed")
        return False
    
    logger.info("✅ Development to production copy prepared")
    logger.info("Files created:")
    logger.info("  - production_import.sql (complete database)")
    logger.info("  - production_restore.sh (restore script)")
    logger.info("  - direct_production_insert.sql (target alert)")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Deploy to production")
    logger.info("2. Production will use development database")
    logger.info("3. Target alert will be accessible via API")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("🎯 Ready for production deployment")
    else:
        logger.error("❌ Copy preparation failed")