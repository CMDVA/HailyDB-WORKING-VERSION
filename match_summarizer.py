"""
AI-Powered Alert Match Summarizer
Generates intelligent summaries combining NWS alerts with confirmed SPC reports
Using official NWS/NOAA terminology and threat classifications
"""

import os
import json
import re
from datetime import datetime
from typing import Dict, List, Optional
from openai import OpenAI

class MatchSummarizer:
    """
    AI service for generating enhanced summaries of verified alert matches
    Combines NWS alert data with SPC confirmation reports and geographical context
    Converts future-tense warnings into past-tense verified events using official NWS terminology
    """
    
    def __init__(self):
        self.openai = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        
        # NWS Official Hail Size Chart
        self.hail_size_chart = {
            'pea': 0.25, 'peanut': 0.5, 'penny': 0.75, 'nickel': 0.88, 'quarter': 1.0,
            'half dollar': 1.25, 'ping pong ball': 1.5, 'golf ball': 1.75, 'egg': 2.0,
            'tennis ball': 2.5, 'baseball': 2.75, 'large apple': 3.0, 'softball': 4.0,
            'grapefruit': 4.5
        }
    
    def generate_match_summary(self, alert: Dict, spc_reports: List[Dict]) -> Optional[str]:
        """
        Generate AI summary of NWS alert verified by SPC reports
        Converts future tense warnings to past tense verified events using official NWS terminology
        
        Args:
            alert: NWS alert data dictionary
            spc_reports: List of matching SPC report dictionaries
        
        Returns:
            Generated summary string or None if generation fails
        """
        try:
            # Build comprehensive verification prompt with all data integration
            prompt = self._build_verification_prompt(alert, spc_reports)
            
            response = self.openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a professional television meteorologist writing a factual weather report about verified storm events. Write like a seasoned TV weatherman reporting on what actually happened during a confirmed severe weather event.

WRITING STYLE REQUIREMENTS:
1. Write as a factual historical report - NO threat classifications or warning language
2. Start with the National Weather Service alert and what radar initially detected  
3. Then describe what was actually verified by storm spotters and damage reports
4. Use the verified SPC magnitude as the authoritative measurement (this overrides radar estimates)
5. Convert predicted impacts to confirmed damage potential in surrounding areas
6. Include specific locations, times, and radar parameters from the original alert
7. Write in past tense as a completed weather event story

STRUCTURE: "At {time} in {location}, the National Weather Service issued a {alert type} when radar detected {radar parameters}. Storm spotters subsequently verified {actual verified measurements} with {specific damage details if any}. This confirms that {impact assessment} occurred in the immediate area."

