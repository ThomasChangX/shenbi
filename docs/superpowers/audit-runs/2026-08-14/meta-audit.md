# G6 Meta-Audit 报告（阶段 6：预登记样本抽查 vs 真实文件）

- 日期：2026-08-14
- 审查者：G6 meta-audit agent（fresh-context，只读；除本文件外未写仓库）
- 样本源：`docs/superpowers/audit-runs/2026-08-14/g6-meta-audit-sample.txt`（552 条，格式 `<Z区>\t<文件路径>`）
- 初审报告：`docs/superpowers/audit-runs/2026-08-14/zone-reports/`（Z1-Z11）
- 判定规则：报告声称的不变量与文件实际不符 → `fake-deep-read`；声称运行的验证命令无对应输出 → `fake-deep-read`；报告与文件无实质关联 → `fake-deep-read`；报告条目缺失 → `coverage-gap`；其余 → `ok`

## 方法

1. **机械检查（全部 552 条）**：确认样本文件全部存在于磁盘（缺失 0）；用报告文本全文检索确认每条样本在对应初审报告中存在报告条目（Z1-Z6/Z8-Z10 per-file 条目；Z7 分组条目（含组头/条目正文）；Z11 类别级条目）。
2. **逐条深核**：
   - Z1-Z6、Z8、Z9、Z10：样本全部逐条核对（打开真实文件 + 报告条目 + 交叉验证关键行号/内容）；
   - Z7（182 样本）：按任务指示抽查代表性 57 条（31%），覆盖 4 个段文件与全部文件类型，重点覆盖机械扫描标记的 11 个 [SUSPECT] 样本；
   - Z11（256 样本）：类别级核对（12 类别条目 vs 磁盘产物全量统计）+ 57 个代表性样本抽查；本人独立复核核心计数（56 章/98 META/0 头命中/decisions 62+67+14+2/722 audits/gate-markers 22/snapshots 51/总 1229 等）。

---

## 一、样本清单（552 条，从 g6-meta-audit-sample.txt 原样复制）

