# agent.py
from __future__ import annotations

import operator
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Sequence, TypedDict

from typing_extensions import Annotated

from langchain_core.messages import AnyMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

from qdrant_client import QdrantClient
from qdrant_client.models import SearchParams
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI

from .config import settings
from .firestore_memory import get_user_metrics


class AgentState(TypedDict):
    """
    State schema for the personalized health QA agent.
    """

    # Chat history (auto-merged)
    messages: Annotated[Sequence[AnyMessage], add_messages]

    # Personalization scope
    user_id: Optional[str]
    timeframe: Optional[Dict[str, str]]              # {"start": ISO, "end": ISO}
    metric_kinds: Annotated[List[str], operator.add] # e.g., ["hr", "hrv", "steps", "sleep"]

    # Parsed question
    question: Optional[str]

    # User data & derived analytics
    metrics: Annotated[List[Dict[str, Any]], operator.add]
    stats: Optional[Dict[str, Any]]
    anomalies: Annotated[List[str], operator.add]

    # Knowledge retrieval (Qdrant)
    relevant_chunks: Annotated[List[Dict[str, Any]], operator.add]
    citations: Annotated[List[Dict[str, Any]], operator.add]

    # Safety flags and final output
    safety_warnings: Annotated[List[str], operator.add]
    answer: Optional[str]


def _qdrant() -> QdrantClient:
    return QdrantClient(
        host=settings.qdrant_host,
        port=settings.qdrant_port,
        prefer_grpc=False,
        timeout=20.0,
    )


def _embedder() -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        azure_deployment=settings.azure_embedding_deployment,
        api_key=settings.azure_openai_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_api_version,
    )


def _chat() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        azure_deployment=settings.azure_deployment_name,
        api_key=settings.azure_openai_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_api_version,
        temperature=0.2,
        timeout=45,
    )


def _mean_sd(values: List[float]) -> tuple[Optional[float], Optional[float]]:
    if not values:
        return None, None
    if len(values) == 1:
        return float(values[0]), 0.0
    return float(mean(values)), float(pstdev(values))


def _safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _format_context(chunks: List[Dict[str, Any]], max_chars: int = 4000) -> str:
    pieces: List[str] = []
    used = 0
    for r in chunks:
        text = r.get("text") or r.get("payload", {}).get("text") or ""
        meta = r.get("metadata") or r.get("payload") or {}
        src = meta.get("source") or meta.get("url") or meta.get("id") or "unknown"
        part = f"[SOURCE: {src}]\n{text}\n"
        if used + len(part) > max_chars:
            break
        pieces.append(part)
        used += len(part)
    return "\n".join(pieces)


