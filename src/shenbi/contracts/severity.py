"""severity 传感/词表单源（spec #105 T1）。

登记域 ``RoutingTier``/``AggregateVocab`` 见 ``docs/framework/status-vocab.md``
（AuditSeverity 域新增两行，spec #34 纪律：先立域再落定义）。六消费点
（revision_router / chapter_loop / parallel_dispatch / audit_layer /
audit_aggregate / tools/report_longitudinal）一律 import 本模块符号，
本地词表交替字面量由 ``tools/lint_severity_single_source.py`` 禁绝。

迁出来源与保留的 probe 教训（压缩版，全文见原位点注释）：
- ``SEV_ENUM_TAIL``：probe6 ch1 legend 守卫（``4. **严重度**：BLOCKING /
  CRITICAL / MINOR`` 文档行不是 finding）——源自 revision_router.py /
  audit_aggregate.py / parallel_dispatch.py 三处同款尾巴。
- ``NEGATION_PAYLOAD_TAIL``：F-5（probe22 #010）零声明守卫
  （``- [BLOCKING] 无`` 不是 finding）——end 锚负向前瞻。
- ``QUOTED_VALUE_TAIL``：#18-1（probe23）引号值守卫
  （``"severity": "BLOCKING"`` 是模板字面量里的值不是声明）。
- bracket/bold 锚定形：audit_aggregate.py:46-47 语义（仅锚定形态计入，
  散文裸词永不计 finding——fixcheck ch2 计数膨胀教训）。
"""

from __future__ import annotations

import re
from typing import Literal, get_args

from shenbi.contracts.enums import Severity

#: registry 面 Literal 形常量——status-vocab.md RoutingTier 行符号。
RoutingTier = Literal["BLOCKING", "CRITICAL"]
#: registry 面 Literal 形常量——status-vocab.md AggregateVocab 行符号。
#: PEP 586 嵌套展平：get_args(AggregateVocab) == 五词元组。
AggregateVocab = Literal[Severity, "WARNING", "ERROR"]

#: 传感面运行时元组（get_args 派生——仓内先例 g0_skill_contract.py:163）。
ROUTING_TIERS: tuple[str, ...] = get_args(RoutingTier)
AGGREGATE_VOCAB: tuple[str, ...] = get_args(AggregateVocab)
#: T4 G4.av.vocab 统一后处理管线查表用。
AGGREGATE_VOCAB_SET: frozenset[str] = frozenset(AGGREGATE_VOCAB)

#: legacy 硬档别名（fixcheck severity-vocabulary reconciliation）：bracket 形
#: ``- [ERROR]`` 是旧模板硬档标签。不入 RoutingTier 值集（registry 值集相等
#: 契约）；audit_layer._ERROR_LABEL_RE 与 router/consolidator CRITICAL 形
#: bracket 词组消费。
ROUTING_HARD_TIER_ALIASES: tuple[str, ...] = ("ERROR",)

#: bracket 形词组单源（I-1）：BLOCKING 形=单词；CRITICAL 形=CRITICAL|ERROR。
#: 禁在消费点以 (*ROUTING_TIERS, *ALIASES) 展开重组——会把 BLOCKING 混入
#: CRITICAL 传感（行为变更）。
ROUTING_BLOCKING_BRACKET_WORDS: tuple[str, ...] = ("BLOCKING",)
ROUTING_CRITICAL_BRACKET_WORDS: tuple[str, ...] = ("CRITICAL", *ROUTING_HARD_TIER_ALIASES)

# ── 三尾巴（迁自 revision_router.py:90/:102/:120，语义逐字保持） ──────────────

#: legend 守卫（probe6 ch1）：值后紧跟枚举续列（``/ CRITICAL / MINOR``）=
#: 格式文档行，非声明。
SEV_ENUM_TAIL = r"(?!\s*[/／、,，]\s*(?:BLOCKING|CRITICAL|MINOR|WARNING|ERROR)\b)"

#: 零声明守卫（F-5/probe22 #010）：bracket 载荷恰为否定词 = 零声明。
#: 公开导出：revision_router.is_negation_payload 的 fullmatch 基底。
NEGATION_WORDS = r"(?:(?:无|暂无|没有)|(?i:none|n/?a)|0)"
NEGATION_PAYLOAD_TAIL = rf"(?!\s*{NEGATION_WORDS}\s*[。.!！]?\s*$)"

#: 引号值守卫（#18-1/probe23）：紧随闭引号 = 模板字面量里的值，非声明。
QUOTED_VALUE_TAIL = r'(?!\*{0,2}")'

# ── 锚定形态传感正则（bracket/bold 两形——语义同 audit_aggregate.py:46-47） ──
#: r2-M5/r3-I2 YAGNI 收缩：cell/key 传感不建模块锚定——audit_aggregate 换装时
#: 本地从 AGGREGATE_VOCAB 组合重建（行为保持）；本模块只建有生产消费方的锚定
#: （BRACKET/BOLD_ANCHOR_RE → G4.av.dispatch_integrity 消费）。

#: audit-T5 I1 修正: 交替必须 `(?:...)` 包裹——裸 join 会把 `^` 只绑定第一分支,
#: 其余词退化为行内任意位置匹配 (`x MINOR` 即算锚定)。捕获组保留 severity 词
#: 供消费点判 tier (G4.av.dispatch_integrity 只认 BLOCKING)。
_BRACKET_WORDS = "|".join(AGGREGATE_VOCAB)
BRACKET_ANCHOR_RE = re.compile(rf"^\s*-\s*\[({_BRACKET_WORDS})\]")
BOLD_ANCHOR_RE = re.compile(rf"\*\*({_BRACKET_WORDS})\*\*")

# ── 聚合节头（修 report_longitudinal.py:558 缺 MINOR 分家） ────────────────────

_SECTION_WORDS = "|".join(AGGREGATE_VOCAB)
SECTION_HEADER_RE = re.compile(rf"^## ({_SECTION_WORDS}) Findings", re.M)

# ── T4 判别器词汇 ─────────────────────────────────────────────────────────────

#: CJK severity 判别词族（r2.5 C-1 精确等值集合成员判定，禁子串/前缀）。
#: audit-T4 处置(d): `阻断` 属 ResonanceVerdict 注册域 (status-vocab.md), 误入本族
#: 在 vol1 回放产生 13 处 bold 形误伤 -- 移出。
CJK_SEVERITY_WORDS: frozenset[str] = frozenset({"严重", "高", "重大", "中", "低", "警告"})
#: key 名 token 豁免集（归一后比较；封英文裸 key bold 形误报面）。
KEY_NAME_TOKENS: frozenset[str] = frozenset({"SEVERITY", "严重度"})
