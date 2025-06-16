
# HailyDB v2.0 - Production Weather Intelligence API

**Real-Time Weather Data Platform for Enterprise Applications**

## Overview

HailyDB is a production-grade National Weather Service (NWS) alert processing platform that provides comprehensive weather intelligence through RESTful APIs. Our system processes multi-source weather data including real-time NWS alerts, Storm Prediction Center verification reports, hurricane tracking data, and AI-enhanced contextual summaries.

**Base URL:** `https://api.hailyai.com`

## Key Features

- 🌪️ **Real-Time Alert Processing** - Live NWS alert ingestion with 5-minute updates
- 🎯 **SPC Storm Verification** - Cross-referenced with official Storm Prediction Center reports
- 🚨 **Live Radar Detection** - Real-time radar-indicated hail and wind events
- 🧠 **AI-Enhanced Intelligence** - OpenAI GPT-4o powered contextual summaries
- 🌊 **Hurricane Track Data** - Complete NOAA HURDAT2 historical hurricane database
- 🔗 **Real-Time Webhooks** - Configurable notifications for external system integration
- 📊 **Enterprise APIs** - Production-ready endpoints with comprehensive filtering

## Data Sources

### Primary Data Streams
- **National Weather Service** - Real-time alerts with full polygon geometry
- **Storm Prediction Center** - Historical verification reports (tornado, wind, hail)
- **NOAA Hurricane Database** - Complete historical hurricane tracks and landfall data
- **Live Radar Processing** - Real-time radar-detected severe weather events
- **AI Enhancement Engine** - Location intelligence and contextual summaries

### Data Update Frequencies
- **NWS Alerts:** Every 5 minutes
- **Live Radar:** Every 60 seconds
- **SPC Reports:** Daily at midnight UTC
- **Hurricane Data:** Historical archive (complete through 2024)

## API Authentication

**Method:** API Key (optional, configurable per deployment)
```http
Authorization: Bearer YOUR_API_KEY
```

**Rate Limits:** 
- Search endpoints: 100 requests/minute
- Detail endpoints: 200 requests/minute
- Webhook management: 50 requests/minute

## Core API Endpoints

### Weather Alerts

#### Search Alerts
```http
GET https://api.hailyai.com/api/alerts/search
```

**Query Parameters:**
- `state` (string) - Two-letter state code (e.g., "TX", "FL")
- `event_type` (string) - Alert type (e.g., "Tornado Warning", "Severe Thunderstorm Warning")
- `severity` (string) - Severity level ("Extreme", "Severe", "Moderate", "Minor")
- `active_only` (boolean) - Only return currently active alerts
- `radar_indicated` (boolean) - Filter for radar-detected events only
- `spc_verified` (boolean) - Filter for SPC-verified events only
- `start_date` (ISO date) - Filter alerts after this date
- `end_date` (ISO date) - Filter alerts before this date
- `limit` (integer) - Number of results (default: 25, max: 100)
- `offset` (integer) - Pagination offset

**Example Request:**
```bash
curl "https://api.hailyai.com/api/alerts/search?state=TX&event_type=Severe%20Thunderstorm%20Warning&radar_indicated=true&limit=10"
```

**Response Format:**
```json
{
  "alerts": [
    {
      "id": "urn:oid:2.49.0.1.840.0.xxx",
      "event": "Severe Thunderstorm Warning",
      "severity": "Severe",
      "area_desc": "Dallas County, TX; Tarrant County, TX",
      "effective": "2025-06-12T18:30:00Z",
      "expires": "2025-06-12T19:30:00Z",
      "radar_indicated": {
        "hail_inches": 1.25,
        "wind_mph": 70
      },
      "spc_verified": true,
      "spc_report_count": 3,
      "ai_summary": "Radar-detected severe thunderstorm with quarter-sized hail and 70 mph winds affecting Dallas metropolitan area",
      "geometry": { /* GeoJSON polygon */ },
      "fips_codes": ["48113", "48439"],
      "affected_states": ["TX"],
      "geometry_bounds": {
        "min_lat": 32.6,
        "max_lat": 33.1,
        "min_lon": -97.5,
        "max_lon": -96.8
      }
    }
  ],
  "total_count": 47,
  "pagination": {
    "limit": 10,
    "offset": 0,
    "has_next": true
  }
}
```

