import logging
from flask import Blueprint, request, jsonify
from routes.auth import token_required
from ai import call_chatbot_groq

bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)


@bp.route("/api/chat", methods=["POST"])
@token_required
def chat():
    data = request.get_json() or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"reply": {"action": "chat", "message": "Please type a question."}}), 400

    try:
        reply = call_chatbot_groq(message)
    except Exception as e:
        logger.error("Chatbot error: %s", e)
        reply = {"action": "chat", "message": "Error occurred. Please try again."}

    return jsonify({"reply": reply})
