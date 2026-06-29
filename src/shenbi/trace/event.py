"""TraceEvent 不可变模型 + hash 链签名。signature 链前一条签名，使整条
trace 篡改可见（G7 校验）。canonical_payload 用排序键，去引号/顺序差异。

v5 spec 成功判据 7/11：完整性靠 hash 链 + compaction 边界 + LEGACY 锚。
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from shenbi.contracts.enums import ActorRole

GENESIS_PREV = "0" * 64  # 链首/compaction 后的合法前驱锚

_SIGNED_FIELDS = (
    "seq",
    "ts",
    "actor",
    "actor_role",
    "action",
    "target",
    "skill",
    "gate",
    "payload",
    "schema_version",
)


def canonical_payload(event: TraceEvent) -> str:
    """排序键 JSON，消除 dict 顺序/引号差异（语义 round-trip 基础）。"""
    core = {k: getattr(event, k) for k in _SIGNED_FIELDS}
    return json.dumps(
        core, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=_json_default
    )


def _json_default(obj: object) -> object:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


def sign(prev_signature: str, payload_canonical: str, schema_version: int) -> str:
    return hashlib.sha256(
        (prev_signature + "|" + payload_canonical + "|" + str(schema_version)).encode("utf-8")
    ).hexdigest()


class TraceEvent(BaseModel):
    model_config = {"frozen": True, "extra": "ignore"}

    seq: int = Field(ge=1)
    ts: datetime = Field(default_factory=lambda: datetime.now(UTC))
    actor: str
    actor_role: ActorRole
    action: str
    target: str
    skill: str | None = None
    gate: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    schema_version: int = Field(ge=1)
    signature: str = ""

    @classmethod
    def sign_and_new(cls, prev_signature: str, **kw: object) -> TraceEvent:
        """构造并算签名（签名空时填入）。保证 signature 链 prev_signature。"""
        obj = cls(**kw)  # type: ignore[arg-type]
        sig = sign(prev_signature, canonical_payload(obj), obj.schema_version)
        return obj.model_copy(update={"signature": sig})
