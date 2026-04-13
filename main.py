from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import jwt

app = Flask(__name__)
CORS(app)

SECRET_KEY = os.getenv("SECRET_KEY", "secret-key")

# Mock data
users = {}
selected_folders = {}

@app.route("/health", methods=["GET"])
def health():
    return {"status": "healthy"}

@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return {"error": "Email and password required"}, 400

    if email in users:
        return {"error": "User already exists"}, 400

    users[email] = password
    token = jwt.encode({"email": email}, SECRET_KEY, algorithm="HS256")

    return {"access_token": token, "user": {"email": email}}, 201

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if email not in users or users[email] != password:
        return {"error": "Invalid credentials"}, 401

    token = jwt.encode({"email": email}, SECRET_KEY, algorithm="HS256")
    return {"access_token": token, "user": {"email": email}}

@app.route("/api/google/oauth-url", methods=["GET"])
def oauth_url():
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI")
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={redirect_uri}&response_type=code&scope=https://www.googleapis.com/auth/drive.readonly"
    }

@app.route("/api/google/folders", methods=["GET"])
def get_folders():
    return {
        "folders": [
            {"id": "folder1", "name": "Project A"},
            {"id": "folder2", "name": "Project B"},
        ]
    }

@app.route("/api/google/select-folder", methods=["POST"])
def select_folder():
    data = request.json
    folder_id = data.get("folder_id")
    selected_folders["current"] = folder_id
    return {"selected_folder_id": folder_id}

@app.route("/api/google/sync", methods=["POST"])
def sync():
    return {"status": "synced", "count": 0}

@app.route("/api/documents", methods=["GET"])
def get_documents():
    return {"documents": []}

@app.errorhandler(404)
def not_found(e):
    return {"error": "Not found"}, 404

@app.errorhandler(500)
def error(e):
    return {"error": str(e)}, 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
