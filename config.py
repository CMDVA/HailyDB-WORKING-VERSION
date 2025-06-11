import os

class Config:
    """Configuration settings for NWS Alert Ingestion Service"""
    
    # NWS API Configuration
    NWS_ALERT_URL = "https://api.weather.gov/alerts/active"
    NWS_HEADERS = {
        'User-Agent': 'HailyDB-NWS-Ingestion/1.0 (contact@hailydb.com)',
        'Accept': 'application/geo+json'
    }
    
    # Database Configuration
    DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/nws_alerts")
    
    # OpenAI Configuration
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    
    # Ingestion Settings
    POLLING_INTERVAL_MINUTES = 5
    REQUEST_TIMEOUT = 30
    
    # Database Write Batch Configuration
    DB_WRITE_BATCH_SIZE = int(os.environ.get("DB_WRITE_BATCH_SIZE", "500"))
    
    # Processing Batch Configuration (for enrichment, matching, etc.)
    ENRICH_BATCH_SIZE = int(os.environ.get("ENRICH_BATCH_SIZE", "25"))
    SPC_MATCH_BATCH_SIZE = int(os.environ.get("SPC_MATCH_BATCH_SIZE", "200"))
    
    # SPC Integration (Future)
    SPC_REPORTS_URL = "https://www.spc.noaa.gov/climo/reports/"
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    
    # Official NWS Hail Size Chart (inches)
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
    
    # Hail size categories for display and filtering
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
        if size_inches >= 4.5:
            return "Record Size"
        elif size_inches >= 4.0:
            return "Softball"
        elif size_inches >= 2.5:
            return "Tennis Ball+"
        elif size_inches >= 2.0:
            return "Egg"
        elif size_inches >= 1.75:
            return "Golf Ball"
        elif size_inches >= 1.5:
            return "Ping Pong"
        elif size_inches >= 1.25:
            return "Half Dollar"
        elif size_inches >= 1.0:
            return "Quarter"
        elif size_inches >= 0.75:
            return "Penny"
        elif size_inches >= 0.5:
            return "Marble"
        elif size_inches >= 0.25:
            return "Pea"
        else:
            return "Small"
    
    @classmethod
    def get_hail_severity(cls, size_inches):
        """Get severity category for hail size"""
        if size_inches >= 4.0:
            return "Extremely Severe"
        elif size_inches >= 2.0:
            return "Severe"
        elif size_inches >= 1.0:
            return "Significant"
        elif size_inches >= 0.5:
            return "Notable"
        else:
            return "Minor"
    
    @classmethod
    def validate(cls):
        """Validate configuration settings"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is required")
        
        return True
