# retriever.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from langchain_openai import AzureOpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, Filter as QFilter, MatchValue, PointStruct, SearchParams, VectorParams

from .config import settings


def _client() -> QdrantClient:
    return QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port, prefer_grpc=False, timeout=20.0)


def _embedder() -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        azure_deployment=settings.azure_embedding_deployment,
        api_key=settings.azure_openai_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_api_version,
    )


def _ensure_collection() -> None:
    client = _client()
    colls = client.get_collections().collections
    exists = any(c.name == settings.qdrant_collection for c in colls)
    if not exists:
        dist = Distance.COSINE if settings.qdrant_distance.upper() == "COSINE" else Distance.DOT
        client.recreate_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(size=settings.embedding_dim, distance=dist),
        )


def upsert_texts(items: List[Dict[str, Any]]) -> List[str]:
    """
    Upsert plain texts with optional metadata.
    Each item: {"text": "...", "metadata": {...}, "id": "optional"}
    """
    _ensure_collection()
    emb = _embedder()
    client = _client()

    payloads: List[Dict[str, Any]] = []
    points: List[PointStruct] = []
    ids: List[str] = []

    texts = [i["text"] for i in items]
    vectors = emb.embed_documents(texts)

    for i, item in enumerate(items):
        pid = item.get("id") or None
        meta = item.get("metadata") or {}
        payload = {"text": item["text"], **meta}
        payloads.append(payload)
        point = PointStruct(id=pid, vector=vectors[i], payload=payload)  # Qdrant will assign id if None
        points.append(point)

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    # Collect actual ids
    for p in points:
        ids.append(str(p.id) if p.id is not None else "")
    return ids


def search(query: str, k: int = 5, where: Optional[Dict[str, Any]] = None):
    """
    Perform a vector search with optional metadata filter (QFilter).
    Returns a list of lightweight objects with page_content + metadata for convenience.
    """
    emb = _embedder()
    client = _client()
    qvec = emb.embed_query(query)

    qfilter: Optional[QFilter] = None
    # Example: where={"key": "category", "value": "health"}
    if where and "key" in where and "value" in where:
        qfilter = QFilter(must=[{"key": where["key"], "match": MatchValue(value=where["value"])}])

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=qvec,
        limit=k,
        query_filter=qfilter,
        with_payload=True,
        with_vectors=False,
        search_params=SearchParams(hnsw_ef=128),
    )

    class _Doc:
        def __init__(self, payload: Dict[str, Any], score: float):
            self.page_content = payload.get("text") or payload.get("page_content") or ""
            self.metadata = {k: v for k, v in payload.items() if k != "text"}
            self.score = score

    return [_Doc(hit.payload or {}, float(hit.score or 0.0)) for hit in results]


def delete_points(ids: List[str]) -> None:
    client = _client()
    client.delete(collection_name=settings.qdrant_collection, points_selector={"points": ids})
