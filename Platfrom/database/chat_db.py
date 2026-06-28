"""
SilverTrade AI — Chat Database
==============================
Stores chat conversations and messages for the AI trading assistant.
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from database.db_config import get_db_engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Create chat conversations table if it doesn't exist."""
    engine = get_db_engine()

    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS chat_conversations (
                id SERIAL PRIMARY KEY,
                apikey_hash VARCHAR(255) NOT NULL,
                conversation_id VARCHAR(255) UNIQUE NOT NULL,
                title VARCHAR(500),
                messages JSONB DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_chat_apikey ON chat_conversations(apikey_hash)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_chat_conversation_id ON chat_conversations(conversation_id)
        """)
        )

        conn.execute(
            text("""
            CREATE INDEX IF NOT EXISTS idx_chat_created_at ON chat_conversations(created_at DESC)
        """)
        )

        conn.commit()

    logger.info("Chat database initialised")


def save_conversation_message(
    apikey_hash: str,
    conversation_id: str,
    user_message: str,
    assistant_reply: str,
    title: Optional[str] = None,
) -> int:
    """Save a conversation message to the database."""
    engine = get_db_engine()

    with engine.connect() as conn:
        # Check if conversation exists
        result = conn.execute(
            "SELECT id, messages FROM chat_conversations WHERE conversation_id = %s",
            (conversation_id,),
        ).fetchone()

        if result:
            # Update existing conversation
            existing_messages = result[1] if isinstance(result[1], list) else []
            new_messages = existing_messages + [
                {
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                {
                    "role": "assistant",
                    "content": assistant_reply,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ]

            if not title and len(existing_messages) == 0:
                title = user_message[:100] + "..." if len(user_message) > 100 else user_message

            conn.execute(
                """UPDATE chat_conversations 
                   SET messages = %s, updated_at = CURRENT_TIMESTAMP, title = COALESCE(%s, title)
                   WHERE conversation_id = %s""",
                (new_messages, title, conversation_id),
            )
            conn.commit()
            return result[0]
        else:
            # Create new conversation
            new_title = title or (
                user_message[:100] + "..." if len(user_message) > 100 else user_message
            )
            new_messages = [
                {
                    "role": "user",
                    "content": user_message,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                {
                    "role": "assistant",
                    "content": assistant_reply,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ]

            result = conn.execute(
                """INSERT INTO chat_conversations (apikey_hash, conversation_id, title, messages)
                   VALUES (%s, %s, %s, %s)
                   RETURNING id""",
                (apikey_hash, conversation_id, new_title, new_messages),
            )
            conn.commit()
            return result.fetchone()[0]


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Get a single conversation by ID."""
    engine = get_db_engine()

    with engine.connect() as conn:
        result = conn.execute(
            "SELECT * FROM chat_conversations WHERE conversation_id = %s", (conversation_id,)
        ).fetchone()

        if result:
            return {
                "id": result[0],
                "apikey_hash": result[1],
                "conversation_id": result[2],
                "title": result[3],
                "messages": result[4],
                "created_at": result[5].isoformat() if result[5] else None,
                "updated_at": result[6].isoformat() if result[6] else None,
            }
        return None


def get_conversations(apikey_hash: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Get all conversations for a user."""
    engine = get_db_engine()

    with engine.connect() as conn:
        result = conn.execute(
            """SELECT * FROM chat_conversations 
               WHERE apikey_hash = %s 
               ORDER BY updated_at DESC 
               LIMIT %s""",
            (apikey_hash, limit),
        ).fetchall()

        conversations = []
        for row in result:
            conversations.append(
                {
                    "id": row[0],
                    "apikey_hash": row[1],
                    "conversation_id": row[2],
                    "title": row[3],
                    "messages": row[4],
                    "created_at": row[5].isoformat() if row[5] else None,
                    "updated_at": row[6].isoformat() if row[6] else None,
                }
            )

        return conversations


def hash_apikey(apikey: str) -> str:
    """Simple hash of API key for privacy."""
    import hashlib

    return hashlib.sha256(apikey.encode()).hexdigest()
