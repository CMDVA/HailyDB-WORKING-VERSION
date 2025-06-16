# HailyDB v2.0 - National Weather Service Alert Intelligence Platform

## Overview

HailyDB is a comprehensive weather intelligence platform that ingests, processes, and enriches National Weather Service (NWS) alerts with AI-powered analysis and Storm Prediction Center (SPC) verification. The system provides real-time weather data processing capabilities for enterprise applications, insurance claims processing, and emergency management systems.

The application is built as a Flask-based web service with PostgreSQL database backend, designed for deployment on Replit's infrastructure with auto-scaling capabilities.

## System Architecture

### Backend Architecture
- **Flask Application** (`main.py`, `app.py`) - Core web service with SQLAlchemy ORM
- **PostgreSQL Database** - Comprehensive relational schema with JSONB support for complex data
- **Background Services** - Autonomous scheduling system without APScheduler dependency
- **RESTful API Design** - Well-structured endpoints following industry standards

### Key Components

#### Data Ingestion Services
- **NWS Alert Ingestion** (`ingest.py`) - Real-time polling of NWS API every 5 minutes
- **SPC Report Ingestion** (`spc_ingest.py`) - Storm Prediction Center historical data import
- **Hurricane Track Data** (`hurricane_ingest.py`) - NOAA HURDAT2 historical hurricane database
- **Live Radar Service** (`live_radar_service.py`) - Real-time radar-detected event processing

#### AI Enhancement Services
- **Alert Enrichment** (`enrich.py`) - OpenAI GPT-4o powered contextual summaries
- **SPC Enhanced Context** (`spc_enhanced_context.py`) - Multi-source enrichment for storm reports
- **Match Summarizer** (`match_summarizer.py`) - AI-powered verification summaries

#### Data Processing Services
- **SPC Matching** (`spc_matcher.py`) - Cross-references NWS alerts with SPC storm reports
- **SPC Verification** (`spc_verification.py`) - Data integrity verification against live SPC data
- **Radar Parsing** - Extracts hail sizes and wind speeds from alert descriptions
- **City Parser** (`city_parser.py`) - Extracts city names from NWS area descriptions

#### Webhook System
- **Webhook Service** (`webhook_service.py`) - Real-time HTTP notifications for external integrations
- **Rule-based Evaluation** - Configurable conditions for alert dispatch

### Data Sources Integration

The system integrates with multiple authoritative weather data sources:

1. **National Weather Service (NWS)** - Real-time alert ingestion via official API
2. **Storm Prediction Center (SPC)** - Historical storm verification reports
3. **NOAA HURDAT2** - Complete hurricane track database
4. **OpenAI GPT-4o** - AI-powered alert enrichment and summarization

## Data Flow

1. **Real-time Ingestion**: NWS alerts polled every 5 minutes and stored with full geometry
2. **Radar Processing**: Hail sizes and wind speeds extracted from alert descriptions
3. **SPC Cross-referencing**: Alerts matched with historical storm reports for verification
4. **AI Enrichment**: Contextual summaries generated using OpenAI GPT-4o
5. **Webhook Dispatch**: Real-time notifications sent to configured external systems
6. **Data Verification**: Continuous integrity checks against source data

## External Dependencies

### Core Dependencies
- **Flask 3.1.1** - Web framework
- **SQLAlchemy 2.0.41** - Database ORM
- **psycopg2-binary 2.9.10** - PostgreSQL adapter
- **Gunicorn 23.0.0** - WSGI server for production deployment

### Enhanced Features
- **OpenAI 1.83.0** - AI enrichment services
- **Shapely 2.1.1** - Geometric operations for alert boundaries
- **Requests 2.32.3** - HTTP client for external API calls
- **APScheduler 3.11.0** - Background task scheduling
- **CacheTools 6.0.0** - TTL caching for webhook deduplication

### Optional Integrations
- **Google Places API** - Enhanced location enrichment (configured via environment)
- **Trafilatura 2.0.0** - Web content extraction for additional context

## Deployment Strategy

### Replit Configuration
- **Target**: Autoscale deployment
- **Runtime**: Python 3.11 with PostgreSQL 16
- **Port**: 5000 (mapped to external port 80)
- **Process**: Gunicorn with bind to 0.0.0.0:5000

### Database Configuration
- **Engine**: PostgreSQL with connection pooling
- **Pool Settings**: 300-second recycle, pre-ping enabled
- **Schema**: Comprehensive relational design with JSONB for complex data structures

### Environment Variables
- `DATABASE_URL` - PostgreSQL connection string
- `OPENAI_API_KEY` - AI enrichment service authentication
- `GOOGLE_PLACES_API_KEY` - Enhanced location services (optional)
- `SESSION_SECRET` - Flask session security
- Various batch size configurations for performance tuning

## Changelog

```
Changelog:
- June 16, 2025. Initial setup
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```