#### Get Alert Details
```http
GET https://api.hailyai.com/api/alerts/{alert_id}
```

Returns complete alert information including full geometry, SPC verification details, and AI-enhanced summaries.

#### County-Specific Alerts
```http
GET https://api.hailyai.com/api/alerts/by-county/{state}/{county}
```

**Example:**
```bash
curl "https://api.hailyai.com/api/alerts/by-county/TX/Dallas"
```

#### AI-Enhanced Summaries
```http
GET https://api.hailyai.com/api/alerts/summaries
```

Returns alerts with AI-generated contextual summaries optimized for insurance, emergency management, and restoration applications.

### Storm Prediction Center (SPC) Reports

#### Search SPC Reports
```http
GET https://api.hailyai.com/api/spc/reports
```

**Query Parameters:**
- `report_date` (YYYY-MM-DD) - Specific date for reports
- `report_type` (string) - "tornado", "wind", or "hail"
- `state` (string) - Two-letter state code
- `county` (string) - County name
- `min_magnitude` (float) - Minimum magnitude (F-scale, mph, or inches)
- `lat` (float) - Latitude for geographic search
- `lon` (float) - Longitude for geographic search
- `radius` (float) - Search radius in miles (requires lat/lon)
- `enriched_only` (boolean) - Only return reports with AI enrichment
- `limit` (integer) - Number of results
- `offset` (integer) - Pagination offset

**Example Request:**
```bash
curl "https://api.hailyai.com/api/spc/reports?report_date=2025-06-10&report_type=hail&min_magnitude=1.0&state=TX"
```

**Response Format:**
```json
{
  "reports": [
    {
      "id": 12345,
      "report_date": "2025-06-10",
      "report_type": "hail",
      "time_utc": "1830",
      "location": "2 SW Dallas",
      "county": "Dallas",
      "state": "TX",
      "latitude": 32.7617,
      "longitude": -96.8089,
      "magnitude": {
        "size_inches": 1.25,
        "size_hundredths": 125
      },
      "comments": "Quarter-sized hail reported by storm spotter",
      "spc_enrichment": {
        "nearby_places": [
          {
            "name": "Downtown Dallas",
            "distance_miles": 0.0,
            "type": "primary_location"
          },
          {
            "name": "Deep Ellum",
            "distance_miles": 1.2,
            "type": "nearby_place"
          }
        ],
        "enriched_summary": "This official storm report documents hail at this location."
      },
      "enhanced_context": {
        "multi_alert_summary": "Part of a larger severe weather event affecting the Dallas-Fort Worth metroplex with multiple hail reports"
      }
    }
  ],
  "total_count": 23,
  "pagination": {
    "limit": 25,
    "offset": 0
  }
}
```

#### Get SPC Report Details
```http
GET https://api.hailyai.com/api/spc/reports/{report_id}
```

#### SPC Report Enrichment
```http
GET https://api.hailyai.com/api/spc/enrichment/{report_id}
```

Returns detailed location intelligence and contextual enrichment for a specific SPC report.

#### Enhanced Context v2.0
```http
GET https://api.hailyai.com/api/spc-reports/{report_id}/enhanced-context
```

**New Feature:** AI-powered Enhanced Context generates comprehensive meteorological summaries using:
- **Multi-source Intelligence:** Cross-references SPC reports with NWS alerts and radar data
- **Location Intelligence:** Uses Google Places API to find exact nearby places instead of generic coordinates  
- **Damage Assessment:** Official NWS hail and wind damage classifications
- **Event Context:** Multi-alert correlation for comprehensive storm analysis

