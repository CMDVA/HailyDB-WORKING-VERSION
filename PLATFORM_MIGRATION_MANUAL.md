# HailyDB Platform Migration Manual
## From Replit to Cursor IDE & Base44 Hosting

### Table of Contents
1. [Migration Overview](#migration-overview)
2. [Prerequisites](#prerequisites)
3. [Platform Export Process](#platform-export-process)
4. [Cursor IDE Setup](#cursor-ide-setup)
5. [Base44 Deployment](#base44-deployment)
6. [Configuration Changes](#configuration-changes)
7. [External Dependencies](#external-dependencies)
8. [Testing & Validation](#testing--validation)
9. [Troubleshooting](#troubleshooting)

---

## Migration Overview

This manual provides step-by-step instructions for migrating HailyDB from Replit to:
- **Cursor IDE**: For development environment
- **Base44**: For production hosting

**Current Application Stats:**
- 44 Python files (~1.2MB total)
- PostgreSQL database with 9,547+ weather alerts
- 22 active core services + 21 deprecated sync scripts
- Flask web application with Gunicorn WSGI server
- Real-time weather data ingestion from multiple APIs

---

## Prerequisites

### Required Accounts & Services
- [ ] **Cursor IDE** subscription (Pro recommended for AI features)
- [ ] **Base44** hosting account with PostgreSQL support
- [ ] **PostgreSQL** database (managed service recommended)
- [ ] **Domain name** (optional, for custom URL)

### Required API Keys (Preserve from Replit)
- [ ] `OPENAI_API_KEY` - OpenAI GPT-4 for AI enhancement services
- [ ] `SESSION_SECRET` - Flask session management
- [ ] `DATABASE_URL` - PostgreSQL connection string
- [ ] `GEONAMES_USERNAME` (optional) - Geographic data enrichment

### Development Tools
- [ ] **Git** - Version control
- [ ] **Python 3.11+** - Application runtime
- [ ] **PostgreSQL client** - Database management
- [ ] **curl/Postman** - API testing

---

## Platform Export Process

### Method 1: Git Repository (Recommended)
```bash
# On Replit Shell
git init
git add .
git commit -m "Initial export from Replit"
git remote add origin https://github.com/yourusername/hailydb.git
git push -u origin main
```

### Method 2: Direct Download
1. **Zip Download**: Use Replit's built-in zip export
2. **SCP Transfer** (for large files):
   ```bash
   scp -r . username@your-local-machine:/path/to/hailydb
   ```

### Method 3: Manual File Copy
- Copy all files except:
  - `.replit` (Replit-specific)
  - `replit.nix` (Nix configuration)
  - `__pycache__/` directories
  - `uv.lock` (Replit package lock)

---

## Cursor IDE Setup

### 1. Install Cursor IDE
- Download from: https://cursor.sh/
- Install Cursor Pro for AI features
- Install Python extension

### 2. Project Setup
```bash
# Clone or open project directory
cd hailydb
cursor .

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Create Requirements File
Create `requirements.txt` from `pyproject.toml`:
```txt
apscheduler>=3.11.0
cachetools>=6.0.0
email-validator>=2.2.0
flask>=3.1.1
flask-dance>=7.1.0
flask-login>=0.6.3
flask-sqlalchemy>=3.1.1
geopy>=2.4.1
gunicorn>=23.0.0
markdown>=3.8.2
oauthlib>=3.3.1
openai>=1.83.0
psycopg2-binary>=2.9.10
pyjwt>=2.10.1
requests>=2.32.3
shapely>=2.1.1
sqlalchemy>=2.0.41
trafilatura>=2.0.0
werkzeug>=3.1.3
```

### 4. Development Configuration
Create `.env` file:
```env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/hailydb_dev

# Flask Configuration  
FLASK_ENV=development
FLASK_DEBUG=True
SESSION_SECRET=your-session-secret-here

# API Keys
OPENAI_API_KEY=your-openai-key-here
GEONAMES_USERNAME=your-geonames-username

# Service URLs (keep as-is)
NWS_ALERT_URL=https://api.weather.gov/alerts/active
SPC_REPORTS_URL=https://www.spc.noaa.gov/climo/reports/
```

### 5. Launch Configuration
Create `.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Flask",
            "type": "python",
            "request": "launch",
            "program": "main.py",
            "env": {
                "FLASK_ENV": "development",
                "FLASK_DEBUG": "1"
            },
            "args": [],
            "console": "integratedTerminal",
            "justMyCode": true
        }
    ]
}
```

---

## Base44 Deployment

### 1. Base44 Account Setup
- Sign up at: https://base44.com/
- Choose plan with PostgreSQL support
- Configure domain (optional)

### 2. Database Setup
```sql
-- Create database
CREATE DATABASE hailydb_production;

-- Create user
CREATE USER hailydb_user WITH ENCRYPTED PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE hailydb_production TO hailydb_user;
```

### 3. Environment Configuration
Base44 environment variables:
```bash
# Production Database
DATABASE_URL=postgresql://hailydb_user:secure_password@your-db-host:5432/hailydb_production

# Flask Configuration
FLASK_ENV=production
SESSION_SECRET=production-session-secret-32-chars-minimum

# API Keys  
OPENAI_API_KEY=your-production-openai-key
GEONAMES_USERNAME=your-geonames-username

# Service Configuration
GUNICORN_WORKERS=4
GUNICORN_TIMEOUT=120
```

### 4. Deployment Configuration
Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app
RUN chown -R app:app /app
USER app

# Expose port
EXPOSE 5000

# Start application
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "main:app"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - FLASK_ENV=production
      - SESSION_SECRET=${SESSION_SECRET}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: unless-stopped
    depends_on:
      - db
      
  db:
    image: postgres:16
    environment:
      - POSTGRES_DB=hailydb_production
      - POSTGRES_USER=hailydb_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

volumes:
  postgres_data:
```

---

## Configuration Changes

### 1. Remove Replit-Specific Code
Remove from `main.py` or `app.py`:
```python
# Remove any Replit-specific imports
# from replit import db  # DELETE
# import replit  # DELETE
```

### 2. Update Database Configuration
Ensure `config.py` uses environment variables:
```python
import os

class Config:
    DATABASE_URL = os.environ.get('DATABASE_URL')
    SECRET_KEY = os.environ.get('SESSION_SECRET')
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    
    # External API URLs (unchanged)
    NWS_ALERT_URL = "https://api.weather.gov/alerts/active"
    SPC_REPORTS_URL = "https://www.spc.noaa.gov/climo/reports/"
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    GEONAMES_API_URL = "http://api.geonames.org"
```

### 3. Static Files Configuration
Ensure Flask serves static files properly:
```python
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
```

### 4. Production Security Settings
```python
# In production configuration
if os.environ.get('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
```

---

## External Dependencies

### API Endpoints Used by HailyDB

#### National Weather Service (NWS)
- **URL**: `https://api.weather.gov/alerts/active`
- **Purpose**: Real-time weather alerts ingestion
- **Authentication**: None required
- **Rate Limit**: ~1000 requests/hour
- **Documentation**: https://www.weather.gov/documentation/services-web-api

#### Storm Prediction Center (SPC)
- **URL**: `https://www.spc.noaa.gov/climo/reports/`
- **Purpose**: Historical storm reports (CSV format)
- **Authentication**: None required
- **Rate Limit**: Reasonable use policy
- **Data Format**: CSV files by date

#### OpenStreetMap Nominatim
- **URL**: `https://nominatim.openstreetmap.org/search`
- **Purpose**: Geographic location lookup
- **Authentication**: None required
- **Rate Limit**: 1 request/second
- **Usage Policy**: https://operations.osmfoundation.org/policies/nominatim/

#### GeoNames API
- **URL**: `http://api.geonames.org`
- **Purpose**: Enhanced geographic data
- **Authentication**: Username required
- **Rate Limit**: 1000 requests/day (free), 30,000/day (premium)
- **Registration**: https://www.geonames.org/login

#### OpenAI API
- **URL**: `https://api.openai.com/v1/`
- **Purpose**: AI enhancement and summarization
- **Authentication**: API key required
- **Models Used**: GPT-4, GPT-4-turbo
- **Rate Limits**: Based on subscription tier

### Service Dependencies
- **PostgreSQL 16+**: Primary database
- **Python 3.11+**: Runtime environment
- **Redis** (optional): Caching layer
- **Nginx** (recommended): Reverse proxy

---

## Testing & Validation

### 1. Local Development Test
```bash
# Start application
python main.py

# Test health endpoint
curl http://localhost:5000/api/health

# Test API endpoints
curl http://localhost:5000/api/alerts
curl http://localhost:5000/api/alerts/radar_detected
```

### 2. Database Migration Verification
```sql
-- Check table count
SELECT COUNT(*) FROM alerts;

-- Verify data integrity
SELECT COUNT(*) FROM spc_reports;
SELECT COUNT(*) FROM hurricane_tracks;

-- Test critical queries
SELECT * FROM alerts WHERE radar_indicated IS NOT NULL LIMIT 5;
```

### 3. Production Deployment Test
```bash
# Test production endpoints
curl https://your-domain.com/api/health
curl https://your-domain.com/api/documentation
curl "https://your-domain.com/api/alerts?limit=10"
```

### 4. Background Service Verification
Monitor logs for:
- Live radar service polling
- SPC data ingestion
- Scheduler execution
- Database operations

---

## Troubleshooting

### Common Migration Issues

#### 1. Database Connection Errors
```bash
# Test database connectivity
psql $DATABASE_URL -c "SELECT version();"

# Check connection string format
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"
```

#### 2. Missing Dependencies
```bash
# Install system packages (Ubuntu/Debian)
sudo apt-get install postgresql-dev libpq-dev python3-dev

# Install Python packages
pip install psycopg2-binary
```

#### 3. Port Conflicts
```bash
# Find processes using port 5000
lsof -i :5000

# Use different port
gunicorn --bind 0.0.0.0:8000 main:app
```

#### 4. Static File Issues
```python
# Ensure static files are served
app = Flask(__name__, static_url_path='/static')

# Or use nginx for static files (production)
location /static/ {
    root /app/;
    expires 1y;
}
```

#### 5. Environment Variable Issues
```bash
# List all environment variables
printenv | grep -E "(DATABASE|FLASK|OPENAI)"

# Load from .env file
source .env
```

### Performance Optimization

#### 1. Database Indexes
```sql
-- Add indexes for common queries
CREATE INDEX idx_alerts_radar_indicated ON alerts USING GIN (radar_indicated);
CREATE INDEX idx_alerts_created_at ON alerts (created_at);
CREATE INDEX idx_alerts_event_type ON alerts (event);
```

#### 2. Gunicorn Configuration
```bash
# Optimal worker count: (2 x CPU cores) + 1
gunicorn --workers 4 --timeout 120 --bind 0.0.0.0:5000 main:app
```

#### 3. Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    location /static/ {
        root /app/;
        expires 1y;
        access_log off;
    }
}
```

---

## Post-Migration Checklist

- [ ] Application starts without errors
- [ ] Database connectivity working
- [ ] All API endpoints responding
- [ ] Background services running
- [ ] Static files loading correctly
- [ ] SSL certificate configured
- [ ] Domain pointing to new server
- [ ] Monitoring & logging configured
- [ ] Backup strategy implemented
- [ ] Performance benchmarks met

---

## Support Resources

### Cursor IDE
- Documentation: https://cursor.sh/docs
- Community: https://cursor.sh/discord

### Base44
- Documentation: https://base44.com/docs
- Support: support@base44.com

### HailyDB
- Issues: Report through your development team
- API Documentation: `/api/documentation` endpoint
- Health Check: `/api/health` endpoint

---

*Last Updated: August 30, 2025*
*Migration Manual Version: 1.0*