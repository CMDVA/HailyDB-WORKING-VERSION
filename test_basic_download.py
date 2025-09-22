#!/usr/bin/env python3
"""
Test basic IEM historical data download without shapefile processing
Just verify we can download the ZIP and check its size
"""
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test basic IEM download for September 2024 Florida"""
    logger.info("=== TESTING BASIC IEM HISTORICAL DATA DOWNLOAD ===")
    
    # Build URL for Sep 2024 Florida
    base_url = "https://mesonet.agron.iastate.edu/cgi-bin/request/gis/watchwarn.py"
    params = {
        'location_group': 'states',
        'states': 'FL',
        'sts': '2024-09-01T00:00Z',
        'ets': '2024-09-30T23:59Z',
        'accept': 'shapefile',
        'limit1': 'yes',
        'limitps': 'yes'
    }
    
    # Build URL
    param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
    url = f"{base_url}?{param_str}"
    
    logger.info(f"Downloading from: {url}")
    
    headers = {
        'User-Agent': 'HailyDB-IEM-Test/1.0 (contact@hailydb.com)',
        'Accept': 'application/zip'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Content-Type: {response.headers.get('content-type')}")
        logger.info(f"Content-Length: {response.headers.get('content-length')}")
        logger.info(f"Content-Disposition: {response.headers.get('content-disposition')}")
        logger.info(f"Downloaded {len(response.content)} bytes")
        
        if len(response.content) > 1000:
            logger.info(f"✅ Successfully downloaded ZIP file with historical data!")
            logger.info(f"File size: {len(response.content):,} bytes")
            
            # Try to detect if it's a valid ZIP
            if response.content.startswith(b'PK'):
                logger.info("✅ File appears to be a valid ZIP archive")
            else:
                logger.warning("❌ File does not appear to be a ZIP archive")
                logger.info(f"First 100 bytes: {response.content[:100]}")
            
            return True
        else:
            logger.error(f"❌ File too small: {len(response.content)} bytes")
            logger.info(f"Response content: {response.content}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)