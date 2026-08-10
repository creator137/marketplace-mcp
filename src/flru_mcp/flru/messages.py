from __future__ import annotations


class MessageService:
    async def list_conversations(self) -> dict:
        return {"error": "NOT_IMPLEMENTED", "reason": "FL.ru message endpoints were not verified during public-page research."}

    async def get_conversation(self, conversation_id: str) -> dict:
        return {"error": "NOT_IMPLEMENTED", "conversation_id": conversation_id}

    async def send_message(self, conversation_id: str, text: str) -> dict:
        return {"error": "NOT_IMPLEMENTED", "conversation_id": conversation_id, "reason": "Sending is intentionally unavailable until form/endpoints are verified."}

