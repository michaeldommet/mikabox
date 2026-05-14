"""
MikaBox Embedding Service
=========================
Handles vector generation and cosine similarity for Lightweight RAG memory.
"""

import json
import logging
from typing import List, Optional

logger = logging.getLogger("mikabox.embeddings")

class EmbeddingService:
    def __init__(self):
        self._available = False
        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np
            self.np = np
            logger.info("Loading sentence-transformers model ('all-MiniLM-L6-v2')...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            self._available = True
            logger.info("Embedding model loaded successfully.")
        except ImportError:
            logger.warning("sentence-transformers or numpy not installed. RAG memory is disabled.")
            self._available = False
        except Exception as e:
            logger.error("Failed to load embedding model: %s", e)
            self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def encode(self, text: str) -> List[float]:
        """Generate a vector embedding for the given text."""
        if not self._available:
            return []
        return self.model.encode(text).tolist()

    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute the cosine similarity between two vectors (-1.0 to 1.0)."""
        if not self._available or not vec1 or not vec2:
            return 0.0
        v1 = self.np.array(vec1)
        v2 = self.np.array(vec2)
        norm1 = self.np.linalg.norm(v1)
        norm2 = self.np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(self.np.dot(v1, v2) / (norm1 * norm2))

# Global singleton
embedding_service = EmbeddingService()
