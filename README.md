# HailyDB v2.0 - National Weather Service Alert Ingestion System

**Production-Ready Weather Data Platform with AI Enrichment and Real-Time Webhooks**

## System Overview

HailyDB is a comprehensive National Weather Service (NWS) Alert Ingestion Service that provides intelligent event-driven weather data processing with advanced features including radar-indicated parsing, real-time webhooks, full geometry/county mapping, SPC verification, hurricane track data integration, and AI-powered enrichment using OpenAI GPT-4o.

### Key Features
- 🌪️ **Real-Time NWS Alert Ingestion** - Automated polling and processing of National Weather Service alerts
- 🎯 **SPC Verification System** - Cross-reference alerts with Storm Prediction Center historical reports
- 🚀 **Live Radar Alerts** - Real-time radar-detected events with webhook dispatch
- 🧠 **AI-Powered Enrichment** - OpenAI GPT-4o enhanced summaries and location intelligence
- 🌊 **Hurricane Track Data** - NOAA HURDAT2 integration for historical hurricane analysis
- 🔗 **Real-Time Webhooks** - Configurable notifications for external system integration
- 📊 **Comprehensive APIs** - RESTful endpoints for all data access patterns

## System Status

**Current Status:** OPERATIONAL WITH CRITICAL ISSUES ⚠️
- Core functionality fully operational
- Data ingestion active and processing correctly
- Critical issue: Live radar service application context errors
- Autonomous scheduler running successfully

## Quick Start

### Access the Application
- **Web Interface:** https://your-hailydb.replit.app
- **Admin Dashboard:** https://your-hailydb.replit.app/internal/dashboard
- **System Status:** https://your-hailydb.replit.app/internal/status

### Manual Operations
Use the admin dashboard to trigger data ingestion operations:
- **NWS Alert Update** - Fetch latest weather alerts
- **SPC Report Ingestion** - Import Storm Prediction Center data
- **Alert-SPC Matching** - Cross-reference and verify alerts
- **AI Enrichment** - Generate enhanced summaries

## API Documentation

### Authentication
- **Method:** API key via Authorization header (optional, configurable)
- **Rate Limits:** 100 requests/minute for search endpoints
- **Response Format:** JSON with consistent error handling

### Core API Endpoints

#### Weather Alert APIs
```bash
# Search alerts with filtering
GET /api/alerts/search?state=TX&event_type=Severe%20Thunderstorm%20Warning&limit=25

# Get specific alert details
GET /api/alerts/{id}

# County-specific alerts
GET /api/alerts/by-county/{state}/{county}

# AI-enriched alert summaries
GET /api/alerts/summaries
```

#### SPC Verification APIs
```bash
# Storm reports with date filtering
GET /api/spc/reports?report_date=2024-06-10&report_type=hail

# Individual SPC report with enrichment
GET /api/spc/reports/{id}

# Enhanced context for SPC reports
GET /api/spc/enrichment/{report_id}
```

#### Live Radar APIs
```bash
# Real-time radar-detected events
GET /api/live-radar-alerts?state=TX&active_only=true

# Radar alert statistics
GET /api/radar-alerts/summary
```

#### Hurricane Data APIs
```bash
# Historical hurricane tracks
GET /api/hurricane-tracks?year=2023&landfall_only=true

# Specific storm track data
GET /api/hurricane-tracks/{storm_id}
```

### Webhook Integration

Configure real-time notifications for external systems:

```json
{
  "webhook_url": "https://your-system.com/webhook",
  "event_type": "hail",
  "threshold_value": 1.0,
  "location_filter": "TX,OK,KS",
  "user_id": "your_client_id"
}
```

**Webhook Management:**
- `GET /api/webhook-rules` - List active rules
- `POST /api/webhook-rules` - Create new rule
- `POST /api/webhook-test` - Test webhook delivery
- `DELETE /api/webhook-rules/{id}` - Remove rule

## Data Sources

### Primary Data Streams
1. **National Weather Service (NWS)**
   - Source: https://api.weather.gov/alerts/active
   - Frequency: Every 5 minutes (autonomous)
   - Content: Real-time weather alerts with full geometry

2. **Storm Prediction Center (SPC)**
   - Source: https://www.spc.noaa.gov/climo/reports/
   - Frequency: Daily at midnight (autonomous)
   - Content: Historical storm verification reports

