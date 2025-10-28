#!/usr/bin/env python3
"""
Merge Production Database into Dev Database
- Identifies unique alerts from production
- Migrates without duplicates
- Handles JSONB columns properly
"""

import psycopg2
from psycopg2.extras import RealDictCursor, Json
import json

# Database connections
PROD_DB = "postgresql://neondb_owner:npg_xc8eF3tdoBIl@ep-withered-firefly-ads6qa9v.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
DEV_DB = "postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"

def get_existing_ids(dev_conn):
    """Get all IDs that already exist in dev database"""
    print("Fetching existing IDs from dev database...")
    cur = dev_conn.cursor()
    cur.execute("SELECT id FROM alerts;")
    existing = {row[0] for row in cur.fetchall()}
    cur.close()
    print(f"Found {len(existing)} existing alerts in dev")
    return existing

def fetch_production_alerts(prod_conn):
    """Fetch all alerts from production database"""
    print("Fetching alerts from production database...")
    cur = prod_conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT * FROM alerts 
        ORDER BY effective DESC;
    """)
    alerts = cur.fetchall()
    cur.close()
    print(f"Found {len(alerts)} alerts in production")
    return alerts

def prepare_alert_for_insert(alert):
    """Convert alert dict to proper format for insertion, handling JSONB columns"""
    prepared = {}
    
    # JSONB columns that need Json() wrapper
    jsonb_columns = ['geometry', 'properties', 'raw', 'ai_tags', 'spc_reports', 'radar_indicated', 
                     'fips_codes', 'county_names', 'geometry_bounds', 'affected_states']
    
    for key, value in alert.items():
        if key in jsonb_columns:
            # Wrap JSONB columns with Json() - handles both dicts and lists
            if value is not None:
                # If it's a list (like text[]), convert to JSON
                if isinstance(value, list):
                    prepared[key] = Json(value)
                else:
                    prepared[key] = Json(value)
            else:
                prepared[key] = None
        elif key == 'city_names':
            # city_names is ARRAY type, keep as-is
            prepared[key] = value
        else:
            prepared[key] = value
    
    return prepared

def migrate_alerts_batch(dev_conn, alerts):
    """Insert multiple alerts into dev database"""
    if not alerts:
        return 0
    
    cur = dev_conn.cursor()
    
    insert_query = """
        INSERT INTO alerts (
            id, event, severity, area_desc, effective, expires, sent,
            geometry, properties, raw, vtec_key, data_source,
            ai_summary, ai_tags, spc_verified, spc_reports,
            spc_confidence_score, spc_match_method, spc_report_count,
            spc_ai_summary, radar_indicated, fips_codes, county_names,
            city_names, location_confidence, geometry_type,
            coordinate_count, affected_states, geometry_bounds,
            ingested_at, updated_at, geom
        ) VALUES (
            %(id)s, %(event)s, %(severity)s, %(area_desc)s, %(effective)s,
            %(expires)s, %(sent)s, %(geometry)s, %(properties)s,
            %(raw)s, %(vtec_key)s, %(data_source)s, %(ai_summary)s,
            %(ai_tags)s, %(spc_verified)s, %(spc_reports)s,
            %(spc_confidence_score)s, %(spc_match_method)s,
            %(spc_report_count)s, %(spc_ai_summary)s, %(radar_indicated)s,
            %(fips_codes)s, %(county_names)s, %(city_names)s,
            %(location_confidence)s, %(geometry_type)s,
            %(coordinate_count)s, %(affected_states)s,
            %(geometry_bounds)s, %(ingested_at)s, %(updated_at)s,
            %(geom)s
        );
    """
    
    inserted = 0
    failed = 0
    errors = []
    
    for alert in alerts:
        try:
            prepared = prepare_alert_for_insert(alert)
            cur.execute(insert_query, prepared)
            inserted += 1
        except Exception as e:
            failed += 1
            if failed <= 3:  # Keep first 3 errors for debugging
                errors.append(str(e))
    
    cur.close()
    return inserted, failed, errors

def main():
    print("=" * 70)
    print("Production to Dev Database Migration")
    print("=" * 70)
    
    # Connect to both databases
    print("\nConnecting to databases...")
    prod_conn = psycopg2.connect(PROD_DB)
    dev_conn = psycopg2.connect(DEV_DB)
    dev_conn.autocommit = False
    
    try:
        # Get existing data
        existing_ids = get_existing_ids(dev_conn)
        prod_alerts = fetch_production_alerts(prod_conn)
        
        # Identify unique alerts (by ID)
        unique_alerts = []
        duplicate_count = 0
        
        for alert in prod_alerts:
            alert_id = alert.get('id')
            if alert_id not in existing_ids:
                unique_alerts.append(alert)
            else:
                duplicate_count += 1
        
        print(f"\nAnalysis:")
        print(f"  Production alerts: {len(prod_alerts)}")
        print(f"  Already in dev: {duplicate_count}")
        print(f"  Unique to migrate: {len(unique_alerts)}")
        
        if len(unique_alerts) == 0:
            print("\n✅ No unique alerts to migrate - databases are in sync!")
            return
        
        # Migrate unique alerts in batches
        print(f"\nMigrating {len(unique_alerts)} unique alerts...")
        batch_size = 100
        total_migrated = 0
        total_failed = 0
        all_errors = []
        
        for i in range(0, len(unique_alerts), batch_size):
            batch = unique_alerts[i:i+batch_size]
            migrated, failed, errors = migrate_alerts_batch(dev_conn, batch)
            total_migrated += migrated
            total_failed += failed
            all_errors.extend(errors)
            dev_conn.commit()
            print(f"  Progress: {min(i+batch_size, len(unique_alerts))}/{len(unique_alerts)} | Inserted: {total_migrated} | Failed: {total_failed}")
        
        # Final stats
        print("\n" + "=" * 70)
        print("Migration Complete!")
        print("=" * 70)
        print(f"✅ Successfully migrated: {total_migrated} alerts")
        if total_failed > 0:
            print(f"❌ Failed: {total_failed} alerts")
            if all_errors:
                print(f"\nSample errors:")
                for err in all_errors[:3]:
                    print(f"  - {err}")
        
        # Verify final counts
        cur = dev_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM alerts;")
        total = cur.fetchone()[0]
        cur.execute("""
            SELECT COUNT(*) FROM alerts 
            WHERE radar_indicated IS NOT NULL 
            AND radar_indicated != 'null'::jsonb 
            AND radar_indicated != '{}'::jsonb;
        """)
        radar = cur.fetchone()[0]
        cur.close()
        
        print(f"\nDev Database Final Totals:")
        print(f"  Total alerts: {total:,}")
        print(f"  Radar-detected: {radar:,}")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        dev_conn.rollback()
        raise
    finally:
        prod_conn.close()
        dev_conn.close()

if __name__ == "__main__":
    main()
