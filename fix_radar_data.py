#!/usr/bin/env python3
"""
CRITICAL: Immediate radar data backfill script
Fixes incomplete radar data for client applications
"""
import sys
sys.path.append('.')

from app import app
from models import Alert
from ingest import IngestService

def backfill_radar_data():
    """Backfill radar data for recent alerts"""
    with app.app_context():
        from app import db
        ingest_service = IngestService(db)
        
        # Get recent alerts without radar data
        alerts_without_radar = Alert.query.filter(
            Alert.effective >= '2025-08-15',
            Alert.radar_indicated.is_(None)
        ).all()
        
        print(f'Found {len(alerts_without_radar)} alerts without radar data')
        
        # Also get alerts with radar data to potentially expand
        alerts_with_radar = Alert.query.filter(
            Alert.effective >= '2025-08-15',
            Alert.radar_indicated.is_not(None)
        ).limit(50).all()
        
        print(f'Found {len(alerts_with_radar)} alerts with existing radar data (checking for improvements)')
        
        total_updated = 0
        newly_populated = 0
        enhanced_existing = 0
        
        # Process alerts without radar data
        for alert in alerts_without_radar:
            if alert.properties:
                radar_data = ingest_service._parse_radar_indicated(alert.properties)
                if radar_data:
                    alert.radar_indicated = radar_data
                    newly_populated += 1
                    total_updated += 1
                    
                    print(f"NEW: {alert.event} - Wind: {radar_data.get('wind_mph', 0)} mph, Hail: {radar_data.get('hail_inches', 0)}\"")
        
        # Process existing radar alerts to check for enhancements
        for alert in alerts_with_radar:
            if alert.properties:
                old_radar = alert.radar_indicated or {}
                new_radar = ingest_service._parse_radar_indicated(alert.properties)
                
                if new_radar:
                    # Check if new extraction found more data
                    old_wind = old_radar.get('wind_mph', 0) or 0
                    new_wind = new_radar.get('wind_mph', 0) or 0
                    old_hail = old_radar.get('hail_inches', 0) or 0
                    new_hail = new_radar.get('hail_inches', 0) or 0
                    
                    if new_wind > old_wind or new_hail > old_hail:
                        alert.radar_indicated = new_radar
                        enhanced_existing += 1
                        total_updated += 1
                        
                        print(f"ENHANCED: {alert.event} - Old: {old_wind}mph/{old_hail}\" → New: {new_wind}mph/{new_hail}\"")
        
        if total_updated > 0:
            db.session.commit()
            print(f'\n✅ SUCCESS: Updated {total_updated} alerts')
            print(f'   - {newly_populated} newly populated')
            print(f'   - {enhanced_existing} enhanced existing')
        else:
            print('No updates needed - radar data already complete')
        
        # Verify improvements
        final_count = Alert.query.filter(
            Alert.effective >= '2025-08-15',
            Alert.radar_indicated.is_not(None)
        ).count()
        
        total_recent = Alert.query.filter(Alert.effective >= '2025-08-15').count()
        
        coverage_pct = (final_count / total_recent * 100) if total_recent > 0 else 0
        
        print(f'\n📊 FINAL COVERAGE: {final_count}/{total_recent} ({coverage_pct:.1f}%) alerts have radar data')
        
        return total_updated

if __name__ == '__main__':
    backfill_radar_data()