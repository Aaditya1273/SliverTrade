"""
SilverTrade AI — RAG Service
=============================
Retrieval-Augmented Generation for the AI trading assistant.

Uses ChromaDB (persistent, local) with OpenAI text-embedding-3-small
to store and retrieve trading knowledge chunks on every chat message.

Usage:
    from services.rag_service import rag

    # On startup (once):
    rag.initialize()

    # Before every LLM call:
    chunks = rag.retrieve("What is a bullish engulfing pattern?")
    # chunks = ["Chunk 1 text...", "Chunk 2 text...", ...]
"""

import json
import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────
_RAG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "rag")
_CHROMA_PATH = os.path.join(_RAG_DIR, "chroma_db")

# ── Embedding model ────────────────────────────────────────────────────
_EMBEDDING_MODEL = "text-embedding-3-small"


class RagService:
    """ChromaDB-backed RAG service for the AI trading assistant."""

    def __init__(self) -> None:
        self._client = None
        self._collection = None
        self._initialized = False

    # ── Public API ──────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Initialize ChromaDB client and collection. Idempotent (safe to call multiple times)."""
        if self._initialized:
            return

        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set — RAG service disabled")
            return

        try:
            import chromadb

            # Ensure data directory exists
            os.makedirs(_CHROMA_PATH, exist_ok=True)

            # Create persistent client
            self._client = chromadb.PersistentClient(path=_CHROMA_PATH)

            # For OpenRouter keys, embeddings go through the same OpenAI API
            # ChromaDB's OpenAIEmbeddingFunction doesn't support custom base_url,
            # so we need to use the OpenAI API directly for embeddings.
            # If using OpenRouter, embeddings won't work (OpenRouter doesn't
            # support the embedding API). In that case, we fall back to a
            # lightweight sentence-transformer for local embeddings.
            import chromadb.utils.embedding_functions as _ef

            if api_key.startswith("sk-or-"):
                # OpenRouter doesn't support embeddings — use local model instead
                logger.info("OpenRouter key detected — using local embedding model for RAG")
                openai_ef = _ef.DefaultEmbeddingFunction()
            else:
                openai_ef = _ef.OpenAIEmbeddingFunction(
                    api_key=api_key,
                    model_name=_EMBEDDING_MODEL,
                )

            # Get or create collection
            collection_name = "trading_knowledge"
            try:
                self._collection = self._client.get_collection(
                    name=collection_name,
                    embedding_function=openai_ef,
                )
                count = self._collection.count()
                logger.info("RAG collection loaded (%d chunks)", count)
            except Exception:
                # Collection doesn't exist — create and seed it
                logger.info("Creating RAG collection and seeding knowledge base...")
                self._collection = self._client.create_collection(
                    name=collection_name,
                    embedding_function=openai_ef,
                )
                self._seed_knowledge_base()

            self._initialized = True
            logger.info("RAG service initialized")

        except Exception as e:
            logger.warning("Failed to initialize RAG service: %s", e)
            self._initialized = False

    def retrieve(self, query: str, n_results: int = 5) -> List[str]:
        """Retrieve the top-N most relevant knowledge chunks for a query.

        Args:
            query: User's message or search query.
            n_results: Number of chunks to retrieve (default 5).

        Returns:
            List of knowledge chunk text strings. Empty list if unavailable.
        """
        if not self._initialized or self._collection is None:
            return []

        if not query or not query.strip():
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
            )

            documents = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]

            # Filter by relevance threshold (cosine distance 0=identical, 2=opposite)
            # 0.9 threshold keeps relevant chunks while filtering noise
            filtered: List[str] = []
            for i, doc in enumerate(documents):
                if doc and (not distances or i >= len(distances) or distances[i] < 0.9):
                    filtered.append(doc)

            return filtered

        except Exception as e:
            logger.warning("RAG retrieval failed: %s", e)
            return []

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ── Private helpers ─────────────────────────────────────────────────

    def _seed_knowledge_base(self) -> None:
        """Index all knowledge chunks from the knowledge base file."""
        if self._collection is None:
            return

        try:
            # Import knowledge chunks dynamically from the knowledge base module
            from services.trading_knowledge_base import KNOWLEDGE_CHUNKS

            documents = []
            metadatas = []
            ids = []

            for i, chunk in enumerate(KNOWLEDGE_CHUNKS):
                documents.append(chunk["text"])
                metadatas.append(
                    {
                        "category": chunk.get("category", "general"),
                        "tags": ",".join(chunk.get("tags", [])),
                    }
                )
                ids.append(f"kb_{i:03d}")

            # Add in batches of 10 to avoid overwhelming the embedding API
            batch_size = 10
            for start in range(0, len(documents), batch_size):
                end = min(start + batch_size, len(documents))
                self._collection.add(
                    documents=documents[start:end],
                    metadatas=metadatas[start:end],
                    ids=ids[start:end],
                )

            logger.info("Seeded %d knowledge chunks into RAG collection", len(documents))

        except ImportError:
            logger.warning("trading_knowledge_base module not found — cannot seed RAG")
        except Exception as e:
            logger.warning("Failed to seed knowledge base: %s", e)


# ── Singleton instance ─────────────────────────────────────────────────
rag = RagService()
