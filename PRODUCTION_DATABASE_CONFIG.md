# Production Database Configuration

## Current Status
- **Main Database**: 9,310+ alerts (complete historical data)
- **Client Applications**: Successfully connected and retrieving data
- **Production Environment**: 5,771 alerts (missing historical data)

## Solution: Single Database Configuration

### Database URL to Use in Production
The complete DATABASE_URL that should be set in production environment to connect to the main database:

```
DATABASE_URL=postgresql://neondb_owner:npg_LRqvaAt5j1uo@ep-cold-dew-adgprhde.c-2.us-east-1.aws.neon.tech/HailyDB_prod?sslmode=require
```

### Configuration Steps
1. In production environment variables, set the DATABASE_URL above
2. Restart production deployment  
3. Production will now access the main database with all 9,310+ alerts
4. All 404 errors for individual alerts will be resolved

### Benefits
- ✅ Immediate fix for production 404 errors
- ✅ No data migration required
- ✅ Client applications continue working unchanged
- ✅ Single source of truth for all environments
- ✅ All historical data immediately available in production

### Verification
After configuration, test the previously failing alert:
```
curl https://api.hailyai.com/api/alerts/urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1
```

Should return alert data instead of 404 error.