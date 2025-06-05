
# HailyDB API Endpoints Documentation

## Overview

HailyDB provides comprehensive RESTful API access to National Weather Service alerts, Storm Prediction Center reports, AI-enriched summaries, and verification data. All endpoints return JSON unless otherwise specified.

**Base URL**: `https://your-app.replit.app`

## Authentication

No authentication required for public endpoints. Internal endpoints are for administrative use.

---

## 🚨 Alert Endpoints

### Get All Alerts
```
GET /alerts
```
**Description**: Retrieve alerts with optional filtering and pagination

**Query Parameters**:
- `page` (int, default: 1) - Page number for pagination
- `per_page` (int, default: 50, max: 100) - Results per page
- `severity` (string) - Filter by severity: "Minor", "Moderate", "Severe", "Extreme"
- `event` (string) - Filter by event type (partial match)
- `category` (string) - Filter by predefined category
- `state` (string) - Filter by state name or abbreviation
- `county` (string) - Filter by county name
- `area` (string) - Filter by area description
- `effective_date` (string, YYYY-MM-DD) - Filter by effective date
- `active_only` (boolean, default: false) - Show only currently active alerts
- `format` (string) - Set to "json" for JSON response

**Categories Available**:
- Severe Weather Alert
- Winter Weather Alert
- Flood Alert
- Coastal Alert
- Wind & Fog Alert
- Fire Weather Alert
- Air Quality & Dust Alert
- Marine Alert
- Tropical Weather Alert
- Tsunami Alert
- General Weather Info

**Example**:
```
GET /alerts?state=TX&severity=Severe&active_only=true&per_page=25
```

**Response**:
```json
{
  "alerts": [
    {
      "id": "urn:oid:2.49.0.1.840.0.uuid",
      "event": "Tornado Warning",
      "severity": "Extreme",
      "area_desc": "Harris County, TX",
      "effective": "2025-06-03T15:30:00Z",
      "expires": "2025-06-03T16:30:00Z",
      "ai_summary": "AI-generated summary",
      "ai_tags": ["tornado", "immediate_threat"]
    }
  ],
  "pagination": {
    "page": 1,
    "pages": 5,
    "per_page": 25,
    "total": 123
  }
}
```

### Get Single Alert
```
GET /alerts/{alert_id}
```
**Description**: Retrieve detailed information for a specific alert

**Response**:
```json
{
  "id": "alert_id",
  "event": "Tornado Warning",
  "severity": "Extreme",
  "area_desc": "Harris County, TX",
  "effective": "2025-06-03T15:30:00Z",
  "expires": "2025-06-03T16:30:00Z",
  "sent": "2025-06-03T15:25:00Z",
  "geometry": { "type": "Polygon", "coordinates": [...] },
  "properties": { /* Full NWS alert properties */ },
  "raw": { /* Complete original NWS alert data */ },
  "ai_summary": "AI-generated summary",
  "ai_tags": ["tornado", "immediate_threat"],
  "spc_verified": true,
  "spc_reports": [{ /* SPC storm reports */ }],
  "ingested_at": "2025-06-03T15:26:00Z"
}
```

### Get Alert Summaries
```
GET /alerts/summary
```
**Description**: Get recent alerts with AI-generated summaries and verification data

**Response**:
```json
{
  "summaries": [
    {
      "id": "alert_id",
      "event": "Severe Thunderstorm Warning",
      "severity": "Severe",
      "area_desc": "Dallas County, TX",
      "effective": "2025-06-03T14:00:00Z",
      "expires": "2025-06-03T15:00:00Z",
      "ai_summary": "AI-generated alert summary",
      "ai_tags": ["severe_thunderstorm", "hail"],
      "spc_verified": true,
      "spc_verification_summary": "AI summary of SPC verification",
      "spc_confidence_score": 0.9,
      "spc_report_count": 3,
      "verification_status": "verified_with_ai_summary"
    }
  ],
  "total_count": 20,
  "verified_count": 12,
  "ai_summary_count": 8
}
```

### Get Active Alerts
```
GET /api/alerts/active
```
**Description**: Get all currently active alerts (within effective/expires window)

**Response**:
```json
{
  "timestamp": "2025-06-03T16:00:00Z",
  "total_active": 15,
  "alerts": [
    {
      "id": "alert_id",
      "event": "High Wind Warning",
      "severity": "Moderate",
      "area_desc": "Cook County, IL",
      "effective": "2025-06-03T10:00:00Z",
      "expires": "2025-06-03T20:00:00Z",
      "ai_summary": "High winds expected",
      "ai_tags": ["high_wind", "power_outages"]
    }
  ]
}
```

