"""
Weather Dashboard: a small Flask app to WATCH what the Agent Bricks
agent is doing with the Weather MCP server. This app displays recent
weather queries, predictions, and travel recommendations made by the agent.

Deploy this as its OWN Databricks App (separate from weather_mcp_server.py) -
one app serves MCP tool calls, the other serves the human-facing UI.

Run locally:
    python app.py
"""

import os
from flask import Flask, jsonify, render_template, request
from datetime import datetime
import query_logger

app = Flask(__name__)


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


@app.errorhandler(Exception)
def handle_exception(err):
    """Ensure all unhandled errors return JSON (not an HTML error page)."""
    status_code = getattr(err, "code", 500)
    if not isinstance(status_code, int):
        status_code = 500
    return jsonify({"error": str(err)}), status_code


@app.route("/")
def index():
    """Dashboard UI showing recent weather agent queries."""
    return render_template("index.html")


@app.route("/api/queries")
def api_queries():
    """Get recent weather queries made by the agent."""
    limit = int(request.args.get("limit", 50))
    return jsonify(query_logger.get_recent_queries(limit))


@app.route("/api/stats")
def api_stats():
    """Get aggregated statistics about weather queries."""
    return jsonify(query_logger.get_query_stats())


@app.route("/api/log", methods=["POST"])
def api_log():
    """Log a new weather query (called by the MCP server)."""
    data = request.get_json()
    query_logger.log_query(data)
    return jsonify({"status": "logged"})


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 8002))
    app.run(debug=True, host=host, port=port)
