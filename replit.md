# HailyDB v2.1 - National Weather Service Alert Intelligence Platform

## Overview
HailyDB is a **historical weather damage intelligence platform** designed to capture and analyze expired NWS alerts containing radar-detected hail and high winds. Unlike active weather platforms, HailyDB's core value proposition is providing comprehensive historical data on **where likely weather damage WAS**, making it essential for insurance claims processing, damage assessment, restoration contractors, and forensic weather analysis.

**Core Business Value**: Historical radar-detected severe weather events (expired alerts with hail/wind data) for damage assessment and insurance claims.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
HailyDB is built as a Flask-based web service with a PostgreSQL backend, optimized for Replit deployment.

### Recent Achievements (August 19, 2025) - v2.1.2 Release
- **Critical Bug Fixed**: Resolved `'NoneType' object has no attribute 'lower'` errors in state enrichment
- **Complete API Coverage**: Fixed missing `/api/alerts/{alert_id}` endpoint for individual alert details
- **State Enrichment Hardened**: Added comprehensive error handling for None/invalid UGC codes
- **Perfect SPC Synchronization**: Achieved 100% data capture with zero variance tolerance
- **Core Business Value Defined**: Repositioned as historical damage intelligence platform
- **NWS API Compliance**: Complete adherence to official NWS OpenAPI specification for data formats
- **Historical Alert Repository**: `/api/alerts/expired` endpoint returns GeoJSON FeatureCollection format
- **Individual Alert Access**: Full JSON API for complete alert details with enrichments
- **Code Cleanup**: Deprecated unused parsers and moved legacy components to `/deprecated` folder
- **Historical Data Stats**: 2,085 expired radar-detected damage events (27.6% of all alerts)
- **Production Ready**: Clean architecture with NWS-standard field naming and response structures

### Backend Architecture
- **Flask Application**: Core web service utilizing SQLAlchemy ORM.
- **PostgreSQL Database**: Relational schema with JSONB support for complex data storage.
- **Background Services**: Autonomous scheduling system for data processing and ingestion.
- **RESTful API**: Standardized API design for external interactions.

### Key Components

#### Data Ingestion Services
- **NWS Alert Ingestion**: Polls the NWS API for real-time alerts.
- **SPC Report Ingestion**: Imports historical data from the Storm Prediction Center.
- **Hurricane Track Data**: Integrates historical hurricane data from NOAA HURDAT2.
- **Live Radar Service**: Processes real-time radar-detected events.

#### AI Enhancement Services
- **Alert Enrichment**: Uses OpenAI GPT-4o for contextual summaries of alerts.
- **SPC Enhanced Context**: Provides multi-source enrichment for storm reports.
- **Match Summarizer**: AI-powered verification summaries for data correlation.

#### Data Processing Services
- **SPC Matching**: Cross-references NWS alerts with SPC storm reports.
- **SPC Verification**: Ensures data integrity against live SPC data.
- **Radar Parsing**: Extracts specific weather parameters like hail sizes and wind speeds from alert descriptions.
- **Enhanced Context Service**: AI-powered enrichment with OpenAI GPT-4o integration.

#### Webhook System
- **Webhook Service**: Delivers real-time HTTP notifications for external integrations.
- **Rule-based Evaluation**: Configurable conditions for alert dispatch.

### UI/UX Decisions
The system prioritizes **historical damage event discovery** with intuitive filtering for expired alerts containing radar-detected hail and wind damage. The interface emphasizes damage assessment workflows rather than active weather monitoring, with clear presentation of radar parameters, expiration timestamps, and geographic coverage. Professional layout optimized for insurance and restoration industry users who need to identify past weather damage locations.

### Data Flow
The system involves real-time ingestion of NWS alerts, followed by radar processing, SPC cross-referencing, AI enrichment, and ultimately, webhook dispatch and continuous data verification.

## Active Production Architecture

### Core Services
- **Flask Application** (`app.py`): Main web service with NWS API-compliant endpoints
- **Alert Model** (`models.py`): SQLAlchemy ORM with NWS field mapping and enrichments
- **Autonomous Scheduler** (`autonomous_scheduler.py`): Background service orchestration
- **SPC Ingestion** (`spc_ingest.py`): Storm Prediction Center data polling
- **Live Radar Service** (`live_radar_service.py`): Real-time NWS alert processing
- **Enhanced Context Service** (`enhanced_context_service.py`): AI enrichment with GPT-4o

### Supporting Services
- **SPC Matching** (`spc_matcher.py`): Cross-referencing alerts with storm reports
- **SPC Verification** (`spc_verification.py`): Data integrity validation
- **SPC Enrichment** (`spc_enrichment.py`): Multi-source data enhancement
- **Webhook Service** (`webhook_service.py`): External integrations

### Deprecated Components
Moved to `/deprecated` folder:
- Legacy parsers (`city_parser.py`, `historical_radar_parser.py`)
- One-time utilities (`comprehensive_data_audit.py`, `spc_sync_fix.py`)
- Development tools (`spc_perfect_parser.py`)

## External Dependencies
- **Flask**: Web framework following NWS API standards
- **SQLAlchemy**: Database ORM with JSONB support for NWS data structures
- **psycopg2-binary**: PostgreSQL adapter for production database
- **Gunicorn**: WSGI server for production deployment
- **OpenAI**: GPT-4o for professional weather intelligence summaries
- **Requests**: HTTP client for NWS and SPC API integration
- **Official Data Sources**: NWS API, Storm Prediction Center, NOAA HURDAT2