#!/usr/bin/env python3
"""
SPC Backfill Runner - Guided Historical Data Import
Systematic approach to backfilling SPC data month by month with user confirmation
"""

import logging
import time
from datetime import date, datetime
from spc_backfill import SPCBackfillService

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_august_2025_backfill():
    """Run backfill for August 2025 as requested"""
    
    print("🚀 SPC Historical Data Backfill - August 2025")
    print("=" * 60)
    print("This will backfill all missing SPC data for August 2025")
    print("Each date will be verified before processing to avoid duplicates")
    print("Processing will be respectful with 2-second delays between requests")
    print("=" * 60)
    
    # Confirm execution
    confirm = input("Proceed with August 2025 backfill? (y/N): ").lower().strip()
    if confirm != 'y':
        print("❌ Backfill cancelled")
        return
    
    # Initialize service
    backfill_service = SPCBackfillService()
    
    try:
        # Run August 2025 backfill
        result = backfill_service.backfill_month(2025, 8, delay_seconds=2)
        
        # Display results
        print("\n" + "="*60)
        print("📊 AUGUST 2025 BACKFILL RESULTS")
        print("="*60)
        print(f"Month: {result['month_name']}")
        print(f"Days Processed: {result['days_processed']}")
        print(f"Successful Days: {result['successful_days']}")
        print(f"Failed Days: {result['failed_days']}")
        print(f"Skipped Days: {result['skipped_days']}")
        print(f"Reports Backfilled: {result['reports_backfilled']}")
        print(f"Processing Time: {result['processing_time']:.1f} seconds")
        
        if result['errors']:
            print(f"\n⚠️ Errors ({len(result['errors'])}):")
            for error in result['errors'][:5]:  # Show first 5 errors
                print(f"  - {error['date']}: {error['error']}")
        
        success_rate = (result['successful_days'] / max(result['days_processed'], 1)) * 100
        print(f"\n✅ Success Rate: {success_rate:.1f}%")
        
        # Ask about continuing to July
        if success_rate > 80 and result['successful_days'] > 0:
            print("\n🎯 August backfill completed successfully!")
            continue_july = input("Continue with July 2025 backfill? (y/N): ").lower().strip()
            if continue_july == 'y':
                run_july_2025_backfill()
        else:
            print("\n⚠️  August had issues. Review errors before continuing.")
        
    except KeyboardInterrupt:
        print("\n⏸️  Backfill interrupted by user")
    except Exception as e:
        print(f"\n💥 Backfill failed: {e}")
        logger.error(f"August backfill error: {e}")

def run_july_2025_backfill():
    """Run backfill for July 2025"""
    
    print("\n🚀 SPC Historical Data Backfill - July 2025")
    print("=" * 60)
    
    backfill_service = SPCBackfillService()
    
    try:
        result = backfill_service.backfill_month(2025, 7, delay_seconds=2)
        
        # Display results  
        success_rate = (result['successful_days'] / max(result['days_processed'], 1)) * 100
        
        print("\n📊 JULY 2025 BACKFILL RESULTS")
        print(f"Successful: {result['successful_days']}, Failed: {result['failed_days']}")
        print(f"Reports: {result['reports_backfilled']}, Success Rate: {success_rate:.1f}%")
        
        # Ask about continuing backwards
        if success_rate > 80:
            continue_backwards = input("Continue with June 2025? (y/N): ").lower().strip()
            if continue_backwards == 'y':
                run_systematic_backfill(start_year=2025, start_month=6)
        
    except Exception as e:
        print(f"💥 July backfill failed: {e}")

def run_systematic_backfill(start_year: int = 2025, start_month: int = 6):
    """Run systematic month-by-month backfill going backwards"""
    
    current_year = start_year
    current_month = start_month
    
    backfill_service = SPCBackfillService()
    
    print(f"\n🔄 Starting systematic backfill from {current_month}/{current_year}")
    
    while current_year >= 2020:  # Reasonable historical limit
        try:
            month_date = date(current_year, current_month, 1)
            month_name = month_date.strftime('%B %Y')
            
            print(f"\n📅 Processing {month_name}")
            
            # Quick verification check - if month already complete, skip
            verification = backfill_service._verify_date(month_date)
            if verification['status'] == 'MATCH' and verification['count'] > 0:
                print(f"✅ {month_name} already has data - skipping")
            else:
                result = backfill_service.backfill_month(current_year, current_month, delay_seconds=3)
                
                success_rate = (result['successful_days'] / max(result['days_processed'], 1)) * 100
                print(f"✅ {month_name}: {result['reports_backfilled']} reports, {success_rate:.1f}% success")
                
                # Break if too many failures
                if success_rate < 50 and result['days_processed'] > 5:
                    print(f"⚠️  High failure rate for {month_name} - stopping systematic backfill")
                    break
            
            # Move to previous month
            current_month -= 1
            if current_month == 0:
                current_month = 12
                current_year -= 1
                
            # Pause between months
            time.sleep(5)
            
        except KeyboardInterrupt:
            print("\n⏸️  Systematic backfill interrupted")
            break
        except Exception as e:
            print(f"💥 Error in systematic backfill: {e}")
            break
    
    # Final summary
    summary = backfill_service.get_summary_report()
    print(f"\n🎯 Systematic Backfill Complete!")
    print(f"Total Reports Backfilled: {summary['total_reports_backfilled']}")
    print(f"Total Days Processed: {summary['total_days_processed']}")
    print(f"Overall Success Rate: {summary['success_rate']:.1f}%")

def main():
    """Main execution with menu options"""
    
    print("🌪️  HailyDB SPC Historical Data Backfill Tool")
    print("="*50)
    print("1. August 2025 Backfill (recommended start)")
    print("2. Custom Month Backfill")
    print("3. Custom Date Range Backfill") 
    print("4. Systematic Backfill (month by month)")
    print("5. Exit")
    print("="*50)
    
    choice = input("Select option (1-5): ").strip()
    
    if choice == '1':
        run_august_2025_backfill()
        
    elif choice == '2':
        try:
            year = int(input("Enter year (e.g., 2025): "))
            month = int(input("Enter month (1-12): "))
            
            backfill_service = SPCBackfillService()
            result = backfill_service.backfill_month(year, month)
            print(f"\n✅ {result['month_name']}: {result['reports_backfilled']} reports backfilled")
            
        except ValueError:
            print("❌ Invalid year or month format")
            
    elif choice == '3':
        try:
            start_date = input("Enter start date (YYYY-MM-DD): ")
            end_date = input("Enter end date (YYYY-MM-DD): ")
            
            backfill_service = SPCBackfillService()
            result = backfill_service.backfill_date_range(start_date, end_date)
            print(f"\n✅ Range backfill: {result['reports_backfilled']} reports")
            
        except Exception as e:
            print(f"❌ Date range error: {e}")
            
    elif choice == '4':
        try:
            year = int(input("Starting year (e.g., 2025): "))
            month = int(input("Starting month (1-12): "))
            run_systematic_backfill(year, month)
        except ValueError:
            print("❌ Invalid year or month format")
            
    elif choice == '5':
        print("👋 Exiting backfill tool")
        
    else:
        print("❌ Invalid option selected")

if __name__ == '__main__':
    main()