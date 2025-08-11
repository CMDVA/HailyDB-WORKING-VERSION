# HailyDB v2.0 - National Weather Service Alert Intelligence Platform

## Overview

HailyDB is a comprehensive weather intelligence platform designed to ingest, process, and enrich National Weather Service (NWS) alerts using AI-powered analysis and Storm Prediction Center (SPC) verification. Its primary purpose is to provide real-time weather data processing capabilities for enterprise applications, insurance claims processing, and emergency management systems, offering significant business value in weather intelligence and risk assessment.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- August 11, 2025: SPC HISTORICAL DATA BACKFILL SYSTEM IMPLEMENTED
  * COMPREHENSIVE BACKFILL SCRIPTS: Created spc_backfill.py and spc_backfill_runner.py for systematic historical data import
  * MONTH-BY-MONTH PROCESSING: Automated backfill system works systematically through historical months
  * VERIFICATION INTEGRATION: Each date is verified before processing to prevent unnecessary duplicate work
  * RESPECTFUL REQUEST HANDLING: Built-in delays and batch processing to avoid overwhelming server resources
  * PROGRESS TRACKING: Comprehensive statistics and error reporting for backfill operations
  * OFF-BY-ONE FIX CONFIRMED: All duplicate detection issues resolved - reimport system works perfectly
  * PRODUCTION READY: Backfill system ready for systematic historical data collection starting with August 2025

## System Architecture

HailyDB is built as a Flask-based web service with a PostgreSQL backend, optimized for Replit deployment.

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
The system focuses on a consistent, professional layout for displaying weather intelligence, ensuring a unified user experience across all report detail pages, regardless of data availability. This includes consistent presentation of enhanced context and location information.

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