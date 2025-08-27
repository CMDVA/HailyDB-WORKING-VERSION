#!/bin/bash
# Production Data Import Script
# Run this in your production environment

echo "🔄 Starting HailyDB production data import..."

# Check if production_sync_data.sql exists
if [ ! -f "production_sync_data.sql" ]; then
    echo "❌ production_sync_data.sql not found"
    exit 1
fi

# Backup existing production data (optional but recommended)
echo "📦 Creating backup of existing production data..."
pg_dump $DATABASE_URL > production_backup_$(date +%Y%m%d_%H%M%S).sql

# Import the development data
echo "📥 Importing development data to production..."
psql $DATABASE_URL < production_sync_data.sql

if [ $? -eq 0 ]; then
    echo "✅ Production data sync completed successfully"
    
    # Verify the import
    echo "🔍 Verifying import..."
    psql $DATABASE_URL -c "SELECT COUNT(*) as total_alerts FROM alerts;"
    
    # Test the previously failing alert
    echo "🧪 Testing previously failing alert..."
    psql $DATABASE_URL -c "SELECT id, event FROM alerts WHERE id = 'urn:oid:2.49.0.1.840.0.47199d556c7667ca8d58be1f58db503767724a66.001.1';"
    
else
    echo "❌ Import failed"
    exit 1
fi
