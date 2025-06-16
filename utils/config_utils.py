"""
Configuration utilities and constants
"""
import os

class PaginationConfig:
    """Centralized pagination configuration"""
    DEFAULT_PAGE_SIZE = 50
    MAX_PAGE_SIZE = 1000
    API_MAX_PAGE_SIZE = 500

class DatabaseConfig:
    """Database configuration constants"""
    WRITE_BATCH_SIZE = int(os.environ.get("DB_WRITE_BATCH_SIZE", "500"))
    ENRICH_BATCH_SIZE = int(os.environ.get("ENRICH_BATCH_SIZE", "25"))
    SPC_MATCH_BATCH_SIZE = int(os.environ.get("SPC_MATCH_BATCH_SIZE", "200"))

class APIConfig:
    """API configuration constants"""
    REQUEST_TIMEOUT = 30
    POLLING_INTERVAL_MINUTES = 5
    
class HailSizeConfig:
    """Centralized hail size configuration"""
    NWS_HAIL_SIZE_CHART = {
        'pea': 0.25,
        'peanut': 0.5,
        'penny': 0.75,
        'nickel': 0.88,
        'quarter': 1.0,
        'half dollar': 1.25,
        'ping pong ball': 1.5,
        'golf ball': 1.75,
        'egg': 2.0,
        'tennis ball': 2.5,
        'baseball': 2.75,
        'large apple': 3.0,
        'softball': 4.0,
        'grapefruit': 4.5
    }
    
    HAIL_SIZE_CATEGORIES = [
        (0.25, "Pea"),
        (0.5, "Marble"), 
        (0.75, "Penny"),
        (1.0, "Quarter"),
        (1.25, "Half Dollar"),
        (1.5, "Ping Pong"),
        (1.75, "Golf Ball"),
        (2.0, "Egg/Tennis Ball"),
        (2.5, "Tennis Ball"),
        (3.0, "Large Apple"),
        (4.0, "Softball"),
        (4.5, "Grapefruit")
    ]
    
    @classmethod
    def get_hail_display_name(cls, size_inches):
        """Get display name for hail size"""
        if not size_inches or size_inches <= 0:
            return "Unknown"
        
        for threshold, name in reversed(cls.HAIL_SIZE_CATEGORIES):
            if size_inches >= threshold:
                return name
        return "Pea"
    
    @classmethod
    def get_hail_severity(cls, size_inches):
        """Get severity category for hail size"""
        if not size_inches or size_inches <= 0:
            return "unknown"
        
        if size_inches >= 2.0:
            return "severe"
        elif size_inches >= 1.0:
            return "significant"
        else:
            return "minor"