**Response Format:**
```json
{
  "enhanced_context": {
    "enhanced_summary": "On June 10, 2025, a severe thunderstorm produced quarter-sized hail near Downtown Dallas. The 1.25-inch hail was reported at Central Business District at 6:30 PM UTC, with radar confirmation showing embedded supercell activity. Other nearby locations include Deep Ellum (1.2mi) and Fair Park (2.1mi).",
    "version": "v2.0",
    "generated_at": "2025-06-16T02:35:14Z",
    "location_context": {
      "event_location": "Downtown Dallas",
      "nearest_major_city": "Dallas at 0.0 miles",
      "nearby_places": [
        {
          "name": "Deep Ellum",
          "distance_miles": 1.2,
          "type": "nearby_place"
        }
      ]
    },
    "damage_assessment": {
      "category": "Large Hail",
      "damage_potential": "moderate damage to vehicles and property", 
      "is_severe": true
    }
  }
}
```

### Live Radar Alerts

#### Real-Time Radar Events
```http
GET https://api.hailyai.com/api/live-radar-alerts
```

**Query Parameters:**
- `states` (string) - Comma-separated state codes (e.g., "TX,OK,AR")
- `active_only` (boolean) - Only return currently active alerts
- `min_hail_size` (float) - Minimum hail size in inches
- `min_wind_speed` (integer) - Minimum wind speed in mph
- `radar_indicated_only` (boolean) - Only radar-detected events

**Example Request:**
```bash
curl "https://api.hailyai.com/api/live-radar-alerts?states=TX,OK&min_hail_size=1.0&active_only=true"
```

**Response Format:**
```json
{
  "alerts": [
    {
      "id": "live_alert_12345",
      "event": "Severe Thunderstorm Warning",
      "maxHailSize": 1.75,
      "maxWindGust": 70,
      "area_desc": "Dallas County, TX; Collin County, TX",
      "affected_states": ["TX"],
      "certainty": "Observed",
      "urgency": "Immediate",
      "radar_indicated_event": true,
      "alert_message_template": "⚠️ 1.75\" hail and 70 mph winds detected by radar near Dallas and Plano!",
      "effective_time": "2025-06-12T18:45:00Z",
      "expires_time": "2025-06-12T19:45:00Z",
      "status": "Active",
      "geometry": { /* GeoJSON polygon */ }
    }
  ],
  "summary": {
    "total_alerts": 15,
    "active_alerts": 12,
    "radar_detected_events": 8,
    "max_hail_size": 2.0,
    "max_wind_speed": 80
  }
}
```

#### Radar Alert Summary
```http
GET https://api.hailyai.com/api/radar-alerts/summary
```

Provides aggregate statistics for current radar-detected events.

### Hurricane Track Data

#### Search Hurricane Tracks
```http
GET https://api.hailyai.com/api/hurricane-tracks
```

**Query Parameters:**
- `storm_id` (string) - NOAA storm identifier (e.g., "AL142020")
- `year` (integer) - Hurricane season year
- `name` (string) - Storm name (e.g., "Ian", "Katrina")
- `landfall_only` (boolean) - Only return storms that made landfall
- `lat` (float) - Latitude for geographic search
- `lon` (float) - Longitude for geographic search
- `radius` (float) - Search radius in miles
- `min_category` (string) - Minimum category ("TS", "CAT1", "CAT2", etc.)
- `start_date` (ISO date) - Filter tracks after this date
- `end_date` (ISO date) - Filter tracks before this date
- `limit` (integer) - Number of results
- `offset` (integer) - Pagination offset

**Example Request:**
```bash
curl "https://api.hailyai.com/api/hurricane-tracks?year=2022&name=Ian&landfall_only=true"
```

**Response Format:**
```json
{
  "tracks": [
    {
      "storm_id": "AL092022",
      "name": "Ian",
      "year": 2022,
      "track_points": [
        {
          "timestamp": "2022-09-28T12:00:00Z",
          "lat": 26.5,
          "lon": -82.0,
          "category": "CAT4",
          "wind_mph": 150,
          "pressure_mb": 940,
          "landfall_location": "Fort Myers, FL"
        }
      ],
      "landfall_points": [
        {
          "location": "Fort Myers, FL",
          "timestamp": "2022-09-28T19:05:00Z",
          "category": "CAT4",
          "wind_mph": 150
        }
      ],
      "max_intensity": {
        "category": "CAT5",
        "wind_mph": 185,
        "pressure_mb": 918
      }
    }
  ],
  "total_count": 1
}
```

