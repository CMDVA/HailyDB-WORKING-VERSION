# HailyDB AI Agent Integration Specification
## Structured API Reference for AI Systems

**Base URL:** `https://api.hailydb.com`  
**Version:** 2.0  
**Format:** JSON  
**Authentication:** Bearer token (production)

---

## Agent Integration Overview

HailyDB provides real-time weather intelligence through RESTful APIs optimized for AI agent consumption. All endpoints return structured JSON with consistent error handling and pagination.

### Key Capabilities for AI Agents
- **Real-time severe weather detection** (hail, wind, tornado alerts)
- **Historical storm verification** through SPC cross-referencing  
- **Geographic filtering** by state, county, FIPS codes, or radius
- **Temporal analysis** with date range and active alert filtering
- **Hurricane tracking** with complete HURDAT2 database access

---

## Primary Endpoints for AI Agents

### 1. Real-Time Severe Weather Monitoring
```
GET https://api.hailydb.com/api/live-radar-alerts?format=json
```

**Purpose:** Immediate severe weather threats (hail ANY size, winds 50+ mph)  
**Update Frequency:** Real-time (5-minute polling)  
**Response Structure:**
```json
{
  "status": "success",
  "statistics": {
    "active_alerts": 206,
    "hail_alerts": 1382,
    "wind_alerts": 1501,
    "live_radar_count": 15,
    "states_affected": 5,
    "period": "7 days"
  },
  "alerts": [
    {
      "id": "urn:oid:...",
      "time": "2025-08-12T02:18:00Z",
      "event": "Severe Thunderstorm Warning",
      "location": "County, State",
      "state": "TX",
      "hail_size": 1.0,
      "wind_speed": 60,
      "description": "HAZARD details",
      "expires": "2025-08-12T03:30:00Z"
    }
  ]
}
```

### 2. Advanced Alert Search
```
GET https://api.hailydb.com/api/alerts/search
```

**Purpose:** Flexible alert filtering with multiple criteria  
**Key Parameters:**
- `state`: State abbreviation (TX, CA, etc.)
- `active_only`: boolean - only current alerts
- `event_type`: specific alert type filter
- `start_date`/`end_date`: YYYY-MM-DD format
- `q`: text search across descriptions
- `page`/`limit`: pagination control

**Agent Usage Example:**
```
GET /api/alerts/search?state=TX&event_type=Severe%20Thunderstorm&active_only=true&limit=50
```

### 3. Currently Active Alerts
```
GET https://api.hailydb.com/api/alerts/active
```

**Purpose:** All active NWS alerts (effective ≤ now < expires)  
**Response:** Array of complete alert objects with radar_indicated data

### 4. SPC Storm Report Verification
```
GET https://api.hailydb.com/api/spc/reports
```

**Purpose:** Verified storm damage reports from Storm Prediction Center  
**Key Parameters:**
- `report_type`: "hail", "wind", "tornado"
- `state`: geographic filter
- `min_magnitude`: intensity threshold
- `start_date`/`end_date`: temporal range

### 5. Geographic Targeting
```
GET https://api.hailydb.com/api/alerts/by-state/{state}
GET https://api.hailydb.com/api/alerts/by-county/{state}/{county}
GET https://api.hailydb.com/api/alerts/radius?lat={lat}&lon={lon}&radius={miles}
```

**Purpose:** Geographic precision for location-specific queries

---

## Data Structure Specifications

### Alert Object Schema
```typescript
interface Alert {
  id: string;
  event: string;
  severity: "Minor" | "Moderate" | "Severe" | "Extreme";
  area_desc: string;
  effective: string; // ISO 8601
  expires: string; // ISO 8601
  radar_indicated: {
    hail_inches: number | null;
    wind_mph: number | null;
    hail_detected: boolean;
    wind_detected: boolean;
    tornado_detected: boolean;
  };
  affected_states: string[];
  fips_codes: string[];
  county_names: string[];
  spc_verified: boolean;
  spc_confidence_score: number | null;
  geometry: GeoJSON;
  ai_summary: string | null;
  spc_ai_summary: string | null;
}
```

### SPC Report Schema
```typescript
interface SPCReport {
  id: number;
  report_date: string; // YYYY-MM-DD
  report_type: "hail" | "wind" | "tornado";
  time_utc: string;
  location: string;
  county: string;
  state: string;
  latitude: number;
  longitude: number;
  magnitude: {
    hail_inches?: number;
    wind_mph?: number;
    tornado_fscale?: string;
    display: string;
  };
  comments: string;
  enhanced_context: {
    version: string;
    summary: string;
    nearby_places: string[];
    generated_at: string;
  };
}
```

---

## AI Agent Workflow Patterns

