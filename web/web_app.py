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
            answer, trace = llm_app.ask_question_with_mcp(question)
            trace = trace or {}
            tool_calls = trace.get("tool_calls") or []
            tool_executions = trace.get("tool_executions") or []
            if not tool_calls and trace.get("tool_call"):
                tool_calls = [trace["tool_call"]]
            if not tool_executions and trace.get("tool_execution"):
                tool_executions = [trace["tool_execution"]]

            tool_names = [
                call.get("name") for call in tool_calls
                if isinstance(call, dict) and call.get("name")
            ]
            raw_results = [
                execution.get("raw_result") for execution in tool_executions
                if isinstance(execution, dict) and not execution.get("error")
            ]
            used_tools = bool(tool_executions)

            payload = {
                "answer": answer,
                "used_tools": used_tools,
                "tool_name": tool_names[-1] if tool_names else None,
                "tool_names": tool_names,
                "tool_data": raw_results[-1] if len(raw_results) == 1 else raw_results,
                "interaction_trace": trace,
            }
        else:
            answer = llm_app.ask_question(question)
            payload = {
                "answer": answer,
                "used_tools": False,
                "tool_name": None,
                "tool_data": None,
                "interaction_trace": None,
            }

        return jsonify(payload), 200
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.exception("Error while handling chat request")
        return jsonify({"error": str(exc)}), 500


@app.get("/api/health")
def health() -> Dict[str, str]:
    """Simple health-check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