#### Get Hurricane Track Details
```http
GET https://api.hailyai.com/api/hurricane-tracks/{storm_id}
```

Returns complete track data for a specific hurricane including all track points and landfall information.

## Webhook Integration

Configure real-time notifications for external systems when specific weather conditions are met.

### Webhook Management

#### Create Webhook Rule
```http
POST https://api.hailyai.com/api/webhook-rules
```

**Request Body:**
```json
{
  "webhook_url": "https://your-system.com/weather-webhook",
  "event_type": "hail",
  "threshold_value": 1.0,
  "location_filter": "TX,OK,AR",
  "user_id": "client_system_123"
}
```

**Event Types:**
- `hail` - Hail size threshold (inches)
- `wind` - Wind speed threshold (mph)
- `damage_probability` - AI-assessed damage likelihood (0.0-1.0)

#### List Webhook Rules
```http
GET https://api.hailyai.com/api/webhook-rules
```

#### Test Webhook
```http
POST https://api.hailyai.com/api/webhook-test
```

#### Delete Webhook Rule
```http
DELETE https://api.hailyai.com/api/webhook-rules/{rule_id}
```

### Webhook Payload Format

When conditions are met, HailyDB sends HTTP POST requests to your webhook URL:

```json
{
  "timestamp": "2025-06-12T18:30:00Z",
  "webhook_rule_id": 123,
  "alert_id": "urn:oid:2.49.0.1.840.0.xxx",
  "event_type": "hail",
  "threshold": 1.0,
  "actual_value": 1.75,
  "trigger_source": "Radar Indicated",
  "location": {
    "area_description": "Dallas County, TX",
    "fips_codes": ["48113"],
    "geometry_bounds": {
      "min_lat": 32.6,
      "max_lat": 33.1,
      "min_lon": -97.5,
      "max_lon": -96.8
    },
    "extracted_cities": ["Dallas", "Irving", "Garland"]
  },
  "alert": {
    "id": "urn:oid:2.49.0.1.840.0.xxx",
    "event": "Severe Thunderstorm Warning",
    "severity": "Severe",
    "area_desc": "Dallas County, TX",
    "effective": "2025-06-12T18:30:00Z",
    "expires": "2025-06-12T19:30:00Z",
    "ai_summary": "Radar-detected severe thunderstorm with golf ball-sized hail affecting Dallas metropolitan area"
  }
}
```

## Data Filtering and Search

### Geographic Filtering

**State-Level:**
```bash
curl "https://api.hailyai.com/api/alerts/search?state=TX"
```

**County-Level:**
```bash
curl "https://api.hailyai.com/api/alerts/search?state=TX&county=Dallas"
```

**FIPS Code:**
```bash
curl "https://api.hailyai.com/api/alerts/search?fips=48113"
```

**Coordinate-Based:**
```bash
curl "https://api.hailyai.com/api/spc/reports?lat=32.7767&lon=-96.7970&radius=25"
```

### Temporal Filtering

**Date Range:**
```bash
curl "https://api.hailyai.com/api/alerts/search?start_date=2025-06-01&end_date=2025-06-12"
```

**Active Alerts Only:**
```bash
curl "https://api.hailyai.com/api/alerts/search?active_only=true"
```

### Event-Specific Filtering

**Radar-Indicated Events:**
```bash
curl "https://api.hailyai.com/api/alerts/search?radar_indicated=true"
```

**SPC-Verified Events:**
```bash
curl "https://api.hailyai.com/api/alerts/search?spc_verified=true"
```

**Severity Levels:**
```bash
curl "https://api.hailyai.com/api/alerts/search?severity=Extreme"
```

## Data Quality and Verification

### SPC Cross-Reference

HailyDB automatically cross-references NWS alerts with official Storm Prediction Center reports:

- **Verification Status:** `spc_verified` field indicates official confirmation
- **Report Count:** `spc_report_count` shows number of matching SPC reports
- **Confidence Score:** `spc_confidence_score` (0.0-1.0) indicates match quality
- **Match Method:** `spc_match_method` shows verification methodology

