from flask import Flask, request, jsonify
import tempfile
from ergo_agent.service import analyze_image_path
app = Flask(__name__)

@app.route("/analyze", methods=["POST"])
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
