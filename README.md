# HailyDB v2.1.3 - Historical Weather Damage Intelligence Platform

A production-ready Flask-based platform that serves as a comprehensive repository for National Weather Service alerts with radar-detected hail and wind parameters. Designed specifically for insurance claims processing, damage assessment, and restoration industry clients who need to know **"where likely damage WAS"**.

## Overview

HailyDB is a **historical weather damage intelligence platform** that mirrors NWS alert data with AI-powered enrichments. Unlike active weather platforms, HailyDB's core value proposition is providing comprehensive historical data on expired NWS alerts containing radar-detected severe weather events for forensic weather analysis and damage assessment workflows.

**Core Business Value**: Historical repository of 7,500+ expired NWS alerts with 2,115+ radar-detected damage events (hail and 50+ mph winds).

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database
- OpenAI API key (optional, for AI enrichment)

### Installation & Setup

1. **Environment Setup**:
   ```bash
   export DATABASE_URL="postgresql://username:password@host:port/database"
   export OPENAI_API_KEY="your-openai-api-key"  # Optional
   ```

2. **Start the Application**:
   ```bash
   gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
   ```

3. **Verify Installation**:
   ```bash
   curl http://localhost:5000/api/health
   ```

## 📊 Core Business Data

### Historical Repository Statistics
- **7,913 Total NWS Alerts** in database
- **7,503 Expired Alerts** (historical data)  
- **2,115 Radar-Detected Damage Events**
  - **1,806 Wind Events** (50+ mph radar-detected)
  - **1,635 Hail Events** (any size radar-detected)
- **Complete Geographic Coverage** (all US states/territories)
- **Date Range**: Historical data spanning multiple years

## 🎯 Pre-Filtered API Endpoints (New in v2.1.3)

### Radar-Detected Damage Events

#### All Radar-Detected Events
```http
GET /api/alerts/radar_detected
```
Returns alerts with **50+ mph winds OR any size hail** detected by radar.
- **Total Events**: 2,115 damage events
- **Use Case**: Complete radar-detected damage inventory

#### Wind Damage Events (50+ mph)
```http
GET /api/alerts/radar_detected/wind
```
Returns alerts with **50+ mph winds** detected by radar.
- **Total Events**: 1,806 wind damage events
- **Use Case**: Wind damage assessment and claims

#### Hail Damage Events (Any Size)
```http
GET /api/alerts/radar_detected/hail
```
Returns alerts with **any size hail** detected by radar.
- **Total Events**: 1,635 hail damage events  
- **Use Case**: Hail damage assessment and claims

### Query Parameters (All Endpoints)

| Parameter | Description | Example |
|-----------|-------------|---------|
| `status` | `active`, `expired`, or `all` | `?status=expired` |
| `state` | State code filter | `?state=TX` |
| `county` | County name filter | `?county=Harris` |
| `start_date` | Date range start | `?start_date=2024-01-01` |
| `end_date` | Date range end | `?end_date=2024-12-31` |
| `limit` | Results per page (max 5,000) | `?limit=1000` |
| `page` | Page number for pagination | `?page=2` |

### Example API Calls

```bash
# Get all expired radar-detected wind events in Texas
curl "http://localhost:5000/api/alerts/radar_detected/wind?status=expired&state=TX&limit=100"

# Get hail events in Harris County for 2024
curl "http://localhost:5000/api/alerts/radar_detected/hail?county=Harris&start_date=2024-01-01&end_date=2024-12-31"

# Get all radar-detected damage events (wind + hail)
curl "http://localhost:5000/api/alerts/radar_detected?status=expired&limit=2000"
```

## 📁 Complete API Reference

### Core Repository Endpoints

#### Historical Alert Repository
```http
GET /api/alerts/expired
```
**Primary business endpoint** - Returns expired NWS alerts with optional radar filtering.
- **Default**: All 7,503 expired alerts
- **With `?has_radar=true`**: Only radar-detected events
- **High Volume**: Supports up to 10,000 results per request

#### Individual Alert Details
```http
GET /api/alerts/{alert_id}
```
Returns complete alert details including enrichments and radar parameters.

#### Active Alerts
```http
GET /api/alerts/active
```
Returns currently active NWS alerts (live monitoring).

#### Geographic Filtering
```http
GET /api/alerts/by-state/{state}
GET /api/alerts/by-county/{state}/{county}
```

#### System Health
```http
GET /api/health
```
Returns system status and database statistics.

## 🗂️ Response Format