### AI Enhancement and Auto-Enrichment

**Autonomous Processing Pipeline:**
1. **Real-time Ingestion:** SPC reports imported every 30 minutes automatically
2. **Auto-Enrichment:** Location intelligence added immediately on import using Google Places API
3. **Enhanced Context:** AI-powered summaries generated every 10 minutes for new reports
4. **Radar Correlation:** Cross-referenced with NWS radar-detected events for verification

**Enhanced Context v2.0 Features:**
- **Multi-source Intelligence:** Correlates SPC reports, NWS alerts, and radar data
- **Location Precision:** Uses smallest nearby place names instead of coordinates
- **Damage Classifications:** Official NWS hail and wind damage categories
- **Production-Ready:** Transaction isolation and error handling for weeks-unattended operation

**AI Enhancement Components:**
- **Location Intelligence:** Nearby places and geographic context from Google Places API
- **Impact Assessment:** NWS-official damage potential classifications
- **Event Summary:** Human-readable meteorological descriptions optimized for end users
- **Radar Context:** Correlation with radar-detected phenomena for verification

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
  "error": {
    "code": "INVALID_PARAMETER",
    "message": "Invalid state code provided",
    "details": {
      "parameter": "state",
      "value": "ZZ",
      "valid_values": ["AL", "AK", "AZ", "..."]
    }
  }
}
```

## Pagination

Large result sets are paginated using offset-based pagination:

```json
{
  "pagination": {
    "limit": 25,
    "offset": 0,
    "total_count": 247,
    "has_next": true,
    "has_prev": false
  }
}
```

**Next Page:**
```bash
curl "https://api.hailyai.com/api/alerts/search?limit=25&offset=25"
```

## Client Libraries and SDKs

### HTTP Client Examples

**Python:**
```python
import requests

response = requests.get(
    "https://api.hailyai.com/api/alerts/search",
    params={
        "state": "TX",
        "radar_indicated": True,
        "limit": 10
    },
    headers={"Authorization": "Bearer YOUR_API_KEY"}
)
alerts = response.json()
```

**JavaScript:**
```javascript
const response = await fetch(
  "https://api.hailyai.com/api/alerts/search?state=TX&radar_indicated=true&limit=10",
  {
    headers: {
      "Authorization": "Bearer YOUR_API_KEY"
    }
  }
);
const data = await response.json();
```

**cURL:**
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://api.hailyai.com/api/alerts/search?state=TX&radar_indicated=true&limit=10"
```

## Use Cases and Applications

### Insurance Industry
- **Claims Automation:** Correlate claims with verified weather events
- **Risk Assessment:** Real-time hail and wind damage probability
- **Geographic Targeting:** FIPS-level event identification
- **Historical Analysis:** Hurricane landfall and track data

### Emergency Management
- **Real-Time Monitoring:** Live radar alerts with webhook notifications
- **Resource Deployment:** Geographic event tracking and impact zones
- **Public Safety:** AI-enhanced event summaries for communication
- **Verification:** SPC cross-referenced official storm reports

### Restoration Contractors
- **Lead Generation:** Real-time alerts for damage-causing events
- **Territory Management:** State and county-level event filtering
- **Market Intelligence:** Historical storm patterns and frequency
- **Competition Analysis:** Event timing and geographic distribution

### Research and Analytics
- **Weather Pattern Analysis:** Historical storm data and trends
- **Climate Research:** Long-term hurricane and severe weather patterns
- **Model Validation:** Radar vs. ground truth verification data
- **Geographic Studies:** County-level weather event distributions

## Rate Limits and Usage Guidelines

### Standard Limits
- **Search Endpoints:** 100 requests/minute
- **Detail Endpoints:** 200 requests/minute
- **Webhook Management:** 50 requests/minute
- **Live Radar API:** 60 requests/minute

### Best Practices
1. **Implement Caching:** Cache responses for appropriate durations
2. **Use Filtering:** Apply geographic and temporal filters to reduce data volume
3. **Pagination:** Use pagination for large result sets
4. **Webhooks:** Use webhooks instead of polling for real-time updates
5. **Error Handling:** Implement exponential backoff for retry logic