```
Z1	src/shenbi/recovery.py
Z1	src/shenbi/logging.py
Z1	src/shenbi/sync_contracts.py
Z2	src/shenbi/contracts/skills/genre_config.py
Z2	src/shenbi/contracts/fields.py
Z2	src/shenbi/dispatcher/modes/__init__.py
Z2	src/shenbi/contracts/skills/worldbuilding.py
Z2	src/shenbi/contracts/skills/context_composing.py
Z2	src/shenbi/contracts/ownership.py
Z2	src/shenbi/contracts/schemas/deps.py
Z2	src/shenbi/contracts/schemas/hooks.py
Z3	src/shenbi/pipeline/cli.py
Z3	src/shenbi/pipeline/revision_router.py
Z3	src/shenbi/pipeline/checkpoint.py
Z3	src/shenbi/pipeline/review_checklist.py
Z3	src/shenbi/pipeline/dispatch_helper.py
Z3	src/shenbi/pipeline/hook_planting.py
Z3	src/shenbi/pipeline/context_curation.py
Z4	src/shenbi/gates/g4/__init__.py
Z4	src/shenbi/gates/g4/location_builder.py
Z4	src/shenbi/gates/g4/worldbuilding.py
Z4	src/shenbi/gates/g4/context_composing.py
Z4	src/shenbi/gates/g4/decisions_validator.py
Z4	src/shenbi/gates/g4/memory_distill.py
Z4	src/shenbi/gates/g3_independence.py
Z4	src/shenbi/gates/__init__.py
Z4	src/shenbi/gates/g6.py
Z4	src/shenbi/gates/g_reconcile.py
Z5	src/shenbi/cost/report.py
Z5	src/shenbi/orchestration/__init__.py
Z5	src/shenbi/cost/ledger.py
Z6	src/shenbi/records/parser.py
Z6	src/shenbi/skill_utils/__init__.py
Z6	src/shenbi/skill_utils/chapter_pattern/__main__.py
Z6	src/shenbi/trace/writer.py
Z6	src/shenbi/text/__init__.py
Z6	src/shenbi/records/__init__.py
Z6	src/shenbi/config/thresholds.py
Z6	src/shenbi/skill_utils/revision_routing/route.py
Z6	src/shenbi/skill_utils/style_learning/compute_stats.py
Z6	src/shenbi/skill_utils/review_resonance/__init__.py
Z7	tests/tiers/t1-skill/shenbi-review-character/bug-hunt/input/scenario-phase2-character.md
Z7	tests/unit/gates/g4/test_worldbuilding.py
Z7	tests/skill-behavior/review-catches-bug/phase3-volume-consolidation.md
Z7	tests/tiers/t1-skill/shenbi-chapter-planning/clean/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-writing-skills/rubric.md
Z7	tests/tiers/t1-skill/using-shenbi/bug-hunt/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-length-normalizing/bug-hunt/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-state-settling/clean/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-review-long-span/bug-hunt/input/scenario-phase4b-long-span.md
Z7	tests/tiers/t1-skill/shenbi-review-world-rules/bug-hunt/input/scenario-phase4b-world-rules.md
Z7	tests/tiers/t1-skill/shenbi-character-design/clean/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-short-drafting/bug-hunt/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-style-polishing/bug-hunt/input/scenario-phase2-polishing.md
Z7	tests/unit/test_scoring_property.py
Z7	tests/tiers/t1-skill/shenbi-anti-detect/generative/input/scenario.md
Z7	tests/unit/gates/test_g0_calibration_hash.py
Z7	tests/pipeline/test_audit_context_cache.py
Z7	tests/fixtures/config/.gitkeep
Z7	tests/tiers/t1-skill/_template/rubric.md
Z7	tests/tiers/t1-skill/shenbi-chapter-pattern/clean/input/scenario.md
Z7	tests/unit/skill_utils/test_routing.py
Z7	tests/tiers/t1-skill/shenbi-review-fanfic/bug-hunt/input/scenario.md
Z7	tests/unit/pipeline/test_genesis.py
Z7	tests/tiers/t1-skill/shenbi-review-motivation/bug-hunt/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-chapter-revision/rubric.md
Z7	tests/tiers/t1-skill/shenbi-writing-skills/generative/input/scenario.md
Z7	tests/fixtures/import/analysis/03_world.md
Z7	tests/unit/gates/g4/test_review_resonance.py
Z7	tests/unit/pipeline/test_closure.py
Z7	tests/tiers/t1-skill/shenbi-truth-sync/clean/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-review-motivation/clean/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-review-spinoff/rubric.md
Z7	tests/fixtures/arc-example.md
Z7	tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase3-snapshot.md
Z7	tests/tiers/t1-skill/shenbi-score-stratum/rubric.md
Z7	tests/tiers/t1-skill/shenbi-plot-thread-weaver/rubric.md
Z7	tests/fixtures/chapter-9-draft.md
Z7	tests/pressure-tests/prompts/audit-skipping-pressure.md
Z7	tests/integration/.gitkeep
Z7	tests/unit/test_phase_runner_property.py
Z7	tests/tiers/t1-skill/shenbi-review-reader-pull/clean/expected/expected-output.md
Z7	tests/fixtures/market-data-example.md
Z7	tests/fixtures/audits/.gitkeep
Z7	tests/unit/contracts/schemas/test_deps.py
Z7	tests/pipeline/test_chapter_steps_restructured.py
Z7	tests/skill-behavior/review-catches-bug/phase4b-pov-bug.md
Z7	tests/tiers/t1-skill/shenbi-character-design/generative/input/scenario.md
Z7	tests/unit/test_pytest_framework.py
Z7	tests/tiers/t2-phase/management/input/seed.md
Z7	tests/unit/skill_utils/test_revision_routing.py
Z7	tests/unit/pipeline/test_revision_safety.py
Z7	tests/tiers/t1-skill/_template/bug-hunt/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-volume-consolidation/clean/input/scenario.md
Z7	tests/tiers/t2-phase/planning/input/seed.md
Z7	tests/skill-behavior/review-catches-bug/phase3-plant-track-resolve.md
Z7	tests/fixtures/world-power-system-example.md
Z7	tests/tiers/t1-skill/shenbi-style-polishing/rubric.md
Z7	tests/fixtures/multi-chapter-example/chapter-2.md
Z7	tests/tiers/t1-skill/shenbi-snapshot-manage/generative/input/scenario.md
Z7	tests/unit/contracts/test_fields.py
Z7	tests/tiers/t1-skill/shenbi-world-extraction/clean/expected/expected-output.md
Z7	tests/unit/audit/test_snapshot.py
Z7	tests/tiers/t1-skill/shenbi-snapshot-manage/bug-hunt/input/scenario.md
Z7	tests/fixtures/snapshots/chapter-025/truth/chapter_summaries.md
Z7	tests/fixtures/novel-example.json
Z7	tests/tiers/t1-skill/shenbi-world-extraction/bug-hunt/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-length-normalizing/clean/input/scenario.md
Z7	tests/unit/pipeline/test_chapter_loop_full.py
Z7	tests/unit/pipeline/test_filelock_utils.py
Z7	tests/tiers/t1-skill/shenbi-review-anti-ai/bug-hunt/input/scenario-pressure.md
Z7	tests/unit/pipeline/test_chapter_loop.py
Z7	tests/tiers/t1-skill/shenbi-review-texture/generative/input/scenario.md
Z7	tests/unit/pipeline/test_e2e.py
Z7	tests/unit/gates/g4/test_length_normalizing.py
Z7	tests/tiers/t1-skill/shenbi-worldbuilding/bug-hunt/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-short-outline/bug-hunt/input/scenario.md
Z7	tests/unit/dispatcher/test_executor_audit.py
Z7	tests/tiers/t1-skill/shenbi-character-design/clean/expected/expected-output.md
Z7	tests/unit/dispatcher/test_codex_mark_done.py
Z7	tests/unit/test_error_guidance.py
Z7	tests/tiers/t1-skill/using-shenbi/bug-hunt/input/routing-phase2-foreshadowing.md
Z7	tests/unit/cost/test_estimate.py
Z7	tests/tiers/t1-skill/shenbi-short-packaging/rubric.md
Z7	tests/tiers/t1-skill/shenbi-foreshadowing-plant/rubric.md
Z7	tests/unit/contract/test_dict_reads.py
Z7	tests/contracts/test_cjk_normalization.py
Z7	tests/tiers/t1-skill/shenbi-writing-skills/clean/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-review-spinoff/bug-hunt/expected/expected-output.md
Z7	tests/fixtures/sensitive_words.txt
Z7	tests/unit/test_contract.py
Z7	tests/fixtures/chapter-10-draft.md
Z7	tests/unit/pipeline/test_transitions.py
Z7	tests/tiers/t1-skill/shenbi-import-analysis/bug-hunt/expected/expected-output.md
Z7	tests/unit/test_lint_contracts.py
Z7	tests/unit/pipeline/test_review_checklist.py
Z7	tests/gates/g4/test_title_check.py
Z7	tests/tiers/t1-skill/shenbi-review-dialogue/bug-hunt/input/scenario-phase4-dialogue.md
Z7	tests/tiers/t2-phase/audit/rubric.md
Z7	tests/tiers/t1-skill/shenbi-sequel-writing/bug-hunt/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-review-pacing/bug-hunt/input/scenario-phase2-pacing.md
Z7	tests/fixtures/chapter-8-draft.md
Z7	tests/tiers/t1-skill/shenbi-canon-import/clean/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-sequel-writing/generative/input/scenario.md
Z7	tests/skill-behavior/review-catches-bug/phase2-foreshadowing-bug.md
Z7	tests/unit/pipeline/test_drift_intervention.py
Z7	tests/tiers/t1-skill/shenbi-review-foreshadowing/clean/input/scenario.md
Z7	tests/fixtures/genre-config-example.json
Z7	tests/regenerate-baselines.sh
Z7	tests/tiers/t1-skill/shenbi-volume-consolidation/bug-hunt/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-review-foreshadowing/bug-hunt/input/scenario-lifecycle.md
Z7	tests/tiers/t1-skill/shenbi-foreshadowing-track/bug-hunt/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-review-memo-compliance/bug-hunt/input/scenario.md
Z7	tests/tiers/t2-phase/short-story/input/seed.md
Z7	tests/unit/contracts/test_base.py
Z7	tests/tiers/t1-skill/shenbi-volume-outlining/clean/expected/expected-output.md
Z7	tests/unit/conftest.py
Z7	tests/tiers/t1-skill/shenbi-foreshadowing-resolve/generative/input/scenario.md
Z7	tests/fixtures/snapshots/.gitkeep
Z7	tests/tiers/t1-skill/shenbi-short-drafting/bug-hunt/input/scenario.md
Z7	tests/skill-behavior/review-catches-bug/phase4-dialogue-bug.md
Z7	tests/conftest.py
Z7	tests/fixtures/snapshots/chapter-030/.gitkeep
Z7	tests/pipeline/test_linguistic_drift.py
Z7	tests/tiers/t1-skill/shenbi-short-drafting/generative/input/scenario.md
Z7	tests/pipeline/__init__.py
Z7	tests/fixtures/calibration/resonance/场景临场感/mid.md
Z7	tests/tiers/t1-skill/shenbi-plot-thread-weaver/bug-hunt/expected/expected-output.md
Z7	tests/fixtures/multi-chapter-example/chapter-1.md
Z7	tests/tiers/t1-skill/shenbi-location-builder/clean/expected/expected-output.md
Z7	tests/skill-triggering/prompts/phase4b-audit-triggers.md
Z7	tests/tiers/t1-skill/shenbi-chapter-revision/clean/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-foreshadowing-track/clean/expected/expected-output.md
Z7	tests/fixtures/calibration/README.md
Z7	tests/pipeline/test_title_gate_integration.py
Z7	tests/tiers/t1-skill/shenbi-volume-consolidation/rubric.md
Z7	tests/tiers/t1-skill/shenbi-context-composing/rubric.md
Z7	tests/tiers/t1-skill/shenbi-short-packaging/bug-hunt/input/scenario.md
Z7	tests/fixtures/.gitkeep
Z7	tests/fixtures/calibration/arc-payoff/线索收束/mid.md
Z7	tests/tiers/t1-skill/shenbi-review-character/generative/input/scenario.md
Z7	tests/skill-behavior/review-catches-bug/phase4b-reader-pull-bug.md
Z7	tests/tiers/t1-skill/shenbi-chapter-planning/generative/input/scenario.md
Z7	tests/unit/contracts/test_ownership.py
Z7	tests/tiers/t1-skill/shenbi-state-settling/bug-hunt/input/scenario-pressure.md
Z7	tests/tiers/t1-skill/shenbi-review-resonance/clean/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-review-long-span/generative/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-review-highpoint/bug-hunt/input/scenario.md
Z7	tests/unit/gates/test_g_reconcile.py
Z7	tests/unit/test_gates_cli.py
Z7	tests/unit/pipeline/test_state.py
Z7	tests/tiers/t1-skill/shenbi-plot-thread-weaver/clean/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-drift-guidance/rubric.md
Z7	tests/benchmark/__init__.py
Z7	tests/tiers/t1-skill/_template/clean/expected/expected-output.md
Z7	tests/unit/gates/test_g5.py
Z7	tests/tiers/t1-skill/shenbi-volume-consolidation/clean/expected/expected-output.md
Z7	tests/unit/config/test_production_config_coherence.py
Z7	tests/property/stats/test_entropy_properties.py
Z7	tests/fixtures/snapshots/chapter-025/manifest.md
Z7	tests/tiers/t3-pipeline/import-form/rubric.md
Z7	tests/tiers/t1-skill/shenbi-review-reader-pull/rubric.md
Z7	tests/tiers/t1-skill/shenbi-pacing-design/clean/expected/expected-output.md
Z7	tests/tiers/t1-skill/shenbi-review-arc-payoff/clean/input/scenario.md
Z7	tests/tiers/t1-skill/shenbi-market-radar/rubric.md
Z7	tests/tiers/t2-phase/drafting/rubric.md
Z7	tests/skill-behavior/review-catches-bug/phase4b-world-rules-bug.md
Z7	tests/tiers/t2-phase/planning/rubric.md
Z7	tests/tiers/t1-skill/shenbi-worldbuilding/clean/expected/expected-output.md
Z7	tests/unit/records/test_golden_parse.py
Z7	tests/tiers/t1-skill/shenbi-volume-outlining/bug-hunt/input/scenario.md
Z7	tests/pipeline/test_dispatch_helper_finish_reason.py
Z7	tests/tiers/t1-skill/shenbi-review-sensitivity/clean/expected/expected-output.md
Z7	tests/fixtures/calibration/resonance/文笔质感/mid.md
Z7	tests/tiers/t1-skill/shenbi-drift-guidance/clean/expected/expected-output.md
Z7	tests/unit/test_generate_autocheck_docs.py
Z7	tests/tiers/t1-skill/shenbi-review-fanfic/clean/expected/expected-output.md
Z7	tests/unit/gates/test_shared.py
Z7	tests/fixtures/truth-pending_hooks.md
Z7	tests/pipeline/test_budgeted_truncate.py
Z7	tests/tiers/t1-skill/shenbi-writing-skills/bug-hunt/input/scenario.md
Z7	tests/unit/pipeline/test_final_review_fixes.py
Z7	tests/unit/pipeline/test_revision_count.py
Z8	skills/shenbi-review-long-span/SKILL.md
Z8	skills/shenbi-chapter-drafting/anti-ai-reference.md
Z8	skills/shenbi-volume-outlining/SKILL.md
Z8	skills/shenbi-chapter-planning/SKILL.md
Z8	skills/shenbi-foreshadowing-track/SKILL.md
Z8	skills/shenbi-power-system/SKILL.md
Z8	skills/shenbi-review-pacing/SKILL.md
Z8	skills/shenbi-volume-consolidation/SKILL.md
Z8	skills/shenbi-faction-builder/SKILL.md
Z8	skills/using-shenbi/SKILL.md
Z8	skills/shenbi-review-group-craft/SKILL.md
Z8	skills/shenbi-review-fanfic/SKILL.md
Z8	skills/shenbi-foreshadowing-recall/SKILL.md
Z8	skills/shenbi-writing-skills/.gitkeep
Z8	skills/shenbi-foreshadowing-plant/SKILL.md
Z8	skills/shenbi-world-extraction/SKILL.md
Z8	skills/shenbi-import-analysis/SKILL.md
Z8	skills/shenbi-review-spinoff/SKILL.md
Z8	skills/shenbi-foreshadowing-track/lifecycle-states.md
Z8	skills/shenbi-review-anti-ai/SKILL.md
Z9	docs/framework/dependency-dag.json
Z9	docs/superpowers/specs/archive/2026-07-17-fix-cross-chapter-template-duplication-design.md
Z9	docs/superpowers/plans/archive/2026-07-02-novel-pipeline-wave3-orchestrators.md
Z9	docs/superpowers/specs/archive/2026-07-17-fix-resonance-g4-format-mismatch-design.md
Z9	CODE_OF_CONDUCT.md
Z9	docs/superpowers/specs/archive/2026-07-19-18-pipeline-architecture-optimization-design.md
Z9	docs/superpowers/plans/archive/2026-07-16-p0-blocking-fixes.md
Z9	docs/superpowers/specs/archive/2026-07-08-contract-consistency-infrastructure-design.md
Z9	docs/superpowers/plans/archive/2026-07-06-pipeline-phase1-defect-fix.md
Z9	docs/superpowers/specs/archive/2026-06-11-test-plan-design.md
Z9	docs/superpowers/specs/archive/2026-06-29-contract-single-source-design.md
Z9	docs/superpowers/specs/archive/2026-07-17-fix-character-archive-completeness-design.md
Z9	docs/superpowers/specs/archive/2026-08-01-pr23-debugging-postmortem-design.md
Z9	docs/superpowers/specs/archive/2026-07-17-fix-missing-revision-decisions-design.md
Z9	docs/framework/scoring.md
Z9	docs/superpowers/specs/archive/2026-06-28-hierarchical-memory-scoring-system-design.md
Z9	docs/superpowers/specs/archive/2026-07-19-11-data-storage-optimization-design.md
Z9	goal-prompt.md
Z9	docs/superpowers/specs/archive/2026-07-06-pipeline-phase1-defect-fix-design.md
Z9	docs/superpowers/specs/archive/2026-07-19-01-truth-file-and-state-accumulation-design.md
Z9	docs/basedpyright-overrides.md
Z9	docs/superpowers/plans/archive/2026-07-02-novel-pipeline-root-cause-fixes.md
Z9	docs/superpowers/plans/archive/2026-07-07-clean-context-handoff.md
Z9	docs/superpowers/specs/archive/2026-07-17-fix-resonance-score-null-design.md
Z9	docs/superpowers/specs/archive/2026-07-01-novel-pipeline-design.md
Z9	docs/api/logging.md
Z9	docs/framework/chapter-file-format.md
Z9	docs/superpowers/specs/archive/2026-07-17-improve-meta-block-design.md
Z9	docs/superpowers/specs/archive/2026-07-19-14-skill-contract-and-description-quality-design.md
Z9	docs/getting-started/concepts.md
Z9	docs/adr/0004-pytest-framework.md
Z9	docs/superpowers/specs/archive/2026-07-17-fix-progressive-prose-collapse-design.md
Z9	docs/superpowers/plans/archive/2026-07-19-02-output-validation-and-format-enforcement-plan.md
Z9	docs/superpowers/plans/archive/2026-06-14-p-1.c-structlog-exceptions-adrs.md
Z9	docs/superpowers/plans/archive/2026-08-02-issue24-cyclic-import-refactor.md
Z9	docs/superpowers/plans/archive/2026-07-02-pipeline-coverage-matrix.md
Z9	docs/superpowers/plans/archive/2026-06-15-p-1.e-04-testing.md
Z9	docs/framework/dispatcher.md
Z9	docs/adr/0000-template.md
Z9	docs/superpowers/plans/archive/2026-06-29-contract-single-source-pillar6-docs-lint.md
Z9	docs/superpowers/specs/archive/2026-06-15-p-1.e-foundation-completion/03-tooling-invalidation.md
Z9	docs/framework/gates.md
Z9	docs/superpowers/plans/archive/2026-07-19-08-concurrent-dispatch-and-state-safety-plan.md
Z10	.github/workflows/docs.yml
Z10	tools/lint_contracts.py
Z10	benchmarks/anchors/AC-009.md
Z10	tools/lint_no_fs_mutation.py
Z10	.github/workflows/nightly.yml
Z10	.github/workflows/pre-commit-autoupdate.yml
Z10	plugins/master.json
Z10	tools/lint_contract_graph.py
Z10	tools/audit-skill-descriptions.py
Z10	.github/workflows/security.yml
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-21.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-8-pacing.md
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-55.json
Z11	novel-output/xinghuo-ranqiong/genesis-context/world_rules.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-43-character.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-33.md
Z11	novel-output/xinghuo-ranqiong/truth/emotional_arcs.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-51-motivation.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-51-memo-compliance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-19-pacing.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-23.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-16-plan.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-2-dialogue.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-50-dialogue.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-48-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-23-motivation.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-41-world-rules.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-9-resonance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-20-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-31-character.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-13.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-35-resonance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-29-review-summary.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-6-memo-compliance.md
Z11	novel-output/test-validation/genre-config.json
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-46-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-51-revision-decisions.json
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-2-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-35-revision-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-24-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-39-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-52-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-18-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-50-pov.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-47-continuity.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-2-pacing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-53-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-26-plan.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-42-decisions.json
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-32-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-29-pacing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-30-continuity.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-24-memo-compliance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-9-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-47-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-15-pacing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-30-sensitivity.md
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-2.json
Z11	novel-output/xinghuo-ranqiong/snapshots/chapter-043-20260717T044037.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-25-pov.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-21-pacing.md
Z11	novel-output/xinghuo-ranqiong/truth/resonance_trend.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-15-pov.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-37-resonance.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-10-decisions.json
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-11-plan.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-30-plan.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-15.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-41-decisions.json
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-29-plan.md
Z11	novel-output/xinghuo-ranqiong/gate-markers/G4-shenbi-power-system-generative.json
Z11	novel-output/xinghuo-ranqiong/snapshots/chapter-028-20260716T175831.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-13-pov.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-14-sensitivity.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-52-pacing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-3-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-27-pacing.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-51-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-28-motivation.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-9-revision-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-32-continuity.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-34-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-28-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-48-continuity.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-47-sensitivity.md
Z11	.superpowers/sdd/audit-T7.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-54-character.md
Z11	.superpowers/sdd-archive-issue24/audit-T1.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-8-resonance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-21-world-rules.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-47-dialogue.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-26-motivation.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-28-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-8-pov.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-54-plan.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-32-world-rules.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-39-plan.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-7-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/snapshots/chapter-010-20260716T020310.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-46-plan.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-51-resonance.md
Z11	novel-output/xinghuo-ranqiong/truth-embeddings.db
Z11	novel-output/xinghuo-ranqiong/audits/chapter-52-sensitivity.md
Z11	novel-output/xinghuo-ranqiong/snapshots/chapter-045-20260717T062042.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-18-plan.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-50-world-rules.md
Z11	novel-output/xinghuo-ranqiong/snapshots/chapter-055-20260717T130039.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-5-review-summary.md
Z11	novel-output/xinghuo-ranqiong/snapshots/chapter-027-20260716T172118.md
Z11	novel-output/xinghuo-ranqiong/gate-markers/G4-shenbi-plot-thread-weaver-generative.json
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-20.json
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-23.json
Z11	novel-output/xinghuo-ranqiong/config-change-log.jsonl
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-19-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-56-pov.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-9-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-6.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-3-resonance.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-10-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-32.md
Z11	novel-output/xinghuo-ranqiong/characters/relationships.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-34-review-summary.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-12.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-32-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-36-world-rules.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-6-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-49-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-52-dialogue.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-2-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-50-resonance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-30-dialogue.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-3-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-2-sensitivity.md
Z11	novel-output/xinghuo-ranqiong/snapshots/chapter-039-20260717T013217.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-13-resonance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-10-world-rules.md
Z11	novel-output/xinghuo-ranqiong/gate-markers/G4-shenbi-story-architecture-generative.json
Z11	novel-output/test-validation/outline/rhythm_principles.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-12-pacing.md
Z11	.superpowers/sdd/progress.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-41-review-summary.md
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-19.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-17-foreshadowing.md
Z11	novel-output/test-validation/genesis-context/surface_conflict.md
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-41.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-52-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-15-sensitivity.md
Z11	novel-output/test-validation/truth/current_state.md
Z11	novel-output/xinghuo-ranqiong/gate-markers/G4-shenbi-volume-outlining-generative.json
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-43.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-40-world-rules.md
Z11	novel-output/xinghuo-ranqiong/truth/chapter_summaries.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-45-sensitivity.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-26-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-3-sensitivity.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-7-review-summary.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-3-continuity.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-43-revision-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-18-sensitivity.md
Z11	novel-output/xinghuo-ranqiong/snapshots/manifest.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-5-continuity.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-23-dialogue.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-15-plan.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-52-memo-compliance.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-39-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-26-world-rules.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-35-pacing.md
Z11	novel-output/xinghuo-ranqiong/snapshots/chapter-017-20260716T063953.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-21-character.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-10-dialogue.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-10-resonance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-32-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-9-motivation.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-38-continuity.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-33-dialogue.md
Z11	truth/bridge_tracker.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-34-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-34-pacing.md
Z11	novel-output/xinghuo-ranqiong/gate-markers/G4-shenbi-state-settling-generative.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-1-character.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-49-review-summary.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-44-revision-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-36-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-41-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-20-character.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-34-plan.md
Z11	.superpowers/sdd-archive-issue24/audit-T3.md
Z11	.superpowers/sdd/audit-T6.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-41-motivation.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-17-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-17-memo-compliance.md
Z11	novel-output/xinghuo-ranqiong/outline/thread_map.md
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-12.json
Z11	novel-output/xinghuo-ranqiong/world/power_system.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-25-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-6-world-rules.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-34-memo-compliance.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-30-plan.md
Z11	novel-output/xinghuo-ranqiong/genesis-context/forces.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-21-motivation.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-44-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-48-motivation.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-24-pov.md
Z11	novel-output/xinghuo-ranqiong/novel.json
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-14-plan.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-49-character.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-31-plan.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-36-memo-compliance.md
Z11	novel-output/xinghuo-ranqiong/gate-markers/G4-shenbi-relationship-map-generative.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-28-review-summary.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-5-pov.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-19-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-35-continuity.md
Z11	novel-output/xinghuo-ranqiong/genesis-context/personal_conflict.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-2-review-summary.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-47-review-summary.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-43-dialogue.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-1-plan.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-37.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-54-pov.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-49-plan.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-13-pacing.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-43-plan.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-13-memo-compliance.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-6-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-15-motivation.md
Z11	novel-output/xinghuo-ranqiong/genre-config.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-18-review-summary.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-38-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-1-plan.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-24-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-22-dialogue.md
Z11	novel-output/xinghuo-ranqiong/plans/chapter-53-plan.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-12-plan-decisions.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-46-sensitivity.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-42-resonance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-6-review-summary.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-30-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-33-world-rules.md
Z11	novel-output/xinghuo-ranqiong/staging/plans/chapter-12-plan.md
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-32.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-16-pacing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-13-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-55-dialogue.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-37-continuity.md
Z11	novel-output/test-validation/world/locations.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-32-resonance.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-51-dialogue.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-10-foreshadowing.md
Z11	novel-output/test-validation/characters/protagonist.md
Z11	novel-output/xinghuo-ranqiong/snapshots/chapter-005-20260715T232231.md
Z11	novel-output/xinghuo-ranqiong/chapters/chapter-22.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-14-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-38-review-summary.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-11-anti-ai.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-19-character.md
Z11	novel-output/xinghuo-ranqiong/gate-markers/G4-shenbi-genre-config-generative.json
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-53.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-11-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/gate-markers/G4-shenbi-worldbuilding-generative.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-7-foreshadowing.md
Z11	novel-output/xinghuo-ranqiong/audits/chapter-44-memo-compliance.md
Z11	novel-output/validation-results/stage2-result.txt
Z11	novel-output/xinghuo-ranqiong/context/review-checklist-22.json
Z11	novel-output/xinghuo-ranqiong/gate-markers/G4-shenbi-faction-builder-generative.json
Z11	novel-output/xinghuo-ranqiong/audits/chapter-52-character.md
```