3. **NOAA Hurricane Database (HURDAT2)**
   - Source: NOAA Atlantic Hurricane Database
   - Content: Historical hurricane tracks and landfall data

4. **OpenAI GPT-4o**
   - Purpose: AI-powered alert enrichment and summarization
   - Usage: On-demand and batch processing

## Database Schema

### Core Tables

#### alerts - Primary weather alert storage
- `nws_id` - Unique NWS alert identifier
- `event_type` - Type of weather event
- `geometry` - Alert polygon geometry (JSONB)
- `radar_indicated` - Radar-detected measurements (JSONB)
- `spc_verified` - Cross-referenced with SPC reports
- `ai_summary` - OpenAI-generated summary
- Full temporal tracking (effective, expires, onset times)

#### spc_reports - Storm verification data
- `report_type` - tornado, wind, or hail
- `coordinates` - Precise latitude/longitude
- `magnitude` - F-scale, wind speed, or hail size
- `spc_enrichment` - AI-powered location context (JSONB)
- Complete SPC metadata and comments

#### live_radar_alerts - Real-time radar events
- `radar_indicated_event` - Boolean radar detection flag
- `hail_inches` - Detected hail size
- `wind_mph` - Detected wind speed
- Real-time processing with webhook dispatch

#### hurricane_tracks - Historical hurricane data
- `storm_id` - Unique hurricane identifier
- `coordinates` - Track point location
- `landfall_location` - Landfall detection and location
- Complete storm intensity and timing data

## System Architecture

### Core Components
- **Flask Backend** - Main application server with SQLAlchemy ORM
- **PostgreSQL Database** - Primary data storage with JSONB support
- **Autonomous Scheduler** - Background service for automated operations
- **Webhook Service** - Real-time notification dispatch
- **AI Enrichment Engine** - OpenAI integration for enhanced content

### Processing Pipeline
1. **Data Ingestion** - Automated polling of external APIs
2. **Deduplication** - Hash-based duplicate detection
3. **Geocoding** - County FIPS mapping and geometry processing
4. **Cross-Reference** - SPC verification and matching
5. **AI Enhancement** - Automated summarization and enrichment
6. **Webhook Dispatch** - Real-time notifications based on rules

## Known Issues and Status

### Critical Issues (Requiring Immediate Attention)
1. **Live Radar Service Application Context Error**
   - Status: CRITICAL
   - Impact: Live radar data not persisting to database
   - Error: `Working outside of application context`

2. **Webhook Type Import Error**
   - Status: HIGH
   - Impact: Webhook evaluation failing in autonomous operations
   - Error: `name 'Any' is not defined`

### System Limitations
- Manual operation triggers required for some functions
- Subject to external API rate limits
- Single point of failure (no redundancy configured)
- Live radar service currently experiencing persistence issues

## Development and Deployment

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="your_postgres_url"
export OPENAI_API_KEY="your_openai_key"

# Run application
python main.py
```

### Production Deployment
- **Platform:** Replit (production-ready)
- **Database:** PostgreSQL with comprehensive schema
- **Monitoring:** Built-in health checks and operation logging
- **Scaling:** Handles nationwide alert volumes effectively

## Monitoring and Maintenance

### Health Monitoring
- **System Status:** `/internal/status` - Comprehensive health metrics
- **Operation Logs:** `/ingestion-logs` - Detailed audit trail
- **Dashboard:** `/internal/dashboard` - System control panel

### Regular Maintenance
- **Daily:** Monitor system health and operation success rates
- **Weekly:** Review data quality and SPC verification coverage
- **Monthly:** Database maintenance and performance optimization

## Support and Documentation

### Additional Resources
- **Admin Dashboard:** Complete system control and monitoring
- **Operation Logs:** Detailed audit trail for troubleshooting
- **Health Checks:** Real-time system status and metrics
- **Error Tracking:** Comprehensive logging with stack traces

### API Support
- **Response Format:** Consistent JSON with error handling
- **Pagination:** Configurable limits and offset support
- **Filtering:** Comprehensive query parameters for all endpoints
- **Error Codes:** Standard HTTP status codes with detailed messages

---

**Last Updated:** December 12, 2024
**Version:** v2.0 Production
**Deployment:** https://your-hailydb.replit.app

For technical support or feature requests, please refer to the admin dashboard or system status endpoint for current operational information.