## Production Deployment and Architecture

### Autonomous Operation Design
HailyDB is designed for **weeks-unattended operation** with comprehensive error handling:

**Background Services:**
- **Autonomous Scheduler:** Self-monitoring background processes without APScheduler dependency
- **Auto-Recovery:** Failed operations automatically retry with exponential backoff
- **Transaction Isolation:** Database operations use proper isolation to prevent corruption
- **Overlap Prevention:** Threading locks prevent duplicate processing during high-load periods

**Monitoring and Health Checks:**
```http
GET /api/autonomous-scheduler/status
```

Returns real-time status of all background operations with countdown timers.

### Required Environment Variables
```bash
# Core Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# AI Enhancement (Required)
OPENAI_API_KEY=sk-xxx  # For Enhanced Context generation

# Location Intelligence (Required for auto-enrichment)
GOOGLE_PLACES_API_KEY=AIzaSyxxx  # For nearby place identification

# Security
SESSION_SECRET=your-random-secret-key

# Performance Tuning (Optional)
DB_WRITE_BATCH_SIZE=500
ENRICH_BATCH_SIZE=25
SPC_MATCH_BATCH_SIZE=200
```

### Deployment Checklist
1. **Database Setup:** PostgreSQL 12+ with JSONB support
2. **API Keys:** Obtain OpenAI and Google Places API credentials
3. **Environment:** Configure all required environment variables
4. **Health Check:** Verify `/health` endpoint returns 200 OK
5. **Auto-Scheduler:** Start autonomous scheduler via `/api/autonomous-scheduler/start`
6. **Data Verification:** Monitor `/api/status` for data freshness indicators

### Troubleshooting Common Issues

**Enhanced Context Generation Failures:**
- **Symptom:** `NoneType comparison error` in logs
- **Cause:** Magnitude fields contain null values
- **Solution:** Fixed in v2.0 with null-safe magnitude extraction

**Auto-Enrichment Not Working:**
- **Symptom:** New SPC reports missing enrichment data
- **Cause:** Auto-enrichment triggered only after successful database commits
- **Verification:** Check logs for "Auto-enriched SPC report" messages

**Webhook Delivery Failures:**
- **Symptom:** External systems not receiving notifications
- **Solution:** Verify webhook URLs are publicly accessible and return 200 status codes
- **Debug:** Use `/api/webhook-test` endpoint to validate webhook configuration

### Performance Optimization

**Database Indexing:**
- Geographic queries: Ensure PostGIS indexes on geometry columns
- Temporal filtering: Index on `effective`, `expires`, `report_date` columns
- Cross-reference: Composite indexes on state/county combinations

**Caching Strategy:**
- **Live Radar API:** 5-minute TTL cache for real-time endpoints
- **SPC Reports:** 1-hour cache for historical data queries
- **Enhanced Context:** Cache until regeneration (permanent until updated)

## Support and Documentation

### Technical Support
- **Documentation:** Complete API reference and deployment guides
- **Status Page:** Real-time system status and uptime monitoring
- **Health Endpoints:** Built-in diagnostic tools for troubleshooting

### Service Level Agreement
- **Uptime:** 99.9% availability guarantee with autonomous recovery
- **Response Time:** < 200ms average for API endpoints
- **Data Freshness:** NWS alerts updated every 5 minutes, SPC reports every 30 minutes
- **Auto-Recovery:** Failed operations retry automatically without manual intervention

## System Status and Monitoring

### Health Endpoints
```http
GET https://api.hailyai.com/health
```

Returns system health and operational status.

### Data Freshness
```http
GET https://api.hailyai.com/api/status
```

Returns last update timestamps for all data sources.

---

**Version:** v2.0 Production with Enhanced Context  
**Last Updated:** June 16, 2025  
**Auto-Enrichment:** Fully autonomous with weeks-unattended operation  
**Enhanced Context:** v2.0 with location intelligence and damage classifications  
**Status:** https://api.hailyai.com/health

*HailyDB is a production-grade weather intelligence platform designed for enterprise applications requiring reliable, real-time weather data with comprehensive verification and AI enhancement.*