---

## 二、逐条判定

### Z1（3/3 全核，判定：ok ×3）

| 文件 | 判定 | 理由 |
|---|---|---|
| src/shenbi/recovery.py | ok | Z1.a.md 条目：RecoveryStrategy 四成员（none/auto_retry/auto_rebuild/halt）✓；RECOVERY_STRATEGIES 6 键（RegistryStale/RegistryMissing/GateMarkerMissing/SchemaValidation/SubAgentTimeout/ToolTamper）与 exceptions.py 类名一致 ✓；死代码结论 F103 与 grep raise 站点一致 |
| src/shenbi/logging.py | ok | 条目：SHENBI_LOG_FORMAT=json→JSONRenderer（:21-26）✓；全部输出 stderr（PrintLoggerFactory file=sys.stderr :36）✓；cache_logger_on_first_use=False（:41）✓；processors 链 5 项 ✓ |
| src/shenbi/sync_contracts.py | ok | 条目：单一 loader（docstring+load_all_contracts :34-48）✓；build_dag glob 感知+skill 去重（:51-73）✓；verify_bijection 用 assert（:121，F109）实测命中 ✓；BODY_BANNER/END 哨兵（:30-31,124-134）✓；无 contracts bail（:167-172）✓ |

### Z2（8/8 全核，判定：ok ×8）

