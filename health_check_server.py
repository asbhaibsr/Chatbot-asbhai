# health_check_server.py
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def health_check():
    """Simple health check endpoint for Koyeb."""
    # You can return any message, as long as it's a 200 OK status
    return jsonify(status="Bot is running and healthy!"), 200

if __name__ == '__main__':
    # Koyeb automatically sets the PORT environment variable
    # We'll use 8000 as a fallback if PORT is not set
    port = int(os.getenv('PORT', 8000))
    print(f"Health check server starting on 0.0.0.0:{port}") # For logs
    # Use debug=False and use_reloader=False for production
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