### Search Alerts
```
GET /api/alerts/search
```
**Description**: Advanced search with external application-friendly parameters

**Query Parameters**:
- `state` (string) - State name or abbreviation
- `county` (string) - County name
- `area` (string) - Area description
- `severity` (string) - Alert severity
- `event_type` (string) - Event type (partial match)
- `active_only` (boolean) - Filter to active alerts only
- `page` (int) - Page number
- `limit` (int, max: 100) - Results per page

**Response**:
```json
{
  "total": 50,
  "page": 1,
  "limit": 25,
  "pages": 2,
  "filters": {
    "state": "TX",
    "severity": "Severe",
    "active_only": true
  },
  "alerts": [{ /* Alert objects */ }]
}
```

### Get Alerts by State
```
GET /api/alerts/by-state/{state}
```
**Parameters**: 
- `active_only` (boolean) - Filter to active alerts

**Response**:
```json
{
  "state": "TX",
  "total_alerts": 25,
  "alerts": [{ /* Alert objects */ }]
}
```

### Get Alerts by County
```
GET /api/alerts/by-county/{state}/{county}
```
**Parameters**: 
- `active_only` (boolean) - Filter to active alerts

**Response**:
```json
{
  "state": "TX",
  "county": "Harris",
  "total_alerts": 8,
  "alerts": [{ /* Alert objects */ }]
}
```

---

## 🌪️ SPC (Storm Prediction Center) Endpoints

### Get SPC Reports
```
GET /api/spc/reports
```
**Description**: Retrieve Storm Prediction Center storm reports with filtering

**Query Parameters**:
- `type` (string) - Report type: "tornado", "wind", "hail"
- `state` (string) - State abbreviation (e.g., "TX")
- `county` (string) - County name (partial match)
- `date` (string, YYYY-MM-DD) - Specific report date
- `limit` (int, max: 500, default: 100) - Results limit
- `offset` (int, default: 0) - Results offset for pagination

**Example**:
```
GET /api/spc/reports?type=tornado&state=KS&date=2025-06-01
```

**Response**:
```json
{
  "reports": [
    {
      "id": 123,
      "report_type": "tornado",
      "report_date": "2025-06-01",
      "time_utc": "1830",
      "location": "2 SW Dodge City",
      "county": "Ford",
      "state": "KS",
      "lat": 37.7000,
      "lon": -100.0500,
      "f_scale": "EF2",
      "comments": "Tornado damaged several buildings"
    }
  ],
  "pagination": {
    "total": 25,
    "limit": 100,
    "offset": 0,
    "has_more": false
  },
  "filters": {
    "type": "tornado",
    "state": "KS",
    "date": "2025-06-01"
  }
}
```

### View SPC Reports (Web Interface)
```
GET /spc/reports
```
**Description**: Web interface for browsing SPC reports

---

## ✅ SPC Verification & Matching Endpoints

### Get SPC Verified Matches
```
GET /spc-matches/data
```
**Description**: API endpoint for verified NWS alert to SPC report matches

**Query Parameters**:
- `hours` (int, default: 168) - Time window in hours (168 = 7 days)
- `event` (string) - Filter by alert event type
- `method` (string) - Filter by matching method: "fips_exact", "proximity"
- `confidence` (string) - Filter by confidence: "high" (≥0.8), "medium" (0.5-0.8), "low" (<0.5)
- `state` (string) - Filter by state abbreviation

**Response**:
```json
{
  "summary": {
    "verified_count": 45,
    "total_reports": 128,
    "high_confidence_count": 38,
    "verification_rate": 12.5
  },
  "matches": [
    {
      "id": "alert_id",
      "effective": "2025-06-01T20:00:00Z",
      "event": "Tornado Warning",
      "area_desc": "Ford County, KS",
      "match_method": "fips_exact",
      "confidence": 0.9,
      "report_count": 2,
      "spc_reports": [
        {
          "report_type": "tornado",
          "time_utc": "2030",
          "location": "3 N Dodge City",
          "county": "Ford",
          "state": "KS",
          "comments": "EF1 tornado"
        }
      ],
      "spc_ai_summary": "AI-generated verification summary"
    }
  ],
  "states": ["KS", "TX", "OK", "NE"]
}
```

### Get SPC Verified Matches (Web Interface)
```
GET /spc-matches
```
**Description**: Web interface for browsing verified matches

### SPC Calendar Verification
```
GET /api/spc/calendar-verification
```
**Description**: 2-month calendar view of SPC data verification status

