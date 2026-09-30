import os
from flask import Flask, jsonify

app = Flask(__name__)

# Read version from environment variable (default: v1)
APP_VERSION = os.getenv("APP_VERSION", "v1.0")

@app.route("/")
def home():
    return jsonify({
        "version": APP_VERSION,
        "status": "Healthy",
        "message": f"Hello from App version {APP_VERSION}!"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)