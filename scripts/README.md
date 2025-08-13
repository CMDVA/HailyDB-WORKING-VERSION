# HailyDB Scripts and Archives

## Directory Structure

### `/historical_backfill/`
Historical data import scripts (2024 backfills, radar backfill utilities)
- `april_2024.sh`, `feb_2024.sh`, `jan_2024.sh`, `march_2024.sh` - Monthly SPC backfill scripts
- `may_2024_backfill.sh` - Comprehensive May 2024 import
- `launch_backfill.sh` - General backfill launcher
- `radar_backfill.py` - Radar data backfill utility
- `spc_backfill.py`, `spc_backfill_runner.py` - SPC data backfill system

### `/data_samples/`
Sample API responses and test data for development
- `real_alert_response.json` - Sample NWS alert response
- `real_radar_response.json` - Sample radar detection response  
- `real_spc_response.json` - Sample SPC report response
- `real_test_response.json` - Test data sample
- `data_audit_results.json` - Data quality audit results

## Note
These scripts are archived for reference and occasional use. The main application runs autonomously without requiring these utilities for normal operation.