**Query Parameters**:
- `offset` (int, default: 0) - Time offset: 0=current period, -1=previous 2 months, 1=next 2 months

**Response**:
```json
{
  "status": "success",
  "results": [
    {
      "date": "2025-06-01",
      "day": 1,
      "hailydb_count": 25,
      "spc_live_count": 25,
      "match_status": "MATCH"
    },
    {
      "date": "2025-06-02",
      "day": 2,
      "hailydb_count": 18,
      "spc_live_count": 20,
      "match_status": "MISMATCH"
    }
  ],
  "date_range": {
    "start": "2025-05-01",
    "end": "2025-06-30"
  },
  "last_updated": "2025-06-03T16:00:00Z"
}
```

---

## 🤖 AI Enrichment Endpoints

### Batch Enrichment
```
POST /api/alerts/enrich-batch
```
**Description**: Enrich a batch of unenriched alerts with AI summaries

**Request Body**:
```json
{
  "limit": 50
}
```

**Response**:
```json
{
  "status": "success",
  "enriched": 45,
  "failed": 5,
  "total_processed": 50,
  "message": "Successfully enriched 45 alerts"
}
```

### Category-Specific Enrichment
```
POST /api/alerts/enrich-by-category
```
**Description**: Enrich alerts by weather category

**Request Body**:
```json
{
  "category": "Severe Weather Alert",
  "limit": 100
}
```

**Response**:
```json
{
  "status": "success",
  "category": "Severe Weather Alert",
  "enriched": 78,
  "failed": 2,
  "total_processed": 80,
  "message": "Successfully enriched 78 'Severe Weather Alert' alerts"
}
```

### Priority Alert Enrichment
```
POST /api/alerts/enrich-priority
```
**Description**: Enrich all high-priority alerts (Severe Weather, Tropical Weather, High Wind)

**Response**:
```json
{
  "status": "success",
  "enriched": 32,
  "failed": 1,
  "total_processed": 33,
  "message": "Successfully enriched 32 priority alerts"
}
```

### Get Enrichment Statistics
```
GET /api/alerts/enrichment-stats
```
**Description**: Get comprehensive enrichment coverage statistics

**Response**:
```json
{
  "total_alerts": 1250,
  "enriched_alerts": 892,
  "enrichment_rate": 71.4,
  "categories": {
    "Severe Weather Alert": {
      "total": 245,
      "enriched": 240,
      "rate": 98.0
    },
    "Winter Weather Alert": {
      "total": 189,
      "enriched": 145,
      "rate": 76.7
    }
  },
  "priority_coverage": {
    "total_priority": 156,
    "enriched_priority": 152,
    "priority_rate": 97.4
  }
}
```

### Get Unenriched Counts
```
GET /api/alerts/unenriched-counts
```
**Description**: Get counts of alerts needing enrichment by category

**Response**:
```json
{
  "priority_alerts": 4,
  "categories": {
    "Severe Weather Alert": 5,
    "Winter Weather Alert": 44,
    "Flood Alert": 23,
    "Marine Alert": 67
  },
  "total_unenriched": 358
}
```

---

## 📊 System Monitoring & Health Endpoints

