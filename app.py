# app.py (Health Check Server)
from flask import Flask
import os # Add os import for PORT

app = Flask(__name__)

@app.route('/')
def hello_world():
    # Health check ke liye ek simple response
    return 'GrryMatters - Bot Health OK!'

if __name__ == "__main__":
    # Koyeb automatically PORT variable set karta hai
    port = int(os.getenv('PORT', 8000))
    print(f"Flask health check server starting on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

