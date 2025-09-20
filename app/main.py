# main.py
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from openai import AzureOpenAI

from .agent import GRAPH
from .config import settings
from .firestore_memory import append_turn, fetch_context
from .retriever import delete_points, search, upsert_texts
from .schemas import (
    ChatRequest,
    ChatResponse,
    DeleteRequest,
    SearchRequest,
    SearchResponse,
    UpsertRequest,
    MetricConfigResponse,
    MetricConfigUpdateRequest,
)
from .security import api_key_auth

load_dotenv()

app = FastAPI(title="MCP Agent API (Azure + Qdrant + Firestore + SSE)")

origins = (
    [o.strip() for o in settings.cors_origins.split(",")]
    if settings.cors_origins
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Direct Azure client used only for legacy/raw streaming cases (not needed for graph streaming)
aoclient = AzureOpenAI(
    api_key=settings.azure_openai_key,
    api_version=settings.azure_api_version,
    azure_endpoint=settings.azure_openai_endpoint,
)


def _default_timeframe(days: int = 7) -> Dict[str, str]:
    """Last N days (UTC) as ISO 8601."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return {"start": start.isoformat(), "end": end.isoformat()}


def _to_lc_history(context: List[Dict[str, Any]]) -> List[Any]:
    """
    Convert stored dict messages to LangChain messages.
    """
    out: List[Any] = []
    for m in context:
        role = (m.get("role") or "").lower()
        content = m.get("content") or ""
        if role == "assistant":
            out.append(AIMessage(content=content))
        else:
            out.append(HumanMessage(content=content))
    return out


@app.get("/healthz")
def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.get(settings.api_prefix + "/ready")
def ready() -> Dict[str, str]:
    return {"status": "ready"}


@app.post(
    settings.api_prefix + "/chat",
    response_model=ChatResponse,
    dependencies=[Depends(api_key_auth)],
)
async def chat(body: ChatRequest) -> ChatResponse:
    """
    Non-streaming chat using LangGraph agent:
      - pulls user metrics
      - retrieves guidance from Qdrant
      - composes grounded answer with citations + disclaimer
    """
    history_raw = fetch_context(body.user_id, settings.max_context_messages)
    history_msgs = _to_lc_history(history_raw)

    timeframe = body.timeframe.model_dump() if body.timeframe else _default_timeframe(7)
    metric_kinds = body.metric_kinds or settings.default_metric_kinds

    initial_state = {
        "messages": history_msgs + [HumanMessage(content=body.message)],
        "user_id": body.user_id,
        "timeframe": timeframe,
        "metric_kinds": metric_kinds,
        "metrics": [],
        "anomalies": [],
        "relevant_chunks": [],
        "citations": [],
        "safety_warnings": [],
    }

    result = GRAPH.invoke(initial_state)

    reply: str = (result.get("answer") or "").strip()
    append_turn(body.user_id, "user", body.message)
    append_turn(body.user_id, "assistant", reply)

    used = result.get("citations") or []
    return ChatResponse(reply=reply, used_docs=used)


@app.post(
    settings.api_prefix + "/chat/stream",
    dependencies=[Depends(api_key_auth)],
)
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    """
    Graph streaming as SSE:
      - Emits node progress events
      - Emits final answer event
    """
    history_raw = fetch_context(body.user_id, settings.max_context_messages)
    history_msgs = _to_lc_history(history_raw)

    timeframe = body.timeframe.model_dump() if body.timeframe else _default_timeframe(7)
    metric_kinds = body.metric_kinds or settings.default_metric_kinds

    initial_state = {
        "messages": history_msgs + [HumanMessage(content=body.message)],
        "user_id": body.user_id,
        "timeframe": timeframe,
        "metric_kinds": metric_kinds,
        "metrics": [],
        "anomalies": [],
        "relevant_chunks": [],
        "citations": [],
        "safety_warnings": [],
    }

    async def sse_gen() -> AsyncGenerator[bytes, None]:
        final_answer: str = ""
        try:
            async for update in GRAPH.astream(initial_state, stream_mode="updates"):
                node_name, payload = next(iter(update.items()))
                maybe_state = payload or {}

                # Capture final answer if produced
                ans = maybe_state.get("answer")
                if isinstance(ans, str) and ans:
                    final_answer = ans

                event = {
                    "type": "node",
                    "node": node_name,
                    "keys": list(maybe_state.keys()),
                }
                yield f"data: {json.dumps(event)}\n\n".encode("utf-8")

            # Persist after completion
            append_turn(body.user_id, "user", body.message)
            append_turn(body.user_id, "assistant", final_answer)

            yield f"data: {json.dumps({'type': 'final', 'answer': final_answer})}\n\n".encode(
                "utf-8"
            )
        except Exception as exc:
            err = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(err)}\n\n".encode("utf-8")
        finally:
            yield b"data: [DONE]\n\n"

    return StreamingResponse(sse_gen(), media_type="text/event-stream")


@app.post(
    settings.api_prefix + "/index/upsert",
    dependencies=[Depends(api_key_auth)],
)
async def index_upsert(body: UpsertRequest) -> Dict[str, Any]:
    ids = upsert_texts([i.model_dump() for i in body.items])
    return {"status": "ok", "ids": ids}


@app.post(
    settings.api_prefix + "/index/delete",
    dependencies=[Depends(api_key_auth)],
)
async def index_delete(body: DeleteRequest) -> Dict[str, Any]:
    delete_points(body.ids)
    return {"status": "ok"}


@app.post(
    settings.api_prefix + "/index/search",
    response_model=SearchResponse,
    dependencies=[Depends(api_key_auth)],
)
async def index_search(body: SearchRequest) -> SearchResponse:
    docs = search(query=body.query, k=body.k, where=body.where)
    results = [{"text": d.page_content, "metadata": d.metadata} for d in docs]
    return SearchResponse(results=results)


# -----------------------------
# Product Manager Configuration Endpoints
# -----------------------------

@app.get(
    settings.api_prefix + "/config/metrics",
    response_model=MetricConfigResponse,
    dependencies=[Depends(api_key_auth)],
    tags=["Configuration"]
)
async def get_metric_config() -> MetricConfigResponse:
    """
    Get current metric configuration.
    
    Returns the current default and available metric kinds that can be analyzed.
    This endpoint is useful for product managers to understand what metrics
    are currently configured for health analysis.
    """
    return MetricConfigResponse(
        default_metric_kinds=settings.default_metric_kinds,
        available_metric_kinds=settings.available_metric_kinds
    )


@app.post(
    settings.api_prefix + "/config/metrics",
    response_model=MetricConfigResponse,
    dependencies=[Depends(api_key_auth)],
    tags=["Configuration"]
)
async def update_metric_config(body: MetricConfigUpdateRequest) -> MetricConfigResponse:
    """
    Update metric configuration.
    
    Allows product managers to adjust which metrics are analyzed by default
    and which metrics are available for analysis.
    
    **Note**: Changes require application restart to take effect.
    Consider using environment variables for production deployments.
    
    **Validation**:
    - All default_metric_kinds must be in available_metric_kinds
    - Metric kinds should be lowercase strings
    - Common metric kinds: hr, hrv, steps, sleep, weight, blood_pressure, temperature, glucose, oxygen_saturation
    """
    # Validate that default metrics are in available metrics
    if body.default_metric_kinds:
        invalid_defaults = set(body.default_metric_kinds) - set(body.available_metric_kinds or settings.available_metric_kinds)
        if invalid_defaults:
            raise ValueError(f"Default metric kinds {invalid_defaults} are not in available metric kinds")
    
    # Update settings (this will only persist for the current session)
    if body.default_metric_kinds is not None:
        settings.default_metric_kinds = body.default_metric_kinds
    
    if body.available_metric_kinds is not None:
        settings.available_metric_kinds = body.available_metric_kinds
    
    return MetricConfigResponse(
        default_metric_kinds=settings.default_metric_kinds,
        available_metric_kinds=settings.available_metric_kinds
    )
