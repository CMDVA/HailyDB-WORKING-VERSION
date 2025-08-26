# HailyDB Database Consolidation Plan

## Current Situation (Aug 26, 2025)
- **Development DB**: 9,310 alerts (complete historical data)
- **Production DB**: 5,771 alerts (missing Aug 11 bulk import)
- **Problem**: Individual alert URLs return 404 in production because alerts don't exist

## Solution: Single Production Database Strategy

### Phase 1: Stop Dual Ingestion (IMMEDIATE)
- Configure development environment to point to production database
- Stop development ingestion to prevent conflicts
- Production becomes single source of truth for new data

### Phase 2: Historical Data Migration (PLANNED)
- Preserve development database as backup (no deletion)
- Create migration script to copy missing 3,539 alerts to production
- Verify data integrity after migration

### Benefits
✅ Fixes production 404 errors immediately
✅ Prevents future data divergence  
✅ Consolidates ingestion to production only
✅ Preserves all existing data
✅ Development remains functional for testing

### Implementation
1. Update development DATABASE_URL to point to production
2. Restart development to use production database
3. Verify individual alert access works
4. Plan historical data migration for complete consolidation

### Safety Measures
- Development database preserved as backup
- No data deletion in any environment
- Incremental verification at each step
- Rollback capability maintained