"""A small, security-conscious Flask API.

The application itself is intentionally minimal — it exists to exercise the
CI/CD pipeline, not to be a feature-rich service. It exposes a health check
and a simple echo endpoint with light input validation.
"""

from __future__ import annotations

from flask import Flask, jsonify, request


def create_app() -> Flask:
    """Application factory. Keeps the app testable and import-safe."""
    app = Flask(__name__)

    # Cap request body size to reduce abuse surface (1 MB).
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

    @app.get("/health")
    def health():
        """Liveness probe used by the container and any orchestrator."""
        return jsonify(status="ok"), 200

    @app.get("/version")
    def version():
        """Expose a build version for traceability in deployments."""
        return jsonify(version=app.config.get("APP_VERSION", "dev")), 200

    @app.post("/echo")
    def echo():
        """Echo a JSON 'message' back to the caller after validation.

        Demonstrates explicit input handling rather than trusting the body.
        """
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or "message" not in data:
            return jsonify(error="JSON body with a 'message' field required"), 400

        message = data["message"]
        if not isinstance(message, str):
            return jsonify(error="'message' must be a string"), 400
        if len(message) > 500:
            return jsonify(error="'message' must be 500 characters or fewer"), 400

        return jsonify(message=message), 200

    return app


# WSGI entrypoint for gunicorn: "app.main:app"
app = create_app()


if __name__ == "__main__":
    # Local development only. Production runs under gunicorn (see Dockerfile).
    app.run(host="127.0.0.1", port=8000)
