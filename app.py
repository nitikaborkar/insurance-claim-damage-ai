from flask import Flask, request, jsonify
import tempfile
import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import filetype
from ergo_agent.service import analyze_image_path
from flask_limiter import Limiter
from flask_cors import CORS
from flask_limiter.util import get_remote_address

def get_user_identifier():
    """Extract user identifier for rate limiting."""
    if hasattr(request, 'authenticated_user'):
        return f"user:{request.authenticated_user}"
    
    api_key = request.headers.get("Authorization", "").replace("Bearer ", "")
    if api_key and len(api_key) > 16:
        return f"key:{api_key[:16]}"
    
    return f"ip:{get_remote_address()}"

#later implementation for user key extraction
# def get_user_key():
#     auth = request.headers.get("Authorization", "")
#     if auth.startswith("Bearer "):
#         return auth.split(" ", 1)[1].strip()  # token string
#     return get_remote_address()  # fallback

app = Flask(__name__)

# Trust proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# File upload security
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}

CORS(app, resources={r"/analyze": {
    "origins": ["https://staging-personal.balanceflo.ai"]
}})

# Rate limiting
REDIS_URL = os.getenv("REDIS_URL", "memory://")
limiter = Limiter(
    app=app,
    key_func=get_user_identifier,
    default_limits=[],
    storage_uri=REDIS_URL,
    strategy="moving-window",
)

# ============ Error Handlers ============

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "error": "File too large",
        "message": "Maximum file size is 10MB"
    }), 413

@app.errorhandler(429)
def rate_limit_exceeded(error):
    return jsonify({
        "error": "Rate limit exceeded",
        "message": str(error.description)
    }), 429

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f"Internal error: {error}")
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred. Please try again later."
    }), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Catch-all for unhandled exceptions"""
    app.logger.exception("Unhandled exception")
    
    # Don't expose details in production
    if app.debug:
        raise e
    
    return jsonify({
        "error": "Internal server error",
        "message": "An unexpected error occurred. Please contact support if the issue persists.",
        "request_id": request.headers.get("X-Request-ID", "unknown")
    }), 500

# ============ Helper Functions ============

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def setup_logging(app):
    """Configure production logging"""
    if not app.debug:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')
        
        # File handler with rotation
        file_handler = RotatingFileHandler(
            'logs/app.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')
    else:
        app.logger.setLevel(logging.DEBUG)
        app.logger.info('Application starting in DEBUG mode')

# ============ Routes ============

@app.route("/analyze", methods=["POST"])
@limiter.limit(
    "50 per day;20 per hour;10 per 10 minutes",
    error_message="Rate limit exceeded. Please try again later."
)
def analyze():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": "Invalid file type",
            "message": f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    try:
        file_bytes = file.read()
    except Exception as e:
        app.logger.error(f"Failed to read uploaded file: {e}")
        return jsonify({"error": "Failed to read file"}), 400

    # Verify actual image content
    kind = filetype.guess(file_bytes)
    if kind is None or kind.extension not in ALLOWED_EXTENSIONS:
        return jsonify({
            "error": "Invalid image format",
            "message": f"File is not a valid image (detected: {kind.extension if kind else 'unknown'})"
        }), 400
    
    image_type = kind.extension

    # Create safe temp file
    safe_filename = secure_filename(file.filename)
    tmp_path = None
    
    try:
        with tempfile.NamedTemporaryFile(
            suffix=f".{image_type}",
            delete=False
        ) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        result = analyze_image_path(tmp_path)
        return jsonify(result), 200
        
    except ValueError as e:
        app.logger.warning(f"Image validation failed: {e}")
        return jsonify({
            "error": "Invalid image",
            "message": str(e)
        }), 400
        
    except Exception as e:
        app.logger.exception("Analysis failed")
        return jsonify({
            "error": "Analysis failed",
            "message": "Unable to process image. Please try again."
        }), 500
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as e:
                app.logger.error(f"Failed to delete temp file {tmp_path}: {e}")

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

# ============ Server Setup ============

if __name__ == "__main__":
    # Setup logging first
    setup_logging(app)
    
    # Check if running in debug mode
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    if debug_mode:
        print("=" * 60)
        print("⚠️  WARNING: Running in DEBUG mode!")
        print("   This should ONLY be used for local development.")
        print("   Debug mode exposes sensitive information.")
        print("=" * 60)
        app.run(host="127.0.0.1", port=8000, debug=True)
    else:
        # Production mode - use Waitress WSGI server
        try:
            from waitress import serve
            print("=" * 60)
            print("🚀 Starting production server (Waitress)")
            print(f"   Listening on: http://0.0.0.0:8000")
            print(f"   Environment: PRODUCTION")
            print("=" * 60)
            serve(app, host="0.0.0.0", port=8000, threads=4)
        except ImportError:
            print("ERROR: waitress not installed. Install with: pip install waitress")
            sys.exit(1)
