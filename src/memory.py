from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from .config import settings


@dataclass
class MemoryItem:
    id: str
    text: str
    metadata: Dict[str, Any]
    created_at: str


class MemoryStore:
    def __init__(self, persist_directory: Optional[str] = None, collection_name: str = "agent_memory"):
        self.persist_directory = persist_directory or settings.chroma_persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        self.client = chromadb.Client(ChromaSettings(persist_directory=self.persist_directory, is_persistent=True))
        self.collection = self.client.get_or_create_collection(collection_name)
        self._model: SentenceTransformer | None = None

    def _embed(self, texts: List[str]) -> List[List[float]]:
        if self._model is None:
            # Small, fast default model
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model.encode(texts, convert_to_numpy=False).tolist()

    def add(self, text: str, metadata: Optional[Dict[str, Any]] = None, item_id: Optional[str] = None) -> str:
        doc_id = item_id or f"mem_{int(datetime.now().timestamp()*1000)}"
        self.collection.add(
            ids=[doc_id],
            documents=[text],
            metadatas=[metadata or {}],
            embeddings=self._embed([text])
        )
        return doc_id

    def query(self, query_text: str, top_k: int = 5, where: Optional[Dict[str, Any]] = None) -> List[MemoryItem]:
        result = self.collection.query(
            query_embeddings=self._embed([query_text]),
            n_results=top_k,
            where=where or {}
        )
        items: List[MemoryItem] = []
        for i in range(len(result["ids"][0])):
            items.append(MemoryItem(
                id=result["ids"][0][i],
                text=result["documents"][0][i],
                metadata=result["metadatas"][0][i] or {},
                created_at=result["metadatas"][0][i].get("created_at", "") if result["metadatas"][0][i] else ""
            ))
        return items

    def delete(self, item_id: str) -> None:
        self.collection.delete(ids=[item_id])


# Global memory instance
memory = MemoryStore()