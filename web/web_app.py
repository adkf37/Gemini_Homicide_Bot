"""Flask web interface for the Gemini Homicide Bot."""
from __future__ import annotations

import logging
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request

from main import LocalLLMApp


# Configure logging for clearer web output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder="templates", static_folder="static")

# Lazily initialized chat application instance
_llm_app: LocalLLMApp | None = None


def get_llm_app() -> LocalLLMApp:
    """Return a singleton instance of ``LocalLLMApp`` for request handling."""
    global _llm_app
    if _llm_app is None:
        logger.info("Initialising LocalLLMApp for web usage")
        _llm_app = LocalLLMApp()
    return _llm_app


@app.route("/")
def index() -> str:
    """Serve the chat interface."""
    return render_template("index.html")


@app.post("/api/chat")
def chat() -> tuple[Any, int]:
    """Process chat requests from the frontend."""
    data: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    question: str = (data.get("question") or "").strip()
    use_tools = data.get("use_tools", True)

    if not question:
        return jsonify({"error": "Question is required."}), 400

    llm_app = get_llm_app()

    try:
        # Allow the frontend to toggle tool usage.
        if use_tools:
            answer = llm_app.ask_question_with_mcp(question)
            used_tools = True
        else:
            answer = llm_app.ask_question(question)
            used_tools = False

        return jsonify({
            "answer": answer,
            "used_tools": used_tools
        }), 200
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Error while handling chat request")
        return jsonify({"error": str(exc)}), 500


@app.get("/api/health")
def health() -> Dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
