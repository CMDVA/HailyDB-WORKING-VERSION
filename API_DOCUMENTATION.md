# HailyDB API Documentation v2.0

## Overview

HailyDB provides a comprehensive RESTful API for accessing National Weather Service alerts, Storm Prediction Center reports, and enhanced weather intelligence data. The API supports real-time alerts, historical analysis, and geographic filtering for enterprise applications.

**Base URL:** `https://your-hailydb-instance.replit.app`

## Authentication

Currently in development. API access is open for testing. Production deployment will require API keys.

## Response Format

All endpoints return JSON responses with consistent error handling:

```json
{
  "status": "success|error",
  "data": {},
  "timestamp": "2025-08-12T02:00:00Z",
  "pagination": {
    "page": 1,
    "per_page": 50,
    "total": 1234,
    "pages": 25
  }
}
```

## Rate Limiting

- **Development**: No limits
- **Production**: 100 requests/minute per client

---

## Core Alert Endpoints

### Get Alerts with Filtering
```http
GET /api/alerts/search
```

Advanced search endpoint with comprehensive filtering options.

**Query Parameters:**
- `state` (string): Filter by state abbreviation (e.g., "TX", "CA")
- `county` (string): Filter by county name
- `area` (string): Filter by area description
- `severity` (string): Filter by severity level
- `event_type` (string): Filter by event type (e.g., "Severe Thunderstorm Warning")
- `active_only` (boolean): Show only currently active alerts (default: false)
- `q` (string): Text search across event, area, and descriptions
- `start_date` (string): Start date filter (YYYY-MM-DD)
- `end_date` (string): End date filter (YYYY-MM-DD)
- `page` (integer): Page number (default: 1)
- `limit` (integer): Records per page (default: 50, max: 100)

**Example Request:**
```bash
curl "https://your-hailydb-instance.replit.app/api/alerts/search?state=TX&event_type=Severe%20Thunderstorm&active_only=true&limit=25"
```

**Example Response:**
```json
{
  "status": "success",
  "filters_applied": {
    "state": "TX",
    "event_type": "Severe Thunderstorm",
    "active_only": true
  },
  "pagination": {
    "page": 1,
    "per_page": 25,
    "total": 156,
    "pages": 7
  },
  "alerts": [
    {
      "id": "urn:oid:2.49.0.1.840.0.13eebe5c24dfb7dbd33c",
      "event": "Severe Thunderstorm Warning",
      "severity": "Severe",
      "area_desc": "Castro, TX; Parmer, TX",
      "effective": "2025-08-12T01:28:00Z",
      "expires": "2025-08-12T02:15:00Z",
      "headline": "Severe Thunderstorm Warning issued August 11 at 8:28PM CDT",
      "radar_indicated": {
        "hail_inches": 1.25,
        "wind_mph": 60,
        "wind_detected": true,
        "hail_detected": true
      },
      "affected_states": ["TX"],
      "spc_verified": false,
      "spc_confidence_score": null
    }
  ]
}
```

### Get Active Alerts Only
```http
GET /api/alerts/active
```

Returns all currently active alerts (effective ≤ now < expires).

**Example Response:**
```json
{
  "timestamp": "2025-08-12T02:00:00Z",
  "total_active": 219,
  "alerts": [...]
}
```

### Get Single Alert
```http
GET /api/alerts/{alert_id}
```

Retrieve detailed information for a specific alert.

**Example Response:**
```json
{
  "id": "alert_12345",
  "event": "Severe Thunderstorm Warning",
  "properties": {
    "headline": "Full headline text",
    "description": "Complete description with hazard details"
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [...]
  },
  "radar_indicated": {
    "hail_inches": 1.25,
    "wind_mph": 60
  },
  "spc_reports": [
    {
      "report_id": 12345,
      "report_type": "hail",
      "magnitude": "1.0",
      "confidence": 0.85
    }
  ],
  "ai_summary": "Enhanced AI-generated summary",
  "spc_ai_summary": "Professional meteorological assessment"
}
```

### Get Alerts by State
```http
GET /api/alerts/by-state/{state}
```

**Parameters:**
- `state` (required): State abbreviation
- `active_only` (optional): Filter to active alerts only

**Example:**
```bash
curl "https://your-hailydb-instance.replit.app/api/alerts/by-state/TX?active_only=true"
```

### Get Alerts by County
```http
GET /api/alerts/by-county/{state}/{county}
```

**Example:**
```bash
curl "https://your-hailydb-instance.replit.app/api/alerts/by-county/TX/Harris"
```

---

## Live Radar Alerts

### Get Live Radar Alerts
```http
GET /api/live-radar-alerts
```

Returns real-time severe weather alerts filtered for:
- Hail of ANY size
- Winds 50+ mph

**Query Parameters:**
- `format` (string): Response format (default: "json")

