# 状态词表登记表（唯一裁决依据）

> 本表是框架全部状态/词表域的唯一裁决依据（spec #34 T1）。
> 格式约定（`tools/lint_status_strings.py` 对账子检查按此解析）：
> - 每域一行，5 列：`| 域 | 主词表 | 合法值 | 生产写方 | 生产读方 |`
> - 主词表列为 `module.Symbol`（`shenbi.` 包内可 import 路径）
> - 合法值列以 `\|` 分隔，必须与该符号实际 Literal 值 / StrEnum 成员值**集合相等**
> - 生产写方/读方为 file 级清单（`-` 表示未持久化/无）
> - 消费侧容错映射（读旧值归一）不算第二词表，登记在域行的「生产读方」注记里

## 域清单

| 域 | 主词表 | 合法值 | 生产写方 | 生产读方 |
|---|---|---|---|---|
| GateStatus | shenbi.status.GateStatus | PASS\|FAIL\|SKIP\|WARN\|UNIMPLEMENTED | gates/shared.py 标记落盘、contracts/base.py GateOutcome.status（T904 合一注解） | gates/cli、scoring、phase_runner/executor |
| PhaseState | shenbi.status.PhaseState | created\|started\|skills_done\|scored\|finalized | phase_runner | phase-state/*.json |
| CommandStatus | shenbi.status.CommandStatus | ok\|blocked\|error\|exists\|degraded | phase_runner、pipeline/cli.py、pipeline/truth_embed.py | CLI 消费者（DEGRADED 为 T908 收编 truth_embed 越表值；T9 行 35 的 cli not_implemented 形态已由先前 ERROR 化统一，不另立） |
| ScoringStatus | shenbi.status.ScoringStatus | ok\|REJECT\|MARKER_MISSING\|UNIMPLEMENTED | scoring.py | dispatcher |
| ScoreClassification | shenbi.status.ScoreClassification | PASS (excellent)\|PASS (acceptable)\|CONDITIONAL\|FAIL | scoring.classify | - |
| SkillProgressStatus | shenbi.status.SkillProgressStatus | pending\|done\|skip | dispatcher/modes/codex.py、trace/materialize.py | gates/g_reconcile.py（容错读旧大写 DONE，T906） |
| AuditSeverity | shenbi.contracts.enums.Severity | BLOCKING\|CRITICAL\|MINOR | 审计产出 | escalation 路由（regex 域大小写归一后比对，revision_router.py、parallel_dispatch.py） |
| ReviewVerdict | shenbi.contracts.enums.Verdict | 通过\|有瑕疵\|不通过 | review-* 技能 md | 评分/审计读取 |
| ResonanceVerdict | shenbi.contracts.enums.ResonanceVerdict | 通过\|阻断\|待人机复核 | review-resonance 技能 md | gates/g4/review_resonance.py（T902：_VERDICTS 裸 tuple 收编） |
| CPZone | shenbi.contracts.enums.CPZone | GREEN\|ORANGE\|RED | - | foreshadowing_resolve.py |
| ActorRole | shenbi.contracts.enums.ActorRole | GENERATOR\|SCORER\|GATE\|SKILL\|HUMAN\|SYSTEM | trace 事件 | trace 审计 |
| TriggerFailureStage | shenbi.contracts.enums.TriggerFailureStage | dispatch\|g4\|g3\|governance | pipeline/triggers | - |
| ScoredBy | shenbi.contracts.enums.ScoredBy | file\|interactive\|subagent | scoring | - |
| DecisionsBasis | shenbi.contracts.schemas.decisions.Basis | adjacent_to_target_chapter\|arc_relevance\|volume_scope\|manual_override | 技能 decisions.json | G2/G4 validator |
| DecisionsSeverityLevel | shenbi.contracts.schemas.decisions.SeverityLevel | low\|medium\|high | 技能 decisions.json | G2/G4 validator（原 Severity 改名消同名，F211） |
| DecisionsHandling | shenbi.contracts.schemas.decisions.Handling | compensate_via_pacing\|explicit_callout\|defer_to_next_chapter\|ignore | 技能 decisions.json | G2/G4 validator |
| DecisionsTrim | shenbi.contracts.schemas.decisions.Trim | none\|oldest_first\|lowest_relevance\|manual | 技能 decisions.json | G2/G4 validator |
| RevisionSeverity | shenbi.contracts.enums.RevisionSeverity | low\|medium\|high | chapter-revision 技能 revision-decisions | G4 值域校验；容错映射读旧值 blocking/critical/critical_per_audit→high、warning→medium、minor/info/none/observation→low（T903） |
| RevisionMode | shenbi.contracts.enums.RevisionMode | spot-fix\|regenerate\|constrained-regenerate\|reconstruction\|no-revision | revision 路由/技能 | G4 值域校验；读旧值 no_op→no-revision（T910，route.py/revision_router.py 双域合一） |
| RevisionStatus | shenbi.contracts.enums.RevisionStatus | preserved\|skipped\|delegated\|reconstructed_from_cross_source_evidence | chapter-revision 技能 revision-decisions | G4（T9 行 38/39 同键合一） |
| ApprovalDecision | shenbi.contracts.enums.ApprovalDecision | approved\|rejected | genre-config novel.json | contracts/skills/genre_config.py validator（T909：与 ReviewDecision 命令域互斥分立） |
| NovelStatus | shenbi.contracts.enums.NovelStatus | worldbuilding\|worldbuilding_complete | worldbuilding 技能 novel.json | -（T911：有生产值立域） |
| WriteMode | shenbi.contracts.enums.WriteMode | create_or_overwrite\|append_dedup\|merge_prose | SKILL.md write-semantics mode | gates/g0_skill_contract.py G0.16（spec #34 T204：值合法性校验） |
| OutputKind | shenbi.contracts.legacy.OutputKind | artifact\|report\|ephemeral | SKILL 契约 kind | G0/G2 |
| RecordState | shenbi.records.writer.RecordState | PENDING\|RELEVANT\|TRIGGER\|TRIGGERED\|REINFORCE | records/writer.py md 表 state 列 | truth_index（md 列与 schemas HookState 的归并归 F815/F820 已立案族） |
| HookState | shenbi.contracts.schemas.hooks.HookState | PLANTED\|RELEVANT\|TRIGGERED\|RESOLVED\|ARCHIVED\|EXPIRED | foreshadowing-lifecycle | truth hooks（F815/F820 已立案族） |
| RegistryKind | shenbi.contracts.schemas.registry.RegistryKind | benchmark\|chapter\|character\|config\|context\|decisions\|import\|outline\|plan\|reference\|report\|short\|snapshot\|style\|truth\|world | truth-files.yaml | registry loader（F445/F440 已立案族） |
| Producer | shenbi.contracts.schemas.registry.Producer | skill\|pipeline\|external\|shared | truth-files.yaml | registry loader |
| OwnershipStatus | shenbi.contracts.ownership.FileChange.status | added\|deleted\|modified\|unchanged | audit snapshot | OWNERSHIP 检查 |
| OwnershipLevel | shenbi.contracts.ownership.FileOwnership.level | field\|record_create\|record_field | - | ownership.py |
| G4Severity | shenbi.pipeline.chapter_loop.G4Severity | hard\|soft\|warn | chapter_loop G4_CHECK_MAP | chapter_loop（独立域，与 AuditSeverity 适用面互斥） |
| DriftSeverity | shenbi.skill_utils.drift_detection.linguistic_drift.DriftResult.severity | NONE\|WARN\|HARD\|ESCALATE | drift 检测 | drift 升级链（独立域，未持久化） |
| WriteSafety | shenbi.pipeline.write_safety.WriteSafety | read_only_audit\|write_isolated\|write_shared | 静态声明 | 审计波串行化 |
| RecoveryStrategy | shenbi.recovery.RecoveryStrategy | none\|auto_retry\|auto_rebuild\|halt | recovery | - |
| DriftKind | shenbi.skill_utils.drift_detection.compute_drift.DriftKind | monotonic_decline\|below_mean_2sigma\|volume_decline | compute_drift | - |
| RevisionRoute | shenbi.pipeline.revision_router.RevisionRoute | spot-fix\|regenerate\|constrained-regenerate\|reconstruction\|no-revision | revision_router | chapter_loop（T910 合一后为 enums.RevisionMode 的别名，值集同域） |
| RevisionDecision | shenbi.pipeline.revision_router.RevisionDecision | pass\|revision\|escalation | revision_router | chapter_loop |
| PipelinePhase | shenbi.pipeline.state.PipelinePhase | genesis\|chapter-loop\|closure\|completed\|failed | pipeline 状态机 | pipeline-state.json |
| GenesisState | shenbi.pipeline.state.GenesisState | pending\|in-progress\|checkpoint-pending\|completed | state 机 | pipeline-state.json（genesis 语义：completed 为终态，与 ChapterStatus.complete 属不同域） |
| ClosureState | shenbi.pipeline.state.ClosureState | pending\|in-progress\|checkpoint-pending\|completed | state 机 | pipeline-state.json |
| ChapterStatus | shenbi.pipeline.state.ChapterStatus | pending\|in-progress\|complete\|settling_failed | chapter_loop.py、error_handler.py | cli.py status 列表（T907：from_dict 容错归一旧值 completed→complete） |
| CheckpointType | shenbi.pipeline.state.CheckpointType | none\|genesis-complete\|chapter-memo\|state-settle\|escalation\|per-chapter\|volume-boundary\|book-closure | state 机 | pending_checkpoint |
| ReviewDecision | shenbi.pipeline.state.ReviewDecision | approve\|modify\|reject | pipeline/cli.py review 命令 | checkpoint_history（命令域，T909 与 ApprovalDecision 分立） |

## 命名约定（非值域，不参与机器对账）

- checker check id 必须带技能前缀，形态 `<skill>:<check-slug>`（F441）

## Dangling（他 spec 承接）

- T302 extract_h2_sections 与 lint 匹配语义统一 → C2 T4 承接（未落地前挂此标记）

## 消费侧容错映射汇总（读旧生产值，非词表）

- RevisionSeverity：blocking/BLOCKING、critical/CRITICAL、critical_per_audit → high；warning → medium；minor/MINOR、info、none、observation → low
- RevisionMode：no_op → no-revision
- SkillProgressStatus：DONE（大写）→ done
- ChapterStatus：completed → complete