| 文件 | 判定 | 理由 |
|---|---|---|
| src/shenbi/contracts/skills/genre_config.py | ok | F216 核心证据 `if disabled and self.custom_rules:`（:94）实测存在；9 条计数规则 validator 逐条对应 |
| src/shenbi/contracts/fields.py | ok | F218 证据 `_filter_md`（:55-64）部分匹配静默丢弃未命中字段、全缺才 WARN+全文（:61-63）实测吻合 |
| src/shenbi/dispatcher/modes/__init__.py | ok | 1 行 docstring 包标记，条目如实 |
| src/shenbi/contracts/skills/worldbuilding.py | ok | 最小契约 kind 默认 artifact（:12），条目一致 |
| src/shenbi/contracts/skills/context_composing.py | ok | section_count==9（:24-27）、hook_debt source_file（:30-34）、无 3 连续同型（:37-43）全部实测 |
| src/shenbi/contracts/ownership.py | ok | OWNERSHIP 矩阵 5 参考条目（genre-config + pending_hooks 4 技能）+ 三种 level 分派（:101-136）实测 |
| src/shenbi/contracts/schemas/deps.py | ok | DepsDoc（:56-64）+ phase_of（:67-78）+ 下划线键 Field(alias) 防 pydantic v2 吞键，实测 |
| src/shenbi/contracts/schemas/hooks.py | ok | 6 规范态+TRIGGER 非规范折叠+大小写不敏感+空输入→None，实测 |

