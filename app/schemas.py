# schemas.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Timeframe(BaseModel):
    start: str = Field(..., description="ISO8601 UTC start, e.g., 2025-09-13T00:00:00Z")
    end: str = Field(..., description="ISO8601 UTC end, e.g., 2025-09-20T00:00:00Z")


class ChatRequest(BaseModel):
    user_id: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    timeframe: Optional[Timeframe] = None
    metric_kinds: Optional[List[str]] = Field(
        default=None,
        description='Metric kinds to analyze, e.g., ["hr","hrv","steps","sleep"].',
    )


class ChatResponse(BaseModel):
    reply: str
    used_docs: Optional[List[Dict[str, Any]]] = None


class UpsertItem(BaseModel):
    text: str
    metadata: Optional[Dict[str, Any]] = None
    id: Optional[str] = None


class UpsertRequest(BaseModel):
    items: List[UpsertItem]


class DeleteRequest(BaseModel):
    ids: List[str]


class SearchRequest(BaseModel):
    query: str
    k: int = 5
    where: Optional[Dict[str, Any]] = None


class SearchResultItem(BaseModel):
    text: str
    metadata: Dict[str, Any]


class SearchResponse(BaseModel):
    results: List[SearchResultItem]


class MetricConfigResponse(BaseModel):
    default_metric_kinds: List[str]
    available_metric_kinds: List[str]


class MetricConfigUpdateRequest(BaseModel):
    default_metric_kinds: Optional[List[str]] = None
    available_metric_kinds: Optional[List[str]] = None
