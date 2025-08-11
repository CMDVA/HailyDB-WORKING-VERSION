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
                        "content": """You are a professional meteorological data analyst specializing in precise threat-level weather summaries aligned to official NWS guidance, designed for actionable intelligence in storm restoration, insurance, and public safety.

CRITICAL REQUIREMENTS:
1. Convert all future tense language from the original warning into past tense verified events
2. Use ONLY official NWS threat classifications: "Very Low Threat", "Low Threat", "Moderate Threat", "High Threat", "Extreme Threat"
3. Integrate ALL data from both NWS alert and SPC damage reports into a single comprehensive description
4. Reference specific times, locations, and verified damage per official reports
5. NEVER reference insurance directly - let the data speak for itself
6. Include hail size equivalents (quarter size, golf ball size, etc.) and wind speeds with official damage ratings

Structure: Lead with "At {time} in {location}, a National Weather Service {alert type} was substantiated with {damage type} at {time} in {location}..." and continue integrating all available data."""
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
        
        # Build professional meteorological summary
        summary_parts = [
            f"At {effective} in {area_desc}, a National Weather Service {event} was substantiated with verified damage reports from the Storm Prediction Center."
        ]
        
        # Add verification details
        if damage_data:
            verification_details = []
            for data in damage_data:
                if data['type'] == 'hail':
                    verification_details.append(f"{data['magnitude']}\" hail ({data['common_name']}) - {data['threat_level']}")
                else:
                    verification_details.append(f"{data['magnitude']} mph winds - {data['threat_level']}")
            
            summary_parts.append(f"Verified damage reports documented: {', '.join(verification_details)}.")
        
        # Add threat level assessment
        threat_summary = []
        if max_hail > 0:
            threat_summary.append(f"Hail threat classified as {self._map_hail_threat_level(max_hail)} based on {max_hail}\" stones")
        if max_wind > 0:
            threat_summary.append(f"Wind threat classified as {self._map_wind_threat_level(max_wind)} based on {max_wind} mph gusts")
        
        if threat_summary:
            summary_parts.append(' and '.join(threat_summary) + ' per National Weather Service criteria.')
        
        # Add damage assessment based on official NWS guidelines
        damage_potential = []
        if max_hail >= 1.75:
            damage_potential.append("significant structural damage to roofing materials and vehicles")
        elif max_hail >= 1.0:
            damage_potential.append("moderate damage to roofing and automotive surfaces")
        elif max_hail >= 0.75:
            damage_potential.append("minor damage to landscaping and exposed surfaces")
        
        if max_wind >= 75:
            damage_potential.append("extensive tree damage and structural impact to buildings")
        elif max_wind >= 58:
            damage_potential.append("tree limb damage and loose outdoor equipment displacement")
        
        if damage_potential:
            summary_parts.append(f"Official damage assessment indicates potential for {', '.join(damage_potential)}.")
        
        # Add geographic and temporal context
        if len(damage_data) > 1:
            locations = [data['location'] for data in damage_data if data['location']]
            if locations:
                unique_locations = list(set(locations))
                summary_parts.append(f"Multiple verification points documented across {len(unique_locations)} distinct locations including {', '.join(unique_locations[:3])}.")
        
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
    
    def _extract_radar_parameters(self, alert: Dict) -> Dict[str, float]:
        """Extract radar-indicated parameters from alert description"""
        description = ""
        if alert.get('properties', {}).get('description'):
            description = alert['properties']['description']
        elif alert.get('raw', {}).get('properties', {}).get('description'):
            description = alert['raw']['properties']['description']
        
        radar_params = {'hail_inches': 0.0, 'wind_mph': 0.0}
        
        if description:
            # Extract hail size
            hail_match = re.search(r'hail.*?(\d+(?:\.\d+)?)\s*(?:inch|in|")', description, re.IGNORECASE)
            if hail_match:
                radar_params['hail_inches'] = float(hail_match.group(1))
            
            # Extract wind speed
            wind_match = re.search(r'wind.*?(\d+)\s*mph', description, re.IGNORECASE)
            if wind_match:
                radar_params['wind_mph'] = float(wind_match.group(1))
        
        return radar_params
    
    def _build_verification_prompt(self, alert: Dict, spc_reports: List[Dict]) -> str:
        """Build comprehensive prompt integrating all NWS and SPC data"""
        
        # Extract core alert information
        event_type = alert.get('event', 'Weather Event')
        area_desc = alert.get('area_desc', 'Unknown Area')
        effective_time = alert.get('effective', 'Unknown Time')
        
        # Extract radar parameters
        radar_params = self._extract_radar_parameters(alert)
        
        # Process all SPC reports for comprehensive damage data
        damage_reports = []
        max_hail = 0.0
        max_wind = 0.0
        
        for report in spc_reports:
            report_type = report.get('report_type', '').lower()
            magnitude = report.get('magnitude', {})
            comments = report.get('comments', '')
            location = report.get('location', '')
            time_utc = report.get('time_utc', '')
            
            # Extract magnitudes
            if report_type == 'hail':
                hail_size = 0.0
                if magnitude and isinstance(magnitude, dict):
                    hail_size = magnitude.get('size_inches', 0.0) or magnitude.get('hail_inches', 0.0)
                max_hail = max(max_hail, hail_size)
                
                if hail_size > 0:
                    damage_reports.append({
                        'type': 'hail',
                        'magnitude': hail_size,
                        'common_name': self._get_hail_common_name(hail_size),
                        'threat_level': self._map_hail_threat_level(hail_size),
                        'location': location,
                        'time': time_utc,
                        'comments': comments
                    })
            
            elif report_type == 'wind':
                wind_speed = 0.0
                if magnitude and isinstance(magnitude, dict):
                    wind_speed = magnitude.get('wind_mph', 0.0) or magnitude.get('speed_mph', 0.0)
                elif comments:
                    # Try to extract from comments
                    wind_match = re.search(r'(\d+)\s*mph', comments)
                    if wind_match:
                        wind_speed = float(wind_match.group(1))
                
                max_wind = max(max_wind, wind_speed)
                
                if wind_speed > 0:
                    damage_reports.append({
                        'type': 'wind',
                        'magnitude': wind_speed,
                        'threat_level': self._map_wind_threat_level(wind_speed),
                        'location': location,
                        'time': time_utc,
                        'comments': comments
                    })
        
        # Build comprehensive prompt
        prompt_parts = [
            f"VERIFIED WEATHER EVENT DATA INTEGRATION:",
            f"",
            f"NWS ALERT:",
            f"- Event Type: {event_type}",
            f"- Alert Time: {effective_time}",
            f"- Area Description: {area_desc}",
            f"- Radar-Indicated Hail: {radar_params['hail_inches']}\" ({self._get_hail_common_name(radar_params['hail_inches'])})" if radar_params['hail_inches'] > 0 else "",
            f"- Radar-Indicated Wind: {radar_params['wind_mph']} mph" if radar_params['wind_mph'] > 0 else "",
            f"",
            f"VERIFIED SPC DAMAGE REPORTS ({len(spc_reports)} reports):"
        ]
        
        # Add each damage report with full details
        for i, report in enumerate(damage_reports, 1):
            magnitude_unit = '"' if report['type'] == 'hail' else ' mph'
            common_name = report.get('common_name', '')
            details_text = f"  - Details: {report['comments'][:100]}..." if report['comments'] else "  - No additional details"
            
            prompt_parts.extend([
                f"Report {i}: {report['type'].upper()}",
                f"  - Magnitude: {report['magnitude']}{magnitude_unit} ({common_name})",
                f"  - Threat Level: {report['threat_level']}",
                f"  - Location: {report['location']}",
                f"  - Time: {report['time']} UTC",
                details_text,
                ""
            ])
        
        # Add analysis requirements
        prompt_parts.extend([
            f"ANALYSIS REQUIREMENTS:",
            f"1. Begin with: 'At {effective_time} in {area_desc}, a National Weather Service {event_type} was substantiated with [damage type] at [time] in [location]...'",
            f"2. Convert ALL future tense language to past tense verified events",
            f"3. Integrate radar-indicated parameters with actual damage reports",
            f"4. Use official NWS threat levels: {self._map_hail_threat_level(max_hail) if max_hail > 0 else ''} {self._map_wind_threat_level(max_wind) if max_wind > 0 else ''}",
            f"5. Include specific times, locations, and damage details from SPC reports",
            f"6. Mention geographic polygon coverage and likely damage areas beyond report points",
            f"7. End with official damage rating based on verified magnitudes",
            f"",
            f"Generate a comprehensive summary integrating ALL data points above into a single coherent description."
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