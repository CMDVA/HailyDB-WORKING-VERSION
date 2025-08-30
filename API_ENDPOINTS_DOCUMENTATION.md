# HailyDB Complete API Documentation
## Comprehensive Endpoint Reference

### Base URL
**Production**: `https://api.hailyai.com`  
**Development**: `http://localhost:5000`

---

## 📊 Core Alert Endpoints

### GET `/api/alerts`
**Primary alerts endpoint with comprehensive filtering**

**Parameters:**
- `limit` (integer): Results per page (default: 50, max: 5000)
- `offset` (integer): Pagination offset (default: 0)
- `status` (string): Filter by status (`active`, `expired`, `all`)
- `event` (string): Filter by event type
- `state` (string): Two-letter state code (e.g., "TX", "FL")
- `county` (string): County name
- `start_date` (date): Start date filter (YYYY-MM-DD)
- `end_date` (date): End date filter (YYYY-MM-DD)
- `lat` (float): Latitude for radius filtering
- `lon` (float): Longitude for radius filtering  
- `radius_mi` (float): Radius in miles (requires lat/lon)

**Response Format:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature", 
      "properties": {
        "id": "urn:oid:2.49.0.1.840.0...",
        "data_source": "nws",
        "source_type": "alert",
        "event": "Severe Thunderstorm Warning",
        "severity": "Minor",
        "urgency": "Immediate",
        "status": "expired",
        "expires": "2025-08-30T20:00:00Z",
        "effective": "2025-08-30T19:00:00Z",
        "radar_indicated": {
          "hail_inches": 1.0,
          "wind_mph": 60,
          "tornado": false
        },
        "areas": [
          {
            "state_code": "TX",
            "county_name": "Harris County"
          }
        ],
        "city_names": ["Houston", "Pasadena", "Sugar Land"],
        "enhanced_context": {
          "damage_assessment": "Significant hail damage likely...",
          "version": "4.1",
          "generated_at": "2025-08-30T19:05:00Z"
        }
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-95.8, 29.5], [-95.2, 29.5], ...]]
      }
    }
  ],
  "metadata": {
    "total_count": 9547,
    "returned_count": 50,
    "has_more": true,
    "pagination": {
      "limit": 50,
      "offset": 0,
      "next_offset": 50
    }
  }
}
```

**Example Calls:**
```bash
# Get recent expired alerts with radar detection
curl "https://api.hailyai.com/api/alerts?status=expired&limit=100"

# Get alerts in Texas with hail or wind damage
curl "https://api.hailyai.com/api/alerts?state=TX&start_date=2024-01-01"

# Get alerts within 25 miles of Houston
curl "https://api.hailyai.com/api/alerts?lat=29.7604&lon=-95.3698&radius_mi=25"
```

---

## 🎯 Pre-Filtered Radar Endpoints

### GET `/api/alerts/radar_detected`
**All radar-detected severe weather events**  
Returns alerts with ANY radar-indicated hail OR 50+ mph winds

**Parameters:** Same as `/api/alerts`

**Specialization:** Pre-filtered for insurance/restoration industry use cases

### GET `/api/alerts/radar_detected/hail`  
**Radar-detected hail events only**  
Returns alerts with ANY size hail detected by radar

**Radar Criteria:**
- Any hail size from pea (0.25") to baseball (2.75")+
- Includes hail diameter and damage assessment

### GET `/api/alerts/radar_detected/wind`
**Radar-detected wind events only**  
Returns alerts with 50+ mph winds detected by radar

**Radar Criteria:**
- Wind speeds 50+ mph (damaging threshold)
- Includes peak wind speed measurements

**Example Calls:**
```bash
# Get all hail damage events in Florida for 2024
curl "https://api.hailyai.com/api/alerts/radar_detected/hail?state=FL&start_date=2024-01-01&end_date=2024-12-31"

# Get high wind events near Dallas  
curl "https://api.hailyai.com/api/alerts/radar_detected/wind?lat=32.7767&lon=-96.7970&radius_mi=50"

