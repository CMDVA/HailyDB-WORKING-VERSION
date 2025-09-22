#!/usr/bin/env python3
"""
Test what's inside the IEM historical ZIP file
Work around shapefile dependency issues by examining raw content
"""
import requests
import zipfile
import tempfile
import os
import logging
from io import BytesIO

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Download and examine ZIP contents"""
    logger.info("=== EXAMINING IEM HISTORICAL ZIP CONTENTS ===")
    
    # Download the historical data
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
    
    param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
    url = f"{base_url}?{param_str}"
    
    headers = {
        'User-Agent': 'HailyDB-IEM-Test/1.0 (contact@hailydb.com)',
        'Accept': 'application/zip'
    }
    
    try:
        logger.info("Downloading historical data...")
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        logger.info(f"Downloaded {len(response.content)} bytes")
        
        # Examine ZIP contents
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(BytesIO(response.content)) as zip_file:
                logger.info(f"ZIP contains {len(zip_file.filelist)} files:")
                
                total_uncompressed = 0
                for file_info in zip_file.filelist:
                    logger.info(f"  - {file_info.filename}: {file_info.file_size} bytes")
                    total_uncompressed += file_info.file_size
                
                logger.info(f"Total uncompressed: {total_uncompressed} bytes")
                
                # Extract all files
                zip_file.extractall(temp_dir)
                
                # Look for key files
                extracted_files = os.listdir(temp_dir)
                logger.info(f"Extracted files: {extracted_files}")
                
                # Look for .dbf file (attribute data) 
                dbf_files = [f for f in extracted_files if f.endswith('.dbf')]
                if dbf_files:
                    logger.info(f"Found DBF file: {dbf_files[0]}")
                    dbf_path = os.path.join(temp_dir, dbf_files[0])
                    
                    # Try to read basic DBF structure
                    with open(dbf_path, 'rb') as f:
                        header = f.read(32)
                        logger.info(f"DBF header: {header[:10].hex()}")
                        
                        # DBF structure: bytes 4-7 contain record count
                        if len(header) >= 8:
                            record_count = int.from_bytes(header[4:8], byteorder='little')
                            logger.info(f"📊 DBF contains {record_count} records!")
                
                # Look for text files
                txt_files = [f for f in extracted_files if f.endswith('.txt')]
                if txt_files:
                    logger.info(f"Found text file: {txt_files[0]}")
                    txt_path = os.path.join(temp_dir, txt_files[0])
                    with open(txt_path, 'r') as f:
                        content = f.read(500)
                        logger.info(f"Text content: {content}")
                
                logger.info("✅ Historical data extraction successful!")
                return True
                
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        return False

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)