All endpoints return **GeoJSON FeatureCollection** format following NWS API OpenAPI specification:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "id": "urn:oid:2.49.0.1.840.0...",
      "type": "Feature",
      "properties": {
        "event": "Severe Thunderstorm Warning",
        "headline": "The National Weather Service in Houston/Galveston has issued a...",
        "description": "At 715 PM CDT, Doppler radar indicated a severe thunderstorm...",
        "severity": "Severe",
        "urgency": "Expected", 
        "certainty": "Observed",
        "effective": "2024-06-15T19:15:00Z",
        "expires": "2024-06-15T20:00:00Z",
        "status": "Actual",
        "areaDesc": "Harris; Fort Bend; Brazoria",
        "radar_indicated": {
          "hail_inches": 1.0,
          "wind_mph": 60
        },
        "affected_states": ["TX"],
        "county_names": [
          {"state": "TX", "county": "Harris"},
          {"state": "TX", "county": "Fort Bend"}
        ],
        "enhanced_summary": "AI-generated damage assessment and location context..."
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[-95.8, 29.7], [-95.3, 29.7], ...]]
      }
    }
  ],
  "title": "Radar-Detected Weather Damage Events - 2,115 alerts with 50+ mph winds or hail",
  "updated": "2025-08-19T23:41:12Z",
  "metadata": {
    "total_results": 2115,
    "page": 1,
    "per_page": 1000,
    "criteria": "50+ mph winds OR any hail size detected by radar",
    "data_source": "National Weather Service alerts with radar parameters"
  }
}
```

## 🏗️ System Architecture

### Core Components

#### Data Ingestion Services
- **NWS Alert Ingestion**: Real-time polling of NWS API every 30 seconds
- **SPC Report Ingestion**: Daily import of Storm Prediction Center reports
- **Live Radar Service**: Processes radar-detected parameters from alert descriptions
- **Hurricane Track Data**: NOAA HURDAT2 historical hurricane integration

#### AI Enhancement Services  
- **Enhanced Context Service**: OpenAI GPT-4o powered damage assessments
- **SPC Matching**: Cross-references NWS alerts with storm reports
- **Match Summarizer**: AI verification summaries for data correlation

#### Background Processing
- **Autonomous Scheduler**: Orchestrates all data processing operations
- **SPC Verification**: Ensures data integrity against live SPC sources
- **State Enrichment**: Geographic data enhancement with error handling

### Database Schema

#### Alert Model (Primary)
```sql
- id: UUID (NWS alert identifier)
- event: VARCHAR (alert type)
- headline: TEXT (alert headline)
- description: TEXT (full alert description)
- severity/urgency/certainty: VARCHAR (NWS standard levels)
- effective/expires: TIMESTAMP (alert timeframe)
- geometry: JSONB (GeoJSON polygon)
- radar_indicated: JSONB (extracted hail/wind parameters)
- affected_states: JSONB (state codes array)
- county_names: JSONB (state/county objects)
- enhanced_summary: TEXT (AI-generated context)
```

#### SPC Report Model
```sql
- location: VARCHAR (human-readable location)
- lat/lon: FLOAT (coordinates)
- wind_speed: INTEGER (mph)
- hail_size: FLOAT (inches)
- event_time: TIMESTAMP (UTC occurrence time)
```

## 🎯 Use Cases & Industry Applications

### Insurance Claims Processing
- **Historical Damage Lookup**: Query radar-detected events by location and date range
- **Claims Validation**: Verify reported damage against NWS radar parameters
- **Risk Assessment**: Analyze historical damage patterns for underwriting

### Restoration Contractors
- **Business Development**: Discover past damage events for marketing
- **Emergency Response**: Monitor active alerts for rapid deployment
- **Historical Analysis**: Understand regional damage patterns

### Forensic Weather Analysis
- **Legal Documentation**: NWS-verified weather data for litigation
- **Engineering Studies**: Historical severe weather for infrastructure planning
- **Research Applications**: Comprehensive database for meteorological research

## 🔧 Configuration

### Environment Variables
```bash
DATABASE_URL="postgresql://..."          # Required: PostgreSQL connection
OPENAI_API_KEY="sk-..."                 # Optional: AI enrichment features
FLASK_SECRET_KEY="your-secret"          # Required: Session security
WEBHOOK_URL="https://..."               # Optional: Real-time notifications
```

### Production Deployment
- **WSGI Server**: Gunicorn with auto-reload
- **Database**: PostgreSQL with JSONB support
- **Background Services**: Autonomous scheduler with error recovery
- **Monitoring**: Health endpoints and comprehensive logging

## 📈 Performance & Scaling

### Current Capacity
- **Database Size**: 7,913 alerts with full geometry and enrichments
- **API Throughput**: Up to 10,000 results per request
- **Real-time Processing**: 13-15 live alerts processed continuously
- **Zero Failures**: Stable ingestion with comprehensive error handling

### Optimization Features
- **Indexed Queries**: Optimized for geographic and temporal filtering
- **Efficient Pagination**: High-volume result handling
- **Background Processing**: Non-blocking data enrichment
- **Error Recovery**: Automatic retry logic for external APIs

## 🚦 System Status (v2.1.3)

✅ **Production Ready**
- Zero ingestion failures
- Complete NWS API compliance
- Stable background processing
- Full historical repository access

✅ **Core Business Data Available**
- 2,115 radar-detected damage events
- Pre-filtered endpoints operational
- Geographic and temporal filtering working
- GeoJSON format standardized

✅ **Enterprise Features**
- AI-powered damage assessments
- Cross-platform webhook delivery
- Comprehensive error handling
- Production monitoring and logging

## 📞 Support & Documentation

### Development Resources
- **System Architecture**: See `replit.md` for detailed technical overview
- **API Examples**: Interactive testing via provided endpoints
- **Error Handling**: Comprehensive logging for troubleshooting

### Integration Support
For client application integration assistance:
1. Review API response examples above
2. Test endpoints with provided curl commands  
3. Implement GeoJSON parsing in your application
4. Use pre-filtered endpoints for optimal performance

---

**HailyDB v2.1.3** - Production-ready historical weather damage intelligence platform optimized for insurance, restoration, and forensic weather analysis workflows.