**Example Response:**
```json
{
  "status": "success",
  "statistics": {
    "active_alerts": 219,
    "hail_alerts": 1380,
    "wind_alerts": 1499,
    "live_radar_count": 25,
    "states_affected": 6,
    "period": "7 days"
  },
  "alerts": [
    {
      "id": "urn:oid:...",
      "time": "2025-08-12T01:28:00Z",
      "event": "Severe Thunderstorm Warning",
      "location": "Castro, TX; Parmer, TX",
      "state": "TX",
      "hail_size": 1.25,
      "wind_speed": 60,
      "description": "HAZARD...60 mph wind gusts and half dollar size hail."
    }
  ]
}
```

---

## SPC Reports

### Get SPC Reports
```http
GET /api/spc/reports
```

**Query Parameters:**
- `report_type` (string): "hail", "wind", or "tornado"
- `state` (string): State abbreviation
- `start_date` (string): YYYY-MM-DD format
- `end_date` (string): YYYY-MM-DD format
- `min_magnitude` (number): Minimum magnitude filter
- `page` (integer): Page number
- `limit` (integer): Records per page

**Example:**
```bash
curl "https://your-hailydb-instance.replit.app/api/spc/reports?report_type=hail&state=TX&min_magnitude=2.0"
```

### Get SPC Report Details
```http
GET /api/spc/reports/{report_id}
```

**Example Response:**
```json
{
  "id": 12345,
  "report_date": "2025-08-11",
  "report_type": "hail",
  "time_utc": "2130",
  "location": "5 WNW AMARILLO",
  "county": "POTTER",
  "state": "TX",
  "latitude": 35.2500,
  "longitude": -101.9167,
  "magnitude": {
    "hail_inches": 2.0,
    "display": "2.00\""
  },
  "comments": "TRAINED SPOTTER REPORTED GOLF BALL SIZE HAIL",
  "enhanced_context": {
    "version": "v4.0",
    "summary": "Professional meteorological location summary",
    "nearby_places": ["Amarillo", "Canyon"],
    "generated_at": "2025-08-12T01:00:00Z"
  },
  "spc_enrichment": {
    "damage_potential": "Significant property damage likely",
    "impact_assessment": "Vehicle damage, roof damage expected"
  }
}
```

### Get Enhanced Context
```http
GET /api/spc/enrichment/{report_id}
```

Returns the Enhanced Context v4.0 summary for a specific SPC report.

---

## Hurricane Data

### Get Hurricane Tracks
```http
GET /api/hurricane-tracks
```

**Query Parameters:**
- `year` (integer): Filter by year
- `basin` (string): Atlantic ("AL") or Pacific ("EP")
- `min_intensity` (integer): Minimum wind speed
- `name` (string): Storm name filter

**Example:**
```bash
curl "https://your-hailydb-instance.replit.app/api/hurricane-tracks?year=2024&basin=AL&min_intensity=100"
```

### Get Specific Hurricane
```http
GET /api/hurricane-tracks/{storm_id}
```

Returns complete track data for a specific hurricane.

---

## Testing & Development Endpoints

### Test Radar Parsing
```http
POST /api/test/radar-parsing
```

Test endpoint for validating radar-indicated parsing logic.

**Request Body:**
```json
{
  "properties": {
    "event": "Severe Thunderstorm Warning",
    "headline": "Golf ball hail and 80 mph winds",
    "description": "Damaging winds of 80 mph and golf ball size hail expected."
  }
}
```

### Get Radar Parsing Summary
```http
GET /api/test/radar-summary
```

Returns summary statistics for radar parsing performance.

### Manual NWS Poll Trigger
```http
POST /api/admin/trigger-nws-poll
```

Manually trigger NWS alert polling (admin endpoint).

---

## Data Models

### Alert Model
```json
{
  "id": "string",
  "event": "string",
  "severity": "string",
  "area_desc": "string",
  "effective": "ISO 8601 datetime",
  "expires": "ISO 8601 datetime",
  "sent": "ISO 8601 datetime",
  "geometry": "GeoJSON geometry object",
  "properties": {
    "headline": "string",
    "description": "string",
    "instruction": "string"
  },
  "radar_indicated": {
    "hail_inches": "number|null",
    "wind_mph": "number|null",
    "hail_detected": "boolean",
    "wind_detected": "boolean"
  },
  "affected_states": ["string"],
  "fips_codes": ["string"],
  "county_names": ["string"],
  "city_names": ["string"],
  "spc_verified": "boolean",
  "spc_confidence_score": "number|null",
  "spc_reports": ["SPC Report objects"],
  "ai_summary": "string|null",
  "spc_ai_summary": "string|null",
  "ingested_at": "ISO 8601 datetime"
}
```

