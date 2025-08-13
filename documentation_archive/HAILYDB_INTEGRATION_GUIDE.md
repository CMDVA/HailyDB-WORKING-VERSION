# HailyDB Integration Guide v2.0
## Complete API Documentation & Developer Reference

**Base URL:** `https://api.hailydb.com`

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Core Alert Endpoints](#core-alert-endpoints)
4. [SPC Report Endpoints](#spc-report-endpoints)
5. [Live Radar Integration](#live-radar-integration)
6. [Hurricane Data](#hurricane-data)
7. [Search & Filtering](#search--filtering)
8. [Data Models](#data-models)
9. [Integration Examples](#integration-examples)
10. [Error Handling](#error-handling)
11. [Rate Limiting](#rate-limiting)
12. [SDK Examples](#sdk-examples)

---

## Quick Start

### Basic API Call
```bash
curl "https://api.hailydb.com/api/alerts/active"
```

### Real-Time Severe Weather
```bash
curl "https://api.hailydb.com/api/live-radar-alerts?format=json"
```

### Search Alerts by State
```bash
curl "https://api.hailydb.com/api/alerts/search?state=TX&active_only=true"
```

---

## Authentication

**Current Status:** Open API for testing  
**Production:** API key authentication (coming soon)

```http
Authorization: Bearer YOUR_API_KEY
```

---

## Core Alert Endpoints

### Get All Active Alerts
**Endpoint:** `GET /api/alerts/active`

Returns all currently active NWS alerts (effective ≤ now < expires).

```bash
curl "https://api.hailydb.com/api/alerts/active"
```

**Response:**
```json
{
  "timestamp": "2025-08-12T02:18:00Z",
  "total_active": 206,
  "alerts": [
    {
      "id": "urn:oid:2.49.0.1.840.0.4f244d96dba7dadd5eb93ff516df448bf7f8be25.001.1",
      "event": "Special Weather Statement",
      "severity": "Moderate",
      "area_desc": "Pushmataha; Pittsburg; Latimer",
      "effective": "2025-08-12T02:24:00",
      "expires": "2025-08-12T03:00:00",
      "sent": "2025-08-12T02:24:00",
      "affected_states": ["OK"],
      "radar_indicated": {
        "hail_inches": 0.0,
        "wind_mph": 50
      },
      "enhanced_geometry": {
        "affected_states": ["OK"],
        "coordinate_count": 10,
        "geometry_bounds": {
          "max_lat": 34.76,
          "max_lon": -95.29,
          "min_lat": 34.39,
          "min_lon": -95.85000000000001
        },
        "geometry_type": "Polygon",
        "has_detailed_geometry": true
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-95.78, 34.5], [-95.77, 34.51], ...]]
      },
      "spc_verified": false,
      "spc_confidence_score": null,
      "spc_match_method": null,
      "spc_report_count": 0,
      "is_active": true,
      "duration_minutes": 36,
      "coordinate_count": 10,
      "ingested_at": "2025-08-12T02:25:03.012945",
      "updated_at": "2025-08-12T02:25:03.012945"
    }
  ]
}
```

### Advanced Alert Search
**Endpoint:** `GET /api/alerts/search`

Most powerful endpoint for filtering alerts with multiple criteria.

**Parameters:**
- `state` (string): State abbreviation (TX, CA, etc.)
- `county` (string): County name
- `event_type` (string): Event type filter
- `severity` (string): Severity level
- `active_only` (boolean): Only active alerts
- `q` (string): Text search
- `start_date` (string): YYYY-MM-DD
- `end_date` (string): YYYY-MM-DD
- `page` (integer): Page number
- `limit` (integer): Results per page (max 100)

```bash
curl "https://api.hailydb.com/api/alerts/search?state=TX&event_type=Severe%20Thunderstorm&active_only=true&limit=25"
```

**Response Format:**
```json
{
  "alerts": [
    {
      "id": "urn:oid:...",
      "event": "Severe Thunderstorm Warning",
      "severity": "Severe",
      "area_desc": "County Names",
      "effective": "2025-08-12T02:00:00",
      "expires": "2025-08-12T03:00:00",
      "radar_indicated": {...},
      "enhanced_geometry": {...},
      "spc_verified": false
    }
  ],
  "filters": {
    "active_only": true,
    "state": "TX",
    "event_type": "Severe Thunderstorm",
    "search_query": "",
    "severity": null,
    "area": null,
    "county": null
  },
  "limit": 25,
  "page": 1,
  "pages": 150,
  "total": 3745
}
```

### Get Single Alert
**Endpoint:** `GET /api/alerts/{alert_id}`

Retrieve complete details for a specific alert including AI summaries and SPC verification.

```bash
curl "https://api.hailydb.com/api/alerts/urn:oid:2.49.0.1.840.0.4f244d96dba7dadd5eb93ff516df448bf7f8be25.001.1"
```

**Note:** Alert IDs use URN format for NWS alerts. For JSON response, add `?format=json`

```bash
curl "https://api.hailydb.com/api/alerts/urn:oid:2.49.0.1.840.0.4f244d96dba7dadd5eb93ff516df448bf7f8be25.001.1?format=json"
```

### Alerts by Geographic Region

#### By State
```bash
curl "https://api.hailydb.com/api/alerts/by-state/TX?active_only=true"
```

#### By County
```bash
curl "https://api.hailydb.com/api/alerts/by-county/TX/Harris"
```

---

## SPC Report Endpoints

### Get SPC Storm Reports
**Endpoint:** `GET /api/spc/reports`

Access Storm Prediction Center verified storm reports with Enhanced Context.

**Parameters:**
- `report_type` (string): "hail", "wind", "tornado"
- `state` (string): State abbreviation
- `start_date` (string): YYYY-MM-DD
- `end_date` (string): YYYY-MM-DD
- `min_magnitude` (number): Minimum intensity
- `page` (integer): Page number
- `limit` (integer): Results per page

```bash
curl "https://api.hailydb.com/api/spc/reports?report_type=hail&state=TX&min_magnitude=2.0"
```

**Response:**
```json
{
  "filters": {
    "county": null,
    "date": null,
    "state": "TX",
    "type": "hail"
  },
  "pagination": {
    "has_more": true,
    "limit": 50,
    "offset": 0,
    "total": 45219
  },
  "reports": [
    {
      "id": 48924,
      "report_date": "2025-08-11",
      "report_type": "hail",
      "time_utc": "2130",
      "location": "5 WNW AMARILLO",
      "county": "POTTER",
      "state": "TX",
      "latitude": 35.2500,
      "longitude": -101.9167,
      "magnitude": {
        "size_hundredths": 200
      },
      "comments": "TRAINED SPOTTER REPORTED GOLF BALL SIZE HAIL",
      "ingested_at": "2025-08-12T00:58:27.487366"
    }
  ]
}
```

### Get Single SPC Report
**Endpoint:** `GET /api/spc/reports/{report_id}`

```bash
curl "https://api.hailydb.com/api/spc/reports/12345"
```

### Enhanced Context Details
**Endpoint:** `GET /api/spc/enrichment/{report_id}`

Get Enhanced Context v4.0 summary for specific SPC report.

```bash
curl "https://api.hailydb.com/api/spc/enrichment/12345"
```

---

## Live Radar Integration

### Real-Time Severe Weather Alerts
**Endpoint:** `GET /api/live-radar-alerts`

Returns alerts filtered for immediate severe weather threats:
- Hail of ANY size
- Winds 50+ mph

```bash
curl "https://api.hailydb.com/api/live-radar-alerts?format=json"
```

**Response:**
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
      "id": "urn:oid:2.49.0.1.840.0.850db515...",
      "time": "2025-08-12T02:18:00Z",
      "event": "Severe Thunderstorm Warning",
      "location": "Deaf Smith, TX; Randall, TX",
      "state": "TX",
      "hail_size": 1.0,
      "wind_speed": 60,
      "description": "HAZARD...60 mph wind gusts and quarter size hail.",
      "expires": "2025-08-12T03:30:00Z"
    }
  ]
}
```

### Radar Alert Summary
**Endpoint:** `GET /api/radar-alerts/summary`

Aggregate statistics for dashboard applications.

```bash
curl "https://api.hailydb.com/api/radar-alerts/summary"
```

---

## Hurricane Data

### Hurricane Track Database
**Endpoint:** `GET /api/hurricane-tracks`

HURDAT2 historical hurricane data with complete track information.

**Parameters:**
- `year` (integer): Filter by year
- `basin` (string): "AL" (Atlantic) or "EP" (Pacific)
- `min_intensity` (integer): Minimum wind speed
- `name` (string): Storm name
- `season` (string): Hurricane season year

```bash
curl "https://api.hailydb.com/api/hurricane-tracks?year=2024&basin=AL&min_intensity=100"
```

### Specific Hurricane Details
**Endpoint:** `GET /api/hurricane-tracks/{storm_id}`

Complete track data for individual hurricane.

```bash
curl "https://api.hailydb.com/api/hurricane-tracks/AL012024"
```

**Response:**
```json
{
  "storm_id": "AL012024",
  "name": "ALBERTO",
  "year": 2024,
  "basin": "AL",
  "track_points": [
    {
      "datetime": "2024-06-19T18:00:00Z",
      "latitude": 25.1,
      "longitude": -97.8,
      "max_wind": 45,
      "min_pressure": 994,
      "status": "TS"
    }
  ],
  "peak_intensity": {
    "max_wind": 50,
    "min_pressure": 990
  },
  "landfall_data": [
    {
      "datetime": "2024-06-20T09:00:00Z",
      "location": "Tamaulipas, Mexico",
      "intensity": 45
    }
  ]
}
```

---

## Search & Filtering

### Geographic Radius Search
**Endpoint:** `GET /api/alerts/radius`

Find alerts within radius of coordinates.

**Parameters:**
- `lat` (float): Latitude
- `lon` (float): Longitude  
- `radius` (float): Radius in miles
- `active_only` (boolean): Only active alerts

```bash
curl "https://api.hailydb.com/api/alerts/radius?lat=29.7604&lon=-95.3698&radius=50&active_only=true"
```

### FIPS Code Search
**Endpoint:** `GET /api/alerts/fips/{fips_code}`

Search by Federal Information Processing Standards county codes.

```bash
curl "https://api.hailydb.com/api/alerts/fips/48201"  # Harris County, TX
```

### Multi-State Search
**Endpoint:** `GET /api/alerts/multi-state`

Search across multiple states simultaneously.

```bash
curl "https://api.hailydb.com/api/alerts/multi-state?states=TX,OK,AR&event_type=Tornado"
```

---

## Data Models

### Complete Alert Object Schema
```json
{
  "id": "urn:oid:2.49.0.1.840.0.{hash}.{sequence}.{version}",
  "event": "Severe Thunderstorm Warning|Tornado Warning|Special Weather Statement|...",
  "severity": "Minor|Moderate|Severe|Extreme",
  "area_desc": "County; County; County",
  "effective": "2025-08-12T02:24:00",
  "expires": "2025-08-12T03:00:00", 
  "sent": "2025-08-12T02:24:00",
  "affected_states": ["TX", "OK"],
  "ai_summary": "string|null",
  "ai_tags": "string|null",
  "city_names": "string|null",
  "coordinate_count": 10,
  "county_names": {},
  "duration_minutes": 36,
  "enhanced_geometry": {
    "affected_states": ["OK"],
    "coordinate_count": 10,
    "county_state_mapping": [],
    "coverage_area_sq_degrees": 0.2072,
    "fips_codes": [],
    "geometry_bounds": {
      "max_lat": 34.76,
      "max_lon": -95.29,
      "min_lat": 34.39,
      "min_lon": -95.85000000000001
    },
    "geometry_type": "Polygon",
    "has_detailed_geometry": true
  },
  "fips_codes": [],
  "geocode": {
    "SAME": ["040127", "040121", "040077"],
    "UGC": ["OKZ049", "OKZ073", "OKZ075"]
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-95.78, 34.5], [-95.77, 34.51], ...]]
  },
  "geometry_bounds": {
    "max_lat": 34.76,
    "max_lon": -95.29,
    "min_lat": 34.39,
    "min_lon": -95.85000000000001
  },
  "geometry_type": "Polygon",
  "ingested_at": "2025-08-12T02:25:03.012945",
  "is_active": true,
  "location_info": {
    "affected_zones": ["https://api.weather.gov/zones/forecast/OKZ049"],
    "area_description": "Pushmataha; Pittsburg; Latimer",
    "coordinate_count": 10,
    "counties": [],
    "fips_codes": [],
    "geocodes": {
      "SAME": ["040127", "040121", "040077"],
      "UGC": ["OKZ049", "OKZ073", "OKZ075"]
    },
    "geometry_bounds": {...},
    "geometry_type": "Polygon",
    "states": []
  },
  "properties": {
    "@id": "https://api.weather.gov/alerts/urn:oid:...",
    "@type": "wx:Alert",
    "affectedZones": ["https://api.weather.gov/zones/forecast/OKZ049"],
    "areaDesc": "Pushmataha; Pittsburg; Latimer",
    "category": "Met",
    "certainty": "Observed",
    "description": "Full NWS alert description text...",
    "effective": "2025-08-11T21:24:00-05:00",
    "event": "Special Weather Statement",
    "expires": "2025-08-11T22:00:00-05:00",
    "headline": "Special Weather Statement issued August 11 at 9:24PM CDT",
    "instruction": "If outdoors, consider seeking shelter inside a building.",
    "parameters": {
      "maxHailSize": ["0.00"],
      "maxWindGust": ["50 MPH"],
      "eventMotionDescription": ["2025-08-12T02:24:00-00:00...storm...345DEG...3KT..."]
    },
    "severity": "Moderate",
    "urgency": "Expected"
  },
  "radar_indicated": {
    "hail_inches": 0.0,
    "wind_mph": 50
  },
  "spc_ai_summary": "string|null",
  "spc_confidence_score": "number|null",
  "spc_match_method": "string|null",
  "spc_report_count": 0,
  "spc_reports": "array|null",
  "spc_verified": false,
  "updated_at": "2025-08-12T02:25:03.012945"
}
```

### SPC Report Object Schema
```json
{
  "id": 48924,
  "report_date": "2025-08-11",
  "report_type": "hail|wind|tornado",
  "time_utc": "2355",
  "location": "3 SSE Mahnomen",
  "county": "Mahnomen", 
  "state": "MN",
  "latitude": 47.27,
  "longitude": -95.93,
  "magnitude": {
    "speed": 58,
    "size_hundredths": 175
  },
  "comments": "Corrects previous non-tstm wnd gst report from 3 SSE Mahnomen. Mesonet station MN044 Mahnomen MN DOT. (FGF)",
  "ingested_at": "2025-08-12T00:58:27.487366"
}
```

### Hurricane Track Object
```json
{
  "storm_id": "string",
  "name": "string",
  "year": "integer",
  "basin": "AL|EP|CP|WP",
  "track_points": [
    {
      "datetime": "ISO 8601 datetime",
      "latitude": "number",
      "longitude": "number",
      "max_wind": "integer",
      "min_pressure": "integer|null",
      "status": "string",
      "forward_speed": "integer|null",
      "direction": "integer|null"
    }
  ],
  "peak_intensity": {
    "max_wind": "integer",
    "min_pressure": "integer",
    "datetime": "ISO 8601 datetime"
  },
  "landfall_data": [
    {
      "datetime": "ISO 8601 datetime",
      "location": "string",
      "intensity": "integer",
      "pressure": "integer|null"
    }
  ],
  "season_stats": {
    "ace": "number",
    "duration_hours": "integer",
    "max_category": "integer"
  }
}
```

---

## Integration Examples

### Python Integration
```python
import requests
from datetime import datetime, timedelta

class HailyDBClient:
    def __init__(self, base_url="https://api.hailydb.com"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_active_alerts(self, state=None):
        """Get currently active alerts"""
        url = f"{self.base_url}/api/alerts/active"
        params = {}
        if state:
            params['state'] = state
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_severe_weather(self, min_hail=None, min_wind=None):
        """Get live radar alerts with severity filters"""
        url = f"{self.base_url}/api/live-radar-alerts"
        response = self.session.get(url, params={'format': 'json'})
        response.raise_for_status()
        
        alerts = response.json()['alerts']
        filtered = []
        
        for alert in alerts:
            if min_hail and alert.get('hail_size', 0) >= min_hail:
                filtered.append(alert)
            elif min_wind and alert.get('wind_speed', 0) >= min_wind:
                filtered.append(alert)
        
        return filtered
    
    def search_alerts(self, **kwargs):
        """Advanced alert search"""
        url = f"{self.base_url}/api/alerts/search"
        response = self.session.get(url, params=kwargs)
        response.raise_for_status()
        return response.json()
    
    def get_spc_reports(self, report_type=None, state=None, days_back=7):
        """Get SPC storm reports"""
        url = f"{self.base_url}/api/spc/reports"
        params = {}
        
        if report_type:
            params['report_type'] = report_type
        if state:
            params['state'] = state
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        params['start_date'] = start_date.strftime('%Y-%m-%d')
        params['end_date'] = end_date.strftime('%Y-%m-%d')
        
        response = self.session.get(url, params=params)
        response.raise_for_status()
        return response.json()

# Usage Examples
client = HailyDBClient()

# Get all active alerts in Texas
tx_alerts = client.get_active_alerts(state="TX")

# Find severe hail storms (2+ inches)
severe_hail = client.get_severe_weather(min_hail=2.0)

# Search for tornado warnings in last 24 hours
tornado_warnings = client.search_alerts(
    event_type="Tornado Warning",
    start_date="2025-08-11",
    active_only=True
)

# Get verified hail reports from SPC
hail_reports = client.get_spc_reports(
    report_type="hail",
    state="TX",
    days_back=30
)
```

### JavaScript Integration
```javascript
class HailyDBAPI {
    constructor(baseUrl = 'https://api.hailydb.com') {
        this.baseUrl = baseUrl;
    }
    
    async getActiveAlerts(state = null) {
        const url = new URL(`${this.baseUrl}/api/alerts/active`);
        if (state) url.searchParams.set('state', state);
        
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }
    
    async getLiveRadarAlerts() {
        const response = await fetch(`${this.baseUrl}/api/live-radar-alerts?format=json`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }
    
    async searchAlerts(filters = {}) {
        const url = new URL(`${this.baseUrl}/api/alerts/search`);
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                url.searchParams.set(key, value);
            }
        });
        
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }
    
    async getSPCReports(filters = {}) {
        const url = new URL(`${this.baseUrl}/api/spc/reports`);
        Object.entries(filters).forEach(([key, value]) => {
            if (value !== null && value !== undefined) {
                url.searchParams.set(key, value);
            }
        });
        
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    }
}

// Usage Examples
const hailydb = new HailyDBAPI();

// Real-time severe weather monitoring
async function monitorSevereWeather() {
    try {
        const data = await hailydb.getLiveRadarAlerts();
        
        data.alerts.forEach(alert => {
            if (alert.hail_size >= 2.0) {
                console.log(`Large hail detected: ${alert.location} - ${alert.hail_size}" hail`);
            }
            if (alert.wind_speed >= 70) {
                console.log(`Damaging winds detected: ${alert.location} - ${alert.wind_speed} mph`);
            }
        });
        
        return data;
    } catch (error) {
        console.error('Error fetching live radar:', error);
    }
}

// Search for recent tornado activity
async function findTornadoActivity(state, days = 7) {
    const endDate = new Date();
    const startDate = new Date();
    startDate.setDate(endDate.getDate() - days);
    
    const alerts = await hailydb.searchAlerts({
        state: state,
        event_type: 'Tornado Warning',
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0]
    });
    
    return alerts;
}
```

### Real-Time Webhook Integration
```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route('/hailydb-webhook', methods=['POST'])
def handle_hailydb_webhook():
    """Process real-time HailyDB notifications"""
    data = request.json
    
    if data['event_type'] == 'alert_matched':
        alert = data['alert']
        conditions = data['matched_conditions']
        
        # Process based on severity
        if 'hail_threshold' in conditions:
            hail_size = alert['radar_indicated']['hail_inches']
            process_hail_alert(alert, hail_size)
        
        if 'wind_threshold' in conditions:
            wind_speed = alert['radar_indicated']['wind_mph']
            process_wind_alert(alert, wind_speed)
    
    return jsonify({'status': 'processed'})

def process_hail_alert(alert, hail_size):
    """Handle hail damage alerts"""
    if hail_size >= 2.0:  # Golf ball or larger
        # Trigger insurance claim system
        create_potential_claim({
            'alert_id': alert['id'],
            'location': alert['area_desc'],
            'hail_size': hail_size,
            'timestamp': alert['effective']
        })

def process_wind_alert(alert, wind_speed):
    """Handle wind damage alerts"""
    if wind_speed >= 70:  # Damaging winds
        # Alert emergency management
        send_emergency_notification({
            'alert_id': alert['id'],
            'location': alert['area_desc'],
            'wind_speed': wind_speed,
            'urgency': 'high' if wind_speed >= 80 else 'moderate'
        })
```

---

## Error Handling

### HTTP Status Codes
- `200 OK` - Successful request
- `400 Bad Request` - Invalid parameters
- `401 Unauthorized` - Invalid API key
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### Error Response Format
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid date format. Expected YYYY-MM-DD.",
    "details": {
      "parameter": "start_date",
      "provided": "2025-13-01",
      "expected": "YYYY-MM-DD"
    }
  },
  "timestamp": "2025-08-12T02:18:00Z",
  "request_id": "req_1234567890"
}
```

### Common Error Codes
- `INVALID_PARAMETER` - Invalid query parameter
- `MISSING_PARAMETER` - Required parameter missing
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `RESOURCE_NOT_FOUND` - Alert/report not found
- `INVALID_DATE_FORMAT` - Date format error
- `INVALID_COORDINATES` - Geographic coordinate error
- `DATABASE_ERROR` - Internal database error
- `EXTERNAL_SERVICE_ERROR` - NWS/SPC service unavailable

---

## Rate Limiting

### Current Limits
- **Development**: No limits (testing)
- **Production**: 100 requests/minute per API key
- **Enterprise**: Custom limits available

### Rate Limit Headers
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1691827200
X-RateLimit-Window: 60
```

### Best Practices
1. **Implement Exponential Backoff**: Wait longer between retries
2. **Cache Responses**: Store frequently accessed data locally
3. **Use Webhooks**: Prefer notifications over frequent polling
4. **Filter Appropriately**: Request only necessary data
5. **Batch Requests**: Combine multiple queries when possible

---

## Advanced Features

### Bulk Data Export
**Endpoint:** `GET /api/export/alerts`

Export large datasets with compression.

```bash
curl "https://api.hailydb.com/api/export/alerts?state=TX&start_date=2025-01-01&format=csv" --output alerts.csv.gz
```

### Historical Analytics
**Endpoint:** `GET /api/analytics/trends`

Temporal analysis and trend data.

```bash
curl "https://api.hailydb.com/api/analytics/trends?metric=hail_frequency&state=TX&period=monthly&years=3"
```

### GeoJSON Export
**Endpoint:** `GET /api/alerts/geojson`

Native GeoJSON format for mapping applications.

```bash
curl "https://api.hailydb.com/api/alerts/geojson?active_only=true&event_type=Severe%20Thunderstorm%20Warning"
```

---

## SDK Examples

### Python SDK (PyPI Package)
```bash
pip install hailydb-python
```

```python
from hailydb import HailyDBClient

client = HailyDBClient(api_key="your_api_key")

# Get active severe weather
alerts = client.alerts.active(state="TX")

# Search with filters
results = client.alerts.search(
    event_type="Tornado Warning",
    active_only=True,
    state=["TX", "OK", "KS"]
)

# Real-time monitoring
for alert in client.live_radar.stream():
    if alert.hail_size >= 2.0:
        print(f"Large hail: {alert.location}")
```

### JavaScript/Node.js SDK
```bash
npm install hailydb-js
```

```javascript
const { HailyDBClient } = require('hailydb-js');

const client = new HailyDBClient({ apiKey: 'your_api_key' });

// Get active alerts
const alerts = await client.alerts.active({ state: 'TX' });

// Real-time subscription
client.liveRadar.subscribe({
  hailThreshold: 2.0,
  windThreshold: 70,
  callback: (alert) => {
    console.log(`Severe weather: ${alert.location}`);
  }
});
```

---

## Testing & Validation Endpoints

### Radar Parsing Test
**Endpoint:** `POST /api/test/radar-parsing`

Test the radar-indicated data extraction from alert text.

```bash
curl -X POST "https://api.hailydb.com/api/test/radar-parsing" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "event": "Severe Thunderstorm Warning",
      "headline": "Golf ball hail and 80 mph winds",
      "description": "Damaging winds of 80 mph and golf ball size hail expected."
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "test_results": [
    {
      "test_case": 1,
      "input": {
        "event": "Severe Thunderstorm Warning",
        "headline": "Golf ball hail and 80 mph winds"
      },
      "radar_indicated": {
        "hail_inches": 1.75,
        "wind_mph": 80
      }
    }
  ]
}
```

### Radar Parsing Statistics
**Endpoint:** `GET /api/test/radar-summary`

Get comprehensive radar parsing performance metrics.

```bash
curl "https://api.hailydb.com/api/test/radar-summary"
```

**Response:**
```json
{
  "status": "success",
  "summary": {
    "total_severe_thunderstorm_warnings": 1456,
    "parsed_with_radar_data": 1456,
    "parsing_success_rate": "100.0%"
  },
  "sample_parsed_alerts": [
    {
      "id": "urn:oid:...",
      "area": "Harris County, TX",
      "radar_indicated": {
        "hail_inches": 1.0,
        "wind_mph": 60
      },
      "effective": "2025-08-12T01:30:00"
    }
  ]
}
```

### Manual NWS Poll Trigger
**Endpoint:** `POST /api/test/nws-poll`

Manually trigger NWS alert ingestion for testing.

```bash
curl -X POST "https://api.hailydb.com/api/test/nws-poll"
```

**Response:**
```json
{
  "status": "success",
  "new_alerts": 4,
  "message": "Polling completed. 4 new alerts ingested."
}
```

---

## Additional Missing Endpoints

### Geographic Radius Search
**Endpoint:** `GET /api/alerts/radius`

Find alerts within a specified radius of coordinates.

**Parameters:**
- `lat` (float, required): Latitude
- `lon` (float, required): Longitude  
- `radius` (float, required): Radius in miles
- `active_only` (boolean): Only active alerts

```bash
curl "https://api.hailydb.com/api/alerts/radius?lat=29.7604&lon=-95.3698&radius=50&active_only=true"
```

### FIPS Code Search
**Endpoint:** `GET /api/alerts/fips/{fips_code}`

Search alerts by Federal Information Processing Standards county codes.

```bash
curl "https://api.hailydb.com/api/alerts/fips/48201"  # Harris County, TX
```

### Alert Enrichment Trigger
**Endpoint:** `POST /alerts/enrich/{alert_id}`

Manually trigger AI enrichment for a specific alert.

```bash
curl -X POST "https://api.hailydb.com/alerts/enrich/urn:oid:2.49.0.1.840.0.{hash}.001.1"
```

### System Health Check
**Endpoint:** `GET /api/health`

Validate system status and data freshness.

```bash
curl "https://api.hailydb.com/api/health"
```

### State Enrichment APIs
**Endpoint:** `POST /api/state-enrichment/enrich`

Batch enrich alerts with missing state information.

```bash
curl -X POST "https://api.hailydb.com/api/state-enrichment/enrich" \
  -H "Content-Type: application/json" \
  -d '{"batch_size": 100}'
```

**Endpoint:** `GET /api/state-enrichment/stats`

Get state enrichment statistics.

```bash
curl "https://api.hailydb.com/api/state-enrichment/stats"
```

---

## Contact & Support

**API Documentation:** https://docs.hailydb.com  
**Status Page:** https://status.hailydb.com  
**Support Email:** api-support@hailydb.com  
**Rate Limit Increases:** enterprise@hailydb.com

---

*HailyDB Integration Guide v2.0 | Last Updated: August 12, 2025*  
*Base URL: https://api.hailydb.com | Production Ready*