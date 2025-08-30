# HailyDB v2.1 - Historical Weather Damage Intelligence Platform

## Overview

HailyDB is a **production-ready historical weather damage intelligence platform** that captures and analyzes expired NWS alerts containing radar-detected severe weather events. Unlike active weather monitoring systems, HailyDB's core value proposition is providing comprehensive historical data on **where likely damage occurred**, making it essential for insurance claims processing, damage assessment, restoration contractors, and forensic weather analysis.

**Core Business Value**: Historical radar-detected severe weather events (expired alerts with hail/wind data) for damage assessment and insurance claims.


## Key Features

### Historical Weather Damage Repository
- Complete archive of expired NWS alerts with radar-detected severe weather
- Focus on damage-causing events: any hail size + 50+ mph winds
- Professional AI-enhanced summaries for insurance industry precision
- Geographic targeting with radius-based filtering using bounding box optimization

### Production API Suite
- **Individual Alert Access**: Complete JSON details with enrichments (`/api/alerts/{alert_id}`)
- **Pre-filtered Endpoints**: Radar-detected hail and wind damage events
- **Data Source Identifiers**: Clear `data_source` and `source_type` fields on 100% of records
- **Bulk Export**: High-volume data access with pagination support (up to 5,000 records)
- **SPC Reports**: 100% historical storm report coverage
- **NWS Compliance**: Official API-standard GeoJSON responses

### AI Enhancement Services
- **OpenAI GPT-4o Integration**: Professional weather intelligence summaries
- **Location Standardization**: County-to-city mapping with confidence scoring
- **Enhanced Context**: Multi-source enrichment for comprehensive analysis
- **Damage Assessment**: Specialized summaries for insurance workflows

## Complete API Reference

### 📊 Core Alert Endpoints (106 Total Routes)

#### Primary Data Access
```bash
GET /api/alerts                         # Main alerts endpoint with full filtering
GET /api/alerts/{alert_id}              # Individual alert details with enrichments  
GET /api/alerts/by-county/{state}/{county}  # County-specific alerts
GET /api/alerts/active                  # Currently active alerts only
```

#### 🎯 Pre-Filtered Radar Detection (Insurance-Ready)
```bash
GET /api/alerts/radar_detected          # Any hail OR 50+ mph winds
GET /api/alerts/radar_detected/hail     # Any hail size detected by radar
GET /api/alerts/radar_detected/wind     # 50+ mph winds detected by radar
```

#### 📈 Historical Storm Reports (SPC Integration)
```bash
GET /api/reports/spc                    # All historical storm reports (2,631+ records)
```

#### 🌀 Hurricane Track Data (NOAA HURDAT2)
```bash  
GET /api/hurricanes                     # Historical hurricane tracks and landfall data
```

#### ⚡ Real-Time Monitoring
```bash
GET /api/live/radar_alerts              # Active radar-detected events
```

#### 🔧 System & Documentation
```bash
GET /api/health                         # System status with real-time statistics
GET /api/documentation                  # Machine-readable API documentation
GET /api/test/radar-summary             # Development radar parsing validation
POST /api/admin/trigger-nws-poll        # Manual data refresh (admin only)
```

### Complete Data Source Integration

#### External APIs Powering HailyDB
- **National Weather Service**: `https://api.weather.gov/alerts/active` (Real-time alerts, 5-min updates)
- **Storm Prediction Center**: `https://www.spc.noaa.gov/climo/reports/` (Historical storm reports, daily)
- **OpenStreetMap Nominatim**: `https://nominatim.openstreetmap.org/search` (Geographic enrichment)
- **GeoNames API**: `http://api.geonames.org` (Enhanced location data, username required)
- **OpenAI API**: `https://api.openai.com/v1/` (GPT-4 AI enhancement, API key required)
- **NOAA HURDAT2**: Hurricane track and landfall historical data

### Example API Calls