### System Health Status
```
GET /internal/status
```
**Description**: Comprehensive system health and diagnostics

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-03T16:00:00Z",
  "database": "healthy",
  "alerts": {
    "total": 1250,
    "recent_24h": 89,
    "active_now": 15
  },
  "spc_verification": {
    "verified_count": 156,
    "unverified_count": 1094,
    "coverage_percentage": 12.5,
    "oldest_unverified": "2025-05-15T10:00:00Z"
  },
  "ingestion": {
    "last_nws_ingestion": "2025-06-03T15:45:00Z",
    "last_spc_ingestion": "2025-06-03T14:30:00Z",
    "failed_jobs_24h": 0
  },
  "system": {
    "environment": "replit",
    "python_version": "3.11",
    "framework": "flask+sqlalchemy"
  },
  "scheduler_operations": {
    "total_operations_24h": 48,
    "successful_operations_24h": 47,
    "failed_operations_24h": 1
  }
}
```

### System Metrics
```
GET /internal/metrics
```
**Description**: Basic alert metrics for monitoring

**Response**:
```json
{
  "total_alerts": 1250,
  "enriched_alerts": 892,
  "active_alerts": 15,
  "recent_24h": 89,
  "recent_7d": 456
}
```

### Autonomous Scheduler Status
```
GET /internal/scheduler/status
```
**Description**: Get autonomous scheduler status with countdown information

**Response**:
```json
{
  "success": true,
  "scheduler": {
    "running": true,
    "thread_alive": true,
    "last_nws_poll": "2025-06-03T16:00:00Z",
    "last_spc_poll": "2025-06-03T15:30:00Z",
    "last_matching": "2025-06-03T15:45:00Z",
    "intervals": {
      "nws_minutes": 5,
      "spc_minutes": 30,
      "matching_minutes": 15
    },
    "next_operation": "nws",
    "next_countdown": 180,
    "nws_countdown": 180,
    "spc_countdown": 1620,
    "match_countdown": 720
  }
}
```

---

## 📋 Ingestion & Operation Logs

### Get Ingestion Logs
```
GET /ingestion-logs/data
```
**Description**: API endpoint for ingestion operation logs

**Query Parameters**:
- `hours` (int, default: 24) - Time window for logs
- `operation_type` (string) - Filter by: "nws_poll", "spc_poll", "spc_match"
- `success` (string) - Filter by success status: "true", "false"

**Response**:
```json
{
  "summary": {
    "success_count": 47,
    "error_count": 1,
    "total_processed": 1250,
    "total_new": 89
  },
  "logs": [
    {
      "started_at": "2025-06-03T15:45:00Z",
      "completed_at": "2025-06-03T15:45:15Z",
      "operation_type": "nws_poll",
      "trigger_method": "internal_timer",
      "success": true,
      "records_processed": 25,
      "records_new": 3,
      "error_message": null,
      "duration": 15.2
    }
  ]
}
```

### View Ingestion Logs (Web Interface)
```
GET /ingestion-logs
```
**Description**: Web interface for browsing ingestion logs

---

## 🔧 Administrative Endpoints

### Manual Ingestion Trigger
```
POST /internal/cron
```
**Description**: Manually trigger ingestion operations

**Request Body**:
```json
{
  "action": "trigger"
}
```

**Response**:
```json
{
  "status": "triggered",
  "ingested_count": 25
}
```

### Start Autonomous Scheduler
```
POST /internal/scheduler/start
```
**Response**:
```json
{
  "success": true,
  "status": "running",
  "message": "Autonomous scheduler started"
}
```

### Stop Autonomous Scheduler
```
POST /internal/scheduler/stop
```
**Response**:
```json
{
  "success": true,
  "status": "stopped",
  "message": "Autonomous scheduler stopped"
}
```

### SPC Data Ingestion
```
POST /internal/spc-ingest
```
**Description**: Trigger systematic SPC report ingestion (T-0 through T-15 days)

**Response**:
```json
{
  "success": true,
  "total_reports": 245,
  "dates_polled": 8,
  "results": [
    {
      "date": "2025-06-03",
      "reports": 0,
      "status": "completed"
    }
  ],
  "message": "Systematic SPC ingestion completed: 245 reports processed across 8 dates"
}
```

### SPC Data Backfill
```
POST /internal/spc-backfill
```
**Description**: Force backfill SPC data for specific date range

**Request Body**:
```json
{
  "start_date": "2025-05-01",
  "end_date": "2025-05-31"
}
```

**Response**:
```json
{
  "success": true,
  "total_reports": 1250,
  "dates_processed": 31,
  "results": [
    {
      "date": "2025-05-01",
      "reports": 45,
      "status": "completed"
    }
  ],
  "message": "Backfill completed: 1250 reports processed across 31 dates"
}
```

### SPC Matching
```
POST /internal/spc-match
```
**Description**: Trigger SPC report matching with NWS alerts

**Response**:
```json
{
  "success": true,
  "processed": 100,
  "matched": 15,
  "message": "SPC matching completed: 15/100 alerts matched"
}
```

### Generate AI Summaries for Verified Matches
```
POST /internal/spc-generate-summaries
```
**Description**: Generate AI summaries for verified matches without summaries

**Response**:
```json
{
  "success": true,
  "message": "Generated 12 AI summaries for verified matches",
  "generated": 12,
  "total_processed": 50
}
```

### Generate Single AI Summary
```
POST /internal/spc-generate-summary/{alert_id}
```
**Description**: Generate AI summary for specific verified alert match

**Response**:
```json
{
  "success": true,
  "message": "AI summary generated successfully",
  "summary": "The Tornado Warning for Ford County was verified by an EF1 tornado report..."
}
```

### Force Re-upload SPC Data
```
POST /internal/spc-reupload/{date}
```
**Description**: Force re-ingestion of SPC data for specific date

**Parameters**: 
- `date` (string, YYYY-MM-DD) - Date to re-upload

**Response**:
```json
{
  "success": true,
  "message": "SPC data re-uploaded for 2025-06-01",
  "reports_processed": 25
}
```

### Enrich All Priority Alerts
```
POST /internal/enrich-all-priority
```
**Description**: Comprehensive enrichment of all priority alerts in database

**Response**:
```json
{
  "success": true,
  "message": "Successfully enriched 156 priority alerts from database",
  "enriched": 156,
  "failed": 2,
  "total_processed": 158,
  "priority_types": ["Tornado Warning", "Tornado Watch", "Severe Thunderstorm Warning"]
}
```

---

## 🔍 Data Verification Endpoints

### SPC Data Verification
```
GET /internal/spc-verify
```
**Description**: Web interface for SPC data integrity verification

**Query Parameters**:
- `start_date` (string, YYYY-MM-DD) - Start date for verification
- `end_date` (string, YYYY-MM-DD) - End date for verification
- `days` (int, default: 7) - Number of days to verify (if dates not provided)
- `format` (string) - Set to "json" for API response

### Today's SPC Verification
```
GET /internal/spc-verify-today
```
**Description**: Get recent SPC verification data for dashboard

**Response**:
```json
{
  "status": "success",
  "results": [
    {
      "date": "2025-06-03",
      "hailydb_count": 0,
      "spc_live_count": 0,
      "match_status": "MATCH"
    },
    {
      "date": "2025-06-02",
      "hailydb_count": 25,
      "spc_live_count": 28,
      "match_status": "MISMATCH"
    }
  ],
  "last_updated": "2025-06-03T16:00:00Z"
}
```

---

## 📱 Web Interface Endpoints

### Main Dashboard
```
GET /
GET /internal/dashboard
```
**Description**: Administrative dashboard with system overview

### View Alerts
```
GET /alerts
```
**Description**: Web interface for browsing and filtering alerts

### View Alert Details
```
GET /alerts/{alert_id}
```
**Description**: Detailed view of individual alert with SPC verification data

### Manual Alert Enrichment
```
POST /alerts/enrich/{alert_id}
```
**Description**: Re-run AI enrichment for specific alert (form submission)

---

## 📈 Error Responses

All endpoints return appropriate HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (alert/resource not found)
- `500` - Internal Server Error

**Error Response Format**:
```json
{
  "status": "error",
  "message": "Detailed error description",
  "error": "Technical error details"
}
```

---

## 🔍 Data Models

### Alert Object
```json
{
  "id": "string",
  "event": "string",
  "severity": "string",
  "area_desc": "string", 
  "effective": "ISO8601 datetime",
  "expires": "ISO8601 datetime",
  "sent": "ISO8601 datetime",
  "geometry": "GeoJSON geometry",
  "properties": "object",
  "raw": "object",
  "ai_summary": "string",
  "ai_tags": ["string"],
  "spc_verified": "boolean",
  "spc_reports": ["object"],
  "spc_ai_summary": "string",
  "spc_confidence_score": "float",
  "spc_report_count": "integer",
  "ingested_at": "ISO8601 datetime"
}
```

### SPC Report Object
```json
{
  "id": "integer",
  "report_type": "string",
  "report_date": "YYYY-MM-DD",
  "time_utc": "string",
  "location": "string",
  "county": "string",
  "state": "string",
  "lat": "float",
  "lon": "float",
  "f_scale": "string",
  "speed": "string", 
  "size": "string",
  "comments": "string"
}
```

---

## 📊 Rate Limits & Best Practices

- **No rate limits** currently implemented
- **Pagination recommended** for large datasets
- **Use active_only filter** for real-time applications
- **Cache responses** when appropriate for better performance
- **Monitor /internal/status** for system health
- **Use batch enrichment** rather than individual alert enrichment

---

## 🚀 Integration Examples

### Get Current Severe Weather Alerts
```bash
curl "https://your-app.replit.app/api/alerts/search?severity=Severe&active_only=true&limit=50"
```

### Monitor Texas Tornado Activity
```bash
curl "https://your-app.replit.app/api/alerts/by-state/TX?active_only=true" | jq '.alerts[] | select(.event | contains("Tornado"))'
```

### Get Recent SPC Tornado Reports
```bash
curl "https://your-app.replit.app/api/spc/reports?type=tornado&limit=25"
```

### Check System Health
```bash
curl "https://your-app.replit.app/internal/status"
```

---

*Last Updated: June 2025*
*HailyDB v2.0 - Production Weather Data Platform*