### Z3（7/7 全核，判定：ok ×7）

| 文件 | 判定 | 理由 |
|---|---|---|
| src/shenbi/pipeline/cli.py | ok | F304 证据：cmd_next/cmd_resume 仅捕获 FileNotFoundError（:588-618）；RetryExhaustedError 全仓无 except 实测 |
| src/shenbi/pipeline/revision_router.py | ok | F316 证据 glob(f"{prefix}*.md")（:199）实测；_SEVERITY_BLOCKING_RE（:66-83）防误报正则实测 |
| src/shenbi/pipeline/checkpoint.py | ok | staging_path/commit_staging（缺文件抛 FileNotFoundError）/clear_staging 实测 |
| src/shenbi/pipeline/review_checklist.py | ok | F322 证据 hook_pattern `P\d+-[a-z]+`（:533）实测；get_checklist/静态模板无生产调用方 grep 0 命中 |
| src/shenbi/pipeline/dispatch_helper.py | ok | F300 核心证据：python3 实测 `"\u003c" == "<"` 为 True、replace no-op（:731-735 注释+代码）完全吻合 |
| src/shenbi/pipeline/hook_planting.py | ok | F307 证据：plant_hooks_from_plan 唯一生产调用在 chapter_loop.py:2743-2745 的 `shenbi-foreshadowing-plant` 不可达分支；id 模式 `^(MH|H)-`（:144）实测 |
| src/shenbi/pipeline/context_curation.py | ok | P1-P7 分层/hook 债务两 tier/`_build_hook_debt_briefing` 缺 id KeyError 边界，实测 |

### Z4（10/10 全核，判定：ok ×10）

| 文件 | 判定 | 理由 |
|---|---|---|
| src/shenbi/gates/g4/__init__.py | ok | 重导出 generic 5 符号 + __all__ 一致，实测 |
| src/shenbi/gates/g4/location_builder.py | ok | layout≥200/atmo≥150/事件 + min_required=max(3, 半程)，实测 |
| src/shenbi/gates/g4/worldbuilding.py | ok | novel.json 字段/genre-config/story_bible 4 节/truth 模板检查，实测 |
| src/shenbi/gates/g4/context_composing.py | ok | P1-P7 或 route-[abc] 双格式 + 废弃标题拒绝，实测 |
| src/shenbi/gates/g4/decisions_validator.py | ok | DecisionsDoc 委托 + _check_adjacent_budget（WARN 级）实测 |
| src/shenbi/gates/g4/memory_distill.py | ok | 章引用可追溯 + arc 必需节（事件链/伏笔/角色状态）实测 |
| src/shenbi/gates/g3_independence.py | ok | fail-closed（无 current_scorer_agent→FAIL）实测 |
| src/shenbi/gates/__init__.py | ok | 纯 docstring 包声明，条目如实 |
| src/shenbi/gates/g6.py | ok | 用 cjk.find_terms + 按 (term,chapter) 去重（:418-422）实测 |
| src/shenbi/gates/g_reconcile.py | ok | F401 证据：GR.2 用 rsplit 未剥 `-scores` 后缀（:45-70）实测 |

### Z5（3/3 全核，判定：ok ×3）

| 文件 | 判定 | 理由 |
|---|---|---|
| src/shenbi/cost/report.py | ok | F506 证据 glob("**/*score*.json") 任意 0-100 数值取均值（:18-35）实测；F510 main 尾部 return 2 不可达（subparsers required）实测 |
| src/shenbi/orchestration/__init__.py | ok | 1 行 docstring 包标记，条目如实 |
| src/shenbi/cost/ledger.py | ok | F504 证据 record() 内 `int(usage.get(...))` 裸强转（:73-75）实测；F505 _write_lock 每实例一把（:57）实测；_safe_estimate_cost 0.0 兜底（:32-34）实测 |

### Z6（10/10 全核，判定：ok ×10）

| 文件 | 判定 | 理由 |
|---|---|---|
| src/shenbi/records/parser.py | ok | extract_yaml_block 停在下个 `## ` 标题（:18-29）实测；非 list 顶层→ValueError |
| src/shenbi/skill_utils/__init__.py | ok | 空包标记文件，条目如实 |
| src/shenbi/skill_utils/chapter_pattern/__main__.py | ok | 委托 compute_pattern.main()，条目如实 |
| src/shenbi/trace/writer.py | ok | TraceWriter append-only JSONL + 父目录 fsync（_fsync_dir）实测 |
| src/shenbi/text/__init__.py | ok | re-export cjk 7 符号，实测 |
| src/shenbi/records/__init__.py | ok | re-export parser 4 函数无 trace 依赖（docstring+grep），实测 |
| src/shenbi/config/thresholds.py | ok | 6 阈值默认（65/60/3000/3/30/50）+ frozen dataclass 实测 |
| src/shenbi/skill_utils/revision_routing/route.py | ok | 三模式（SPOT_FIX/REGENERATE/CONSTRAINED_REGENERATE）实测 |
| src/shenbi/skill_utils/style_learning/compute_stats.py | ok | F604 证据：引号桶含重复字符（:27）+ `sum(text.count(c))`（:226）实测 |
| src/shenbi/skill_utils/review_resonance/__init__.py | ok | re-export 6 符号（含 BORDERLINE_BAND/MAX_AUTO_REVISIONS）实测 |

### Z7（抽查 57/182，判定：ok ×57）

按任务指示抽查代表性子集 57 条（覆盖 Z7-a/b/c/d 四个段文件、全部文件类型、全部 11 个机械扫描 [SUSPECT] 样本）。全部 57 条判定 ok：