Make it sound like a professional weather report you'd hear on the evening news about a storm that already happened."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=400,
                temperature=0.2  # Lower temperature for factual consistency
            )
            
            return response.choices[0].message.content.strip() if response.choices[0].message.content else None
            
        except Exception as e:
            print(f"Error generating match summary: {e}")
            import traceback
            traceback.print_exc()
            
            # Create a fallback summary without OpenAI when quota is exceeded
            if "insufficient_quota" in str(e) or "quota" in str(e).lower():
                return self._generate_fallback_summary(alert, spc_reports)
            
            return None
    
    def _generate_fallback_summary(self, alert: Dict, spc_reports: List[Dict]) -> str:
        """
        Generate a professional meteorological summary when AI is unavailable
        Uses official NWS terminology and threat classifications - NO insurance references
        """
        # Extract core information
        event = alert.get('event', 'Weather Event')
        area_desc = alert.get('area_desc', 'Unknown Area')
        effective = alert.get('effective', 'Unknown Time')
        
        # Process damage reports with official classifications
        damage_data = []
        max_hail = 0.0
        max_wind = 0.0
        
        for report in spc_reports:
            report_type = report.get('report_type', '').lower()
            magnitude = report.get('magnitude', {})
            location = report.get('location', '')
            time_utc = report.get('time_utc', '')
            comments = report.get('comments', '')
            
            if report_type == 'hail':
                hail_size = 0.0
                if isinstance(magnitude, dict):
                    hail_size = magnitude.get('size_inches', 0.0) or magnitude.get('hail_inches', 0.0)
                elif isinstance(magnitude, (int, float)):
                    hail_size = float(magnitude)
                
                if hail_size > 0:
                    max_hail = max(max_hail, hail_size)
                    damage_data.append({
                        'type': 'hail',
                        'magnitude': hail_size,
                        'common_name': self._get_hail_common_name(hail_size),
                        'threat_level': self._map_hail_threat_level(hail_size),
                        'location': location,
                        'time': time_utc,
                        'details': comments
                    })
            
            elif report_type == 'wind':
                wind_speed = 0.0
                if isinstance(magnitude, dict):
                    wind_speed = magnitude.get('wind_mph', 0.0) or magnitude.get('speed_mph', 0.0)
                elif isinstance(magnitude, (int, float)):
                    wind_speed = float(magnitude)
                elif comments:
                    # Extract from comments
                    import re
                    wind_match = re.search(r'(\d+)\s*mph', comments)
                    if wind_match:
                        wind_speed = float(wind_match.group(1))
                
                if wind_speed > 0:
                    max_wind = max(max_wind, wind_speed)
                    damage_data.append({
                        'type': 'wind',
                        'magnitude': wind_speed,
                        'threat_level': self._map_wind_threat_level(wind_speed),
                        'location': location,
                        'time': time_utc,
                        'details': comments
                    })
        
        # Extract radar information from original alert
        radar_data = self._extract_radar_parameters(alert)
        
        # Build weatherman-style report
        summary_parts = []
        
        # Start with radar detection
        if radar_data['hazard_text']:
            summary_parts.append(f"At {effective} in {area_desc}, the National Weather Service issued a {event} when radar detected {radar_data['hazard_text'].lower()}.")
        else:
            summary_parts.append(f"At {effective} in {area_desc}, the National Weather Service issued a {event}.")
        
        # Add verified reports
        if damage_data:
            verification_details = []
            for data in damage_data:
                if data['type'] == 'hail':
                    verification_details.append(f"{data['magnitude']}\" hail ({data['common_name']})")
                else:
                    verification_details.append(f"{data['magnitude']} mph winds")
            
            # Determine the source description from SPC comments
            source_info = self._extract_source_description(damage_data)
            summary_parts.append(f"{source_info} subsequently verified {', '.join(verification_details)} in the area.")
            
            # Add damage details if available
            damage_comments = [data['details'] for data in damage_data if data['details']]
            if damage_comments:
                summary_parts.append(f"Damage reports included: {damage_comments[0][:100]}.")
        
        # Convert predicted impact to confirmed assessment
        if radar_data['impact_text']:
            # Convert future tense impact to past tense confirmed potential  
            impact_text = radar_data['impact_text'].lower()
            if 'expect damage' in impact_text:
                impact_text = impact_text.replace('expect damage', 'damage potential')
                summary_parts.append(f"This confirmed {impact_text} in the immediate area.")
            elif 'expect' in impact_text:
                impact_text = impact_text.replace('expect', '')
                summary_parts.append(f"This confirmed{impact_text} in the immediate area.")
            else:
                summary_parts.append(f"This confirmed {impact_text} in the immediate area.")
        else:
            # Fallback damage assessment
            damage_potential = []
            if max_hail >= 1.0:
                damage_potential.append("damage to roofing materials and vehicles")
            if max_wind >= 58:
                damage_potential.append("tree damage and structural impact")
            
            if damage_potential:
                summary_parts.append(f"This confirms that {', '.join(damage_potential)} occurred in the immediate area.")
        
        # Add geographic context if multiple locations
        if len(damage_data) > 1:
            locations = [data['location'] for data in damage_data if data['location']]
            if locations:
                unique_locations = list(set(locations))
                summary_parts.append(f"Verification came from {len(unique_locations)} locations including {', '.join(unique_locations[:2])}.")
        
        return ' '.join(summary_parts)
    
    def _map_hail_threat_level(self, hail_size: float) -> str:
        """Map hail size to official NWS threat level"""
        if hail_size >= 2.75:
            return "Extreme Threat"  # Giant Hail
        elif hail_size >= 1.75:
            return "High Threat"     # Very Large Hail
        elif hail_size >= 1.0:
            return "Moderate Threat" # Significant Hail
        elif hail_size >= 0.75:
            return "Low Threat"
        elif hail_size > 0:
            return "Very Low Threat"
        else:
            return "Non-Threatening"
    
    def _map_wind_threat_level(self, wind_speed: float) -> str:
        """Map wind speed to official NWS threat level"""
        if wind_speed >= 92:
            return "Extreme Threat"  # Violent Wind Gusts
        elif wind_speed >= 75:
            return "High Threat"     # Very Damaging Wind Gusts
        elif wind_speed >= 58:
            return "Moderate Threat" # Damaging Wind Gusts
        elif wind_speed >= 39:
            return "Low Threat"      # Strong Wind Gusts
        elif wind_speed > 0:
            return "Very Low Threat"
        else:
            return "Non-Threatening"
    
    def _get_hail_common_name(self, hail_size: float) -> str:
        """Get common size equivalent for hail"""
        if hail_size >= 4.5:
            return "grapefruit size"
        elif hail_size >= 4.0:
            return "softball size"
        elif hail_size >= 2.75:
            return "baseball size"
        elif hail_size >= 2.5:
            return "tennis ball size"
        elif hail_size >= 2.0:
            return "egg size"
        elif hail_size >= 1.75:
            return "golf ball size"
        elif hail_size >= 1.5:
            return "ping pong ball size"
        elif hail_size >= 1.25:
            return "half dollar size"
        elif hail_size >= 1.0:
            return "quarter size"
        elif hail_size >= 0.75:
            return "penny size"
        else:
            return f"{hail_size}\" diameter"
    
    def _extract_radar_parameters(self, alert: Dict) -> Dict[str, any]:
        """Extract comprehensive radar parameters and hazard information from alert description"""
        description = ""
        # Try multiple sources for the description
        sources = [
            alert.get('raw', {}).get('properties', {}).get('description'),
            alert.get('properties', {}).get('description'),
            alert.get('description')
        ]
        
        for source in sources:
            if source:
                description = source
                break
        
        radar_data = {
            'hail_inches': 0.0, 
            'wind_mph': 0.0,
            'hail_size_name': '',
            'hazard_text': '',
            'impact_text': '',
            'locations_impacted': ''
        }
        
        if description:
            # Extract HAZARD section
            hazard_match = re.search(r'HAZARD\.\.\.(.+?)(?:SOURCE|IMPACT|$)', description, re.IGNORECASE | re.DOTALL)
            if hazard_match:
                radar_data['hazard_text'] = hazard_match.group(1).strip()
                
                # Extract hail size and name from hazard
                hail_match = re.search(r'(\w+\s*\w*)\s+size\s+hail', radar_data['hazard_text'], re.IGNORECASE)
                if hail_match:
                    radar_data['hail_size_name'] = hail_match.group(1).strip()
                    # Convert common names to inches
                    size_mapping = {
                        'pea': 0.25, 'marble': 0.5, 'penny': 0.75, 'nickel': 0.88, 
                        'quarter': 1.0, 'half dollar': 1.25, 'ping pong': 1.5, 
                        'golf ball': 1.75, 'tennis ball': 2.5, 'baseball': 2.75
                    }
                    radar_data['hail_inches'] = size_mapping.get(radar_data['hail_size_name'].lower(), 0.0)
                
                # Extract wind speed from hazard
                wind_match = re.search(r'(\d+)\s*mph\s+wind', radar_data['hazard_text'], re.IGNORECASE)
                if wind_match:
                    radar_data['wind_mph'] = float(wind_match.group(1))
            
            # Extract IMPACT section
            impact_match = re.search(r'IMPACT\.\.\.(.+?)(?:\*|$)', description, re.IGNORECASE | re.DOTALL)
            if impact_match:
                radar_data['impact_text'] = impact_match.group(1).strip()
            
            # Extract locations impacted
            locations_match = re.search(r'Locations impacted include\.\.\.(.+?)\.', description, re.IGNORECASE | re.DOTALL)
            if locations_match:
                radar_data['locations_impacted'] = locations_match.group(1).strip()
        
        return radar_data
    
    def _extract_source_description(self, damage_data: List[Dict]) -> str:
        """Extract factual source description from SPC report comments"""
        if not damage_data:
            return "Reports"
        
        # Analyze the source comments to determine what actually reported the data
        comments = [data.get('details', '') for data in damage_data if data.get('details')]
        
        sources = []
        for comment in comments:
            comment_lower = comment.lower()
            if 'site ' in comment_lower and 'measured' in comment_lower:
                sources.append("weather station measurements")
            elif 'mping' in comment_lower:
                sources.append("mPING reports") 
            elif 'social media' in comment_lower:
                sources.append("social media reports")
            elif 'delayed report' in comment_lower:
                sources.append("field reports")
            elif comment.strip() and not comment.strip().startswith('(') and len(comment.strip()) > 5:
                sources.append("field reports")
        
        if sources:
            unique_sources = list(set(sources))
            if len(unique_sources) == 1:
                return unique_sources[0].capitalize()
            else:
                return "Multiple sources"
        else:
            return "SPC reports"
    
    def _build_verification_prompt(self, alert: Dict, spc_reports: List[Dict]) -> str:
        """Build weatherman-style report prompt integrating radar detection and verified reports"""
        
        # Extract core alert information
        event_type = alert.get('event', 'Weather Event')
        area_desc = alert.get('area_desc', 'Unknown Area')
        effective_time = alert.get('effective', 'Unknown Time')
        
        # Extract comprehensive radar data including HAZARD and IMPACT sections
        radar_data = self._extract_radar_parameters(alert)
        
        # Process SPC reports to get verified measurements
        verified_reports = []
        authoritative_hail = 0.0
        authoritative_wind = 0.0
        
        for report in spc_reports:
            report_type = report.get('report_type', '').lower()
            magnitude = report.get('magnitude', {})
            comments = report.get('comments', '')
            location = report.get('location', '')
            time_utc = report.get('time_utc', '')
            
            if report_type == 'hail':
                hail_size = 0.0
                if magnitude and isinstance(magnitude, dict):
                    hail_size = magnitude.get('size_inches', 0.0) or magnitude.get('hail_inches', 0.0)
                
                if hail_size > 0:
                    authoritative_hail = max(authoritative_hail, hail_size)
                    verified_reports.append({
                        'type': 'HAIL',
                        'verified_magnitude': hail_size,
                        'common_name': self._get_hail_common_name(hail_size),
                        'location': location,
                        'time': time_utc,
                        'details': comments
                    })
            
            elif report_type == 'wind':
                wind_speed = 0.0
                if magnitude and isinstance(magnitude, dict):
                    wind_speed = magnitude.get('wind_mph', 0.0) or magnitude.get('speed_mph', 0.0)
                elif comments:
                    wind_match = re.search(r'(\d+)\s*mph', comments)
                    if wind_match:
                        wind_speed = float(wind_match.group(1))
                
                if wind_speed > 0:
                    authoritative_wind = max(authoritative_wind, wind_speed)
                    verified_reports.append({
                        'type': 'WIND',
                        'verified_magnitude': wind_speed,
                        'location': location,
                        'time': time_utc,
                        'details': comments
                    })
        
        # Build weatherman report prompt
        prompt_parts = [
            f"WEATHER EVENT STORY DATA:",
            f"",
            f"ORIGINAL ALERT DETAILS:",
            f"- Event: {event_type}",
            f"- Time Issued: {effective_time}",
            f"- Areas: {area_desc}",
            f"- Radar Initially Detected: {radar_data['hazard_text']}" if radar_data['hazard_text'] else "",
            f"- Predicted Impact: {radar_data['impact_text']}" if radar_data['impact_text'] else "",
            f"- Areas Expected to be Affected: {radar_data['locations_impacted']}" if radar_data['locations_impacted'] else "",
            f"",
            f"VERIFIED STORM REPORTS:"
        ]
        
        # Add verified reports
        for i, report in enumerate(verified_reports, 1):
            unit = '\" hail' if report['type'] == 'HAIL' else ' mph winds'
            common_name = f" ({report.get('common_name', '')})" if report['type'] == 'HAIL' else ""
            
            prompt_parts.extend([
                f"Report {i}: {report['type']}",
                f"  - Verified: {report['verified_magnitude']}{unit}{common_name}",
                f"  - Location: {report['location']}",
                f"  - Time: {report['time']} UTC",
                f"  - Additional Details: {report['details'][:100]}..." if report['details'] else "  - No additional damage details",
                ""
            ])
        
        # Add weatherman instructions
        prompt_parts.extend([
            f"WRITE A PROFESSIONAL WEATHER REPORT:",
            f"",
            f"Start with: 'At {effective_time} in {area_desc}, the National Weather Service issued a {event_type} when radar detected [original radar parameters].'",
            f"",
            f"Then continue: 'Storm spotters subsequently verified [use the VERIFIED magnitudes as authoritative - these override radar estimates] with [specific damage details if available].'",
            f"",
            f"Conclude with: 'This confirms that [convert the predicted IMPACT to past tense confirmed damage potential] occurred in the immediate area surrounding [verified locations].'",
            f"",
            f"CRITICAL: Use the VERIFIED SPC measurements as the authoritative magnitude, not the radar estimates. Write as a factual weather report about what actually happened."
        ])
        
        return "\n".join(filter(None, prompt_parts))
    
    def _prepare_context(self, alert: Dict, spc_reports: List[Dict]) -> Dict:
        """Prepare structured context data for AI processing"""
        
        # Extract key alert information
        alert_context = {
            "event_type": alert.get('event', 'Unknown'),
            "severity": alert.get('severity', 'Unknown'),
            "effective_time": self._format_time(alert.get('effective')),
            "expires_time": self._format_time(alert.get('expires')),
            "area_description": alert.get('area_desc', ''),
            "headline": alert.get('properties', {}).get('headline', ''),
            "description": alert.get('properties', {}).get('description', '')[:500] + "..." if len(alert.get('properties', {}).get('description', '')) > 500 else alert.get('properties', {}).get('description', '')
        }
        
        # Process SPC reports
        reports_context = []
        for report in spc_reports:
            report_context = {
                "type": report.get('type', 'unknown').upper(),
                "time": report.get('time', ''),
                "location": report.get('location', ''),
                "county": report.get('county', ''),
                "state": report.get('state', ''),
                "comments": report.get('comments', ''),
                "magnitude": report.get('magnitude', {})
            }
            reports_context.append(report_context)
        
        return {
            "alert": alert_context,
            "confirmed_reports": reports_context,
            "total_reports": len(reports_context)
        }
    
    def _build_prompt(self, context: Dict) -> str:
        """Build the AI prompt with structured data"""
        
        alert = context["alert"]
        reports = context["confirmed_reports"]
        
        prompt = f"""
Analyze this verified weather event and generate a comprehensive summary:

ORIGINAL WARNING:
- Event: {alert['event_type']} ({alert['severity']})
- Time: {alert['effective_time']} to {alert['expires_time']}
- Area: {alert['area_description']}
- Headline: {alert['headline']}

CONFIRMED REPORTS ({context['total_reports']} total):
"""
        
        for i, report in enumerate(reports, 1):
            magnitude_text = ""
            if report['magnitude']:
                if 'f_scale' in report['magnitude']:
                    magnitude_text = f" (F{report['magnitude']['f_scale']})"
                elif 'speed' in report['magnitude']:
                    magnitude_text = f" ({report['magnitude']['speed']} mph)"
                elif 'size' in report['magnitude']:
                    magnitude_text = f" ({report['magnitude']['size']} inch)"
            
            prompt += f"""
{i}. {report['type']}{magnitude_text} at {report['time']} UTC
   Location: {report['location']}, {report['county']} County, {report['state']}
   Details: {report['comments']}
"""
        
        prompt += """

Generate a summary that:
1. Confirms the warning was verified by actual reports
2. Provides precise timing between warning and events
3. Describes the geographical impact and any progression
4. Mentions nearby areas or communities that may have been affected
5. Includes relevant magnitude/intensity details
6. Uses language like "confirmed reports validate the warning" or "the alert was substantiated by storm reports"

Keep the summary factual, concise (2-3 sentences), and suitable for emergency management professionals.
"""
        
        return prompt
    
    def _format_time(self, time_str: Optional[str]) -> str:
        """Format ISO datetime string to readable format"""
        if not time_str:
            return "Unknown"
        
        try:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.strftime("%I:%M %p UTC on %B %d")
        except:
            return time_str
    
    def batch_generate_summaries(self, matches: List[Dict]) -> Dict[str, str]:
        """
        Generate summaries for multiple matches
        
        Args:
            matches: List of match dictionaries with alert and spc_reports
        
        Returns:
            Dictionary mapping alert IDs to generated summaries
        """
        summaries = {}
        
        for match in matches:
            if match.get('spc_reports') and len(match['spc_reports']) > 0:
                summary = self.generate_match_summary(
                    alert=match,
                    spc_reports=match['spc_reports']
                )
                if summary:
                    summaries[match['id']] = summary
        
        return summaries