```bash
# Insurance Use Cases - Get all hail damage in Texas for 2024
curl "https://api.hailyai.com/api/alerts/radar_detected/hail?state=TX&start_date=2024-01-01&end_date=2024-12-31&limit=500"

# Restoration Contractors - Find recent wind damage near Houston
curl "https://api.hailyai.com/api/alerts/radar_detected/wind?lat=29.7604&lon=-95.3698&radius_mi=25&status=expired"

# Research Analysis - Historical tornado activity (SPC reports)
curl "https://api.hailyai.com/api/reports/spc?type=tornado&start_date=2020-01-01&limit=1000"

# Individual Alert Investigation - Complete details with AI enhancement
curl "https://api.hailyai.com/api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1"

# System Health - Real-time statistics and service status  
curl "https://api.hailyai.com/api/health"

# Hurricane Tracking - Landfall events by category
curl "https://api.hailyai.com/api/hurricanes?landfall_only=true&category=3"
```

#### Advanced Filtering Capabilities
```bash
# Geographic Targeting
?lat=40.7128&lon=-74.0060&radius_mi=25  # Radius-based filtering
?state=TX&county=Harris                 # State/county filtering

# Temporal Filtering  
?start_date=2024-01-01&end_date=2024-12-31  # Date range
?status=expired                             # Alert status

# High-Volume Export
?limit=1000&offset=5000                     # Pagination for large datasets
```

### Current System Statistics (Real-Time)
- **Total Alerts**: 9,547+ (with continuous ingestion)
- **Radar-Detected Events**: 2,120+ (damage-causing threshold)
- **SPC Storm Reports**: 2,631+ (100% historical coverage)
- **Hurricane Tracks**: 445+ (NOAA HURDAT2 integration)
- **Update Frequency**: Every 5 minutes (NWS) / Daily (SPC)
- **API Response Time**: <300ms average

## Data Source Identification

All API responses include clear data source identifiers for easy client application integration:

### Response Format Examples

**SPC Reports Response:**
```json
{
  "items": [
    {
      "id": "spc-20250820-1318-12345",
      "data_source": "spc",
      "source_type": "report",
      "type": "wind",
      "verified": true,
      "wind_mph": 65,
      "city": "Houston",
      "state": "TX"
    }
  ]
}
```

**NWS Alerts Response:**
```json
{
  "features": [
    {
      "properties": {
        "id": "urn:oid:2.49.0.1.840.0.abc123...",
        "data_source": "nws",
        "source_type": "alert",
        "event": "Severe Thunderstorm Warning",
        "areaDesc": "Harris County, TX",
        "hailydb_enrichments": {
          "radar_indicated": {
            "hail_inches": 1.75,
            "wind_mph": 60
          }
        }
      }
    }
  ]
}
```

### Client Integration Benefits
- **Easy Filtering**: `event.data_source === 'nws'` or `'spc'`
- **Source Type Distinction**: Separate verified reports from warning alerts
- **100% Database Coverage**: All existing records have these identifiers
- **Consistent API Responses**: Same field names across all endpoints

## Business Applications

### Insurance Industry
- **Claims Verification**: Historical radar data for damage timeline analysis
- **Risk Assessment**: Geographic damage patterns and frequency analysis
- **Forensic Analysis**: Detailed weather summaries for claims investigation
- **Address-Level Targeting**: City name standardization with confidence scoring

### Restoration Contractors
- **Market Intelligence**: Historical damage locations for business development
- **Resource Planning**: Geographic analysis of severe weather patterns
- **Client Acquisition**: Data-driven targeting for restoration services

### Emergency Management
- **Pattern Analysis**: Historical severe weather impact assessment
- **Preparedness Planning**: Geographic vulnerability identification
- **Response Optimization**: Historical event analysis for resource allocation

## Technical Architecture

### Backend Stack
- **Flask Application**: Production-grade web service with SQLAlchemy ORM
- **PostgreSQL Database**: Relational schema with JSONB support for complex data
- **Background Services**: Autonomous scheduling for continuous data processing
- **RESTful API**: NWS-compliant responses with comprehensive error handling

### Data Sources
- **National Weather Service**: Real-time alert ingestion with radar parameter extraction
- **Storm Prediction Center**: Historical storm report verification and correlation
- **NOAA HURDAT2**: Hurricane track and landfall data integration
- **OpenAI GPT-4o**: Professional weather intelligence enhancement

### Key Components

#### Data Ingestion
- **NWS Alert Service**: Continuous polling with test message filtering
- **SPC Report Service**: Historical data synchronization with 100% coverage
- **Live Radar Processing**: Real-time extraction of damage-relevant parameters
- **Hurricane Integration**: Historical track data with landfall analysis