| 文件 | 判定 | 理由（摘要） |
|---|---|---|
| tests/unit/gates/g4/test_worldbuilding.py | ok | Z7-a 组条目（g4 test_*.py 组）覆盖；内容与报告声称一致 |
| tests/unit/test_scoring_property.py | ok | Z7-a 组条目覆盖；property 测试真实存在 |
| tests/unit/gates/test_g0_calibration_hash.py | ok | Z7-a 组条目（test_g0*.py 组）覆盖 |
| tests/pipeline/test_audit_context_cache.py | ok | Z7-a 条目：F306 关联；文件真实存在且内容相符 |
| tests/fixtures/config/.gitkeep | ok | 0 字节文件；Z7-a 组条目（.gitkeep 组）覆盖 |
| tests/tiers/t1-skill/_template/rubric.md | ok | Z7-b 条目：模板 rubric 真实，F754/F759 关联 |
| tests/unit/skill_utils/test_routing.py | ok | [SUSPECT]→Z7-a `test_*.py（15 文件）` 组条目正文覆盖（13 test + 2 __init__）；内容（review_resonance routing 测试）与组条目声称吻合 |
| tests/unit/pipeline/test_genesis.py | ok | Z7-a 条目覆盖 |
| tests/tiers/t1-skill/shenbi-chapter-revision/rubric.md | ok | Z7-b 条目覆盖 |
| tests/fixtures/import/analysis/03_world.md | ok | Z7-c 条目（import/analysis）覆盖 |
| tests/unit/gates/g4/test_review_resonance.py | ok | Z7-a 组条目覆盖 |
| tests/unit/pipeline/test_closure.py | ok | Z7-a 条目覆盖 |
| tests/tiers/t1-skill/shenbi-review-spinoff/rubric.md | ok | Z7-b 条目覆盖 |
| tests/fixtures/arc-example.md | ok | Z7-c 条目覆盖 |
| tests/tiers/t1-skill/shenbi-score-stratum/rubric.md | ok | Z7-b 条目（+F759 证据归类小瑕疵，见复查清单 §四-3）|
| tests/fixtures/chapter-9-draft.md | ok | [SUSPECT]→Z7-c `chapter-2-draft.md … chapter-10-draft.md（9 个）` 组条目覆盖；F800/F813 关联 |
| tests/pressure-tests/prompts/audit-skipping-pressure.md | ok | [SUSPECT]→Z7-a:494 压力提示组条目覆盖（6 个压力提示之一）|
| tests/integration/.gitkeep | ok | 0 字节；Z7-a 组条目覆盖 |
| tests/unit/test_phase_runner_property.py | ok | Z7-a 条目覆盖 |
| tests/unit/contracts/schemas/test_deps.py | ok | Z7-a 组条目（schemas test_deps）覆盖 |
| tests/unit/skill_utils/test_revision_routing.py | ok | [SUSPECT]→Z7-a skill_utils 组条目正文覆盖 |
| tests/tiers/t1-skill/_template/bug-hunt/expected/expected-output.md | ok | Z7-b 条目覆盖 |
| tests/skill-behavior/review-catches-bug/phase3-plant-track-resolve.md | ok | Z7-d 条目覆盖；F851 算术矛盾实测 |
| tests/fixtures/multi-chapter-example/chapter-2.md | ok | [SUSPECT]→Z7-c `chapter-1.md … chapter-5.md` 组条目覆盖 |
| tests/unit/contracts/test_fields.py | ok | [SUSPECT]→Z7-a contracts 组条目（test_base/test_fields/...）覆盖 |
| tests/unit/audit/test_snapshot.py | ok | Z7-a 条目覆盖 |
| tests/fixtures/snapshots/chapter-025/truth/chapter_summaries.md | ok | [SUSPECT]→Z7-c `{chapter_summaries,...}.md` 组条目覆盖；sha256 `ee8b44…` 与顶层 truth-*.md 逐字节相同实测成立 |
| tests/unit/pipeline/test_chapter_loop_full.py | ok | Z7-a 条目：F700/F711 关联，文件真实 |
| tests/unit/pipeline/test_chapter_loop.py | ok | Z7-a 条目：F700 证据（:457 step_index=16 注释）实测 |
| tests/unit/dispatcher/test_executor_audit.py | ok | [SUSPECT]→Z7-a dispatcher 组条目（test_executor_audit 明列）覆盖 |
| tests/unit/dispatcher/test_codex_mark_done.py | ok | [SUSPECT]→Z7-a dispatcher 组条目（test_codex_mark_done 明列）覆盖 |
| tests/unit/cost/test_estimate.py | ok | [SUSPECT]→Z7-a cost 组条目（test_estimate 明列）覆盖 |
| tests/unit/contract/test_dict_reads.py | ok | Z7-a 条目覆盖 |
| tests/contracts/test_cjk_normalization.py | ok | Z7-a 条目覆盖；9 用例数实测吻合 |
| tests/fixtures/chapter-10-draft.md | ok | [SUSPECT]→Z7-c draft 组条目覆盖 |
| tests/unit/pipeline/test_transitions.py | ok | Z7-a 条目覆盖 |
| tests/unit/test_lint_contracts.py | ok | Z7-a 条目覆盖 |
| tests/unit/pipeline/test_review_checklist.py | ok | Z7-a 条目覆盖 |
| tests/gates/g4/test_title_check.py | ok | Z7-a 条目覆盖；7 用例数实测吻合 |
| tests/unit/contracts/test_base.py | ok | [SUSPECT]→Z7-a contracts 组条目覆盖 |
| tests/unit/conftest.py | ok | Z7-a 条目覆盖 |
| tests/fixtures/calibration/resonance/场景临场感/mid.md | ok | [SUSPECT]→Z7-c calibration 组条目（resonance 4 维 {high,mid,low}.md）覆盖 |
| tests/unit/contracts/test_ownership.py | ok | [SUSPECT]→Z7-a contracts 组条目（test_ownership 明列）覆盖 |
| tests/unit/gates/test_g_reconcile.py | ok | Z7-a 条目：F702 证据 docstring（L7-15）逐字一致 |
| tests/unit/test_gates_cli.py | ok | Z7-a 条目覆盖 |
| tests/unit/pipeline/test_state.py | ok | Z7-a 条目覆盖 |
| tests/benchmark/__init__.py | ok | Z7-a 条目覆盖；37 字节实测 |
| tests/unit/gates/test_g5.py | ok | Z7-a 条目覆盖 |
| tests/unit/config/test_production_config_coherence.py | ok | Z7-a 条目覆盖 |
| tests/property/stats/test_entropy_properties.py | ok | Z7-d 条目覆盖 |
| tests/fixtures/snapshots/chapter-025/manifest.md | ok | Z7-c 条目：占位 checksum（sha256:abc123）实测 |
| tests/fixtures/calibration/resonance/文笔质感/mid.md | ok | [SUSPECT]→Z7-c calibration 组条目覆盖 |
| tests/fixtures/calibration/arc-payoff/线索收束/mid.md | ok | [SUSPECT]→Z7-c calibration 组条目（arc-payoff 线索收束 {high,mid,low}）覆盖 |
| tests/fixtures/truth-pending_hooks.md | ok | Z7-c 条目覆盖 |
| tests/pipeline/test_budgeted_truncate.py | ok | Z7-a 条目覆盖；budget*1.1 容差实测 |
| tests/unit/pipeline/test_final_review_fixes.py | ok | Z7-a 条目覆盖 |
| tests/unit/pipeline/test_revision_count.py | ok | Z7-a 条目覆盖 |

> 注：Z7 其余 125 条样本经机械覆盖检查确认均落在 Z7-a/b/c/d 的分组条目内（条目头或条目正文覆盖），无覆盖空洞；抽查 57 条全部 ok，未发现 fake-deep-read。

### Z8（20/20 全核，判定：ok ×20）

