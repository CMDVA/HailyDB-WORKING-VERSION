#!/usr/bin/env python3
"""
SPC Historical Data Backfill Script for HailyDB
Systematic month-by-month backfill with verification and progress tracking
"""

import logging
import requests
import json
import time
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from calendar import monthrange

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SPCBackfillService:
    """
    Comprehensive SPC historical data backfill service
    Handles month-by-month backfill with verification and progress tracking
    """
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'HailyDB-SPC-Backfill/2.0'
        })
        
        # Progress tracking
        self.total_days_processed = 0
        self.successful_days = 0
        self.failed_days = 0
        self.skipped_days = 0
        self.total_reports_backfilled = 0
        
        # Error tracking
        self.errors = []
        self.failed_dates = []
        
    def backfill_month(self, year: int, month: int, delay_seconds: int = 2) -> Dict:
        """
        Backfill SPC data for an entire month
        
        Args:
            year: Target year (e.g., 2025)
            month: Target month (1-12)
            delay_seconds: Delay between date requests to avoid overwhelming server
            
        Returns:
            Dictionary with backfill results and statistics
        """
        month_name = date(year, month, 1).strftime('%B %Y')
        logger.info(f"🚀 Starting SPC backfill for {month_name}")
        
        # Reset month statistics
        month_stats = {
            'year': year,
            'month': month,
            'month_name': month_name,
            'days_processed': 0,
            'successful_days': 0,
            'failed_days': 0,
            'skipped_days': 0,
            'reports_backfilled': 0,
            'errors': [],
            'processing_time': 0,
            'start_time': datetime.now()
        }
        
        # Get the number of days in this month
        _, days_in_month = monthrange(year, month)
        
        # Process each day in the month
        for day in range(1, days_in_month + 1):
            target_date = date(year, month, day)
            
            try:
                logger.info(f"📅 Processing {target_date.strftime('%Y-%m-%d')} ({day}/{days_in_month})")
                
                # Check if we should process this date (skip future dates)
                if target_date > date.today():
                    logger.info(f"⏭️  Skipping future date: {target_date}")
                    month_stats['skipped_days'] += 1
                    self.skipped_days += 1
                    continue
                
                # First, verify current data status
                verification_result = self._verify_date(target_date)
                
                if verification_result['status'] == 'MATCH' and verification_result['count'] > 0:
                    logger.info(f"✅ {target_date} already has {verification_result['count']} reports - skipping")
                    month_stats['skipped_days'] += 1
                    self.skipped_days += 1
                    continue
                
                # Perform backfill for this date
                backfill_result = self._backfill_single_date(target_date)
                
                if backfill_result['success']:
                    month_stats['successful_days'] += 1
                    month_stats['reports_backfilled'] += backfill_result.get('reports_ingested', 0)
                    self.successful_days += 1
                    self.total_reports_backfilled += backfill_result.get('reports_ingested', 0)
                    
                    logger.info(f"✅ {target_date}: {backfill_result.get('reports_ingested', 0)} reports backfilled")
                else:
                    month_stats['failed_days'] += 1
                    month_stats['errors'].append({
                        'date': target_date.isoformat(),
                        'error': backfill_result.get('error', 'Unknown error')
                    })
                    self.failed_days += 1
                    self.errors.append(f"{target_date}: {backfill_result.get('error', 'Unknown error')}")
                    self.failed_dates.append(target_date)
                    
                    logger.error(f"❌ {target_date}: {backfill_result.get('error', 'Unknown error')}")
                
                month_stats['days_processed'] += 1
                self.total_days_processed += 1
                
                # Progress report every 5 days
                if day % 5 == 0 or day == days_in_month:
                    self._log_progress(month_stats, day, days_in_month)
                
                # Respectful delay between requests
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                
            except KeyboardInterrupt:
                logger.warning("⏸️  Backfill interrupted by user")
                break
            except Exception as e:
                error_msg = f"Unexpected error processing {target_date}: {e}"
                logger.error(f"💥 {error_msg}")
                month_stats['failed_days'] += 1
                month_stats['errors'].append({
                    'date': target_date.isoformat(), 
                    'error': error_msg
                })
                self.failed_days += 1
                self.errors.append(error_msg)
                continue
        
        # Calculate final statistics
        month_stats['processing_time'] = (datetime.now() - month_stats['start_time']).total_seconds()
        
        # Log month completion summary
        self._log_month_summary(month_stats)
        
        return month_stats
    
    def backfill_date_range(self, start_date: str, end_date: str, delay_seconds: int = 2) -> Dict:
        """
        Backfill SPC data for a specific date range
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format  
            delay_seconds: Delay between requests
            
        Returns:
            Backfill results and statistics
        """
        start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        logger.info(f"🚀 Starting SPC backfill from {start_date} to {end_date}")
        
        range_stats = {
            'start_date': start_date,
            'end_date': end_date,
            'total_days': (end_dt - start_dt).days + 1,
            'days_processed': 0,
            'successful_days': 0,
            'failed_days': 0,
            'skipped_days': 0,
            'reports_backfilled': 0,
            'errors': [],
            'start_time': datetime.now()
        }
        
        current_date = start_dt
        while current_date <= end_dt:
            try:
                logger.info(f"📅 Processing {current_date.strftime('%Y-%m-%d')}")
                
                # Skip future dates
                if current_date > date.today():
                    logger.info(f"⏭️  Skipping future date: {current_date}")
                    range_stats['skipped_days'] += 1
                    current_date += timedelta(days=1)
                    continue
                
                # Verify and backfill
                verification = self._verify_date(current_date)
                
                if verification['status'] == 'MATCH' and verification['count'] > 0:
                    logger.info(f"✅ {current_date} already complete - skipping")
                    range_stats['skipped_days'] += 1
                else:
                    backfill_result = self._backfill_single_date(current_date)
                    
                    if backfill_result['success']:
                        range_stats['successful_days'] += 1
                        range_stats['reports_backfilled'] += backfill_result.get('reports_ingested', 0)
                        logger.info(f"✅ {current_date}: {backfill_result.get('reports_ingested', 0)} reports")
                    else:
                        range_stats['failed_days'] += 1
                        range_stats['errors'].append({
                            'date': current_date.isoformat(),
                            'error': backfill_result.get('error', 'Unknown error')
                        })
                        logger.error(f"❌ {current_date}: {backfill_result.get('error')}")
                
                range_stats['days_processed'] += 1
                
                # Delay between requests
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                
            except KeyboardInterrupt:
                logger.warning("⏸️  Backfill interrupted")
                break
            except Exception as e:
                logger.error(f"💥 Error processing {current_date}: {e}")
                range_stats['failed_days'] += 1
                range_stats['errors'].append({
                    'date': current_date.isoformat(),
                    'error': str(e)
                })
            
            current_date += timedelta(days=1)
        
        range_stats['processing_time'] = (datetime.now() - range_stats['start_time']).total_seconds()
        
        logger.info(f"🎯 Date range backfill complete: {range_stats['successful_days']}/{range_stats['days_processed']} successful")
        
        return range_stats
    
    def _verify_date(self, target_date: date) -> Dict:
        """Verify current data status for a date"""
        try:
            url = f"{self.base_url}/spc/verification"
            params = {
                'start_date': target_date.isoformat(),
                'end_date': target_date.isoformat(),
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('results') and len(data['results']) > 0:
                    result = data['results'][0]
                    return {
                        'status': result.get('match_status', 'UNKNOWN'),
                        'count': result.get('hailydb_count', 0),
                        'spc_count': result.get('spc_live_count', 0)
                    }
            
            return {'status': 'ERROR', 'count': 0, 'spc_count': 0}
            
        except Exception as e:
            logger.warning(f"Verification failed for {target_date}: {e}")
            return {'status': 'ERROR', 'count': 0, 'spc_count': 0}
    
    def _backfill_single_date(self, target_date: date) -> Dict:
        """Backfill SPC data for a single date"""
        try:
            url = f"{self.base_url}/internal/spc-reupload/{target_date.isoformat()}"
            
            response = self.session.post(url, timeout=120)  # Extended timeout for data processing
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text[:200]}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _log_progress(self, month_stats: Dict, current_day: int, total_days: int):
        """Log progress for current month"""
        progress_pct = (current_day / total_days) * 100
        logger.info(f"📊 Progress: {current_day}/{total_days} days ({progress_pct:.1f}%) | "
                   f"✅ {month_stats['successful_days']} success | "
                   f"⏭️ {month_stats['skipped_days']} skipped | "
                   f"❌ {month_stats['failed_days']} failed | "
                   f"📈 {month_stats['reports_backfilled']} reports")
    
    def _log_month_summary(self, month_stats: Dict):
        """Log completion summary for month"""
        success_rate = (month_stats['successful_days'] / max(month_stats['days_processed'], 1)) * 100
        
        logger.info(f"🎯 {month_stats['month_name']} COMPLETE:")
        logger.info(f"   📅 Days Processed: {month_stats['days_processed']}")
        logger.info(f"   ✅ Successful: {month_stats['successful_days']} ({success_rate:.1f}%)")
        logger.info(f"   ⏭️ Skipped: {month_stats['skipped_days']}")
        logger.info(f"   ❌ Failed: {month_stats['failed_days']}")
        logger.info(f"   📈 Reports Backfilled: {month_stats['reports_backfilled']}")
        logger.info(f"   ⏱️ Processing Time: {month_stats['processing_time']:.1f} seconds")
        
        if month_stats['errors']:
            logger.warning(f"   ⚠️ {len(month_stats['errors'])} errors occurred")
    
    def get_summary_report(self) -> Dict:
        """Get comprehensive summary of backfill operations"""
        return {
            'total_days_processed': self.total_days_processed,
            'successful_days': self.successful_days,
            'failed_days': self.failed_days,
            'skipped_days': self.skipped_days,
            'success_rate': (self.successful_days / max(self.total_days_processed, 1)) * 100,
            'total_reports_backfilled': self.total_reports_backfilled,
            'error_count': len(self.errors),
            'failed_dates': [d.isoformat() for d in self.failed_dates],
            'errors': self.errors[-10:]  # Last 10 errors for brevity
        }


