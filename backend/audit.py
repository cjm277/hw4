"""Append-only audit trail of agent-loop activity: output/audit_trail.json.

One entry per chat turn: when it happened, who (user id or guest), which page, the (already scrubbed)
message, every model request and tool call in the loop with short args/results and timestamps, token usage,
how the turn stopped, and any safety events. The file is a JSON array that only ever grows: new entries are
written in place of the closing "]", so earlier entries are never rewritten, and nothing wipes it between
runs or server restarts.

Privacy: the message stored is the guard-scrubbed text (no card numbers or passwords), email addresses in
previews are masked, and shoppers are identified by user id only.
"""

import json
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    RetryPromptPart,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_core import to_json

AUDIT_PATH = Path(__file__).resolve().parents[1] / "output" / "audit_trail.json"
PREVIEW_CHARS = 240
OUTPUT_TOOL = "final_result"  # PydanticAI's structured-output tool: the agent's final answer

_lock = threading.Lock()
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
SHOP_EMAIL = "orderdept@campuscustoms.com"  # public contact address: no need to mask

# Phrases typical of attempts to give the agent new instructions. Flagged in the trail for review.
# Detection only: the agent's prompt rules are what make it refuse.
INJECTION_HINTS = re.compile(
    r"ignore (all |any |your |the )?(previous|prior|above) (instructions|rules)|you are now|act as|pretend (to be|you are)"
    r"|developer mode|system prompt|reveal (your|the) (prompt|instructions)|^\s*(system|admin|developer)\s*:"
    r"|as (the |a )?(store )?manager|new instructions",
    re.I | re.M,
)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def preview(value: Any) -> str:
    text = value if isinstance(value, str) else to_json(value).decode("utf-8", "replace")
    text = EMAIL_RE.sub(lambda m: m.group(0) if m.group(0).lower() == SHOP_EMAIL else "[email]", " ".join(text.split()))
    return text if len(text) <= PREVIEW_CHARS else text[: PREVIEW_CHARS - 1] + "…"


def injection_suspected(text: str) -> bool:
    return bool(INJECTION_HINTS.search(text))


@dataclass
class TurnAudit:
    """Collects one chat turn's activity, then appends it to the trail."""

    user_id: int | None
    page: str
    message: str  # guard-scrubbed text
    model: str | None = None
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = field(default_factory=now_iso)
    _start: float = field(default_factory=time.perf_counter)
    steps: list[dict] = field(default_factory=list)
    stop_reason: str = "unknown"
    finish_reason: str | None = None
    usage: dict = field(default_factory=dict)
    safety: list[str] = field(default_factory=list)
    reply: str = ""
    product_ids: list[str] = field(default_factory=list)
    page_results: int | None = None

    def add_run(self, messages: list[ModelMessage]) -> None:
        """Record the agent loop: each model request, tool call (args) and tool result, in order."""
        for m in messages:
            if isinstance(m, ModelResponse):
                calls = [p for p in m.parts if isinstance(p, ToolCallPart)]
                self.finish_reason = m.finish_reason or self.finish_reason
                self.steps.append(
                    {
                        "time": m.timestamp.isoformat(timespec="milliseconds"),
                        "step": "model_response",
                        "tool_calls": [p.tool_name for p in calls],
                        "text": preview(" ".join(p.content for p in m.parts if isinstance(p, TextPart))) or None,
                    }
                )
                for p in calls:
                    self.steps.append(
                        {
                            "time": m.timestamp.isoformat(timespec="milliseconds"),
                            "step": "final_answer" if p.tool_name == OUTPUT_TOOL else "tool_call",
                            "tool": p.tool_name,
                            "args": preview(p.args_as_dict()),
                        }
                    )
            elif isinstance(m, ModelRequest):
                for p in m.parts:
                    if isinstance(p, ToolReturnPart) and p.tool_name != OUTPUT_TOOL:
                        self.steps.append(
                            {
                                "time": p.timestamp.isoformat(timespec="milliseconds"),
                                "step": "tool_result",
                                "tool": p.tool_name,
                                "result": preview(p.content),
                            }
                        )
                    elif isinstance(p, RetryPromptPart):
                        self.steps.append(
                            {
                                "time": p.timestamp.isoformat(timespec="milliseconds"),
                                "step": "retry",
                                "tool": p.tool_name,
                                "result": preview(p.content),
                            }
                        )

    def stop(self, reason: str) -> None:
        self.stop_reason = reason

    def to_entry(self) -> dict:
        tools = [s["tool"] for s in self.steps if s["step"] == "tool_call"]
        return {
            "run_id": self.run_id,
            "time": self.started_at,
            "duration_ms": round((time.perf_counter() - self._start) * 1000),
            "user": f"user:{self.user_id}" if self.user_id else "guest",
            "page": self.page,
            "message": preview(self.message),
            "model": self.model,
            "tools_used": list(dict.fromkeys(tools)),
            "steps": self.steps,
            "stop_reason": self.stop_reason,
            "finish_reason": self.finish_reason,
            "usage": self.usage,
            "safety": self.safety,
            "reply": preview(self.reply),
            "product_ids": self.product_ids,
            "page_results": self.page_results,
        }

    def write(self) -> None:
        append(self.to_entry())


def append(entry: dict) -> None:
    """Append one entry to the JSON array without rewriting anything already in the file."""
    block = json.dumps(entry, indent=2, ensure_ascii=False)
    with _lock:
        AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if not AUDIT_PATH.exists() or AUDIT_PATH.stat().st_size == 0:
            AUDIT_PATH.write_text("[\n" + block + "\n]\n", encoding="utf-8")
            return
        with open(AUDIT_PATH, "r+b") as f:
            data_end = f.seek(0, 2)
            tail_len = min(data_end, 4096)
            f.seek(data_end - tail_len)
            tail = f.read(tail_len)
            close = tail.rfind(b"]")
            if close == -1:  # not a JSON array we wrote: keep it, start a fresh file beside it
                f.close()
                AUDIT_PATH.replace(AUDIT_PATH.with_name(f"audit_trail.unreadable-{int(time.time())}.json"))
                AUDIT_PATH.write_text("[\n" + block + "\n]\n", encoding="utf-8")
                return
            before = tail[:close].rstrip()
            has_entries = not before.endswith(b"[")
            f.seek(data_end - tail_len + close)
            f.write(((",\n" if has_entries else "") + block + "\n]\n").encode("utf-8"))
            f.truncate()
