# Production Database Import Instructions

## Complete Dataset Export Created ✅

**File**: `complete_alerts_export.json`  
**Size**: 88MB  
**Records**: 9,513 alerts  
**Content**: Complete historical weather alert database

## Import Methods

### Method 1: Direct JSON Import (Recommended)
```python
import json
import psycopg2

# Load the exported data
with open('complete_alerts_export.json', 'r') as f:
    alerts_data = json.load(f)

# Connect to production database
conn = psycopg2.connect("YOUR_PRODUCTION_DATABASE_URL")
cur = conn.cursor()

# Clear existing data (optional)
# cur.execute("TRUNCATE TABLE alerts CASCADE")

# Insert each alert
for alert in alerts_data:
    cur.execute("""
        INSERT INTO alerts (
            id, event, effective, expires, status, message_type, category, 
            urgency, severity, certainty, areas_desc, ugc_codes, geometry, 
            references, ingested_at, radar_detected, hail_size, wind_speed, 
            has_polygon, geometry_bounds, ai_summary, data_source, source_type, city_names
        ) VALUES (
            %(id)s, %(event)s, %(effective)s, %(expires)s, %(status)s, 
            %(message_type)s, %(category)s, %(urgency)s, %(severity)s, 
            %(certainty)s, %(areas_desc)s, %(ugc_codes)s, %(geometry)s, 
            %(references)s, %(ingested_at)s, %(radar_detected)s, %(hail_size)s, 
            %(wind_speed)s, %(has_polygon)s, %(geometry_bounds)s, %(ai_summary)s, 
            %(data_source)s, %(source_type)s, %(city_names)s
        ) ON CONFLICT (id) DO UPDATE SET
            event = EXCLUDED.event,
            effective = EXCLUDED.effective,
            expires = EXCLUDED.expires,
            status = EXCLUDED.status,
            radar_detected = EXCLUDED.radar_detected,
            hail_size = EXCLUDED.hail_size,
            wind_speed = EXCLUDED.wind_speed
    """, alert)

conn.commit()
cur.close()
conn.close()
```

### Method 2: PostgreSQL COPY Command
```sql
-- Create temporary table
CREATE TEMP TABLE alerts_import (data jsonb);

-- Load JSON data
\copy alerts_import FROM 'complete_alerts_export.json'

-- Insert from JSON
INSERT INTO alerts SELECT 
    (data->>'id')::varchar,
    (data->>'event')::varchar,
    (data->>'effective')::timestamp,
    -- ... continue for all fields
FROM alerts_import;
```

## Verification After Import

Test the previously failing alert:
```bash
curl "YOUR_PRODUCTION_API_URL/api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1"
```

Should return alert data instead of 404.

## Result
After import, your production API will have access to all 9,513 weather alerts, resolving the 404 errors and providing complete historical data to your users.