# Get all radar-detected damage events (comprehensive)
curl "https://api.hailyai.com/api/alerts/radar_detected?status=expired&limit=1000"
```

---

## 🔍 Individual Alert Access

### GET `/api/alerts/{alert_id}`
**Complete individual alert details with full enrichments**

**Path Parameter:**
- `alert_id`: Full NWS alert identifier (URL-encoded)

**Response:** Complete alert object with all available enrichments

**Example:**
```bash
curl "https://api.hailyai.com/api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1"
```

### GET `/api/alerts/by-county/{state}/{county}`
**Alerts filtered by specific state and county**

**Path Parameters:**
- `state`: Two-letter state code
- `county`: County name (URL-encoded)

**Example:**
```bash
curl "https://api.hailyai.com/api/alerts/by-county/TX/Harris"
```

---

## 📈 SPC Storm Reports

### GET `/api/reports/spc`
**Historical Storm Prediction Center reports with 100% coverage**

**Parameters:**
- `limit` (integer): Results per page (default: 50, max: 2000)
- `offset` (integer): Pagination offset
- `date` (date): Specific date (YYYY-MM-DD)
- `start_date` (date): Start date range
- `end_date` (date): End date range
- `state` (string): State filter
- `type` (string): Report type (`tornado`, `hail`, `wind`)
- `lat`, `lon`, `radius_mi`: Geographic radius filtering

**Response Format:**
```json
{
  "reports": [
    {
      "id": "spc-20250830-1430-001",
      "data_source": "spc", 
      "source_type": "report",
      "date_time": "2025-08-30T19:30:00Z",
      "type": "hail",
      "size_inches": 1.75,
      "location": "2 E HOUSTON",
      "county": "HARRIS",
      "state": "TX",
      "lat": 29.7604,
      "lon": -95.3698,
      "comments": "Quarter to golf ball size hail reported",
      "enhanced_context": {
        "damage_category": "moderate",
        "insurance_significance": "likely claims activity",
        "nearby_places": ["Houston", "Pasadena"]
      }
    }
  ],
  "metadata": {
    "total_count": 2631,
    "returned_count": 50,
    "filters_applied": ["type=hail", "state=TX"]
  }
}
```

**Example Calls:**
```bash
# Get recent hail reports
curl "https://api.hailyai.com/api/reports/spc?type=hail&limit=100"

# Get tornado reports for specific date
curl "https://api.hailyai.com/api/reports/spc?type=tornado&date=2025-08-30"

# Get wind reports in Texas
curl "https://api.hailyai.com/api/reports/spc?type=wind&state=TX"
```

---

## 🌀 Hurricane Track Data

### GET `/api/hurricanes`
**Historical hurricane track and landfall data from NOAA HURDAT2**

**Parameters:**
- `year` (integer): Hurricane season year
- `name` (string): Hurricane name
- `category` (integer): Saffir-Simpson category (1-5)
- `landfall_only` (boolean): Only storms that made landfall

**Response Format:**
```json
{
  "storms": [
    {
      "id": "AL012024",
      "name": "Alberto", 
      "year": 2024,
      "max_category": 1,
      "landfall_locations": [
        {
          "date": "2024-06-20T12:00:00Z",
          "location": "Tamaulipas, Mexico",
          "category": 1,
          "max_winds": 80
        }
      ],
      "track_points": [
        {
          "timestamp": "2024-06-19T00:00:00Z",
          "lat": 23.4,
          "lon": -97.8,
          "max_winds": 65,
          "category": 0
        }
      ]
    }
  ]
}
```

---

## ⚡ Real-Time Live Data

### GET `/api/live/radar_alerts`
**Real-time radar-detected alerts (active monitoring)**

**Purpose:** Current severe weather with radar-detected parameters  
**Update Frequency:** Every 5 minutes  
**Use Case:** Real-time monitoring dashboards

**Response:** Same format as `/api/alerts/radar_detected` but filtered to active events

---

## 🔧 System & Admin Endpoints

### GET `/api/health`
**System health check and real-time statistics**

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-08-30T19:15:00Z",
  "database_status": "connected",
  "services": {
    "live_radar_service": "active",
    "spc_ingestion": "active", 
    "scheduler": "running"
  },
  "statistics": {
    "total_alerts": 9547,
    "radar_detected_alerts": 2120,
    "spc_reports": 2631,
    "hurricane_tracks": 445,
    "last_ingestion": "2025-08-30T19:10:00Z"
  },
  "performance": {
    "average_response_time_ms": 285,
    "database_query_time_ms": 45
  }
}
```

### GET `/api/documentation`
**Complete API documentation (this endpoint serves machine-readable docs)**

**Purpose:** AI agents and automated integrations  
**Format:** Structured JSON documentation  
**Coverage:** 100% of public API endpoints

### POST `/api/admin/trigger-nws-poll` 🔒
**Manually trigger NWS data polling (admin only)**

**Authentication:** Admin credentials required  
**Purpose:** Force immediate data refresh

### GET `/api/test/radar-summary`
**Development endpoint for radar parsing validation**

**Purpose:** Testing and validation  
**Response:** Summary of radar parsing statistics

---

## 📊 Data Source Overview

### External APIs Used

#### National Weather Service (NWS) 
- **URL:** `https://api.weather.gov/alerts/active`
- **Purpose:** Real-time weather alerts
- **Update Frequency:** Every 5 minutes
- **Rate Limits:** ~1000 requests/hour
- **Authentication:** None required
- **Data Format:** GeoJSON FeatureCollection

