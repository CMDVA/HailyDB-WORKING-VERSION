# HailyDB API Integration Guide

A comprehensive guide for integrating external applications with HailyDB's enhanced weather alert intelligence platform.

## Overview

HailyDB provides real-time National Weather Service (NWS) alert data enriched with AI analysis, radar-indicated measurements, SPC verification, and comprehensive geometry processing. This guide demonstrates how to leverage HailyDB's API for insurance claims, field operations, emergency management, and partner integrations.

## Core API Endpoints

### 1. Alert Search and Retrieval

#### Get Recent Alerts
```bash
curl "https://your-hailydb.com/api/alerts/search?limit=50&active_only=true"
```

#### Search by Location
```bash
curl "https://your-hailydb.com/api/alerts/search?state=TX&county=Harris&limit=25"
```

#### Filter by Event Type and Severity
```bash
curl "https://your-hailydb.com/api/alerts/search?event_type=Tornado%20Warning&severity=Extreme&limit=10"
```

#### Get Specific Alert Details
```bash
curl "https://your-hailydb.com/api/alerts/{alert_id}"
```

### 2. Real-Time Webhook Integration

#### Register Webhook for Hail Events
```bash
curl -X POST "https://your-hailydb.com/internal/webhook-rules" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://your-app.com/webhooks/hail-alerts",
    "event_type": "hail",
    "threshold_value": 1.0,
    "location_filter": "TX",
    "user_id": "your_user_id"
  }'
```

#### Register Webhook for Wind Events
```bash
curl -X POST "https://your-hailydb.com/internal/webhook-rules" \
  -H "Content-Type: application/json" \
  -d '{
    "webhook_url": "https://your-app.com/webhooks/wind-alerts", 
    "event_type": "wind",
    "threshold_value": 60,
    "location_filter": "OK",
    "user_id": "your_user_id"
  }'
```

#### List Active Webhook Rules
```bash
curl "https://your-hailydb.com/internal/webhook-rules"
```

#### Delete Webhook Rule
```bash
curl -X DELETE "https://your-hailydb.com/internal/webhook-rules/{rule_id}"
```

## Enhanced Data Structure

### Alert Response Format

```json
{
  "id": "urn:oid:2.49.0.1.840.0...",
  "event": "Severe Thunderstorm Warning",
  "severity": "Moderate",
  "area_desc": "Harris, TX; Montgomery, TX",
  "effective": "2025-06-10T20:15:00Z",
  "expires": "2025-06-10T21:00:00Z",
  "sent": "2025-06-10T20:14:32Z",
  
  "radar_indicated": {
    "hail_inches": 1.25,
    "wind_mph": 70
  },
  
  "fips_codes": ["48201", "48339"],
  "county_names": [
    {"county": "Harris", "state": "TX"},
    {"county": "Montgomery", "state": "TX"}
  ],
  "geometry_type": "Polygon",
  "coordinate_count": 156,
  "affected_states": ["TX"],
  "geometry_bounds": {
    "min_lat": 30.1234,
    "max_lat": 30.5678,
    "min_lon": -95.9876,
    "max_lon": -95.5432
  },
  
  "spc_verified": true,
  "spc_reports": [
    {
      "type": "hail",
      "size": 1.25,
      "location": "Spring, TX",
      "time": "20:22Z"
    }
  ],
  "spc_confidence_score": 0.89,
  
  "enhanced_geometry": {
    "has_detailed_geometry": true,
    "coverage_area_sq_degrees": 0.125,
    "county_state_mapping": [...],
    "affected_states": ["TX"]
  },
  
  "ai_summary": "Severe thunderstorm with quarter-size hail and 70 mph winds affecting northwestern Harris County and southern Montgomery County.",
  "ai_tags": ["hail", "damaging_winds", "property_damage_risk"]
}
```

## Integration Examples

### 1. Insurance Claims Processing