def _citation_block(citations: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for i, c in enumerate(citations, 1):
        src = c.get("source") or "unknown"
        score = c.get("score")
        tail = f" (sim {score:.3f})" if isinstance(score, (int, float)) else ""
        lines.append(f"[{i}] {src}{tail}")
    return "\n".join(lines)


SYSTEM_INSTRUCTIONS = (
    "You are a careful health information assistant. "
    "Personalize using the user's metrics and ONLY the retrieved context. "
    "Use bracketed citations like [1], [2]. "
    "Do not provide diagnosis or dosing; be concise and structured."
)


def node_parse_user(state: AgentState) -> AgentState:
    """
    Parse the latest user message, initialize list-merged fields.
    """
    question: Optional[str] = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            question = (msg.content or "").strip()
            break
        if isinstance(msg, dict) and msg.get("type") == "human":
            question = str(msg.get("content") or "").strip()
            break

    return {
        "question": question,
        "metric_kinds": state.get("metric_kinds") or [],
        "metrics": [],
        "anomalies": [],
        "relevant_chunks": [],
        "citations": [],
        "safety_warnings": [],
    }


def node_pull_metrics(state: AgentState) -> AgentState:
    """
    Fetch metrics from Firestore for user_id/timeframe/kinds.
    """
    user_id = state.get("user_id")
    timeframe = state.get("timeframe") or {}
    kinds = state.get("metric_kinds") or []

    if not user_id or not timeframe.get("start") or not timeframe.get("end"):
        return {"metrics": []}

    data = get_user_metrics(
        user_id=user_id,
        start_iso=timeframe["start"],
        end_iso=timeframe["end"],
        kinds=kinds,
    )

    cleaned: List[Dict[str, Any]] = []
    for p in data or []:
        cleaned.append(
            {
                "kind": p.get("kind"),
                "ts": p.get("ts"),
                "value": _safe_float(p.get("value")),
                "unit": p.get("unit"),
            }
        )
    return {"metrics": cleaned}


def node_analyze(state: AgentState) -> AgentState:
    """
    Compute per-kind aggregates and simple z-score outlier flags.
    """
    points = state.get("metrics") or []
    by_kind: Dict[str, List[float]] = {}
    for p in points:
        v = _safe_float(p.get("value"))
        k = p.get("kind")
        if v is None or not k:
            continue
        by_kind.setdefault(k, []).append(v)

    stats: Dict[str, Any] = {}
    flags: List[str] = []
    for k, vals in by_kind.items():
        mu, sd = _mean_sd(vals)
        stats[k] = {"mean": mu, "stdev": sd, "n": len(vals)}
        if mu is not None and sd and sd > 0:
            lo, hi = mu - 2.5 * sd, mu + 2.5 * sd
            outliers = [v for v in vals if v < lo or v > hi]
            if outliers:
                flags.append(f"{k}: {len(outliers)} outlier(s) beyond ±2.5σ")

    return {"stats": stats, "anomalies": flags}


def node_retrieve(state: AgentState) -> AgentState:
    """
    Retrieve guidance from Qdrant, lightly enriched with metric stats.
    """
    q = (state.get("question") or "").strip()
    if not q:
        return {"relevant_chunks": [], "citations": []}

    stats = state.get("stats") or {}
    enrich: List[str] = []
    for k in ("hr", "hrv", "sleep", "steps"):
        if k in stats and stats[k].get("mean") is not None:
            enrich.append(f"{k} mean {stats[k]['mean']:.1f}")
    enriched = q if not enrich else f"{q} | {'; '.join(enrich)}"

    client = _qdrant()
    emb = _embedder()
    vector = emb.embed_query(enriched)

    results = client.search(
        collection_name=settings.qdrant_collection,
        query_vector=vector,
        limit=6,
        with_payload=True,
        with_vectors=False,
        search_params=SearchParams(hnsw_ef=128),
    )

    chunks: List[Dict[str, Any]] = []
    cites: List[Dict[str, Any]] = []
    for hit in results:
        payload = hit.payload or {}
        text = payload.get("text") or payload.get("page_content") or ""
        meta = {
            "id": payload.get("id") or payload.get("doc_id"),
            "source": payload.get("source") or payload.get("url") or payload.get("path"),
            "title": payload.get("title"),
            "chunk": payload.get("chunk") or payload.get("chunk_id"),
        }
        chunks.append({"text": text, "score": float(hit.score or 0.0), "metadata": meta})
        cites.append({"id": meta["id"], "source": meta["source"], "score": float(hit.score or 0.0)})

    return {"relevant_chunks": chunks, "citations": cites}


EMERGENCY_SIGNS = (
    "crushing chest pain",
    "shortness of breath",
    "fainting",
    "stroke",
    "severe bleeding",
    "unconscious",
)


def node_safety(state: AgentState) -> AgentState:
    """
    Very lightweight safety heuristics. Replace with a guardrail service as needed.
    """
    warnings: List[str] = []
    q = (state.get("question") or "").lower()
    if any(k in q for k in EMERGENCY_SIGNS):
        warnings.append("Possible emergency symptoms mentioned — advise urgent in-person care.")

    anomalies = state.get("anomalies") or []
    if any(a.startswith("hr:") for a in anomalies):
        warnings.append("Unusual heart rate pattern detected; seek medical review if persistent.")

    return {"safety_warnings": warnings}


def node_answer(state: AgentState) -> AgentState:
    """
    Compose the final answer, with citations and disclaimer.
    """
    question = state.get("question") or ""
    stats = state.get("stats") or {}
    anomalies = state.get("anomalies") or []
    chunks = state.get("relevant_chunks") or []
    citations = state.get("citations") or []
    safety = state.get("safety_warnings") or []

    # Metrics summary
    parts: List[str] = []
    for k, st in stats.items():
        mu, sd, n = st.get("mean"), st.get("stdev"), st.get("n")
        if mu is not None and n:
            seg = f"- {k.upper()}: mean {mu:.1f}"
            if isinstance(sd, (int, float)):
                seg += f", σ {sd:.1f}"
            seg += f" over {n} pts"
            parts.append(seg)
    metrics_summary = "\n".join(parts) if parts else "No recent metrics available for the requested window."

    context = _format_context(chunks)
    cites = _citation_block(citations)
    disclaimer = (
        "Note: This is general information based on your data and referenced materials, "
        "not medical advice. For diagnosis, dosing, or urgent issues, consult a clinician "
        "or seek in-person care."
    )

    user_prompt = (
        f"Question:\n{question}\n\n"
        f"Your recent metrics (summary):\n{metrics_summary}\n"
    )
    if anomalies:
        user_prompt += "\nDetected anomalies:\n- " + "\n- ".join(anomalies) + "\n"
    user_prompt += "\nContext (verbatim excerpts):\n" + context + "\n\n"
    user_prompt += (
        "Instructions:\n"
        "- Personalize using the user's metrics.\n"
        "- Use ONLY the provided context for claims; add bracketed citations.\n"
        "- If context is insufficient, say so and suggest what data or timeframe would help.\n"
        "- Keep the answer under ~180 words.\n"
    )
    if safety:
        user_prompt += "\nSafety considerations:\n- " + "\n- ".join(safety) + "\n"
    if cites:
        user_prompt += f"\nSources:\n{cites}\n"

    llm = _chat()
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": user_prompt},
    ]
    resp = llm.invoke(messages)
    content = (resp.content or "").strip() + "\n\n" + disclaimer

    return {"answer": content, "messages": [AIMessage(content=content)]}


def build_graph():
    builder = StateGraph(AgentState)
    builder.add_node("parse_user", node_parse_user)
    builder.add_node("pull_metrics", node_pull_metrics)
    builder.add_node("analyze_metrics", node_analyze)
    builder.add_node("retrieve_guidance", node_retrieve)
    builder.add_node("safety", node_safety)
    builder.add_node("answer", node_answer)

    builder.add_edge(START, "parse_user")
    builder.add_edge("parse_user", "pull_metrics")
    builder.add_edge("pull_metrics", "analyze_metrics")
    builder.add_edge("analyze_metrics", "retrieve_guidance")
    builder.add_edge("retrieve_guidance", "safety")
    builder.add_edge("safety", "answer")
    builder.add_edge("answer", END)

    return builder.compile()


GRAPH = build_graph()
