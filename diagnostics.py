"""
Taurus API Diagnostics
A minimal app to diagnose deployment issues
"""

from flask import Flask, jsonify
import sys
import os
import platform

app = Flask(__name__)

@app.route('/')
def index():
    return """
    <html>
    <head><title>Taurus API Diagnostics</title></head>
    <body>
        <h1>Taurus API Diagnostics</h1>
        <p>This is a diagnostic version of the Taurus API.</p>
        <p>Use /health to check system status.</p>
        <p>Use /info for detailed environment information.</p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "version": "diagnostic"})

@app.route('/info')
def info():
    """Return detailed information about the environment"""
    return jsonify({
        "python_version": sys.version,
        "platform": platform.platform(),
        "environment_variables": dict(os.environ),
        "working_directory": os.getcwd(),
        "directory_contents": os.listdir(),
    })

if __name__ == '__main__':
    # Get port from environment variable for Azure deployment
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 