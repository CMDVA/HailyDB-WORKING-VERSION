#!/usr/bin/env python3
"""
Comprehensive NWS Alert Ingestion Script
Maximizes alert collection from all available NWS endpoints
"""

import logging
import requests
import time
from datetime import datetime, timedelta
from app import app, db
from models import Alert, IngestionLog
from ingest import IngestService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ComprehensiveIngestService:
    """Enhanced ingestion service to maximize NWS alert collection"""
    
    def __init__(self):
        self.base_service = IngestService(db)
        self.headers = {
            'User-Agent': 'HailyDB-Comprehensive-Ingestion/2.0 (contact@hailydb.com)',
            'Accept': 'application/geo+json'
        }
        
    def ingest_all_available_alerts(self):
        """Comprehensive ingestion from multiple NWS endpoints"""
        total_new = 0
        total_updated = 0
        
        # Endpoint configurations for maximum coverage
        endpoints = [
            {
                'name': 'All Alerts (No Status Filter)', 
                'url': 'https://api.weather.gov/alerts',
                'params': {'limit': 500}
            },
            {
                'name': 'All Actual Alerts', 
                'url': 'https://api.weather.gov/alerts',
                'params': {'status': 'actual', 'limit': 500}
            },
            {
                'name': 'All Test Alerts', 
                'url': 'https://api.weather.gov/alerts',
                'params': {'status': 'test', 'limit': 500}
            },
            {
                'name': 'All Draft Alerts', 
                'url': 'https://api.weather.gov/alerts',
                'params': {'status': 'draft', 'limit': 500}
            },
            {
                'name': 'Recent 7 Days', 
                'url': 'https://api.weather.gov/alerts',
                'params': {
                    'start': (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z',
                    'limit': 500
                }
            },
            {
                'name': 'Recent 30 Days', 
                'url': 'https://api.weather.gov/alerts',
                'params': {
                    'start': (datetime.utcnow() - timedelta(days=30)).isoformat() + 'Z',
                    'limit': 500
                }
            }
        ]
        
        for endpoint_config in endpoints:
            logger.info(f"Ingesting from: {endpoint_config['name']}")
            try:
                new_count, updated_count = self._ingest_from_endpoint(
                    endpoint_config['url'], 
                    endpoint_config['params']
                )
                total_new += new_count
                total_updated += updated_count
                logger.info(f"  Results: {new_count} new, {updated_count} updated")
                
                # Brief delay between endpoints to be respectful
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error ingesting from {endpoint_config['name']}: {e}")
                continue
        
        logger.info(f"Comprehensive ingestion complete: {total_new} total new, {total_updated} total updated")
        return total_new, total_updated
    
    def _ingest_from_endpoint(self, base_url, params):
        """Ingest all alerts from a specific endpoint with pagination"""
        new_count = 0
        updated_count = 0
        page_count = 0
        
        # Start with base URL and parameters
        url = base_url
        first_request = True
        
        while url:
            try:
                # Add parameters only on first request
                if first_request:
                    response = requests.get(url, params=params, headers=self.headers, timeout=45)
                    first_request = False
                else:
                    response = requests.get(url, headers=self.headers, timeout=45)
                
                response.raise_for_status()
                data = response.json()
                
                features = data.get('features', [])
                page_count += 1
                
                if not features:
                    logger.info(f"    Page {page_count}: No features found, stopping pagination")
                    break
                
                logger.info(f"    Page {page_count}: Processing {len(features)} alerts")
                
                # Process alerts in batches using existing service
                page_new, page_updated = self._process_alert_batch(features)
                new_count += page_new
                updated_count += page_updated
                
                # Handle pagination
                pagination = data.get('pagination', {})
                url = pagination.get('next')
                
                if not url:
                    logger.info(f"    Completed after {page_count} pages")
                    break
                    
                # Respectful delay between pages
                time.sleep(1)
                
            except requests.RequestException as e:
                logger.error(f"    HTTP error on page {page_count}: {e}")
                break
            except Exception as e:
                logger.error(f"    Processing error on page {page_count}: {e}")
                break
        
        return new_count, updated_count
    
    def _process_alert_batch(self, features):
        """Process a batch of alert features"""
        new_count = 0
        updated_count = 0
        
        for feature in features:
            try:
                result = self.base_service._process_alert_feature(feature)
                if result == 'new':
                    new_count += 1
                elif result == 'updated':
                    updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to process alert feature: {e}")
                continue
        
        # Commit this batch
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f"Error committing batch: {e}")
            db.session.rollback()
        
        return new_count, updated_count

def main():
    """Main execution function"""
    with app.app_context():
        logger.info("Starting comprehensive NWS alert ingestion")
        
        # Get baseline count
        initial_count = db.session.query(Alert).count()
        logger.info(f"Initial alert count: {initial_count}")
        
        # Run comprehensive ingestion
        service = ComprehensiveIngestService()
        new_count, updated_count = service.ingest_all_available_alerts()
        
        # Get final count
        final_count = db.session.query(Alert).count()
        logger.info(f"Final alert count: {final_count}")
        logger.info(f"Net increase: {final_count - initial_count} alerts")
        
        return new_count, updated_count

if __name__ == '__main__':
    main()