### 1. Real-Time Severe Weather Monitoring
```python
# Continuous monitoring pattern for AI agents
async def monitor_severe_weather():
    response = await get("https://api.hailydb.com/api/live-radar-alerts?format=json")
    data = response.json()
    
    for alert in data['alerts']:
        # Hail damage assessment
        if alert['hail_size'] >= 2.0:  # Golf ball or larger
            yield {
                'threat_type': 'large_hail',
                'severity': 'high' if alert['hail_size'] >= 2.75 else 'moderate',
                'location': alert['location'],
                'impact': 'vehicle_property_damage'
            }
        
        # Wind damage assessment  
        if alert['wind_speed'] >= 70:  # Damaging winds
            yield {
                'threat_type': 'damaging_winds',
                'severity': 'extreme' if alert['wind_speed'] >= 80 else 'high',
                'location': alert['location'],
                'impact': 'structural_tree_damage'
            }
```

### 2. Historical Event Analysis
```python
# Pattern for historical storm analysis
async def analyze_storm_history(state, days=30):
    # Get recent alerts
    alerts = await get(f"/api/alerts/search?state={state}&start_date={start_date}")
    
    # Get SPC verification
    spc_reports = await get(f"/api/spc/reports?state={state}&start_date={start_date}")
    
    # Cross-reference for accuracy assessment
    verified_events = []
    for alert in alerts['alerts']:
        if alert['spc_verified']:
            verified_events.append({
                'predicted': alert['radar_indicated'],
                'verified': alert['spc_reports'],
                'accuracy': alert['spc_confidence_score']
            })
    
    return verified_events
```

### 3. Geographic Risk Assessment
```python
# Pattern for location-based risk analysis
async def assess_location_risk(lat, lon, radius=50):
    # Get recent activity in radius
    response = await get(f"/api/alerts/radius?lat={lat}&lon={lon}&radius={radius}")
    
    risk_factors = {
        'hail_frequency': 0,
        'wind_frequency': 0,
        'tornado_activity': 0,
        'recent_damage': 0
    }
    
    for alert in response['alerts']:
        if alert['radar_indicated']['hail_detected']:
            risk_factors['hail_frequency'] += 1
        if alert['radar_indicated']['wind_detected']:
            risk_factors['wind_frequency'] += 1
        if alert['event'] == 'Tornado Warning':
            risk_factors['tornado_activity'] += 1
        if alert['spc_verified']:
            risk_factors['recent_damage'] += 1
    
    return risk_factors
```

---

## Error Handling for AI Agents

### Standard Error Response
```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable description",
    "details": {
      "parameter": "problematic_field",
      "provided": "invalid_value",
      "expected": "valid_format"
    }
  },
  "timestamp": "2025-08-12T02:18:00Z"
}
```

### Error Codes for Agent Logic
- `INVALID_PARAMETER` → Retry with corrected parameters
- `RATE_LIMIT_EXCEEDED` → Implement exponential backoff
- `RESOURCE_NOT_FOUND` → Handle as empty result set
- `DATABASE_ERROR` → Retry after delay
- `EXTERNAL_SERVICE_ERROR` → Fallback to cached data

---

## Pagination Handling

### Standard Pagination Response
```json
{
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 1234,
    "pages": 25,
    "has_next": true,
    "has_prev": false
  },
  "data": []
}
```

### Agent Pagination Pattern
```python
async def get_all_results(endpoint, params={}):
    all_results = []
    page = 1
    
    while True:
        params['page'] = page
        response = await get(endpoint, params=params)
        data = response.json()
        
        all_results.extend(data['alerts'] or data['reports'])
        
        if not data.get('pagination', {}).get('has_next', False):
            break
            
        page += 1
        
    return all_results
```

---

## Real-Time Integration Patterns

### 1. Webhook Notifications (Recommended)
```python
# Webhook receiver for real-time alerts
@app.route('/hailydb-webhook', methods=['POST'])
def handle_webhook():
    payload = request.json
    
    if payload['event_type'] == 'alert_matched':
        alert = payload['alert']
        conditions = payload['matched_conditions']
        
        # Process immediately without polling
        process_real_time_alert(alert, conditions)
    
    return {'status': 'processed'}
```

### 2. Intelligent Polling
```python
# Efficient polling with state tracking
class WeatherMonitor:
    def __init__(self):
        self.last_check = None
        self.known_alerts = set()
    
    async def check_for_updates(self):
        # Only get new alerts since last check
        params = {}
        if self.last_check:
            params['start_date'] = self.last_check.strftime('%Y-%m-%d')
        
        response = await get("/api/alerts/active", params=params)
        new_alerts = [a for a in response['alerts'] if a['id'] not in self.known_alerts]
        
        # Update tracking
        self.known_alerts.update(a['id'] for a in response['alerts'])
        self.last_check = datetime.now()
        
        return new_alerts
```

---

## Data Quality Indicators