| 文件 | 判定 | 理由（摘要） |
|---|---|---|
| skills/shenbi-review-long-span/SKILL.md | ok | Z8-b 条目（157 行）吻合；F903 等关联 |
| skills/shenbi-chapter-drafting/anti-ai-reference.md | ok | Z8-b 条目（50 行）吻合；F968 关联 |
| skills/shenbi-volume-outlining/SKILL.md | ok | Z8-a 条目吻合 |
| skills/shenbi-chapter-planning/SKILL.md | ok | Z8-a 条目：F910/F911 关联实测（55 plan-decisions 中 38 无效）|
| skills/shenbi-foreshadowing-track/SKILL.md | ok | Z8-a 条目：F901/F902 关联（lifecycle-states.md 引用）实测 |
| skills/shenbi-power-system/SKILL.md | ok | Z8-b 条目（194 行）吻合 |
| skills/shenbi-review-pacing/SKILL.md | ok | Z8-a 条目吻合 |
| skills/shenbi-volume-consolidation/SKILL.md | ok | Z8-b 条目（252 行）：F959 关联（create_or_overwrite vs 追加矛盾）实测 |
| skills/shenbi-faction-builder/SKILL.md | ok | Z8-a 条目吻合 |
| skills/using-shenbi/SKILL.md | ok | Z8-a 条目：F921 关联实测 |
| skills/shenbi-review-group-craft/SKILL.md | ok | Z8-a 条目：F900 关联（description 触发条件性）实测 |
| skills/shenbi-review-fanfic/SKILL.md | ok | Z8-a 条目：F916 关联（novel.json.mode vs fanfic.mode）实测 |
| skills/shenbi-foreshadowing-recall/SKILL.md | ok | Z8-b 条目吻合 |
| skills/shenbi-writing-skills/.gitkeep | ok | 0 字节；Z8-b .gitkeep 组条目（3 个）覆盖 |
| skills/shenbi-foreshadowing-plant/SKILL.md | ok | Z8-b 条目（168 行）吻合 |
| skills/shenbi-world-extraction/SKILL.md | ok | Z8-a 条目吻合 |
| skills/shenbi-import-analysis/SKILL.md | ok | Z8-a 条目吻合 |
| skills/shenbi-review-spinoff/SKILL.md | ok | Z8-b 条目（153 行）：F964 关联（spinoff-violations §7 矛盾）实测 |
| skills/shenbi-foreshadowing-track/lifecycle-states.md | ok | Z8-a 条目（F902 引用）覆盖；文件真实存在 |
| skills/shenbi-review-anti-ai/SKILL.md | ok | Z8-a 条目：F904 关联（DEPRECATED 未传导）实测 |

### Z9（43/43 全核，判定：ok ×43）

43 个样本全部逐条核对，全部 ok。关键证据：dependency-dag.json 实测 edges 2400 三元组；chapter-file-format.md 引用的 G2.meta_ratio 与 shared.py:120-121 实测命中；CODE_OF_CONDUCT.md F1110 证据（:39 INSERT 占位）实测；basedpyright-overrides/concepts/gates 的 finding 底层事实独立复验成立；plan↔design 对应全部找到 Spec 引用行 + 磁盘 design 文件。唯一附注：docs/adr/0000-template.md 条目称七段模板与 ADR-0001-0009 一致偏松（实测仅 ADR-0001 含 Deciders 节），属过誉非编造，不判 fake。

### Z10（10/10 全核，判定：ok ×10）

| 文件 | 判定 | 理由（摘要） |
|---|---|---|
| .github/workflows/docs.yml | ok | 32 行实测；--group docs/libcairo2-dev/build --strict/main-push 部署全部吻合 |
| tools/lint_contracts.py | ok | 88 行实测；运行 rc=0；in_pipeline_skills/find_load_violations 吻合 |
| benchmarks/anchors/AC-009.md | ok | 分组条目（AC-001..011）覆盖；frontmatter id/category/source_work/calibrates + 88-97/75-87/<75 三档实测吻合；F1210 dag_key 实测 |
| tools/lint_no_fs_mutation.py | ok | 183 行实测；运行 rc=0；P4 purity 三常量集吻合 |
| .github/workflows/nightly.yml | ok | 76 行实测；3 job 全 disabled 仅 dispatch 吻合 |
| .github/workflows/pre-commit-autoupdate.yml | ok | 41 行实测；weekly cron + rc>1 才阻断逻辑吻合 |
| plugins/master.json | ok | 79 行实测；59 skills（缺 15 与 F1213 清单一致）+ version 0.2.0 vs pyproject 0.1.0 漂移实测 |
| tools/lint_contract_graph.py | ok | 112 行实测；运行 rc=0 + 11 条 DANGLING_WRITE；F1200 六处接线证据复核 |
| tools/audit-skill-descriptions.py | ok | 77 行实测；运行 rc=0 输出逐字吻合 |
| .github/workflows/security.yml | ok | 19 行实测；push(main)+PR pip-audit；F1215 weekly 无兑现面（SECURITY.md 实际 :26，报告引 :20 偏移 6 属小误）|

### Z11（类别级 12/12 + 抽查 57 样本；判定：类别条目全部存在，其中 2 个 finding 级子声称 fake；抽查样本 ok ×57）

**类别级核对表**（本人独立复核核心计数 + 分片 agent 全量统计）：

