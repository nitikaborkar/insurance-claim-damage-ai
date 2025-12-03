# Comprehensive Code Review – Security, Best Practices, Bug Risks

This document provides a detailed security and code quality review of the Ergonomic Risk Assessment application. Each issue includes severity rating, detailed explanation, and actionable solutions tailored to the Flask + LangGraph + Anthropic tech stack.

---

## Table of Contents
1. [Critical Security Issues](#critical-security-issues)
2. [High Severity Issues](#high-severity-issues)
3. [Medium Severity Issues](#medium-severity-issues)
4. [Low Severity Issues](#low-severity-issues)
5. [Best Practices & Code Quality](#best-practices--code-quality)
6. [Quick Reference - Priority Fixes](#quick-reference---priority-fixes)

---

## Critical Security Issues

### 🔴 **CRITICAL-1: Secrets Exposed in Version Control** -- ✅
**Location:** `.env` file in repository root
**Severity:** CRITICAL
**Current State:** API keys are committed to git repository

**Problem:**
The `.env` file contains live API keys that are visible in the repository:
```
ANTHROPIC_API_KEY = sk-ant-api03-...
LANGCHAIN_API_KEY = lsv2_pt_...
```

While `.env` is in `.gitignore`, **it's already been committed** (visible via `ls -la`). Anyone with repository access has these credentials.

**Impact:**
- Unauthorized API usage charges to your Anthropic/LangChain accounts
- Potential data exfiltration
- Quota exhaustion attacks
- Account compromise

**Solution:**

1. **IMMEDIATE ACTION - Revoke exposed keys:** 
   ```bash
   # Visit these URLs to rotate keys:
   # Anthropic: https://console.anthropic.com/settings/keys
   # LangChain: https://smith.langchain.com/settings
   ```

2. **Remove from git history:**
   ```bash
   # Remove .env from all commits
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch .env" \
     --prune-empty --tag-name-filter cat -- --all

   # Force push (coordinate with team first!)
   git push origin --force --all
   ```

3. **Use environment variables only:**

   Update [app.py](app.py) to load config at startup:
   ```python
   # Add at top of app.py, before any imports from ergo_agent
   import os
   from dotenv import load_dotenv

   load_dotenv()  # Load .env but never commit it

   # Validate required secrets at startup
   required_vars = ["ANTHROPIC_API_KEY"]
   missing = [var for var in required_vars if not os.getenv(var)]
   if missing:
       raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
   ```

4. **For production, use secret management:**
   - AWS: AWS Secrets Manager or Parameter Store
   - GCP: Secret Manager
   - Azure: Key Vault
   - Docker: Docker secrets or Kubernetes secrets
   - Heroku: Config vars

5. **Create `.env.example` for documentation:**
   ```bash
   # .env.example (commit this)
   ANTHROPIC_API_KEY=your_key_here
   LANGCHAIN_API_KEY=your_key_here
   ```

---

## High Severity Issues

### 🔴 **HIGH-1: Missing Authentication on `/analyze` Endpoint** -- TODO
**Location:** [app.py:29-45](app.py#L29-L45)
**Severity:** HIGH
**CVSS Score:** 8.1 (High)

**Problem:**
The `/analyze` endpoint has no authentication. Anyone with the endpoint URL can:
- Submit unlimited images
- Consume your Anthropic API quota
- Access ergonomic analysis results
- Potentially perform reconnaissance attacks

**Current Code:**
```python
@app.route("/analyze", methods=["POST"])
@limiter.limit("50 per day;20 per hour;10 per minute")
def analyze():
    # No auth check!
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
```

**Impact:**
- **Financial:** Anthropic Claude Sonnet-4 costs ~$15 per million tokens. An attacker could drain your budget
- **Operational:** API quota exhaustion = service downtime
- **Privacy:** No audit trail of who accessed the service

**Solution Options:**

**Option A: API Key Authentication (Simplest for Flask)**

1. Generate API keys for clients:
   ```python
   import secrets
   api_key = secrets.token_urlsafe(32)
   ```

2. Implement middleware:
   ```python
   # Add to app.py

   import secrets
   from functools import wraps
   from flask import request, jsonify

   # Store in database or environment (for demo, using env)
   VALID_API_KEYS = set(os.getenv("VALID_API_KEYS", "").split(","))

   def require_api_key(f):
       @wraps(f)
       def decorated_function(*args, **kwargs):
           api_key = request.headers.get("X-API-Key")

           if not api_key:
               return jsonify({"error": "Missing X-API-Key header"}), 401

           if api_key not in VALID_API_KEYS:
               return jsonify({"error": "Invalid API key"}), 401

           # Store for rate limiting
           request.authenticated_user = api_key
           return f(*args, **kwargs)
       return decorated_function

   @app.route("/analyze", methods=["POST"])
   @require_api_key  # Add this decorator
   @limiter.limit("50 per day;20 per hour;10 per minute")
   def analyze():
       # ... existing code
   ```

3. Update rate limiter to use authenticated user:
   ```python
   def get_user_identifier():
       # Use authenticated key if available
       return getattr(request, 'authenticated_user', get_remote_address())
   ```

**Option B: JWT Authentication (More Scalable)**

```python
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
jwt = JWTManager(app)

@app.route("/analyze", methods=["POST"])
@jwt_required()
@limiter.limit("50 per day;20 per hour;10 per minute")
def analyze():
    current_user = get_jwt_identity()
    # ... existing code
```

**Option C: OAuth2/OIDC (Enterprise)**
Use Flask-OIDC or Authlib for integration with Auth0, Okta, Google, etc.

**Recommendation:**
Start with **Option A** (API Key) for immediate protection, migrate to **Option B** (JWT) as you scale.

---

### 🔴 **HIGH-2: Production Server Running in Debug Mode** -- ✅
**Location:** [app.py:47-48](app.py#L47-L48)
**Severity:** HIGH

**Problem:**
```python
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
```

Running Flask with `debug=True` on `0.0.0.0` exposes:
- **Stack traces** with file paths and code snippets
- **Environment variables** (including secrets!)
- **Interactive debugger** accessible remotely via PIN
- **Automatic code reloading** which can cause race conditions

**Real Attack Example:**
```bash
# Attacker sends malformed request
curl -X POST http://your-server:8000/analyze

# Server responds with full stack trace:
# File "/app/ergo_agent/nodes.py", line 185
#   ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# ApiKeyError: Invalid key sk-ant-api03-...
```

**Solution:**

1. **Use environment-based configuration:**
   ```python
   # app.py
   import os

   if __name__ == "__main__":
       debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"

       if debug_mode:
           print("⚠️  WARNING: Running in DEBUG mode!")
           app.run(host="127.0.0.1", port=8000, debug=True)  # Only localhost
       else:
           # Use production WSGI server
           from waitress import serve
           serve(app, host="0.0.0.0", port=8000, threads=4)
   ```

2. **Update requirements.txt:**
   ```
   waitress==3.0.2  # Production WSGI server
   ```

3. **Add custom error handlers:**
   ```python
   # Add to app.py

   @app.errorhandler(500)
   def internal_error(error):
       app.logger.error(f"Internal error: {error}")
       return jsonify({
           "error": "Internal server error",
           "message": "An unexpected error occurred. Please try again later."
       }), 500

   @app.errorhandler(Exception)
   def handle_exception(e):
       # Log the error
       app.logger.exception("Unhandled exception")

       # Return generic error to client
       return jsonify({
           "error": "Internal server error",
           "request_id": request.headers.get("X-Request-ID", "unknown")
       }), 500
   ```

4. **Use proper logging:**
   ```python
   import logging
   from logging.handlers import RotatingFileHandler

   if not app.debug:
       file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=10)
       file_handler.setFormatter(logging.Formatter(
           '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
       ))
       file_handler.setLevel(logging.INFO)
       app.logger.addHandler(file_handler)
       app.logger.setLevel(logging.INFO)
   ```

---

### 🔴 **HIGH-3: Unsafe File Upload Handling** -- ✅
**Location:** [app.py:40-42](app.py#L40-L42), [ergo_agent/state.py:45-66](ergo_agent/state.py#L45-L66)
**Severity:** HIGH

**Problem:**
Multiple file upload vulnerabilities:

1. **No file size validation** - Could upload gigabyte files
2. **No MIME type checking** - Could upload executables disguised as images
3. **Decompression bomb vulnerability** - ZIP bombs in image format
4. **Infinite compression loop** - `load_and_compress` can hang forever
5. **User filename used unsafely** - Path traversal potential

**Current Vulnerable Code:**
```python
# app.py
with tempfile.NamedTemporaryFile(suffix=file.filename, delete=True) as tmp:
    file.save(tmp.name)  # No size check!
    result = analyze_image_path(tmp.name)

# state.py
def load_and_compress(image_path, max_size_kb=4800):
    img = Image.open(image_path)  # Can trigger decompression bomb!

    while len(data) > max_size_kb * 1024:  # Infinite loop if image won't compress!
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70)
        data = buffer.getvalue()
```

**Attack Scenarios:**

1. **Decompression Bomb:**
   ```
   Attacker uploads 10KB image that decompresses to 10GB → Server OOM crash
   ```

2. **Infinite Loop:**
   ```
   Upload 100MB already-compressed image → Compression loop never reduces size → Request hangs
   ```

3. **Path Traversal:**
   ```
   filename = "../../.ssh/authorized_keys.jpg"
   → Could overwrite system files
   ```

**Comprehensive Solution:**

1. **Add Flask file size limit:**
   ```python
   # app.py - Add after app initialization

   # Maximum file size: 10MB
   app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

   @app.errorhandler(413)
   def request_entity_too_large(error):
       return jsonify({
           "error": "File too large",
           "message": "Maximum file size is 10MB"
       }), 413
   ```

2. **Validate file type before processing:**
   ```python
   # app.py
   from werkzeug.utils import secure_filename
   import imghdr

   ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'}
   MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

   def allowed_file(filename):
       return '.' in filename and \
              filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

   @app.route("/analyze", methods=["POST"])
   @limiter.limit("50 per day;20 per hour;10 per minute")
   def analyze():
       if "image" not in request.files:
           return jsonify({"error": "No image file provided"}), 400

       file = request.files["image"]

       if file.filename == "":
           return jsonify({"error": "Empty filename"}), 400

       # Validate file extension
       if not allowed_file(file.filename):
           return jsonify({
               "error": "Invalid file type",
               "message": f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
           }), 400

       # Read file into memory to check actual content
       file_bytes = file.read()

       # Verify it's actually an image
       image_type = imghdr.what(None, h=file_bytes)
       if image_type not in ALLOWED_EXTENSIONS:
           return jsonify({
               "error": "Invalid image format",
               "message": f"File is not a valid image (detected: {image_type})"
           }), 400

       # Save to temp file with safe name
       safe_filename = secure_filename(file.filename)
       with tempfile.NamedTemporaryFile(suffix=f".{image_type}", delete=False) as tmp:
           tmp.write(file_bytes)
           tmp_path = tmp.name

       try:
           result = analyze_image_path(tmp_path)
           return jsonify(result), 200
       except Exception as e:
           app.logger.exception("Analysis failed")
           return jsonify({
               "error": "Analysis failed",
               "message": "Unable to process image"
           }), 500
       finally:
           # Clean up temp file
           if os.path.exists(tmp_path):
               os.unlink(tmp_path)
   ```

3. **Fix the compression function with safety limits:**
   ```python
   # ergo_agent/state.py

   from PIL import Image, UnidentifiedImageError
   import base64
   import io

   def load_and_compress(image_path, max_size_kb=4800, max_dimension=2048):
       """
       Load and compress an image safely with decompression bomb protection.

       Args:
           image_path: Path to image file
           max_size_kb: Maximum output size in KB (default 4.8MB)
           max_dimension: Maximum width/height in pixels (default 2048)

       Returns:
           Base64-encoded JPEG string

       Raises:
           ValueError: If image is invalid or too large
           UnidentifiedImageError: If file is not a valid image
       """

       # Set decompression bomb protection (default is 178 million pixels)
       # This prevents ZIP bomb attacks
       Image.MAX_IMAGE_PIXELS = 89_000_000  # ~9000x9900 pixels max

       try:
           img = Image.open(image_path)

           # Verify the image is valid without loading all data
           img.verify()

           # Re-open after verify() as it closes the file
           img = Image.open(image_path)

       except UnidentifiedImageError:
           raise ValueError("File is not a valid image")
       except Image.DecompressionBombError:
           raise ValueError("Image is too large (possible decompression bomb)")
       except Exception as e:
           raise ValueError(f"Failed to open image: {str(e)}")

       # Check dimensions before processing
       if img.width > max_dimension or img.height > max_dimension:
           raise ValueError(f"Image dimensions ({img.width}x{img.height}) exceed maximum ({max_dimension}x{max_dimension})")

       # Convert RGBA/LA/P with transparency to RGB for JPEG
       if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
           img = img.convert("RGB")
       elif img.mode not in ("RGB", "L"):  # RGB or Grayscale only
           img = img.convert("RGB")

       # Resize large images (maintain aspect ratio)
       img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

       # Try progressive quality reduction with maximum attempts
       max_attempts = 5
       quality = 85
       quality_step = 15

       for attempt in range(max_attempts):
           buffer = io.BytesIO()
           img.save(buffer, format="JPEG", quality=quality, optimize=True)
           data = buffer.getvalue()

           if len(data) <= max_size_kb * 1024:
               # Success!
               return base64.b64encode(data).decode("utf-8")

           # Reduce quality for next attempt
           quality -= quality_step
           if quality < 20:
               # Last resort: reduce dimensions further
               current_width, current_height = img.size
               img = img.resize(
                   (int(current_width * 0.8), int(current_height * 0.8)),
                   Image.Resampling.LANCZOS
               )
               quality = 50  # Reset quality after resize

       # If we get here, image is too large even after compression
       raise ValueError(f"Image could not be compressed below {max_size_kb}KB after {max_attempts} attempts")
   ```

---

## Medium Severity Issues

### 🟡 **MEDIUM-1: Weak Rate Limiting Implementation** -- TODO
**Location:** [app.py:8-10, 23-30](app.py#L8-L30)
**Severity:** MEDIUM

**Problem:**
Rate limiting uses IP address from `get_remote_address()`, which breaks behind proxies:
- All users behind corporate NAT appear as same IP → Rate limit shared
- Attacker can spoof `X-Forwarded-For` header → Bypass rate limits

**Current Code:**
```python
def get_user_identifier():
    # TODO: later: read real user/token here
    return get_remote_address()

limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[]
)
```

**Solution:**

```python
# app.py

from werkzeug.middleware.proxy_fix import ProxyFix

# Add ProxyFix middleware to trust proxy headers
# x_for=1 means trust the first X-Forwarded-For entry
# x_proto=1 means trust X-Forwarded-Proto (http vs https)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

def get_user_identifier():
    """
    Extract user identifier for rate limiting.
    Priority:
    1. Authenticated user (once auth is implemented)
    2. API key from header
    3. Real IP from X-Forwarded-For (behind proxy)
    4. Direct connection IP (development)
    """

    # If authenticated, use user ID
    if hasattr(request, 'authenticated_user'):
        return f"user:{request.authenticated_user}"

    # Use API key if present
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key[:16]}"  # First 16 chars

    # Use real IP (ProxyFix ensures this is correct)
    return f"ip:{get_remote_address()}"

# Apply rate limits with better configuration
limiter = Limiter(
    app=app,
    key_func=get_user_identifier,
    default_limits=[],
    storage_uri="memory://",  # Use Redis in production: "redis://localhost:6379"
    strategy="moving-window",  # More accurate than fixed-window
)

# Add more granular limits
@app.route("/analyze", methods=["POST"])
@limiter.limit(
    "100 per day;30 per hour;10 per 10 minutes",  # More conservative
    error_message="Rate limit exceeded. Please try again later."
)
def analyze():
    # ...
```

**For Production with Redis:**
```python
# requirements.txt
redis==5.2.1
flask-limiter[redis]==3.8.0

# app.py
import os

limiter = Limiter(
    app=app,
    key_func=get_user_identifier,
    storage_uri=os.getenv("REDIS_URL", "redis://localhost:6379"),
    strategy="moving-window"
)
```

---

### 🟡 **MEDIUM-2: Unpinned Dependencies** -- NOT DONE FOR NOW
**Location:** [requirements.txt](requirements.txt)
**Severity:** MEDIUM

**Problem:**
All dependencies are unpinned:
```
flask
langgraph
langchain-anthropic
pillow
```

This causes:
- **Security risk:** Automatic installation of vulnerable versions
- **Breaking changes:** Major version updates break your app
- **Non-reproducible builds:** Different developers get different versions

**Real Example:**
Pillow <10.3.0 had CVE-2024-28219 (arbitrary code execution)

**Solution:**

1. **Generate pinned requirements:**
   ```bash
   # Install current versions
   pip install flask langgraph langchain-anthropic langchain-core pandas openpyxl python-dotenv pillow flask-limiter flask-cors

   # Export exact versions
   pip freeze > requirements.txt
   ```

2. **Create layered requirements:**

   **requirements.in** (human-readable):
   ```
   # Web framework
   flask>=3.1.0,<4.0.0
   flask-limiter>=3.8.0,<4.0.0
   flask-cors>=5.0.0,<6.0.0
   werkzeug>=3.1.0,<4.0.0
   waitress>=3.0.0,<4.0.0

   # AI/ML
   langgraph>=0.2.0,<0.3.0
   langchain-anthropic>=0.3.0,<0.4.0
   langchain-core>=0.3.0,<0.4.0

   # Data processing
   pandas>=2.2.0,<3.0.0
   openpyxl>=3.1.0,<4.0.0
   pillow>=11.0.0,<12.0.0

   # Utilities
   python-dotenv>=1.0.0,<2.0.0
   ```

   **requirements.txt** (auto-generated with exact versions):
   ```bash
   pip-compile requirements.in
   ```

3. **Set up automated security scanning:**

   **.github/workflows/security.yml:**
   ```yaml
   name: Security Scan

   on: [push, pull_request]

   jobs:
     security:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with:
             python-version: '3.11'
         - name: Install dependencies
           run: pip install pip-audit
         - name: Run security audit
           run: pip-audit -r requirements.txt
   ```

4. **Use Dependabot:**

   **.github/dependabot.yml:**
   ```yaml
   version: 2
   updates:
     - package-ecosystem: "pip"
       directory: "/"
       schedule:
         interval: "weekly"
       open-pull-requests-limit: 10
   ```

---

### 🟡 **MEDIUM-3: Missing Error Handling in Service Layer** -- ✅
**Location:** [ergo_agent/service.py:44](ergo_agent/service.py#L44)
**Severity:** MEDIUM

**Problem:**
Assumes `recommendations` list always has items:
```python
rec = final_state["recommendations"][0]  # IndexError if empty!
return {
    "observed_risks": rec.get("observed_risks", []),
    # ...
}
```

If the LLM fails or returns unexpected data, this crashes with an unhelpful error.

**Solution:**

```python
# ergo_agent/service.py

def analyze_image_path(image_path: str) -> dict:
    """
    Analyze an image for ergonomic risks.

    Args:
        image_path: Path to image file

    Returns:
        dict: Analysis results with risk assessment and recommendations

    Raises:
        ValueError: If image is invalid
        RuntimeError: If analysis fails
    """
    try:
        image_base64 = load_and_compress(image_path)
    except ValueError as e:
        # Invalid image or compression failed
        raise ValueError(f"Image processing failed: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Unexpected error loading image: {str(e)}")

    # Initialize state
    initial_state = {
        "image_base64": image_base64,
        "image_path": image_path,
        "activity_category": "",
        "activity_title": "",
        "scene_context": "",
        "relevant_checks": [],
        "risk_analysis": [],
        "flagged_risks": [],
        "recommendations": [],
        "overall_risk_level": None,
        "messages": [],
        "should_skip_ergonomics": False,
        "filter_result": None,
    }

    try:
        final_state = _graph.invoke(initial_state)
    except Exception as e:
        # Log the full error for debugging
        print(f"Graph execution failed: {e}")
        raise RuntimeError(f"Analysis pipeline failed: {str(e)}")

    # Handle skipped analysis
    if final_state.get("should_skip_ergonomics"):
        fr = final_state.get("filter_result") or {}
        return {
            "image_path": image_path,
            "activity_category": final_state.get("activity_category", ""),
            "activity_title": final_state.get("activity_title", ""),
            "scene_context": final_state.get("scene_context", ""),
            "skipped": True,
            "skip_reason": fr.get("reason", "Image not suitable for ergonomic assessment."),
            "risk_analysis": [],
            "observed_risks": [],
            "recommendations": [],
            "overall_risk_level": None,
        }

    # Safely extract recommendations
    recommendations_list = final_state.get("recommendations", [])

    if not recommendations_list:
        # Fallback if no recommendations generated
        print("Warning: No recommendations generated by pipeline")
        return {
            "image_path": image_path,
            "activity_category": final_state.get("activity_category", "UNKNOWN"),
            "activity_title": final_state.get("activity_title", ""),
            "scene_context": final_state.get("scene_context", ""),
            "skipped": False,
            "skip_reason": None,
            "risk_analysis": final_state.get("risk_analysis", []),
            "observed_risks": [],
            "recommendations": ["Analysis completed but no specific recommendations were generated."],
            "overall_risk_level": "UNDETERMINED",
        }

    # Extract first recommendation safely
    rec = recommendations_list[0]

    return {
        "image_path": image_path,
        "activity_category": final_state.get("activity_category", ""),
        "activity_title": final_state.get("activity_title", ""),
        "scene_context": final_state.get("scene_context", ""),
        "skipped": False,
        "skip_reason": None,
        "risk_analysis": final_state.get("risk_analysis", []),
        "observed_risks": rec.get("observed_risks", []),
        "recommendations": rec.get("recommendations", []),
        "overall_risk_level": rec.get("overall_risk_level", "UNDETERMINED"),
    }
```

---

## Low Severity Issues

### 🟢 **LOW-1: Secrets Validation Not Centralized** -- ✅ (centralised in config.py)
**Location:** [ergo_agent/config.py](ergo_agent/config.py), [app.py](app.py)
**Severity:** LOW

**Problem:**
`config.py` validates API keys but is never imported by `app.py`. If keys are missing, the app starts successfully but crashes on first request.

**Solution:**

```python
# app.py - Add at the very top, before other imports

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Validate required secrets at startup
REQUIRED_ENV_VARS = [
    "ANTHROPIC_API_KEY",
]

OPTIONAL_ENV_VARS = {
    "LANGCHAIN_API_KEY": "LangChain tracing will be disabled",
}

missing_required = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]

if missing_required:
    raise RuntimeError(
        f"Missing required environment variables: {', '.join(missing_required)}\n"
        f"Please create a .env file with these variables."
    )

# Warn about missing optional vars
for var, message in OPTIONAL_ENV_VARS.items():
    if not os.getenv(var):
        print(f"⚠️  {var} not set - {message}")

# Now import application modules
from flask import Flask, request, jsonify
# ... rest of imports
```

---

### 🟢 **LOW-2: Missing Data File Validation** 
**Location:** [ergo_agent/state.py:14-18](ergo_agent/state.py#L14-L18)
**Severity:** LOW

**Problem:**
`activities.json` loaded at import time without error handling. If file is missing/corrupt, server crashes with unclear error.

**Solution:**

```python
# ergo_agent/state.py

import json
import os
from pathlib import Path

# ============================================================================
# DATA LOADING
# ============================================================================

def load_ergonomic_data():
    """Load ergonomic activities data with validation."""

    data_file = Path(__file__).parent.parent / "activities.json"

    if not data_file.exists():
        raise FileNotFoundError(
            f"activities.json not found at {data_file}\n"
            f"This file is required for the application to function."
        )

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"activities.json is not valid JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to load activities.json: {e}")

    # Validate structure
    if not isinstance(data, dict):
        raise ValueError("activities.json must be a JSON object")

    # Validate each activity has required fields
    for activity, checks in data.items():
        if not isinstance(checks, list):
            raise ValueError(f"Activity '{activity}' must have a list of checks")

        for i, check in enumerate(checks):
            required_fields = ["cue", "body_region", "risk", "quick_fix", "long_term_practice"]
            missing = [f for f in required_fields if f not in check]
            if missing:
                raise ValueError(
                    f"Activity '{activity}', check {i}: missing fields {missing}"
                )

    print(f"✅ Loaded {len(data)} ergonomic activity categories")
    return data

# Load data at module initialization
try:
    ERGONOMIC_DATA = load_ergonomic_data()
    ACTIVITY_CATEGORIES = list(ERGONOMIC_DATA.keys())
except Exception as e:
    print(f"🛑 FATAL: Failed to load ergonomic data: {e}")
    raise
```

---

### 🟢 **LOW-3: Insufficient Logging** -- ✅
**Location:** Throughout application
**Severity:** LOW

**Problem:**
No structured logging. Debug information only printed to console. Hard to troubleshoot production issues.

**Solution:**

```python
# app.py

import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(app):
    """Configure application logging."""

    # Create logs directory
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    # File handler (for production)
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10_000_000,  # 10MB
        backupCount=10
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # Configure app logger
    app.logger.addHandler(console_handler)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)

    # Log startup
    app.logger.info("Application starting up")
    app.logger.info(f"Python version: {sys.version}")
    app.logger.info(f"Flask version: {flask.__version__}")

# Call during app initialization
setup_logging(app)

# Use throughout app:
@app.route("/analyze", methods=["POST"])
def analyze():
    app.logger.info(f"Analysis request from {get_remote_address()}")

    try:
        # ... processing
        app.logger.info(f"Analysis completed successfully for {file.filename}")
        return jsonify(result), 200
    except Exception as e:
        app.logger.error(f"Analysis failed: {e}", exc_info=True)
        return jsonify({"error": "Analysis failed"}), 500
```

---

## Best Practices & Code Quality

### 📘 **BP-1: Add Request ID Tracking**

**Benefit:** Correlate logs across distributed system, easier debugging

```python
# app.py

import uuid

@app.before_request
def add_request_id():
    """Add unique request ID for tracking."""
    request.id = request.headers.get('X-Request-ID', str(uuid.uuid4()))

@app.after_request
def add_request_id_header(response):
    """Include request ID in response."""
    response.headers['X-Request-ID'] = request.id
    return response

# Use in logs:
app.logger.info(f"[{request.id}] Analysis started")
```

---

### 📘 **BP-2: Add Health Check Endpoint** -- ✅

**Benefit:** Load balancer monitoring, Kubernetes readiness probes

```python
@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring."""

    checks = {
        "status": "healthy",
        "checks": {
            "api_key": bool(os.getenv("ANTHROPIC_API_KEY")),
            "data_file": os.path.exists("activities.json"),
        }
    }

    # Overall health
    all_healthy = all(checks["checks"].values())
    status_code = 200 if all_healthy else 503
    checks["status"] = "healthy" if all_healthy else "unhealthy"

    return jsonify(checks), status_code

@app.route("/ready", methods=["GET"])
def readiness_check():
    """Readiness check - is app ready to serve traffic?"""
    # Could add check for model loading, database connection, etc.
    return jsonify({"ready": True}), 200
```

---

### 📘 **BP-3: Add Input Validation Schema** -- ✅

**Benefit:** Catch bad requests early, better error messages

```python
# app.py

from marshmallow import Schema, fields, ValidationError

class AnalyzeRequestSchema(Schema):
    image = fields.Raw(required=True)

@app.route("/analyze", methods=["POST"])
def analyze():
    # Validate request
    try:
        schema = AnalyzeRequestSchema()
        schema.load(request.files)
    except ValidationError as e:
        return jsonify({"error": "Invalid request", "details": e.messages}), 400

    # ... rest of processing
```

---

### 📘 **BP-4: Add Timeouts to LLM Calls** -- ✅

**Benefit:** Prevent hung requests, better resource utilization

```python
# ergo_agent/nodes.py

def make_model(model_name: str = "claude-sonnet-4-20250514", timeout: int = 60):
    """Create Anthropic model with timeout."""
    base = ChatAnthropic(
        model=model_name,
        temperature=0,
        max_retries=3,
        timeout=timeout,  # Add timeout
        max_tokens=4096,
    )
    return base

# Use shorter timeout for fallback model
llm = make_model("claude-sonnet-4-20250514", timeout=60)
llm_fallback = make_model("claude-haiku-3-20241022", timeout=30)
```

---

### 📘 **BP-5: Add Prometheus Metrics** 

**Benefit:** Production observability, performance monitoring

```python
# requirements.txt
prometheus-flask-exporter==0.23.1

# app.py
from prometheus_flask_exporter import PrometheusMetrics

metrics = PrometheusMetrics(app)

# Auto-instruments all endpoints
# Access metrics at /metrics

# Add custom metrics
analysis_duration = metrics.histogram(
    'image_analysis_duration_seconds',
    'Time spent analyzing images',
    labels={'activity': lambda: request.view_args.get('activity', 'unknown')}
)

@app.route("/analyze", methods=["POST"])
@analysis_duration.time()
def analyze():
    # ... automatically timed
```

---

## Quick Reference - Priority Fixes

**Implement these fixes in order of priority:**

### 🔴 IMMEDIATE (Do Today)
1. **Revoke exposed API keys** and remove from git history
2. **Add authentication** to `/analyze` endpoint
3. **Disable debug mode** and use production WSGI server
4. **Add file upload validation** (size, type, decompression bomb protection)

### 🟡 HIGH PRIORITY (This Week)
5. **Fix rate limiting** with ProxyFix middleware
6. **Pin dependencies** and set up security scanning
7. **Add error handling** in service layer
8. **Add comprehensive logging**

### 🟢 GOOD TO HAVE (This Month)
9. **Add health check endpoints**
10. **Add request ID tracking**
11. **Add input validation schemas**
12. **Set up monitoring/metrics**

---

## Testing the Fixes

After implementing fixes, test with these scenarios:

```bash
# 1. Test without API key
curl -X POST http://localhost:8000/analyze \
  -F "image=@test.jpg"
# Expected: 401 Unauthorized

# 2. Test with valid API key
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: your_key_here" \
  -F "image=@test.jpg"
# Expected: 200 OK with analysis results

# 3. Test file size limit
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: your_key_here" \
  -F "image=@huge_file.jpg"  # >10MB
# Expected: 413 Request Entity Too Large

# 4. Test invalid file type
curl -X POST http://localhost:8000/analyze \
  -H "X-API-Key: your_key_here" \
  -F "image=@malware.exe"
# Expected: 400 Bad Request (Invalid file type)

# 5. Test rate limiting
for i in {1..15}; do
  curl -X POST http://localhost:8000/analyze \
    -H "X-API-Key: your_key_here" \
    -F "image=@test.jpg"
done
# Expected: First 10 succeed, rest get 429 Too Many Requests

# 6. Test health endpoint
curl http://localhost:8000/health
# Expected: 200 OK with health status
```

---

## Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/3.1.x/security/)
- [Pillow Security Docs](https://pillow.readthedocs.io/en/stable/releasenotes/)
- [Anthropic API Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/best-practices)

---

