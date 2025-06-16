"""
Response utility functions for standardized API responses
"""
from flask import jsonify
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def success_response(data=None, message="Success", status=200):
    """Standardized success response format"""
    response = {"success": True}
    if message:
        response["message"] = message
    if data is not None:
        response["data"] = data
    return jsonify(response), status

def error_response(message="An error occurred", status=500, error_details=None):
    """Standardized error response format"""
    response = {
        "success": False,
        "error": message
    }
    if error_details:
        response["details"] = error_details
    return jsonify(response), status

def handle_errors(f):
    """Decorator for standardized error handling"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in {f.__name__}: {str(e)}")
            return error_response(f"Error in {f.__name__}: {str(e)}")
    return wrapper

def paginated_response(data, page, per_page, total, message="Success"):
    """Standardized paginated response format"""
    return jsonify({
        "success": True,
        "message": message,
        "data": data,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page
        }
    })