#### Enhancement Services
- **AI Enrichment**: Professional weather summaries with business context
- **Location Intelligence**: City name extraction with confidence scoring
- **Cross-Reference Matching**: SPC report correlation with NWS alerts
- **Damage Assessment**: Specialized analysis for insurance applications

#### API Infrastructure
- **Individual Access**: Complete alert details with all enrichments
- **Bulk Export**: High-volume data access for enterprise clients
- **Geographic Filtering**: Radius-based targeting with geometry optimization
- **Error Handling**: Comprehensive status codes and detailed error messages

## Installation & Deployment

### Local Development
```bash
# Clone and setup
git clone <repository>
cd hailydb

# Install dependencies
pip install -r requirements.txt

# Configure database
export DATABASE_URL="postgresql://..."

# Start application
python main.py
```

### Production Deployment
The system is optimized for Replit deployment with:
- **Gunicorn WSGI server** for production stability
- **PostgreSQL integration** with connection pooling
- **Autonomous background services** for continuous data processing
- **Health monitoring** with comprehensive system diagnostics

## Data Quality & Verification

### Continuous Validation
- **SPC Synchronization**: 100% accuracy verification against official sources
- **Radar Parameter Extraction**: Validated against NWS alert descriptions
- **Geographic Accuracy**: County-to-city mapping with confidence scoring
- **AI Enhancement Quality**: Professional meteorological analysis standards

### Error Handling
- **Comprehensive Logging**: Detailed operation tracking and error reporting
- **Graceful Degradation**: System continues operation during service interruptions
- **Data Integrity Checks**: Automatic validation and correction processes
- **Status Monitoring**: Real-time health checks and performance metrics

## API Reference

### Base URL
```
https://api.hailyai.com
```

### Response Formats
All API responses return JSON format with consistent structure:
- **SPC Reports**: Array of items with pagination metadata
- **NWS Alerts**: GeoJSON FeatureCollection format (NWS-compliant)
- **System Endpoints**: JSON objects with status and data fields

### HTTP Status Codes
- **200 OK**: Successful request with data
- **400 Bad Request**: Invalid parameters or malformed request
- **404 Not Found**: Resource not found or invalid endpoint
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: System error

### Headers
All requests should include:
```
Accept: application/json
User-Agent: YourApp/1.0
```

## Data Models

### SPC Report Model
```json
{
  "id": "spc-20250820-1318-12345",
  "data_source": "spc",
  "source_type": "report",
  "type": "wind|hail|tornado",
  "verified": true,
  "hail_in": 1.75,
  "wind_mph": 65,
  "tornado_scale": "EF2",
  "time_utc": "2025-08-20T13:18:00Z",
  "lat": 29.7604,
  "lon": -95.3698,
  "city": "Houston",
  "county": "Harris",
  "state": "TX",
  "comments": "Trained spotter reported quarter-sized hail..."
}
```

### NWS Alert Model
```json
{
  "type": "Feature",
  "properties": {
    "id": "urn:oid:2.49.0.1.840.0.abc123...",
    "data_source": "nws",
    "source_type": "alert",
    "event": "Severe Thunderstorm Warning",
    "severity": "Severe",
    "areaDesc": "Harris County, TX",
    "effective": "2025-08-20T13:00:00Z",
    "expires": "2025-08-20T14:00:00Z",
    "headline": "Severe Thunderstorm Warning until 2:00 PM CDT",
    "description": "At 1:00 PM CDT, a severe thunderstorm...",
    "hailydb_enrichments": {
      "radar_indicated": {
        "hail_inches": 1.75,
        "wind_mph": 60
      },
      "spc_verified": true,
      "spc_reports": [...],
      "ai_summary": "Professional weather analysis..."
    }
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [[...]]
  }
}
```

## Integration Examples