### SPC Report Model
```json
{
  "id": "integer",
  "report_date": "YYYY-MM-DD",
  "report_type": "hail|wind|tornado",
  "time_utc": "string",
  "location": "string",
  "county": "string",
  "state": "string",
  "latitude": "number",
  "longitude": "number",
  "magnitude": {
    "hail_inches": "number|null",
    "wind_mph": "number|null",
    "tornado_fscale": "string|null",
    "display": "string"
  },
  "comments": "string",
  "enhanced_context": {
    "version": "string",
    "summary": "string",
    "nearby_places": ["string"],
    "generated_at": "ISO 8601 datetime"
  },
  "spc_enrichment": "object|null",
  "ingested_at": "ISO 8601 datetime"
}
```

---

## Error Handling

### HTTP Status Codes
- `200 OK`: Successful request
- `400 Bad Request`: Invalid parameters
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid date format. Expected YYYY-MM-DD.",
    "details": {
      "parameter": "start_date",
      "provided": "2025-13-01"
    }
  },
  "timestamp": "2025-08-12T02:00:00Z"
}
```

### Common Error Codes
- `INVALID_PARAMETER`: Invalid query parameter
- `MISSING_PARAMETER`: Required parameter missing
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `RESOURCE_NOT_FOUND`: Alert/report not found
- `INTERNAL_ERROR`: Server processing error

---

## Usage Examples

### Real-Time Weather Monitoring
```python
import requests

# Monitor active severe weather in Texas
response = requests.get(
    "https://your-hailydb-instance.replit.app/api/alerts/search",
    params={
        "state": "TX",
        "active_only": "true",
        "event_type": "Severe Thunderstorm Warning",
        "limit": 100
    }
)

alerts = response.json()["alerts"]
for alert in alerts:
    hail_size = alert["radar_indicated"]["hail_inches"]
    wind_speed = alert["radar_indicated"]["wind_mph"]
    if hail_size and hail_size >= 2.0:  # Golf ball size or larger
        print(f"Large hail alert: {alert['area_desc']} - {hail_size}\" hail")
```

### Historical Analysis
```python
# Analyze hail reports for insurance claims
response = requests.get(
    "https://your-hailydb-instance.replit.app/api/spc/reports",
    params={
        "report_type": "hail",
        "state": "TX",
        "start_date": "2025-06-01",
        "end_date": "2025-08-01",
        "min_magnitude": 1.0
    }
)

reports = response.json()["reports"]
for report in reports:
    print(f"{report['report_date']}: {report['location']} - {report['magnitude']['display']} hail")
```

### Webhook Integration
```python
# Real-time alert processing
def process_webhook(alert_data):
    if alert_data["radar_indicated"]["hail_inches"] >= 2.0:
        # Trigger insurance claim system
        create_potential_claim(alert_data)
    
    if alert_data["radar_indicated"]["wind_mph"] >= 70:
        # Alert emergency management
        send_emergency_notification(alert_data)
```

---

## Performance Guidelines

### Optimization Tips
1. **Use Pagination**: Always specify reasonable `limit` values (≤ 100)
2. **Filter Appropriately**: Use geographic and temporal filters to reduce dataset size
3. **Cache Frequently**: Cache static data like county lists and alert types
4. **Active Filtering**: Use `active_only=true` for real-time applications

### Query Examples
```bash
# Efficient: Specific geographic and temporal filtering
curl "/api/alerts/search?state=TX&county=Harris&start_date=2025-08-01&limit=50"

# Inefficient: No filtering on large dataset
curl "/api/alerts/search?limit=1000"
```

### Rate Limiting Best Practices
- Implement exponential backoff for retries
- Cache responses when appropriate
- Use webhook notifications instead of frequent polling
- Request only necessary data fields

---

## SDKs and Libraries

### Python SDK (Coming Soon)
```python
from hailydb import HailyDBClient

client = HailyDBClient(api_key="your_api_key")
alerts = client.alerts.search(state="TX", active_only=True)
```

### JavaScript SDK (Coming Soon)
```javascript
import { HailyDBClient } from 'hailydb-js';

const client = new HailyDBClient({ apiKey: 'your_api_key' });
const alerts = await client.alerts.search({ state: 'TX', activeOnly: true });
```

---

## Webhook Notifications

### Webhook Configuration
Configure real-time notifications for specific conditions:

```json
{
  "webhook_url": "https://your-app.com/hailydb-webhook",
  "conditions": {
    "hail_threshold": 2.0,
    "wind_threshold": 70,
    "states": ["TX", "OK"],
    "event_types": ["Severe Thunderstorm Warning", "Tornado Warning"]
  }
}
```

### Webhook Payload
```json
{
  "event_type": "alert_matched",
  "timestamp": "2025-08-12T02:00:00Z",
  "alert": {
    "id": "alert_12345",
    "event": "Severe Thunderstorm Warning",
    "radar_indicated": {
      "hail_inches": 2.5,
      "wind_mph": 75
    },
    "area_desc": "Harris County, TX"
  },
  "matched_conditions": ["hail_threshold", "wind_threshold"]
}
```

---

*API Documentation v2.0 | Last Updated: August 12, 2025*