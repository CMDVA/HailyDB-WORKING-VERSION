#!/usr/bin/env python3
"""
Create Production Database and Sync Data
Creates the production database and syncs all data from development
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_production_database():
    """Create the production database"""
    admin_url = "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/postgres?sslmode=require"
    
    try:
        # Connect to postgres (admin database)
        admin_conn = psycopg2.connect(admin_url)
        admin_conn.autocommit = True  # Required for CREATE DATABASE
        
        with admin_conn.cursor() as cursor:
            # Check if production database exists
            cursor.execute("""
                SELECT 1 FROM pg_database WHERE datname = 'HailyDB_prod';
            """)
            
            if cursor.fetchone():
                logger.info("✅ Production database HailyDB_prod already exists")
            else:
                # Create production database
                cursor.execute("CREATE DATABASE \"HailyDB_prod\";")
                logger.info("✅ Created production database HailyDB_prod")
        
        admin_conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create production database: {e}")
        return False

def sync_schema_and_data():
    """Sync schema and data from development to production"""
    dev_url = "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
    prod_url = "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/HailyDB_prod?sslmode=require"
    
    try:
        # Connect to both databases
        dev_conn = psycopg2.connect(dev_url)
        prod_conn = psycopg2.connect(prod_url)
        
        logger.info("✅ Connected to both databases")
        
        # Get the complete schema from development
        with dev_conn.cursor() as dev_cursor:
            # Get CREATE TABLE statement for alerts
            dev_cursor.execute("""
                SELECT 
                    'CREATE TABLE alerts (' ||
                    string_agg(
                        column_name || ' ' || 
                        CASE 
                            WHEN data_type = 'character varying' THEN 'VARCHAR'
                            WHEN data_type = 'text' THEN 'TEXT'
                            WHEN data_type = 'timestamp without time zone' THEN 'TIMESTAMP'
                            WHEN data_type = 'jsonb' THEN 'JSONB'
                            WHEN data_type = 'boolean' THEN 'BOOLEAN'
                            WHEN data_type = 'integer' THEN 'INTEGER'
                            WHEN data_type = 'double precision' THEN 'DOUBLE PRECISION'
                            WHEN data_type = 'ARRAY' THEN 'VARCHAR[]'
                            ELSE data_type
                        END ||
                        CASE 
                            WHEN is_nullable = 'NO' THEN ' NOT NULL'
                            ELSE ''
                        END ||
                        CASE 
                            WHEN column_name = 'id' THEN ' PRIMARY KEY'
                            WHEN column_default IS NOT NULL AND column_default != '' THEN ' DEFAULT ' || column_default
                            ELSE ''
                        END,
                        ', '
                        ORDER BY ordinal_position
                    ) || ');' as create_statement
                FROM information_schema.columns 
                WHERE table_name = 'alerts'
                AND table_schema = 'public';
            """)
            
            create_stmt = dev_cursor.fetchone()
            if not create_stmt:
                logger.error("❌ Could not get alerts table schema")
                return False
            
            create_statement = create_stmt[0]
            
        # Create table in production
        with prod_conn.cursor() as prod_cursor:
            logger.info("🏗️ Creating alerts table in production...")
            prod_cursor.execute("DROP TABLE IF EXISTS alerts;")
            prod_cursor.execute(create_statement)
            prod_conn.commit()
            logger.info("✅ Production table created")
            
            # Copy all data
            logger.info("📥 Copying all data...")
            with dev_conn.cursor(cursor_factory=RealDictCursor) as dev_cursor:
                dev_cursor.execute("SELECT COUNT(*) as total FROM alerts;")
                total = dev_cursor.fetchone()['total']
                logger.info(f"🔄 Copying {total:,} alerts...")
                
                # Use COPY for efficient bulk transfer
                dev_cursor.execute("""
                    COPY alerts TO STDOUT WITH (FORMAT CSV, HEADER, DELIMITER ',', QUOTE '"', ESCAPE '"');
                """)
                
                # Copy data directly
                prod_cursor.copy_expert("""
                    COPY alerts FROM STDIN WITH (FORMAT CSV, HEADER, DELIMITER ',', QUOTE '"', ESCAPE '"');
                """, dev_cursor)
                
                prod_conn.commit()
                logger.info(f"✅ Copied {total:,} alerts to production")
        
        # Verify the sync
        with prod_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT COUNT(*) as total FROM alerts;")
            prod_total = cursor.fetchone()['total']
            
            cursor.execute("""
                SELECT id, event FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            target = cursor.fetchone()
            
            logger.info(f"🔍 Production verification: {prod_total:,} alerts")
            if target:
                logger.info(f"✅ Target alert found: {target['event']}")
                return True
            else:
                logger.error("❌ Target alert missing after sync")
                return False
        
    except Exception as e:
        logger.error(f"❌ Schema/data sync failed: {e}")
        return False
    
    finally:
        if 'dev_conn' in locals():
            dev_conn.close()
        if 'prod_conn' in locals():
            prod_conn.close()

def main():
    """Main function"""
    logger.info("🏗️ Creating production database and syncing data")
    
    # Step 1: Create production database
    if not create_production_database():
        return False
    
    # Step 2: Sync schema and data
    if not sync_schema_and_data():
        return False
    
    logger.info("🎉 PRODUCTION DATABASE CREATED AND SYNCED!")
    logger.info("Production now has complete data including the target alert")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)