```python
import requests
import json
from datetime import datetime, timedelta

class InsuranceClaimsBot:
    def __init__(self, hailydb_base_url, webhook_url):
        self.base_url = hailydb_base_url
        self.webhook_url = webhook_url
        self.setup_hail_monitoring()
    
    def setup_hail_monitoring(self):
        """Register webhook for hail events affecting coverage areas"""
        webhook_config = {
            "webhook_url": f"{self.webhook_url}/hail-events",
            "event_type": "hail", 
            "threshold_value": 0.75,  # 3/4 inch or larger
            "user_id": "insurance_bot"
        }
        
        response = requests.post(
            f"{self.base_url}/internal/webhook-rules",
            json=webhook_config
        )
        print(f"Hail monitoring active: {response.status_code}")
    
    def process_hail_alert(self, alert_data):
        """Process incoming hail alert for claims preparation"""
        radar_indicated = alert_data.get('radar_indicated', {})
        hail_size = radar_indicated.get('hail_inches', 0)
        
        if hail_size >= 1.0:  # Quarter size or larger
            self.create_potential_claim_area(alert_data)
            self.notify_field_adjusters(alert_data)
    
    def create_potential_claim_area(self, alert_data):
        """Create coverage area for potential claims"""
        bounds = alert_data.get('geometry_bounds', {})
        county_names = alert_data.get('county_names', [])
        
        claim_area = {
            "event_id": alert_data['id'],
            "event_type": alert_data['event'],
            "hail_size": alert_data['radar_indicated']['hail_inches'],
            "affected_counties": [f"{c['county']}, {c['state']}" for c in county_names],
            "coverage_bounds": bounds,
            "estimated_properties": self.estimate_property_count(bounds),
            "severity_level": self.classify_damage_potential(alert_data)
        }
        
        return claim_area
    
    def estimate_property_count(self, bounds):
        """Estimate property count in affected area"""
        if not bounds:
            return 0
        
        area_sq_degrees = (bounds['max_lat'] - bounds['min_lat']) * \
                         (bounds['max_lon'] - bounds['min_lon'])
        
        # Rough estimate: ~1000 properties per 0.01 sq degrees in suburban areas
        return int(area_sq_degrees * 100000)
```

### 2. Field Operations Dispatch

```javascript
class FieldOperationsManager {
    constructor(hailydbBaseUrl, apiKey) {
        this.baseUrl = hailydbBaseUrl;
        this.apiKey = apiKey;
        this.setupWindMonitoring();
    }
    
    async setupWindMonitoring() {
        // Monitor for damaging wind events
        const webhookConfig = {
            webhook_url: `${this.baseUrl}/webhooks/wind-damage`,
            event_type: "wind",
            threshold_value: 58, // Damaging wind threshold
            user_id: "field_ops"
        };
        
        const response = await fetch(`${this.baseUrl}/internal/webhook-rules`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.apiKey}`
            },
            body: JSON.stringify(webhookConfig)
        });
        
        console.log('Wind monitoring active:', response.status);
    }
    
    async processWindAlert(alertData) {
        const radarIndicated = alertData.radar_indicated || {};
        const windSpeed = radarIndicated.wind_mph || 0;
        
        if (windSpeed >= 58) {
            await this.dispatchFieldTeams(alertData);
            await this.prepareEmergencyResponse(alertData);
        }
    }
    
    async dispatchFieldTeams(alertData) {
        const affectedCounties = alertData.county_names || [];
        const geometryBounds = alertData.geometry_bounds;
        
        const dispatchPlan = {
            alert_id: alertData.id,
            event_type: alertData.event,
            wind_speed: alertData.radar_indicated.wind_mph,
            deployment_areas: affectedCounties,
            priority_zones: this.calculatePriorityZones(geometryBounds),
            estimated_response_time: this.calculateResponseTime(affectedCounties)
        };
        
        // Dispatch to field management system
        return this.sendToFieldManagement(dispatchPlan);
    }
    
    calculatePriorityZones(bounds) {
        if (!bounds) return [];
        
        const centerLat = (bounds.max_lat + bounds.min_lat) / 2;
        const centerLon = (bounds.max_lon + bounds.min_lon) / 2;
        
        return [
            { lat: centerLat, lon: centerLon, priority: 'high', radius_miles: 5 },
            { lat: centerLat, lon: centerLon, priority: 'medium', radius_miles: 15 }
        ];
    }
}
```

### 3. Emergency Management Integration

```python
class EmergencyManagementBot:
    def __init__(self, hailydb_url):
        self.hailydb_url = hailydb_url
        self.setup_tornado_monitoring()
    
    def setup_tornado_monitoring(self):
        """Setup monitoring for tornado warnings"""
        webhook_config = {
            "webhook_url": f"{self.hailydb_url}/emergency/tornado-alerts",
            "event_type": "damage_probability", 
            "threshold_value": 0.7,  # High damage probability
            "user_id": "emergency_mgmt"
        }
        
        requests.post(f"{self.hailydb_url}/internal/webhook-rules", json=webhook_config)
    
    def get_active_severe_weather(self):
        """Get all active severe weather alerts"""
        params = {
            'active_only': 'true',
            'event_type': 'Tornado Warning,Severe Thunderstorm Warning',
            'limit': 100
        }
        
        response = requests.get(f"{self.hailydb_url}/api/alerts/search", params=params)
        return response.json()
    
    def analyze_threat_level(self, alert):
        """Analyze threat level based on radar indicated data"""
        radar_data = alert.get('radar_indicated', {})
        
        threat_score = 0
        if radar_data.get('hail_inches', 0) >= 2.0:  # Golf ball or larger
            threat_score += 3
        elif radar_data.get('hail_inches', 0) >= 1.0:  # Quarter or larger  
            threat_score += 2
            
        if radar_data.get('wind_mph', 0) >= 80:  # Hurricane force
            threat_score += 3
        elif radar_data.get('wind_mph', 0) >= 58:  # Damaging winds
            threat_score += 2
            
        spc_confidence = alert.get('spc_confidence_score', 0)
        if spc_confidence >= 0.8:
            threat_score += 1
            
        return min(threat_score, 5)  # Max threat level of 5
