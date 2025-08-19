#!/usr/bin/env python3
"""
State Enrichment Service for HailyDB
Enriches alerts with missing state information using UGC code mappings
"""

import logging
import re
from typing import List, Optional, Dict, Set
from datetime import datetime

logger = logging.getLogger(__name__)

class StateEnrichmentService:
    """
    Comprehensive state enrichment service that extracts state information 
    from UGC codes, SAME codes, and area descriptions
    """
    
    def __init__(self):
        """Initialize the UGC to state mapping"""
        # UGC state code mappings (first 2 characters of UGC codes)
        self.ugc_state_mapping = {
            # Land zones (Zxxx)
            'AL': 'AL', 'AK': 'AK', 'AZ': 'AZ', 'AR': 'AR', 'CA': 'CA', 'CO': 'CO',
            'CT': 'CT', 'DE': 'DE', 'FL': 'FL', 'GA': 'GA', 'HI': 'HI', 'ID': 'ID',
            'IL': 'IL', 'IN': 'IN', 'IA': 'IA', 'KS': 'KS', 'KY': 'KY', 'LA': 'LA',
            'ME': 'ME', 'MD': 'MD', 'MA': 'MA', 'MI': 'MI', 'MN': 'MN', 'MS': 'MS',
            'MO': 'MO', 'MT': 'MT', 'NE': 'NE', 'NV': 'NV', 'NH': 'NH', 'NJ': 'NJ',
            'NM': 'NM', 'NY': 'NY', 'NC': 'NC', 'ND': 'ND', 'OH': 'OH', 'OK': 'OK',
            'OR': 'OR', 'PA': 'PA', 'RI': 'RI', 'SC': 'SC', 'SD': 'SD', 'TN': 'TN',
            'TX': 'TX', 'UT': 'UT', 'VT': 'VT', 'VA': 'VA', 'WA': 'WA', 'WV': 'WV',
            'WI': 'WI', 'WY': 'WY', 'DC': 'DC',
            # Marine zones (PZxxx, AMxxx, GMxxx, PKxxx, etc.)
            'PZ': 'CA',  # Pacific zones generally California
            'AM': 'AK',  # Alaska Marine zones
            'GM': 'FL',  # Gulf of Mexico zones generally Florida/Gulf states
            'PK': 'AK',  # Alaska Pacific zones
            'AN': 'NC',  # Atlantic North zones
            'AS': 'FL',  # Atlantic South zones
        }
        
        # Enhanced SAME code to state mapping (first 3 digits)
        self.same_state_mapping = {
            '001': 'AL', '002': 'AK', '004': 'AZ', '005': 'AR', '006': 'CA', '008': 'CO',
            '009': 'CT', '010': 'DE', '011': 'DC', '012': 'FL', '013': 'GA', '015': 'HI',
            '016': 'ID', '017': 'IL', '018': 'IN', '019': 'IA', '020': 'KS', '021': 'KY',
            '022': 'LA', '023': 'ME', '024': 'MD', '025': 'MA', '026': 'MI', '027': 'MN',
            '028': 'MS', '029': 'MO', '030': 'MT', '031': 'NE', '032': 'NV', '033': 'NH',
            '034': 'NJ', '035': 'NM', '036': 'NY', '037': 'NC', '038': 'ND', '039': 'OH',
            '040': 'OK', '041': 'OR', '042': 'PA', '044': 'RI', '045': 'SC', '046': 'SD',
            '047': 'TN', '048': 'TX', '049': 'UT', '050': 'VT', '051': 'VA', '053': 'WA',
            '054': 'WV', '055': 'WI', '056': 'WY',
            # Marine/coastal SAME codes
            '057': 'CA',  # California marine zones
            '058': 'FL',  # Florida marine zones
            '059': 'TX',  # Texas marine zones
        }
    
    def extract_states_from_ugc(self, ugc_codes: List[str]) -> Set[str]:
        """Extract state codes from UGC codes"""
        states = set()
        
        if not ugc_codes:
            return states
            
        for ugc in ugc_codes:
            # Safety check for None or invalid UGC codes
            if ugc is None or not isinstance(ugc, str) or len(ugc) < 2:
                continue
                
            try:
                # Extract state prefix from UGC code
                # Examples: MIZ024 -> MI, PZZ530 -> PZ (marine CA), CAZ123 -> CA
                state_prefix = ugc[:2].upper()
                
                if state_prefix and state_prefix in self.ugc_state_mapping:
                    states.add(self.ugc_state_mapping[state_prefix])
            except (AttributeError, IndexError, TypeError) as e:
                logger.warning(f"Failed to process UGC code '{ugc}': {e}")
                continue
                
        return states
    
    def extract_states_from_same(self, same_codes: List[str]) -> Set[str]:
        """Extract state codes from SAME codes"""
        states = set()
        
        if not same_codes:
            return states
            
        for same in same_codes:
            # Safety check for None or invalid SAME codes
            if same is None or not isinstance(same, str) or len(same) < 3:
                continue
                
            try:
                # Extract state code from first 3 digits of SAME code
                # Example: 026007 -> 026 -> MI
                state_code = same[:3]
                
                if state_code and state_code in self.same_state_mapping:
                    states.add(self.same_state_mapping[state_code])
            except (AttributeError, IndexError, TypeError) as e:
                logger.warning(f"Failed to process SAME code '{same}': {e}")
                continue
                
        return states
    
    def extract_states_from_area_desc(self, area_desc: str) -> Set[str]:
        """Extract state codes from area description text"""
        states = set()
        
        # Safety check for None or invalid area description
        if not area_desc or not isinstance(area_desc, str):
            return states
            
        try:
            # Method 1: Look for standard state abbreviations
            state_pattern = r'\b([A-Z]{2})\b'
            potential_states = re.findall(state_pattern, area_desc)
            
            # Validate against known state codes
            valid_state_codes = {
                'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID',
                'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
                'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK',
                'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV',
                'WI', 'WY', 'DC'
            }
            
            for state in potential_states:
                if state in valid_state_codes:
                    states.add(state)
            
            # Method 2: Look for state names in area description
            state_name_mapping = {
                'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
                'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT', 'delaware': 'DE',
                'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI', 'idaho': 'ID',
                'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA', 'kansas': 'KS',
                'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME', 'maryland': 'MD',
                'massachusetts': 'MA', 'michigan': 'MI', 'minnesota': 'MN', 'mississippi': 'MS',
                'missouri': 'MO', 'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
                'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM', 'new york': 'NY',
                'north carolina': 'NC', 'north dakota': 'ND', 'ohio': 'OH', 'oklahoma': 'OK',
                'oregon': 'OR', 'pennsylvania': 'PA', 'rhode island': 'RI', 'south carolina': 'SC',
                'south dakota': 'SD', 'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT',
                'vermont': 'VT', 'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
                'wisconsin': 'WI', 'wyoming': 'WY'
            }
            
            area_lower = area_desc.lower()
            for state_name, state_code in state_name_mapping.items():
                if state_name in area_lower:
                    states.add(state_code)
                    
        except (AttributeError, TypeError) as e:
            logger.warning(f"Failed to process area description '{area_desc}': {e}")
        
        return states
    
    def enrich_alert_states(self, alert) -> bool:
        """
        Enrich a single alert with state information
        Returns True if enrichment was successful, False otherwise
        """
        try:
            all_states = set()
            
            # Extract from geocode UGC
            if alert.properties:
                geocode = alert.properties.get('geocode', {})
                if isinstance(geocode, dict):
                    ugc_codes = geocode.get('UGC', [])
                    if isinstance(ugc_codes, list):
                        all_states.update(self.extract_states_from_ugc(ugc_codes))
                    
                    same_codes = geocode.get('SAME', [])
                    if isinstance(same_codes, list):
                        all_states.update(self.extract_states_from_same(same_codes))
            
            # Extract from area description
            if alert.area_desc:
                all_states.update(self.extract_states_from_area_desc(alert.area_desc))
            
            # Update the alert if we found states
            if all_states:
                alert.affected_states = list(sorted(all_states))
                logger.debug(f"Enriched alert {alert.id} with states: {all_states}")
                return True
            else:
                logger.debug(f"No states found for alert {alert.id}")
                return False
                
        except Exception as e:
            logger.error(f"Error enriching states for alert {alert.id}: {e}")
            return False
    
    def enrich_alerts_batch(self, db, limit: int = 1000) -> Dict[str, int]:
        """
        Enrich a batch of alerts with missing state information
        Returns statistics about the enrichment process
        """
        try:
            from models import Alert
            from sqlalchemy import or_, cast, String
            
            # Query alerts with missing state information using proper JSONB syntax
            from sqlalchemy import text
            alerts_query = Alert.query.filter(
                or_(
                    Alert.affected_states.is_(None),
                    text("affected_states = '[]'::jsonb")
                )
            ).limit(limit)
            
            alerts = alerts_query.all()
            logger.info(f"Processing {len(alerts)} alerts for state enrichment")
            
            enriched_count = 0
            failed_count = 0
            
            for alert in alerts:
                if self.enrich_alert_states(alert):
                    enriched_count += 1
                else:
                    failed_count += 1
            
            # Commit the changes
            db.session.commit()
            
            stats = {
                'processed': len(alerts),
                'enriched': enriched_count,
                'failed': failed_count,
                'success_rate': (enriched_count / len(alerts)) * 100 if alerts else 0
            }
            
            logger.info(f"State enrichment completed: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error during batch state enrichment: {e}")
            db.session.rollback()
            return {
                'processed': 0,
                'enriched': 0,
                'failed': 0,
                'success_rate': 0,
                'error': str(e)
            }
    
    def enrich_all_alerts(self, db, batch_size: int = 1000) -> Dict[str, int]:
        """
        Enrich all alerts with missing state information in batches
        Returns comprehensive statistics
        """
        total_stats = {
            'total_processed': 0,
            'total_enriched': 0,
            'total_failed': 0,
            'batches_processed': 0
        }
        
        while True:
            batch_stats = self.enrich_alerts_batch(db, batch_size)
            
            if batch_stats['processed'] == 0:
                break
                
            total_stats['total_processed'] += batch_stats['processed']
            total_stats['total_enriched'] += batch_stats['enriched']
            total_stats['total_failed'] += batch_stats['failed']
            total_stats['batches_processed'] += 1
            
            logger.info(f"Completed batch {total_stats['batches_processed']}: {batch_stats}")
            
            # Break if we processed fewer than batch_size (last batch)
            if batch_stats['processed'] < batch_size:
                break
        
        total_stats['overall_success_rate'] = (
            (total_stats['total_enriched'] / total_stats['total_processed']) * 100 
            if total_stats['total_processed'] > 0 else 0
        )
        
        logger.info(f"State enrichment complete: {total_stats}")
        return total_stats

def test_state_extraction():
    """Test function to validate state extraction logic"""
    service = StateEnrichmentService()
    
    # Test UGC extraction
    ugc_test = ['MIZ024', 'PZZ530', 'CAZ123']
    ugc_states = service.extract_states_from_ugc(ugc_test)
    print(f"UGC {ugc_test} -> States: {ugc_states}")
    
    # Test SAME extraction
    same_test = ['026007', '057530']
    same_states = service.extract_states_from_same(same_test)
    print(f"SAME {same_test} -> States: {same_states}")
    
    # Test area description extraction
    area_test = "Alpena"
    area_states = service.extract_states_from_area_desc(area_test)
    print(f"Area '{area_test}' -> States: {area_states}")

if __name__ == "__main__":
    test_state_extraction()