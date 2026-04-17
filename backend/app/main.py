"""
Nivesh Flask Application — internal service proxied by Next.js.
Handles PDF parsing, mfapi.in integration, and portfolio operations.
"""
import logging

from flask import Flask
from flask_cors import CORS

from app.routers.upload import upload_bp
from app.routers.portfolio import portfolio_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

app = Flask(__name__)

# CORS — only Next.js server should call this, but allow localhost for dev
CORS(app, origins=["http://localhost:3000", "http://127.0.0.1:3000"])

app.register_blueprint(upload_bp)
app.register_blueprint(portfolio_bp)


@app.get("/health")
def health():
    return {"status": "healthy", "service": "Nivesh Flask"}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, debug=True)