```

## Webhook Payload Examples

### Hail Event Webhook
```json
{
  "webhook_rule_id": 123,
  "trigger_type": "hail",
  "trigger_value": 1.25,
  "threshold_met": true,
  "alert": {
    "id": "urn:oid:2.49.0.1.840.0...",
    "event": "Severe Thunderstorm Warning",
    "radar_indicated": {
      "hail_inches": 1.25,
      "wind_mph": 65
    },
    "county_names": [
      {"county": "Harris", "state": "TX"}
    ],
    "geometry_bounds": {
      "min_lat": 29.7,
      "max_lat": 30.1,
      "min_lon": -95.8,
      "max_lon": -95.3
    },
    "effective": "2025-06-10T20:15:00Z",
    "expires": "2025-06-10T21:00:00Z"
  },
  "timestamp": "2025-06-10T20:15:30Z"
}
```

### Wind Event Webhook
```json
{
  "webhook_rule_id": 124,
  "trigger_type": "wind", 
  "trigger_value": 70,
  "threshold_met": true,
  "alert": {
    "id": "urn:oid:2.49.0.1.840.0...",
    "event": "Severe Thunderstorm Warning",
    "radar_indicated": {
      "wind_mph": 70,
      "hail_inches": 0.88
    },
    "affected_states": ["OK"],
    "spc_verified": true,
    "spc_confidence_score": 0.92
  },
  "timestamp": "2025-06-10T20:16:45Z"
}
```

## Data Processing Tips

### 1. Radar-Indicated Intelligence
- `radar_indicated.hail_inches`: Direct measurement from radar analysis
- `radar_indicated.wind_mph`: Estimated wind speeds from radar returns
- Only present for Severe Thunderstorm Warnings with parseable radar data
- Success rate ~1.8% due to specific NWS text formatting requirements

### 2. Geometry Processing
- `geometry_type`: Polygon, MultiPolygon, or Point classification
- `coordinate_count`: Complexity indicator for coverage analysis  
- `geometry_bounds`: Bounding box for quick spatial queries
- `coverage_area_sq_degrees`: Calculated coverage area

### 3. SPC Verification
- `spc_verified`: Boolean indicating Storm Prediction Center confirmation
- `spc_reports`: Array of actual storm reports matching the alert
- `spc_confidence_score`: 0.0-1.0 confidence in verification accuracy
- `spc_match_method`: "fips", "latlon", or "none"

## Rate Limits and Best Practices

### API Rate Limits
- Search endpoints: 100 requests/minute
- Webhook management: 20 requests/minute  
- Individual alert retrieval: 200 requests/minute

### Webhook Best Practices
- Implement exponential backoff for failed deliveries
- Respond with HTTP 200 within 10 seconds
- Process webhooks asynchronously to avoid timeouts
- Validate webhook signatures for security

### Polling Alternatives
Instead of polling, use webhooks for real-time notifications:

```python
# Don't do this - inefficient polling
while True:
    alerts = get_recent_alerts()
    process_alerts(alerts)
    time.sleep(60)  # Poll every minute

# Do this - efficient webhook processing  
@app.route('/webhook/alerts', methods=['POST'])
def handle_alert_webhook():
    alert_data = request.json
    process_alert_async(alert_data['alert'])
    return '', 200
```

## Error Handling

### Common HTTP Status Codes
- `200`: Success
- `400`: Bad Request - Invalid parameters
- `404`: Alert/Resource not found
- `429`: Rate limit exceeded
- `500`: Server error

### Example Error Response
```json
{
  "status": "error",
  "message": "Invalid event_type parameter",
  "code": "INVALID_PARAMETER",
  "details": {
    "parameter": "event_type",
    "allowed_values": ["hail", "wind", "damage_probability"]
  }
}
```

## Support and Resources

### API Documentation
- Base URL: `https://your-hailydb.com`
- API Version: v2.0 (with enhanced geometry processing)
- Response Format: JSON
- Authentication: API key via Authorization header

### Contact Information
- Technical Support: [Contact your HailyDB administrator]
- API Status: [Status page URL]
- Documentation Updates: [Documentation repository]

---

*This guide covers HailyDB's enhanced API capabilities including radar-indicated parsing, real-time webhooks, and comprehensive geometry processing for insurance, field operations, and emergency management applications.*