def main():
    """Main execution function with command line argument support"""
    import argparse
    
    parser = argparse.ArgumentParser(description='SPC Historical Data Backfill Tool')
    parser.add_argument('--month', type=int, help='Target month (1-12)')
    parser.add_argument('--year', type=int, help='Target year (e.g., 2025)')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--delay', type=int, default=2, help='Delay between requests (seconds)')
    parser.add_argument('--base-url', type=str, default='http://localhost:5000', help='HailyDB base URL')
    
    args = parser.parse_args()
    
    # Create backfill service
    backfill_service = SPCBackfillService(base_url=args.base_url)
    
    try:
        if args.month and args.year:
            # Month-based backfill
            logger.info(f"Starting month-based backfill: {args.month}/{args.year}")
            result = backfill_service.backfill_month(args.year, args.month, args.delay)
            
        elif args.start_date and args.end_date:
            # Date range backfill
            logger.info(f"Starting date range backfill: {args.start_date} to {args.end_date}")
            result = backfill_service.backfill_date_range(args.start_date, args.end_date, args.delay)
            
        else:
            # Default: Current month backfill
            current_date = date.today()
            logger.info(f"Starting current month backfill: {current_date.month}/{current_date.year}")
            result = backfill_service.backfill_month(current_date.year, current_date.month, args.delay)
        
        # Print final summary
        summary = backfill_service.get_summary_report()
        print("\n" + "="*60)
        print("📋 BACKFILL SUMMARY REPORT")
        print("="*60)
        print(f"Total Days Processed: {summary['total_days_processed']}")
        print(f"Successful Days: {summary['successful_days']}")
        print(f"Failed Days: {summary['failed_days']}")
        print(f"Skipped Days: {summary['skipped_days']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
        print(f"Total Reports Backfilled: {summary['total_reports_backfilled']}")
        print(f"Errors: {summary['error_count']}")
        
        if summary['failed_dates']:
            print(f"\n❌ Failed Dates: {', '.join(summary['failed_dates'])}")
        
        print("="*60)
        
        return result
        
    except KeyboardInterrupt:
        logger.info("🛑 Backfill interrupted by user")
        summary = backfill_service.get_summary_report()
        print(f"\n⏸️ Partial Summary: {summary['successful_days']} successful, {summary['failed_days']} failed")
        
    except Exception as e:
        logger.error(f"💥 Backfill failed: {e}")
        return None


if __name__ == '__main__':
    main()