### Real Estate & Insurance Integration
```python
import requests
from datetime import datetime, timedelta

class HailyDBClient:
    def __init__(self, base_url="https://api.hailyai.com"):
        self.base_url = base_url
    
    def get_property_damage_history(self, lat, lon, radius_mi=5, years=3):
        """Get comprehensive damage history for a property location"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=years * 365)
        
        # Get SPC verified reports
        spc_url = f"{self.base_url}/api/reports/spc"
        spc_params = {
            'lat': lat, 'lon': lon, 'radius_mi': radius_mi,
            'start_date': start_date, 'end_date': end_date,
            'limit': 1000
        }
        
        # Get radar-detected NWS alerts
        nws_url = f"{self.base_url}/api/alerts/radar_detected"
        nws_params = {
            'lat': lat, 'lon': lon, 'radius_mi': radius_mi,
            'start_date': start_date, 'end_date': end_date,
            'status': 'expired', 'limit': 1000
        }
        
        spc_response = requests.get(spc_url, params=spc_params)
        nws_response = requests.get(nws_url, params=nws_params)
        
        return {
            'spc_reports': spc_response.json(),
            'nws_alerts': nws_response.json(),
            'summary': {
                'total_events': spc_response.json()['total'] + nws_response.json()['total'],
                'search_radius': radius_mi,
                'time_period': f"{start_date} to {end_date}"
            }
        }
```

### Restoration Contractor Integration
```javascript
class WeatherDamageAnalyzer {
    constructor(apiBase = 'https://api.hailyai.com') {
        this.apiBase = apiBase;
    }
    
    async getMarketOpportunities(state, startDate, endDate) {
        // Get high-wind damage events for roofing opportunities
        const windResponse = await fetch(
            `${this.apiBase}/api/alerts/radar_detected/wind?state=${state}&start_date=${startDate}&end_date=${endDate}&limit=500`
        );
        
        // Get hail damage events for roof/siding opportunities  
        const hailResponse = await fetch(
            `${this.apiBase}/api/alerts/radar_detected/hail?state=${state}&start_date=${startDate}&end_date=${endDate}&limit=500`
        );
        
        const [windData, hailData] = await Promise.all([
            windResponse.json(),
            hailResponse.json()
        ]);
        
        return this.analyzeOpportunities(windData, hailData);
    }
    
    analyzeOpportunities(windData, hailData) {
        const opportunities = [];
        
        // Process wind damage locations
        windData.features?.forEach(feature => {
            const props = feature.properties;
            if (props.data_source === 'nws' && props.hailydb_enrichments?.radar_indicated?.wind_mph >= 58) {
                opportunities.push({
                    type: 'roof_wind_damage',
                    location: props.areaDesc,
                    severity: props.hailydb_enrichments.radar_indicated.wind_mph,
                    date: props.effective,
                    coordinates: feature.geometry
                });
            }
        });
        
        // Process hail damage locations
        hailData.features?.forEach(feature => {
            const props = feature.properties;
            const hailSize = props.hailydb_enrichments?.radar_indicated?.hail_inches;
            if (hailSize >= 1.0) { // Quarter size or larger
                opportunities.push({
                    type: 'hail_damage',
                    location: props.areaDesc,
                    severity: `${hailSize}" hail`,
                    date: props.effective,
                    coordinates: feature.geometry
                });
            }
        });
        
        return opportunities.sort((a, b) => new Date(b.date) - new Date(a.date));
    }
}
```

## Authentication

Currently, HailyDB APIs are publicly accessible without authentication. For production enterprise usage, contact support for API key provisioning.

### Future Enterprise Features
- **API Key Authentication**: Secure access with usage tracking
- **Rate Limiting by Tier**: Different limits based on subscription level
- **Webhook Subscriptions**: Real-time notifications for new damage events
- **Custom Data Exports**: Bulk historical data access

## Rate Limiting

### Current Limits
- **Public Access**: 1000 requests per hour per IP
- **Response Size**: Maximum 5000 records per request
- **Concurrent Requests**: Up to 10 simultaneous connections

### Headers
Rate limit information included in response headers:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1692547200
```

### Best Practices
- Implement exponential backoff for failed requests
- Use appropriate pagination with `limit` and `offset`
- Cache responses when possible to reduce API calls
- Monitor rate limit headers to avoid throttling

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_COORDINATES",
    "message": "Latitude must be between -90 and 90",
    "details": {
      "parameter": "lat",
      "provided_value": "999",
      "valid_range": "[-90, 90]"
    }
  },
  "request_id": "req_abc123xyz789"
}
```

### Common Error Codes
- **INVALID_PARAMETERS**: Malformed or out-of-range parameters
- **INVALID_COORDINATES**: Geographic coordinates outside valid ranges
- **INVALID_DATE_RANGE**: Date parameters in incorrect format or invalid range
- **RATE_LIMIT_EXCEEDED**: Too many requests within time window
- **INTERNAL_ERROR**: System error, contact support with request_id

### Error Handling Examples
```python
import requests
from time import sleep

