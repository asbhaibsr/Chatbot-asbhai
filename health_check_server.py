# health_check_server.py
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def health_check():
    """Simple health check endpoint for Koyeb."""
    return jsonify(status="Health Check OK"), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    print(f"Health check server starting on 0.0.0.0:{port}")
    # Using debug=False and use_reloader=False for production
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