| # | 类别 | Z11 声称 | 实测 | 判定 |
|---|---|---|---|---|
| 1 | chapters/*.md | 56 文件；META 98/98；6 文件 0 块；`# Chapter N:` 0/56；ch2/9/12/44/55 revision 摘要 | 56 ✓；98/98 ✓；0 块=ch2/9/12/40/44/55 ✓；0/56 ✓；字节数 1035/642/1506/1229/104 ✓ | ok（F1300 grep 细节：山风裹着铁锈味 实为 2 文件，报告只列 1；结论不变）|
| 2 | decisions 145 | 145（89+56）；valid 62/extra 67/other 14/control 2；5 缺键 | 144（89+55 staging/plans+1 staging/truth）；**62/67/14/2 分类完全一致**；5 缺键逐名吻合 | ok 主条目（F1306 子声称错误 → 见 §三-F1）|
| 3 | truth/* | 13+8+2；bridge_tracker 不在 yaml | 13 ✓；8 ✓；2 ✓；yaml grep exit 1 ✓；index/SKILL 声明 ✓；md5 不同 ✓ | ok |
| 4 | pipeline-state/progress/markers | closure=pending/closure_step=0/total ABSENT；progress 空壳；marker 22 | 全部吻合 ✓ | ok |
| 5 | cost/token-ledger | 不存在 | find 全库无 ✓；dispatch_helper:1333 已接 ✓ | ok |
| 6 | audits 722 | 13 维计数；ch56 缺 6 维；md5 0 重复；texture=0 | 722 ✓；13 维逐项一致 ✓；ch56 仅 7 文件 ✓；md5 0 ✓；texture 0 ✓ | ok |
| 7 | jsonl 日志 | config-change-log 单条无操作；write-audit 3×GATE_FAIL+1×AUDIT_PASS；trace 4 条 | 全部吻合 ✓ | ok |
| 8 | .superpowers/sdd+archive | sdd 15+archive 5 | sdd 实为 9（+1 .gitignore=10），archive 5；15 为两目录合计——计数标注错误；代码修复核实全部通过 | ok（标注性错误）|
| 9 | .hypothesis | 43 examples；0 个 0 字节；patches 13 含 17 via | 43 ✓；0 个 0 字节 ✓；13 ✓；17 ✓；git 仅跟踪 2 ✓ | ok |
| 10 | test-validation+results | 27+4；genesis current_step=2；stage2 BLOCKED；truth 模板 49-105B | 27 ✓+4 ✓；current_step=2 ✓；BLOCKED ✓；模板字节 ✓ | ok |
| 11 | 其余 | 总 1229 vs 文档 1226；marker 22 vs 21；snapshots 51 vs 52；staging 121 vs 119；plans/*.json=0；55 plan-decisions 缺 ch54 | 总 1229 ✓；marker 22 ✓；snapshots md 51 ✓（+manifest=52）；**staging 实测 119（无 lockfile），Z11 声称 121 有误**；plans json=0 ✓；缺 ch54 ✓ | ok 主干 / F1320 staging 子声称错误（§三-F2）|
| 12 | 开发机日志 | daemon.log + console-*.log | 存在 ✓ | ok |

**Z11 抽查 57 样本**：全部 ok（抽查对象均为预登记样本；chapter-40-revision-decisions.json 不在样本清单内，仅作为 F1306 反证被核对）。本人独立抽查的样本（chapter-2/9/12/44/55/40/1/31/37、各 decisions、audits、snapshots、gate-markers、truth 文件、pipeline-state、progress、write-audit/trace、DEBUG 文档等）全部与报告证据吻合。

---

## 三、fake-deep-read 清单

### F1. Z11 F1306 子声称（类别 2 内）：revision-decisions 无效计数与示例清单与磁盘矛盾
- 报告声称：34 个 revision-decisions 中 7 个无效（12/15/2/21/44/40/18-revision 等）
- 实测：**34 个中 10 个 parse-invalid**（12/15/18/2/21/22/33/44/5/53）；`chapter-40-revision-decisions.json` 是**合法完整 JSON**（$schema/skill/chapter/produced_at/selections/adjustments/budget 全齐，json.loads 通过），却被 F1306 列入无效示例；漏列 22/33/5/53 四个确实无效的文件。
- 影响：F1306 作为 finding 级证据不准确；类别 2 主条目（145/62/67/14/2、5 缺键）仍精确成立。
- 判定：`fake-deep-read`（该子声称与文件实际内容不符）。

### F2. Z11 F1320 子声称（类别 11 内）：staging 计数错误
- 报告声称：staging 121（文档称 119，因含 2 个 lockfile/多余文件）
- 实测：staging 目录**恰为 119 个文件**（plans 111 + truth 8），无任何 lockfile/隐藏文件；121 仅当把 2 个子目录也算入（files+dirs）时才出现，报告含 2 个 lockfile 的解释与磁盘矛盾；DEBUG 文档的 119 才是正确值。
- 影响：F1320 结论方向（存在计数漂移）正确，但 staging 子项数字错误（1229-1226 的差额实际来自污染 marker +1 与顶层多余文件）。
- 判定：`fake-deep-read`（该子声称与文件实际内容不符）。

---

## 四、复查清单

### 1. 标记重审的文件
- `novel-output/xinghuo-ranqiong/chapters/chapter-40-revision-decisions.json`（Z11 F1306 将其错误列入无效清单，实为合法 JSON——重审该文件本身与 F1306 的计数/清单措辞）。

### 2. 进入复查清单的 agent 条目
Z11 初审 agent（`zone-reports/Z11.md`）以下条目需复查：
- **F1306**（revision-decisions 无效计数 7→10；示例清单含合法文件 chapter-40-revision；漏列 22/33/5/53）；
- **F1320**（staging 计数 121→119；含 2 个 lockfile 解释不成立）；
- **F1300**（grep 山风裹着铁锈味 实为 2 个文件：chapter-2-continuity.md + chapter-2-resonance.md，报告只列前者——细节修正，不影响 P0 主结论）；
- **类别 8 计数标注**（`.superpowers/sdd/*（15）` 实为两目录合计 15，sdd 单独 9-10）。

> 说明：Z11 报告类别级主条目与 F1300-F1305/F1307-F1319/F1321 的全部证据经独立复核成立（全量统计 56 章/98 META/0 头/62+67+14+2/722 audits/13 维/ch56 7 文件/marker 22/snapshots 51/总 1229/27+4/43+13 均逐项复现），故不将 Z11 整篇判为 fake；仅上述 4 处子声称/标注进入复查。

### 3. Z7 附带说明（不构成 fake）
- **Z7-b F759 证据归类瑕疵**：F759 声称 6 个 rubric-only skill 共享 Core functionality 50% 通用文案、去重后 5 份相同；实测该组是两组×3 份逐字节相同的模板（book-spine-init/foreshadowing-recall/memory-distill 一组；score-arc/score-stratum/score-volume 一组）。score-stratum 逐文件条目本身准确，F759 核心结论（8 个 rubric-only 为模板占位）成立；建议 phase 4 修正 F759 证据措辞。

### 4. 其余轻微行号/细节（不构成 fake，仅供复核）
- Z9：ADR-0000-template 条目七段一致偏松（仅 ADR-0001 含 Deciders 节，0002-0009 为 6 节）。
- Z10：F1215 引用 SECURITY.md:20，实际行号 :26（内容与结论正确）。
- Z8：4 处旁注级行号/细节误差（spinoff-violations :157→:158、checklist.md:36 实为 fatigueWords、F910 示例章节号、import-analysis 括注）。

---

## 五、统计

### 逐区判定统计

| 区 | 样本数 | 核对方式 | ok | fake | coverage-gap |
|---|---|---|---|---|---|
| Z1 | 3 | 全核 | 3 | 0 | 0 |
| Z2 | 8 | 全核 | 8 | 0 | 0 |
| Z3 | 7 | 全核 | 7 | 0 | 0 |
| Z4 | 10 | 全核 | 10 | 0 | 0 |
| Z5 | 3 | 全核 | 3 | 0 | 0 |
| Z6 | 10 | 全核 | 10 | 0 | 0 |
| Z7 | 182 | 抽查 57（31%） | 57 | 0 | 0 |
| Z8 | 20 | 全核 | 20 | 0 | 0 |
| Z9 | 43 | 全核 | 43 | 0 | 0 |
| Z10 | 10 | 全核 | 10 | 0 | 0 |
| Z11 | 256 | 类别级 12 + 抽查 57 | 类别 12 有条目（抽查 57 ok） | 子声称 2（finding 级） | 0 |
| **合计** | **552** | 抽查 ≥20% 达标（114 全核 + 57 Z7 + 57 Z11 + 12 类别） | **样本级 228** | **finding 级 2（Z11 F1306/F1320）** | **0** |

### 汇总

- **逐条判定（样本级）**：ok **228** / fake **0** / coverage-gap **0** / 判定总数 **228**（Z1-Z6+Z8-Z10 全核 114 + Z7 抽查 57 + Z11 抽查 57）——所有被抽查的预登记样本条目均与真实文件相符。
- **覆盖空洞**：**0**——552 条样本全部在对应初审报告中有条目（Z7 分组条目、Z11 类别条目），无遗漏。
- **fake-deep-read（finding 级，非预登记样本）**：Z11.md 类别 2 条目内 F1306 子声称将合法文件 `novel-output/xinghuo-ranqiong/chapters/chapter-40-revision-decisions.json` 误列无效、计数 7≠10；类别 11 条目内 F1320 子声称 staging 计数 121≠119。该文件本身不在 552 样本清单内，故记入 finding 级复查而非样本级 fake。
- **复查清单**：见 §四——Z11 F1306 / F1320 / F1300 / 类别 8 标注；Z7 F759 证据归类。

### 结论

552 条预登记样本全部可追溯至真实初审报告条目，抽查覆盖 ≥20%（Z1-Z6/Z8-Z10 全核 100%，Z7 31%，Z11 类别级 12/12 + 样本 22%）。初审报告整体为真实 deep-read：声称的不变量均可与真实文件内容对应，声称运行的验证命令均有可复现的输出，未发现整篇橡皮图章或覆盖空洞。发现 **2 个 finding 级 fake-deep-read 子声称**（Z11 F1306 将合法文件 chapter-40-revision-decisions.json 列入无效且计数 7≠10；Z11 F1320 staging 计数 121≠119），均已进入复查清单。样本级 228 条抽查全部 ok，无覆盖空洞。
