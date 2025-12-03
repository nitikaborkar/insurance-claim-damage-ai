import os
from dotenv import load_dotenv

load_dotenv()  # Load .env but never commit it

# Validate required secrets at startup
required_vars = ["ANTHROPIC_API_KEY", "LANGCHAIN_API_KEY"]
missing = [var for var in required_vars if not os.getenv(var)]
if missing:
    raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

from flask import Flask, request, jsonify
import tempfile
from ergo_agent.service import analyze_image_path
from flask_limiter import Limiter
from flask_cors import CORS
from flask_limiter.util import get_remote_address

def get_user_identifier():
    # TODO: later: read real user/token here
    return get_remote_address()

#later implementation for user key extraction
# def get_user_key():
#     auth = request.headers.get("Authorization", "")
#     if auth.startswith("Bearer "):
#         return auth.split(" ", 1)[1].strip()  # token string
#     return get_remote_address()  # fallback


app = Flask(__name__)
CORS(app, resources={r"/analyze": {"origins": ["https://app.balanceflo.ai", "http://localhost:5173", "https://personal.balanceflo.ai", "https://staging-personal.balanceflo.ai"]}})

limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=[]
)
limiter.init_app(app)

@app.route("/analyze", methods=["POST"])
@limiter.limit("50 per day;20 per hour;10 per minute")
def analyze():
    # Expect multipart/form-data with "image" field
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    # Save to temp file
    with tempfile.NamedTemporaryFile(suffix=file.filename, delete=True) as tmp:
        file.save(tmp.name)
        result = analyze_image_path(tmp.name)

    return jsonify(result), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