### Alert Confidence Levels
- `radar_indicated` → NWS radar detection (real-time)
- `spc_verified` → Storm Prediction Center confirmation (post-event)
- `spc_confidence_score` → 0.0-1.0 verification confidence
- `ai_summary` → Enhanced context analysis

### Data Freshness
- `ingested_at` → When alert entered HailyDB
- `effective` → When alert becomes active
- `sent` → Original NWS timestamp
- `expires` → Alert expiration time

---

## Performance Optimization for AI Agents

### 1. Efficient Querying
```python
# Use specific filters to reduce data transfer
params = {
    'active_only': True,  # Reduces dataset size
    'state': 'TX',        # Geographic filtering
    'limit': 100,        # Control batch size
    'event_type': 'Severe Thunderstorm Warning'  # Event filtering
}
```

### 2. Caching Strategy
```python
# Cache frequently accessed data
from datetime import timedelta
import asyncio

class CachedHailyDB:
    def __init__(self):
        self.cache = {}
        self.cache_duration = timedelta(minutes=5)
    
    async def get_active_alerts_cached(self, state=None):
        cache_key = f"active_alerts_{state}"
        
        if cache_key in self.cache:
            cached_time, data = self.cache[cache_key]
            if datetime.now() - cached_time < self.cache_duration:
                return data
        
        # Fetch fresh data
        data = await self.get_active_alerts(state)
        self.cache[cache_key] = (datetime.now(), data)
        return data
```

### 3. Parallel Processing
```python
# Process multiple states simultaneously
async def monitor_multiple_states(states):
    tasks = [get_active_alerts(state) for state in states]
    results = await asyncio.gather(*tasks)
    
    return dict(zip(states, results))
```

---

## Hurricane Data Integration

### Hurricane Track Access
```
GET https://api.hailydb.com/api/hurricane-tracks?year=2024&basin=AL
```

**AI Agent Usage:**
```python
async def analyze_hurricane_season(year, basin='AL'):
    response = await get(f"/api/hurricane-tracks?year={year}&basin={basin}")
    storms = response.json()['tracks']
    
    analysis = {
        'total_storms': len(storms),
        'major_hurricanes': len([s for s in storms if s['peak_intensity']['max_wind'] >= 111]),
        'landfall_events': [],
        'peak_activity_month': None
    }
    
    # Process landfall data
    for storm in storms:
        if storm.get('landfall_data'):
            analysis['landfall_events'].extend(storm['landfall_data'])
    
    return analysis
```

---

## Testing and Development

### API Health Check
```
GET https://api.hailydb.com/api/health
```

### Radar Parsing Validation
```
POST https://api.hailydb.com/api/test/radar-parsing
Content-Type: application/json

{
  "properties": {
    "event": "Severe Thunderstorm Warning",
    "description": "Golf ball size hail and 80 mph winds expected"
  }
}
```

---

## Rate Limiting for AI Agents

### Production Limits
- **Standard:** 100 requests/minute
- **Enterprise:** Custom limits available
- **Burst:** 20% over limit for 30 seconds

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1691827200
```

### Agent Rate Limiting Strategy
```python
import time
from datetime import datetime, timedelta

class RateLimitedClient:
    def __init__(self, requests_per_minute=100):
        self.requests_per_minute = requests_per_minute
        self.request_times = []
    
    async def make_request(self, endpoint, params={}):
        # Clean old requests
        now = datetime.now()
        self.request_times = [t for t in self.request_times if now - t < timedelta(minutes=1)]
        
        # Check rate limit
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_times[0]).total_seconds()
            await asyncio.sleep(sleep_time)
        
        # Make request
        self.request_times.append(now)
        return await self.get(endpoint, params)
```

---

## Summary for AI Agents

**Primary Endpoints:**
1. `GET /api/live-radar-alerts?format=json` - Real-time severe weather
2. `GET /api/alerts/search` - Flexible alert filtering  
3. `GET /api/alerts/active` - Currently active alerts
4. `GET /api/spc/reports` - Verified storm reports
5. `GET /api/hurricane-tracks` - Hurricane database

**Key Data Fields:**
- `radar_indicated.hail_inches` - Hail size detection
- `radar_indicated.wind_mph` - Wind speed detection  
- `spc_verified` - Post-event verification status
- `spc_confidence_score` - Verification confidence (0.0-1.0)
- `affected_states[]` - Geographic impact area

**Best Practices:**
- Use geographic and temporal filtering to optimize queries
- Implement proper error handling and retry logic
- Cache frequently accessed data with 5-minute TTL
- Prefer webhooks over polling for real-time notifications
- Monitor rate limits and implement exponential backoff

---

*AI Agent Integration Specification v2.0 | HailyDB Production API*  
*Base URL: https://api.hailydb.com | Real-time Weather Intelligence*