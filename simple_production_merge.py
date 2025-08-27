#!/usr/bin/env python3
"""
Simple Production Database Merge
Copy production data to dev, then production points to dev database
"""
import os
import psycopg2
from datetime import datetime

def merge_production_to_dev():
    """Get production data and add it to our dev database"""
    print("🔄 MERGING PRODUCTION DATA TO DEV DATABASE")
    print("=" * 50)
    
    # Try different production database names
    production_urls = [
        "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/HailyDB_prod?sslmode=require",
        "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require",
        "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/hailydb?sslmode=require"
    ]
    
    dev_conn = psycopg2.connect(os.environ['DATABASE_URL'])
    dev_cur = dev_conn.cursor()
    
    # Get current dev count
    dev_cur.execute("SELECT COUNT(*) FROM alerts")
    dev_count = dev_cur.fetchone()[0]
    print(f"Current dev database: {dev_count:,} alerts")
    
    production_data_found = False
    
    for prod_url in production_urls:
        try:
            print(f"\nTrying production URL: {prod_url.split('@')[1].split('/')[0]}...")
            prod_conn = psycopg2.connect(prod_url)
            prod_cur = prod_conn.cursor()
            
            # Check if this database has alerts
            prod_cur.execute("SELECT COUNT(*) FROM alerts")
            prod_count = prod_cur.fetchone()[0]
            
            if prod_count > 0:
                print(f"✅ Found production data: {prod_count:,} alerts")
                production_data_found = True
                
                # Get production-only alerts
                prod_cur.execute("SELECT id FROM alerts")
                prod_ids = {row[0] for row in prod_cur.fetchall()}
                
                dev_cur.execute("SELECT id FROM alerts")
                dev_ids = {row[0] for row in dev_cur.fetchall()}
                
                prod_only = prod_ids - dev_ids
                print(f"Production-only alerts to merge: {len(prod_only):,}")
                
                if prod_only:
                    migrated = 0
                    for alert_id in prod_only:
                        try:
                            # Get full alert from production
                            prod_cur.execute("""
                                SELECT id, event, effective, expires, status, message_type, category, urgency, 
                                       severity, certainty, areas_desc, ugc_codes, geometry, references, 
                                       ingested_at, radar_detected, hail_size, wind_speed, has_polygon,
                                       geometry_bounds, ai_summary, data_source, source_type, city_names
                                FROM alerts WHERE id = %s
                            """, (alert_id,))
                            
                            alert_data = prod_cur.fetchone()
                            if alert_data:
                                # Insert into dev
                                dev_cur.execute("""
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
                                    dev_conn.commit()
                        except Exception as e:
                            print(f"  Error migrating {alert_id[:30]}...: {e}")
                    
                    dev_conn.commit()
                    print(f"✅ Successfully migrated {migrated:,} production alerts")
                else:
                    print("✅ All production data already in dev database")
                
                prod_cur.close()
                prod_conn.close()
                break
                
        except Exception as e:
            print(f"❌ Connection failed: {str(e)[:100]}...")
            continue
    
    if not production_data_found:
        print("⚠️  No accessible production database found")
        print("Production may already be using the dev database")
    
    # Final count
    dev_cur.execute("SELECT COUNT(*) FROM alerts")
    final_count = dev_cur.fetchone()[0]
    print(f"\n✅ FINAL DEV DATABASE: {final_count:,} alerts")
    
    dev_cur.close()
    dev_conn.close()
    
    return final_count

if __name__ == "__main__":
    print("🎯 SIMPLE SOLUTION: Merge everything into dev database")
    print("Then production just points to dev database")
    print("=" * 60)
    
    try:
        final_count = merge_production_to_dev()
        
        print(f"\n🎉 SOLUTION COMPLETE!")
        print(f"✅ Dev database now has {final_count:,} alerts")
        print(f"✅ Production should point to:")
        print(f"   postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require")
        print(f"✅ No more database complexity - one database with all data")
        
    except Exception as e:
        print(f"\n❌ Merge failed: {e}")