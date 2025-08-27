#!/usr/bin/env python3
"""
Production Data Bridge - Sync development data to production database
Logically transfers complete alert data from dev environment to production
"""

import os
import json
import psycopg2
from psycopg2.extras import Json, RealDictCursor
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_connections():
    """Get both development and production database connections"""
    try:
        # Current development database (complete data)
        dev_url = os.environ.get('DATABASE_URL')
        if not dev_url:
            raise ValueError("DATABASE_URL not found for development")
        
        dev_conn = psycopg2.connect(dev_url)
        logger.info("✅ Connected to development database")
        
        # Production database would need separate connection
        # For now, we'll export data that can be imported to production
        return dev_conn, None
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        raise

def check_schema_compatibility(conn):
    """Verify the database schema is compatible"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Check alerts table structure
            cursor.execute("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'alerts'
                ORDER BY ordinal_position;
            """)
            
            columns = cursor.fetchall()
            logger.info(f"✅ Found {len(columns)} columns in alerts table")
            
            # Verify key columns exist
            required_columns = ['id', 'event', 'properties', 'geometry', 'raw']
            existing_columns = [col['column_name'] for col in columns]
            
            missing = [col for col in required_columns if col not in existing_columns]
            if missing:
                logger.error(f"❌ Missing required columns: {missing}")
                return False
                
            logger.info("✅ Schema compatibility verified")
            return True
            
    except Exception as e:
        logger.error(f"❌ Schema check failed: {e}")
        return False

def export_alerts_for_production(conn, batch_size=1000):
    """Export all alerts in production-ready format"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get total count
            cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            total = cursor.fetchone()['total']
            logger.info(f"📊 Exporting {total:,} alerts for production sync")
            
            # Export in batches to avoid memory issues
            exported_count = 0
            batch_num = 0
            
            # Create production-ready export file
            export_file = 'production_sync_data.sql'
            
            with open(export_file, 'w') as f:
                # Write header
                f.write("-- HailyDB Production Data Sync\n")
                f.write(f"-- Generated: {datetime.now().isoformat()}\n")
                f.write(f"-- Total alerts: {total:,}\n\n")
                
                # Begin transaction
                f.write("BEGIN;\n\n")
                
                # Disable constraints for faster import
                f.write("SET session_replication_role = replica;\n\n")
                
                while exported_count < total:
                    offset = batch_num * batch_size
                    
                    cursor.execute("""
                        SELECT * FROM alerts 
                        ORDER BY id 
                        LIMIT %s OFFSET %s;
                    """, (batch_size, offset))
                    
                    batch = cursor.fetchall()
                    if not batch:
                        break
                    
                    # Write INSERT statements for this batch
                    for alert in batch:
                        # Prepare values, handling JSON and special types
                        values = []
                        for key, value in alert.items():
                            if value is None:
                                values.append('NULL')
                            elif isinstance(value, (dict, list)):
                                values.append(f"'{json.dumps(value)}'::jsonb")
                            elif isinstance(value, datetime):
                                values.append(f"'{value.isoformat()}'::timestamp")
                            elif isinstance(value, bool):
                                values.append(str(value).lower())
                            elif isinstance(value, (int, float)):
                                values.append(str(value))
                            else:
                                # Escape single quotes in strings
                                escaped = str(value).replace("'", "''")
                                values.append(f"'{escaped}'")
                        
                        # Build INSERT statement
                        columns = ', '.join(alert.keys())
                        values_str = ', '.join(values)
                        
                        f.write(f"INSERT INTO alerts ({columns}) VALUES ({values_str}) ON CONFLICT (id) DO NOTHING;\n")
                    
                    exported_count += len(batch)
                    batch_num += 1
                    
                    if batch_num % 10 == 0:  # Log progress every 10 batches
                        logger.info(f"📈 Exported {exported_count:,}/{total:,} alerts ({exported_count/total*100:.1f}%)")
                
                # Re-enable constraints
                f.write("\nSET session_replication_role = DEFAULT;\n")
                
                # Commit transaction
                f.write("COMMIT;\n")
                
            logger.info(f"✅ Export complete: {exported_count:,} alerts saved to {export_file}")
            return export_file
            
    except Exception as e:
        logger.error(f"❌ Export failed: {e}")
        raise

def create_production_import_script():
    """Create a script to import data into production"""
    script_content = '''#!/bin/bash
# Production Data Import Script
# Run this in your production environment

echo "🔄 Starting HailyDB production data import..."

# Check if production_sync_data.sql exists
if [ ! -f "production_sync_data.sql" ]; then
    echo "❌ production_sync_data.sql not found"
    exit 1
fi

# Backup existing production data (optional but recommended)
echo "📦 Creating backup of existing production data..."
pg_dump $DATABASE_URL > production_backup_$(date +%Y%m%d_%H%M%S).sql

# Import the development data
echo "📥 Importing development data to production..."
psql $DATABASE_URL < production_sync_data.sql

if [ $? -eq 0 ]; then
    echo "✅ Production data sync completed successfully"
    
    # Verify the import
    echo "🔍 Verifying import..."
    psql $DATABASE_URL -c "SELECT COUNT(*) as total_alerts FROM alerts;"
    
    # Test the previously failing alert
    echo "🧪 Testing previously failing alert..."
    psql $DATABASE_URL -c "SELECT id, event FROM alerts WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';"
    
else
    echo "❌ Import failed"
    exit 1
fi
'''
    
    with open('production_import.sh', 'w') as f:
        f.write(script_content)
    
    # Make it executable
    os.chmod('production_import.sh', 0o755)
    logger.info("✅ Created production_import.sh script")

def main():
    """Main function to bridge data to production"""
    logger.info("🌉 Starting HailyDB production data bridge")
    
    try:
        # Get database connections
        dev_conn, _ = get_database_connections()
        
        # Check schema compatibility
        if not check_schema_compatibility(dev_conn):
            logger.error("❌ Schema incompatibility detected")
            return False
        
        # Export alerts for production
        export_file = export_alerts_for_production(dev_conn)
        
        # Create import script
        create_production_import_script()
        
        logger.info("🎯 Production bridge complete!")
        logger.info("📋 Next steps:")
        logger.info("   1. Copy production_sync_data.sql to your production environment")
        logger.info("   2. Run: ./production_import.sh")
        logger.info("   3. Verify the previously failing alert works")
        logger.info(f"   4. Test: /api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Bridge failed: {e}")
        return False
    
    finally:
        if 'dev_conn' in locals():
            dev_conn.close()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)