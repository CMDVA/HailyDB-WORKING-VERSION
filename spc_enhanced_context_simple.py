"""
Simple Enhanced Context generation for SPC reports - bypasses transaction issues
Generates Enhanced Context for ALL SPC reports, not just verified ones
"""

import json
import os
from datetime import datetime
from openai import OpenAI
from models import SPCReport
from app import db

class SimpleEnhancedContext:
    """Simple Enhanced Context generator for immediate testing and backfill"""
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
    
    def generate_for_report(self, report_id: int) -> dict:
        """Generate Enhanced Context for a single SPC report"""
        try:
            # Get the report
            report = db.session.get(SPCReport, report_id)
            if not report:
                return {"success": False, "error": f"Report {report_id} not found"}
            
            # Extract magnitude value from JSON if needed
            magnitude_value = None
            if report.magnitude:
                if isinstance(report.magnitude, dict):
                    if report.report_type.upper() == "WIND" and 'speed' in report.magnitude:
                        magnitude_value = report.magnitude['speed']
                    elif report.report_type.upper() == "HAIL" and 'size_inches' in report.magnitude:
                        magnitude_value = report.magnitude['size_inches']
                else:
                    magnitude_value = report.magnitude
            
            # Format magnitude display
            if report.report_type.upper() == "WIND":
                magnitude_display = f"{int(magnitude_value)} mph" if magnitude_value else "unknown speed"
            elif report.report_type.upper() == "HAIL":
                magnitude_display = f"{magnitude_value:.2f} inch" if magnitude_value else "unknown size"
            else:
                magnitude_display = str(magnitude_value) if magnitude_value else "unknown magnitude"
            
            # Create basic Enhanced Context summary
            enhanced_summary = f"On {report.report_date}, a {report.report_type.lower()} event was reported at {report.location} in {report.county} County, {report.state}. The {report.report_type.lower()} measured {magnitude_display}."
            
            if report.comments:
                enhanced_summary += f" {report.comments}"
            
            # Create Enhanced Context data structure
            enhanced_context = {
                "enhanced_summary": enhanced_summary,
                "version": "v2.0",
                "generated_at": datetime.utcnow().isoformat(),
                "generation_metadata": {
                    "method": "simple_direct",
                    "report_type": report.report_type,
                    "magnitude_value": magnitude_value
                }
            }
            
            # Update the report directly
            report.enhanced_context = enhanced_context
            report.enhanced_context_version = "v2.0"
            report.enhanced_context_generated_at = datetime.utcnow()
            
            db.session.commit()
            
            return {
                "success": True,
                "report_id": report_id,
                "enhanced_context": enhanced_context
            }
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    def backfill_all_reports(self, batch_size: int = 100) -> dict:
        """Backfill Enhanced Context for all SPC reports missing it"""
        try:
            # Count total reports needing Enhanced Context
            total_reports = db.session.query(SPCReport).filter(
                (SPCReport.enhanced_context_version != "v2.0") |
                (SPCReport.enhanced_context_version.is_(None))
            ).count()
            
            processed = 0
            successful = 0
            errors = 0
            
            print(f"Starting backfill for {total_reports} SPC reports...")
            
            while processed < total_reports:
                # Get next batch
                reports = db.session.query(SPCReport).filter(
                    (SPCReport.enhanced_context_version != "v2.0") |
                    (SPCReport.enhanced_context_version.is_(None))
                ).limit(batch_size).all()
                
                if not reports:
                    break
                
                for report in reports:
                    result = self.generate_for_report(report.id)
                    if result["success"]:
                        successful += 1
                    else:
                        errors += 1
                        print(f"Error processing report {report.id}: {result['error']}")
                    
                    processed += 1
                    
                    if processed % 50 == 0:
                        print(f"Progress: {processed}/{total_reports} ({successful} successful, {errors} errors)")
            
            return {
                "success": True,
                "total_reports": total_reports,
                "processed": processed,
                "successful": successful,
                "errors": errors
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

def generate_enhanced_context_for_report(report_id: int) -> dict:
    """Standalone function to generate Enhanced Context for a single report"""
    service = SimpleEnhancedContext()
    return service.generate_for_report(report_id)

def backfill_all_enhanced_context(batch_size: int = 100) -> dict:
    """Standalone function to backfill Enhanced Context for all reports"""
    service = SimpleEnhancedContext()
    return service.backfill_all_reports(batch_size)