#### Storm Prediction Center (SPC)
- **URL:** `https://www.spc.noaa.gov/climo/reports/`  
- **Purpose:** Historical storm reports
- **Update Frequency:** Daily (new date files)
- **Rate Limits:** Reasonable use policy
- **Authentication:** None required  
- **Data Format:** CSV files by date

#### OpenStreetMap Nominatim
- **URL:** `https://nominatim.openstreetmap.org/search`
- **Purpose:** Geographic location enrichment
- **Rate Limits:** 1 request/second
- **Authentication:** None required
- **Usage:** City name standardization

#### GeoNames API  
- **URL:** `http://api.geonames.org`
- **Purpose:** Enhanced geographic data  
- **Rate Limits:** 1000-30000/day (based on account)
- **Authentication:** Username required
- **Usage:** Location enrichment services

#### OpenAI API
- **URL:** `https://api.openai.com/v1/`
- **Purpose:** AI enhancement and damage assessment
- **Models:** GPT-4, GPT-4-turbo
- **Authentication:** API key required
- **Usage:** Enhanced context generation

---

## 🚀 Performance Specifications

### Response Times
- **Simple queries:** <200ms average
- **Complex geo queries:** <500ms average  
- **Large result sets:** <1000ms for 1000+ records
- **Individual alerts:** <100ms average

### Rate Limits
- **General API:** 100 requests/minute
- **Burst capacity:** 10 requests/second
- **Large exports:** 5000 records maximum per request

### Caching
- **Alert summaries:** 5-minute cache
- **SPC reports:** 1-hour cache  
- **System health:** 30-second cache
- **Individual alerts:** 10-minute cache

---

## 📝 Response Standards

### Success Responses
- **200 OK:** Standard successful response
- **Content-Type:** `application/json`
- **Encoding:** UTF-8

### Error Responses
```json
{
  "error": true,
  "message": "Alert not found",
  "status_code": 404,
  "timestamp": "2025-08-30T19:15:00Z"
}
```

**Error Codes:**
- **400:** Bad Request (invalid parameters)
- **404:** Resource Not Found
- **429:** Rate Limit Exceeded  
- **500:** Internal Server Error
- **503:** Service Temporarily Unavailable

### Data Quality Guarantees
- **100% NWS Compliance:** All alert data matches official NWS API format
- **Complete Radar Detection:** All alerts with radar parameters preserved
- **Geographic Accuracy:** Validated coordinate data with proper projections
- **Temporal Consistency:** All timestamps in ISO 8601 UTC format

---

## 🔍 Query Examples

### Insurance Use Cases
```bash
# Get all hail damage in hurricane-prone areas (2024 season)
curl "https://api.hailyai.com/api/alerts/radar_detected/hail?start_date=2024-06-01&end_date=2024-11-30&state=FL&limit=500"

# Find wind damage events near specific address
curl "https://api.hailyai.com/api/alerts/radar_detected/wind?lat=29.7604&lon=-95.3698&radius_mi=10&status=expired"

# Get comprehensive damage report for county
curl "https://api.hailyai.com/api/alerts/radar_detected?state=TX&county=Harris&start_date=2024-01-01"
```

### Research Use Cases  
```bash
# Historical tornado activity analysis
curl "https://api.hailyai.com/api/reports/spc?type=tornado&start_date=2020-01-01&end_date=2024-12-31&limit=2000"

# Hurricane landfall tracking
curl "https://api.hailyai.com/api/hurricanes?landfall_only=true&category=3"

# Severe weather frequency by region
curl "https://api.hailyai.com/api/alerts/radar_detected?lat=35.2271&lon=-101.8313&radius_mi=100&start_date=2023-01-01"
```

### Real-Time Monitoring
```bash
# Active severe weather with radar detection
curl "https://api.hailyai.com/api/live/radar_alerts"

# System health check
curl "https://api.hailyai.com/api/health"

# Current ingestion status
curl "https://api.hailyai.com/api/documentation"
```

---

## 📞 Support & Integration

### Integration Assistance
- **Technical Documentation:** This endpoint documentation
- **Sample Code:** Available in multiple languages
- **Rate Limit Increases:** Contact for enterprise usage
- **Custom Endpoints:** Available for specific use cases

### Data Export Options
- **JSON API:** Standard REST endpoints  
- **Bulk Export:** Large dataset downloads
- **Real-time Streaming:** WebSocket connections (enterprise)
- **Database Direct:** PostgreSQL access (enterprise)

---

*Last Updated: August 30, 2025*  
*API Version: 2.1*  
*Documentation Version: 1.0*