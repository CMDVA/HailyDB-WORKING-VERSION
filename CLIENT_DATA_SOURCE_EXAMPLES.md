# HailyDB Data Source Identification Guide

## Data Source Identifiers Added

All HailyDB API responses now include clear data source identifiers for easy client application filtering:

### SPC Reports (Storm Prediction Center)
```json
{
  "id": "spc-20250820-1318-12345",
  "data_source": "spc",
  "source_type": "report",
  "type": "wind",
  "verified": true,
  "wind_mph": 65,
  "city": "Houston",
  "state": "TX"
}
```

### NWS Alerts (National Weather Service)
```json
{
  "id": "urn:oid:2.49.0.1.840.0.abc123...",
  "data_source": "nws",
  "source_type": "alert",
  "event": "Severe Thunderstorm Warning",
  "areaDesc": "Harris County, TX",
  "radar_indicated": {
    "hail_inches": 1.75,
    "wind_mph": 60
  }
}
```

## Client Application Usage

### JavaScript/TypeScript Example
```javascript
async function getComprehensiveDamageFeed(lat, lon, radiusMiles, startDate, endDate) {
    const [spcResponse, nwsResponse] = await Promise.all([
        fetch(`/api/reports/spc?lat=${lat}&lon=${lon}&radius_mi=${radiusMiles}&start_date=${startDate}&end_date=${endDate}`),
        fetch(`/api/alerts/radar_detected?lat=${lat}&lon=${lon}&radius_mi=${radiusMiles}&start_date=${startDate}&end_date=${endDate}&status=expired`)
    ]);
    
    const [spcData, nwsData] = await Promise.all([
        spcResponse.json(),
        nwsResponse.json()
    ]);
    
    // Combine and filter by data source
    const allEvents = [];
    
    // Add SPC reports
    if (spcData.items) {
        spcData.items.forEach(item => {
            console.log(`SPC Report: ${item.data_source} - ${item.source_type} - ${item.type}`);
            allEvents.push(item);
        });
    }
    
    // Add NWS alerts  
    if (nwsData.features) {
        nwsData.features.forEach(feature => {
            const props = feature.properties;
            console.log(`NWS Alert: ${props.data_source} - ${props.source_type} - ${props.event}`);
            allEvents.push({
                ...props,
                geometry: feature.geometry
            });
        });
    }
    
    // Easy filtering by data source
    const spcOnly = allEvents.filter(event => event.data_source === 'spc');
    const nwsOnly = allEvents.filter(event => event.data_source === 'nws');
    const reportsOnly = allEvents.filter(event => event.source_type === 'report');
    const alertsOnly = allEvents.filter(event => event.source_type === 'alert');
    
    return {
        all: allEvents,
        spc: spcOnly,
        nws: nwsOnly,
        reports: reportsOnly,
        alerts: alertsOnly
    };
}
```

### Python Example
```python
def process_damage_feed(data):
    """Process and categorize damage events by data source"""
    
    spc_reports = []
    nws_alerts = []
    
    # Process SPC reports
    if 'items' in data:
        for item in data['items']:
            if item.get('data_source') == 'spc' and item.get('source_type') == 'report':
                spc_reports.append({
                    'id': item['id'],
                    'type': item['type'],
                    'location': f"{item['city']}, {item['state']}",
                    'magnitude': item.get('wind_mph') or item.get('hail_in'),
                    'verified': item['verified'],
                    'source': 'Storm Prediction Center'
                })
    
    # Process NWS alerts
    if 'features' in data:
        for feature in data['features']:
            props = feature['properties']
            if props.get('data_source') == 'nws' and props.get('source_type') == 'alert':
                nws_alerts.append({
                    'id': props['id'],
                    'event': props['event'],
                    'area': props['areaDesc'],
                    'radar_data': props.get('radar_indicated'),
                    'geometry': feature['geometry'],
                    'source': 'National Weather Service'
                })
    
    return {
        'spc_reports': spc_reports,
        'nws_alerts': nws_alerts,
        'total_events': len(spc_reports) + len(nws_alerts)
    }
```

## Benefits for Client Applications

1. **Easy Data Type Identification**: Every record clearly shows whether it's from SPC or NWS
2. **Source Type Distinction**: Separate "reports" (verified damage) from "alerts" (warnings)  
3. **100% Database Coverage**: All existing records now have these identifiers
4. **No Schema Changes**: Added through model serialization, no database migration needed
5. **Consistent API Responses**: Same field names across all endpoints

## Updated API Endpoints

All these endpoints now include data source identifiers:

- `/api/reports/spc` - All items have `data_source: 'spc'` and `source_type: 'report'`
- `/api/alerts/radar_detected` - All features have `data_source: 'nws'` and `source_type: 'alert'` 
- `/api/alerts/active` - All features have `data_source: 'nws'` and `source_type: 'alert'`
- `/api/alerts/radar_detected/hail` - All features have `data_source: 'nws'` and `source_type: 'alert'`
- `/api/alerts/radar_detected/wind` - All features have `data_source: 'nws'` and `source_type: 'alert'`

This makes it simple for client applications to distinguish between official NWS alerts and verified SPC damage reports in their data processing workflows.