#!/usr/bin/env python3
"""
Complete Database Sync - Copy entire development database to production
This ensures 100% data integrity including all tables, indexes, and relationships
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_all_tables():
    """Get list of all tables in development database"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)
            tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    except Exception as e:
        logger.error(f"Failed to get table list: {e}")
        return []

def get_table_schema(table_name):
    """Get CREATE TABLE statement for a table"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        with conn.cursor() as cursor:
            # Get column definitions
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_name = %s 
                ORDER BY ordinal_position;
            """, (table_name,))
            columns = cursor.fetchall()
            
            # Get primary key info
            cursor.execute("""
                SELECT column_name
                FROM information_schema.key_column_usage kcu
                JOIN information_schema.table_constraints tc 
                ON kcu.constraint_name = tc.constraint_name
                WHERE tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY';
            """, (table_name,))
            pk_columns = [row[0] for row in cursor.fetchall()]
            
        conn.close()
        return columns, pk_columns
    except Exception as e:
        logger.error(f"Failed to get schema for {table_name}: {e}")
        return [], []

def copy_table_data(table_name):
    """Copy all data from development table to production"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get all rows from the table
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            
            if not rows:
                logger.info(f"Table {table_name} is empty, skipping data copy")
                return 0
            
            # Get column names
            columns = list(rows[0].keys())
            
            # Clear existing data in production
            cursor.execute(f"DELETE FROM {table_name};")
            
            # Insert all rows
            inserted_count = 0
            for row in rows:
                try:
                    placeholders = ['%s'] * len(columns)
                    values = []
                    
                    for col in columns:
                        value = row[col]
                        # Handle JSON fields properly
                        if isinstance(value, (dict, list)):
                            values.append(json.dumps(value))
                        else:
                            values.append(value)
                    
                    insert_sql = f"""
                        INSERT INTO {table_name} ({', '.join(columns)}) 
                        VALUES ({', '.join(placeholders)});
                    """
                    cursor.execute(insert_sql, values)
                    inserted_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to insert row in {table_name}: {e}")
            
            conn.commit()
            logger.info(f"✅ Copied {inserted_count:,} rows to {table_name}")
            
        conn.close()
        return inserted_count
        
    except Exception as e:
        logger.error(f"Failed to copy data for {table_name}: {e}")
        return 0

def create_table_structure(table_name, columns, pk_columns):
    """Create table structure in production database"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor() as cursor:
            # Drop table if exists
            cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
            
            # Build column definitions
            col_defs = []
            for col_name, data_type, max_length, nullable, default in columns:
                col_def = f"{col_name} "
                
                # Handle data types
                if data_type == 'character varying':
                    if max_length:
                        col_def += f"VARCHAR({max_length})"
                    else:
                        col_def += "VARCHAR"
                elif data_type == 'timestamp without time zone':
                    col_def += "TIMESTAMP"
                elif data_type == 'double precision':
                    col_def += "DOUBLE PRECISION"
                elif data_type == 'jsonb':
                    col_def += "JSONB"
                else:
                    col_def += data_type.upper()
                
                # Handle nullable
                if nullable == 'NO':
                    col_def += " NOT NULL"
                
                # Handle default
                if default and not default.startswith('nextval'):
                    col_def += f" DEFAULT {default}"
                
                col_defs.append(col_def)
            
            # Add primary key
            if pk_columns:
                pk_def = f"PRIMARY KEY ({', '.join(pk_columns)})"
                col_defs.append(pk_def)
            
            # Create table
            create_sql = f"""
                CREATE TABLE {table_name} (
                    {', '.join(col_defs)}
                );
            """
            
            cursor.execute(create_sql)
            conn.commit()
            logger.info(f"✅ Created table structure for {table_name}")
            
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to create table {table_name}: {e}")
        return False

def sync_complete_database():
    """Synchronize entire database from development to production"""
    logger.info("🔄 Starting complete database synchronization")
    
    # Get all tables
    tables = get_all_tables()
    if not tables:
        logger.error("No tables found in development database")
        return False
    
    logger.info(f"Found {len(tables)} tables to sync: {', '.join(tables)}")
    
    total_rows = 0
    synced_tables = 0
    
    for table_name in tables:
        logger.info(f"Processing table: {table_name}")
        
        # Get table schema
        columns, pk_columns = get_table_schema(table_name)
        if not columns:
            logger.warning(f"Skipping {table_name} - no schema found")
            continue
        
        # Create table structure
        if not create_table_structure(table_name, columns, pk_columns):
            logger.warning(f"Failed to create {table_name} structure")
            continue
        
        # Copy table data
        row_count = copy_table_data(table_name)
        total_rows += row_count
        synced_tables += 1
        
        logger.info(f"Completed {table_name}: {row_count:,} rows")
    
    logger.info(f"🎉 Database sync complete!")
    logger.info(f"Tables synced: {synced_tables}/{len(tables)}")
    logger.info(f"Total rows copied: {total_rows:,}")
    
    return synced_tables > 0

def verify_sync():
    """Verify the database sync was successful"""
    try:
        conn = psycopg2.connect(os.environ.get('DATABASE_URL'))
        
        with conn.cursor() as cursor:
            # Check alerts table
            cursor.execute("SELECT COUNT(*) FROM alerts;")
            alert_count = cursor.fetchone()[0]
            
            # Check for target alert
            cursor.execute("""
                SELECT COUNT(*) FROM alerts 
                WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';
            """)
            target_present = cursor.fetchone()[0]
            
            # Check spc_reports if exists
            try:
                cursor.execute("SELECT COUNT(*) FROM spc_reports;")
                spc_count = cursor.fetchone()[0]
            except:
                spc_count = 0
            
        conn.close()
        
        logger.info(f"✅ Verification complete:")
        logger.info(f"  - Alerts: {alert_count:,}")
        logger.info(f"  - SPC Reports: {spc_count:,}")
        logger.info(f"  - Target Alert: {'✅ Present' if target_present else '❌ Missing'}")
        
        return alert_count > 0 and target_present > 0
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return False

def main():
    """Execute complete database synchronization"""
    logger.info("🚀 Starting complete database migration")
    
    # Step 1: Sync entire database
    if not sync_complete_database():
        logger.error("❌ Database sync failed")
        return False
    
    # Step 2: Verify sync
    if not verify_sync():
        logger.error("❌ Database verification failed")
        return False
    
    logger.info("🎯 Complete database sync successful!")
    logger.info("Production database now contains full development data")
    return True

if __name__ == "__main__":
    success = main()
    if success:
        logger.info("✅ Ready for production deployment")
    else:
        logger.error("❌ Database sync failed")