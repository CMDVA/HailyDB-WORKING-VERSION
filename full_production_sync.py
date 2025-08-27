#!/usr/bin/env python3
"""
Full Production Database Sync
Comprehensive migration to preserve ALL data from both environments
"""
import os
import sys
import psycopg2
from datetime import datetime

def get_connection(is_production=False):
    """Get database connection"""
    if is_production:
        # Production database
        return psycopg2.connect(
            host="ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech",
            database="HailyDB_prod",
            user="neondb_owner", 
            password="npg_LRqvaAt5j1uo",
            sslmode="require"
        )
    else:
        # Main/Development database 
        return psycopg2.connect(os.environ['DATABASE_URL'])

def analyze_databases():
    """Compare both databases comprehensively"""
    print("🔍 COMPREHENSIVE DATABASE ANALYSIS")
    print("=" * 50)
    
    main_conn = get_connection(False)
    prod_conn = get_connection(True)
    
    main_cur = main_conn.cursor()
    prod_cur = prod_conn.cursor()
    
    try:
        # Count alerts in each database
        main_cur.execute("SELECT COUNT(*) FROM alerts")
        main_count = main_cur.fetchone()[0]
        
        prod_cur.execute("SELECT COUNT(*) FROM alerts") 
        prod_count = prod_cur.fetchone()[0]
        
        print(f"📊 ALERT COUNTS:")
        print(f"Main Database: {main_count:,} alerts")
        print(f"Production Database: {prod_count:,} alerts")
        print()
        
        # Find production-only alerts
        print("🔍 FINDING PRODUCTION-ONLY ALERTS...")
        prod_cur.execute("SELECT id FROM alerts")
        prod_ids = {row[0] for row in prod_cur.fetchall()}
        
        main_cur.execute("SELECT id FROM alerts")
        main_ids = {row[0] for row in main_cur.fetchall()}
        
        prod_only = prod_ids - main_ids
        main_only = main_ids - prod_ids
        
        print(f"Production-only alerts: {len(prod_only):,}")
        print(f"Main-only alerts: {len(main_only):,}")
        
        if prod_only:
            print(f"\n📋 SAMPLE PRODUCTION-ONLY ALERTS:")
            sample_ids = list(prod_only)[:5]
            for alert_id in sample_ids:
                prod_cur.execute("SELECT event, ingested_at FROM alerts WHERE id = %s", (alert_id,))
                event, ingested = prod_cur.fetchone()
                print(f"  - {event} (ID: {alert_id[:50]}...)")
        
        # Check SPC reports
        try:
            main_cur.execute("SELECT COUNT(*) FROM spc_reports")
            main_spc = main_cur.fetchone()[0]
            
            prod_cur.execute("SELECT COUNT(*) FROM spc_reports")
            prod_spc = prod_cur.fetchone()[0]
            
            print(f"\n📊 SPC REPORTS:")
            print(f"Main Database: {main_spc:,} reports")
            print(f"Production Database: {prod_spc:,} reports")
        except:
            print("\n⚠️  SPC reports table structure differs between databases")
        
        return {
            'main_count': main_count,
            'prod_count': prod_count,
            'prod_only_count': len(prod_only),
            'main_only_count': len(main_only),
            'prod_only_ids': prod_only
        }
            
    finally:
        main_cur.close()
        prod_cur.close()
        main_conn.close()
        prod_conn.close()

def migrate_production_data():
    """Migrate ALL unique production data to main database"""
    print("\n🚀 STARTING FULL PRODUCTION MIGRATION")
    print("=" * 50)
    
    analysis = analyze_databases()
    prod_only_ids = analysis['prod_only_ids']
    
    if not prod_only_ids:
        print("✅ No unique production data to migrate")
        return
    
    print(f"📦 Migrating {len(prod_only_ids):,} production-only alerts...")
    
    main_conn = get_connection(False)
    prod_conn = get_connection(True)
    
    main_cur = main_conn.cursor()
    prod_cur = prod_conn.cursor()
    
    migrated = 0
    failed = 0
    
    try:
        for alert_id in prod_only_ids:
            try:
                # Get full alert data from production
                prod_cur.execute("""
                    SELECT id, event, effective, expires, status, message_type, category, urgency, 
                           severity, certainty, areas_desc, ugc_codes, geometry, references, 
                           ingested_at, radar_detected, hail_size, wind_speed, has_polygon,
                           geometry_bounds, ai_summary, data_source, source_type, city_names
                    FROM alerts WHERE id = %s
                """, (alert_id,))
                
                alert_data = prod_cur.fetchone()
                if not alert_data:
                    continue
                
                # Insert into main database
                main_cur.execute("""
                    INSERT INTO alerts (
                        id, event, effective, expires, status, message_type, category, urgency,
                        severity, certainty, areas_desc, ugc_codes, geometry, references,
                        ingested_at, radar_detected, hail_size, wind_speed, has_polygon,
                        geometry_bounds, ai_summary, data_source, source_type, city_names
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING
                """, alert_data)
                
                migrated += 1
                if migrated % 100 == 0:
                    print(f"  Migrated {migrated:,} alerts...")
                    main_conn.commit()
                    
            except Exception as e:
                failed += 1
                print(f"  ❌ Failed to migrate {alert_id[:50]}...: {e}")
        
        main_conn.commit()
        
        print(f"\n✅ MIGRATION COMPLETE!")
        print(f"  Successfully migrated: {migrated:,} alerts")
        print(f"  Failed: {failed:,} alerts")
        
        # Final verification
        main_cur.execute("SELECT COUNT(*) FROM alerts")
        final_count = main_cur.fetchone()[0]
        print(f"  Final main database count: {final_count:,} alerts")
        
    finally:
        main_cur.close()
        prod_cur.close()
        main_conn.close()
        prod_conn.close()

if __name__ == "__main__":
    print("🔄 FULL PRODUCTION DATABASE SYNC")
    print("Preserving ALL data from both environments")
    print("=" * 60)
    
    try:
        migrate_production_data()
        print("\n🎯 READY FOR PRODUCTION DEPLOYMENT")
        print("Both databases now combined into main database")
        print("Set production DATABASE_URL to main database for complete access")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)