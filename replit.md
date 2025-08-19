# HailyDB v2.0 - National Weather Service Alert Intelligence Platform

## Overview
HailyDB is a **historical weather damage intelligence platform** designed to capture and analyze expired NWS alerts containing radar-detected hail and high winds. Unlike active weather platforms, HailyDB's core value proposition is providing comprehensive historical data on **where likely weather damage WAS**, making it essential for insurance claims processing, damage assessment, restoration contractors, and forensic weather analysis.

**Core Business Value**: Historical radar-detected severe weather events (expired alerts with hail/wind data) for damage assessment and insurance claims.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
HailyDB is built as a Flask-based web service with a PostgreSQL backend, optimized for Replit deployment.

### Recent Achievements (August 19, 2025)
- **Perfect SPC Synchronization**: Achieved 100% data capture with zero variance tolerance
- **Core Business Value Defined**: Repositioned as historical damage intelligence platform
- **Historical Alert Repository**: Created `/api/alerts/expired` endpoint following NWS API standards
- **Historical Data Stats**: 2,085 expired radar-detected damage events (27.6% of all alerts)
- **Insurance Industry Focus**: Optimized for "where damage WAS" rather than active weather

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
- **City Parser**: Extracts city names from NWS area descriptions.

#### Webhook System
- **Webhook Service**: Delivers real-time HTTP notifications for external integrations.
- **Rule-based Evaluation**: Configurable conditions for alert dispatch.

### UI/UX Decisions
The system prioritizes **historical damage event discovery** with intuitive filtering for expired alerts containing radar-detected hail and wind damage. The interface emphasizes damage assessment workflows rather than active weather monitoring, with clear presentation of radar parameters, expiration timestamps, and geographic coverage. Professional layout optimized for insurance and restoration industry users who need to identify past weather damage locations.

### Data Flow
The system involves real-time ingestion of NWS alerts, followed by radar processing, SPC cross-referencing, AI enrichment, and ultimately, webhook dispatch and continuous data verification.

## External Dependencies

- **Flask**: Web framework.
- **SQLAlchemy**: Database ORM.
- **psycopg2-binary**: PostgreSQL adapter.
- **Gunicorn**: WSGI server.
- **OpenAI**: For AI enrichment services (GPT-4o).
- **Shapely**: For geometric operations related to alert boundaries.
- **Requests**: HTTP client for external API calls.
- **CacheTools**: Used for caching, specifically for webhook deduplication.
- **National Weather Service (NWS)**: Official API for real-time alert ingestion.
- **Storm Prediction Center (SPC)**: Source for historical storm verification reports.
- **NOAA HURDAT2**: Source for the complete hurricane track database.
```