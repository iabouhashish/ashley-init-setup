# firestore_memory.py
from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Dict, List, Optional

from google.cloud import firestore

from .config import settings


# Ensure emulator host is set before creating the client
if getattr(settings, "firestore_emulator_host", None):
    os.environ["FIRESTORE_EMULATOR_HOST"] = settings.firestore_emulator_host

_db = firestore.Client(project=settings.gcp_project_id)


# -----------------------------
# Chat history helpers
# -----------------------------
def _conv_ref(user_id: str):
    return (
        _db.collection(settings.firestore_collection)
        .document(user_id)
        .collection("messages")
    )


def fetch_context(user_id: str, limit: Optional[int] = None) -> List[Dict]:
    limit = limit or settings.max_context_messages
    docs = _conv_ref(user_id).order_by("created_at").stream()
    messages = [
        {
            "role": (d.to_dict() or {}).get("role", "user"),
            "content": (d.to_dict() or {}).get("content", ""),
        }
        for d in docs
    ]
    return messages[-limit:]


def append_turn(user_id: str, role: str, content: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    _conv_ref(user_id).add({"role": role, "content": content, "created_at": now})


# -----------------------------
# Metrics helpers
# -----------------------------
def _metrics_ref(user_id: str):
    """
    Collection path: <firestore_collection>/<user_id>/metrics
    Each doc:
      {
        kind: "hr" | "hrv" | "steps" | "sleep" | ...,
        ts:   Firestore Timestamp (UTC),
        value: number,
        unit: "bpm" | "ms" | ...
      }
    """
    return (
        _db.collection(settings.firestore_collection)
        .document(user_id)
        .collection("metrics")
    )


def _parse_iso_utc(s: str) -> datetime:
    if not s:
        raise ValueError("Empty ISO datetime string.")
    iso = s.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_user_metrics(
    user_id: str,
    start_iso: str,
    end_iso: str,
    kinds: List[str] | None = None,
) -> List[Dict]:
    """
    Fetch metric points for a user within [start_iso, end_iso] (inclusive),
    optionally filtered to specific kinds.
    Returns:
      [{"kind": str, "ts": "<ISO8601 UTC>", "value": float, "unit": str}, ...]
    """
    start_dt = _parse_iso_utc(start_iso)
    end_dt = _parse_iso_utc(end_iso)

    q = (
        _metrics_ref(user_id)
        .where("ts", ">=", start_dt)
        .where("ts", "<=", end_dt)
        .order_by("ts")
    )

    if kinds:
        uniq = list(dict.fromkeys(kinds))
        if len(uniq) <= 10:
            q = q.where("kind", "in", uniq)
        # if > 10, fallback to client-side filter below

    docs = q.stream()

    out: List[Dict] = []
    for d in docs:
        data = d.to_dict() or {}
        k = data.get("kind")
        if kinds and len(kinds) > 10 and k not in kinds:
            continue

        ts_val = data.get("ts")
        if isinstance(ts_val, datetime):
            ts_iso = ts_val.astimezone(timezone.utc).isoformat()
        else:
            ts_iso = str(ts_val)

        try:
            val = float(data.get("value"))
        except Exception:
            continue

        out.append(
            {
                "kind": k,
                "ts": ts_iso,
                "value": val,
                "unit": data.get("unit"),
            }
        )

    return out


def add_metric(
    user_id: str,
    kind: str,
    value: float,
    unit: str,
    ts: Optional[datetime] = None,
) -> None:
    """
    Convenience helper for seeding dev/test data.
    """
    ts = ts or datetime.now(timezone.utc)
    _metrics_ref(user_id).add(
        {"kind": kind, "value": float(value), "unit": unit, "ts": ts}
    )
