"""
HailyDB v2.0 - Modular Flask Application
Refactored from 4,935-line monolith into clean modular architecture
"""
import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Import core modules first
from utils.config_utils import HailSizeConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints - import here to avoid circular imports
    from routes.api_routes import api_bp
    from routes.admin_routes import admin_bp
    from routes.web_routes import web_bp
    
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)
    
    # Jinja2 template filters
    @app.template_filter('number_format')
    def number_format(value):
        """Format numbers with commas for thousands"""
        if value is None:
            return "N/A"
        try:
            return f"{int(value):,}"
        except (ValueError, TypeError):
            return str(value)
    
    @app.template_filter('hail_display_name')
    def hail_display_name(size_inches):
        """Get display name for hail size using centralized configuration"""
        return HailSizeConfig.get_hail_display_name(size_inches)
    
    @app.template_filter('hail_severity')
    def hail_severity(size_inches):
        """Get severity category for hail size using centralized configuration"""
        return HailSizeConfig.get_hail_severity(size_inches)
    
    @app.template_filter('determine_enhanced_status')
    def determine_enhanced_status(log_row):
        """Determine enhanced status display and color coding for operation logs"""
        if not log_row:
            return {'status': 'unknown', 'color': 'gray', 'icon': 'question'}
        
        status = getattr(log_row, 'status', 'unknown').lower()
        
        if status == 'success':
            return {'status': 'Success', 'color': 'green', 'icon': 'check'}
        elif status == 'error':
            return {'status': 'Error', 'color': 'red', 'icon': 'x'}
        elif status == 'in_progress':
            return {'status': 'Running', 'color': 'blue', 'icon': 'clock'}
        else:
            return {'status': 'Unknown', 'color': 'gray', 'icon': 'question'}
    
    # Initialize services within app context
    with app.app_context():
        # Import models to ensure tables are created
        import models
        
        # Create all database tables
        db.create_all()
        
        # Initialize background services
        try:
            # Initialize live radar service
            from live_radar_service import LiveRadarAlertService
            live_radar_service = LiveRadarAlertService()
            live_radar_service.start_polling()
            logger.info("Live radar alert service initialized and started")
            
            # Initialize autonomous scheduler
            from autonomous_scheduler import init_scheduler, start_scheduler
            init_scheduler(db.session)
            start_scheduler()
            logger.info("Autonomous scheduler initialized and started")
            
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

# Create application instance
app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)