def robust_api_call(url, params, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:  # Rate limited
                sleep(2 ** attempt)  # Exponential backoff
                continue
            elif response.status_code >= 400:
                error_data = response.json()
                print(f"API Error: {error_data['error']['message']}")
                return None
                
        except requests.RequestException as e:
            if attempt == max_retries - 1:
                raise e
            sleep(2 ** attempt)
    
    return None
```

## Webhooks

### Webhook Configuration (Enterprise)
Real-time notifications for new damage events in specified geographic areas.

```json
{
  "webhook_id": "wh_abc123",
  "url": "https://your-app.com/webhooks/hailydb",
  "events": ["new_radar_detection", "spc_report_verified"],
  "filters": {
    "states": ["TX", "FL", "CA"],
    "min_hail_size": 1.0,
    "min_wind_speed": 58
  },
  "active": true
}
```

### Webhook Payload Example
```json
{
  "event_type": "new_radar_detection",
  "timestamp": "2025-08-20T14:30:00Z",
  "data": {
    "alert_id": "urn:oid:2.49.0.1.840.0.abc123...",
    "event": "Severe Thunderstorm Warning",
    "area": "Harris County, TX",
    "radar_indicated": {
      "hail_inches": 1.75,
      "wind_mph": 65
    },
    "geometry": {...}
  },
  "webhook_id": "wh_abc123"
}
```

## SDK Development

### Python SDK (Planned)
```bash
pip install hailydb-python
```

```python
from hailydb import HailyDBClient

client = HailyDBClient(api_key="your_api_key")
damage_events = client.get_damage_history(
    lat=29.7604, lon=-95.3698, 
    radius_mi=25, days_back=90
)
```

### JavaScript/TypeScript SDK (Planned)
```bash
npm install @hailydb/client
```

```typescript
import { HailyDBClient } from '@hailydb/client';

const client = new HailyDBClient({ apiKey: 'your_api_key' });
const events = await client.getRadarDetectedEvents({
  lat: 29.7604,
  lon: -95.3698,
  radiusMi: 25,
  startDate: '2025-01-01'
});
```

## Performance & Monitoring

### System Health
Monitor system status via health endpoint:
```bash
curl https://api.hailyai.com/api/health
```

### Performance Metrics
- **Average Response Time**: <300ms for most queries
- **Availability**: 99.9% uptime SLA
- **Data Freshness**: NWS alerts updated every 5 minutes, SPC reports daily

### Monitoring Dashboard
Real-time system metrics available at: https://status.hailyai.com

### Performance Optimization Tips
- Use geographic filtering to limit result sets
- Implement appropriate caching for historical queries  
- Use pagination for large data sets
- Monitor response headers for performance guidance

## License & Usage

This platform provides historical weather damage intelligence for legitimate business applications including insurance claims processing, damage assessment, and restoration industry operations. All data sources are publicly available through official government APIs.

---

**HailyDB v2.1.9** - Production-ready historical weather damage intelligence platform with comprehensive API suite and clear data source identification for insurance and restoration industry clients.

## Client Integration Examples

### JavaScript/TypeScript
```javascript
// Get comprehensive damage feed for a location
const response = await fetch('https://api.hailyai.com/api/reports/spc?lat=29.7604&lon=-95.3698&radius_mi=50');
const data = await response.json();

// Filter by data source
const spcReports = data.items.filter(item => item.data_source === 'spc');
const verifiedReports = data.items.filter(item => item.source_type === 'report');
```

### Python
```python
import requests

# Get radar-detected alerts
response = requests.get('https://api.hailyai.com/api/alerts/radar_detected?lat=40.7128&lon=-74.0060&radius_mi=25')
data = response.json()

# Process by data source
for feature in data['features']:
    props = feature['properties']
    if props['data_source'] == 'nws' and props['source_type'] == 'alert':
        print(f"NWS Alert: {props['event']} - {props['areaDesc']}")
```