## 快照清单

**查询时间**: 2026-06-12 12:00
**项目**: 星火燃穹：位面解放战争史
**Checksum 方法**: 所有 checksum 由 `python3 -c "import hashlib; print(hashlib.sha256(open('FILE_PATH','rb').read()).hexdigest())"` 计算，非 LLM 生成

**总数**: 1 个快照
**已创建**: chapter-001

### 快照索引

| 章节 | 创建时间 | 触发器 | 文件数 | 备注 |
|------|---------|--------|--------|------|
| chapter-001 | 2026-06-12 12:00 | chapter_completion | 12（6真实+5待创建+1章节） | 第1章审计全部PASS后创建 |

### 快照详情 — chapter-001

**创建时间**: 2026-06-12 12:00
**触发器**: chapter_completion
**章节标题**: 第一章 熔炉边的异乡人
**章节字数**: 4572字
**Checksum 验证**: 随机文件 `truth/pending_hooks.md` 二次计算一致（8faa499b...d56048），文件未被修改

**快照文件清单**:

| # | 文件名 | 来源 | 状态 | 行数 | SHA256 (前16字符) |
|---|--------|------|------|------|-------------------|
| 1 | current_state.md | tests/fixtures/truth-current_state.md | 真实数据 | 57 | 18ad5599f993b562 |
| 2 | pending_hooks.md | tests/fixtures/truth-pending_hooks.md | 真实数据 | 87 | 8faa499b28ca8281 |
| 3 | chapter_summaries.md | tests/fixtures/truth-chapter_summaries.md | 真实数据 | 62 | ee8b44b79dcbad9b |
| 4 | character_matrix.md | tests/fixtures/truth-character_matrix.md | 真实数据 | 96 | 0b2006cb8249b53f |
| 5 | emotional_arcs.md | tests/fixtures/truth-emotional_arcs.md | 真实数据 | 91 | cb282051486ee019 |
| 6 | particle_ledger.md | tests/fixtures/truth-particle_ledger.md | 真实数据 | 73 | eac5be1c89bef5c6 |
| 7 | subplot_board.md | -- | 待创建 | -- | skipped |
| 8 | author_intent.md | -- | 待创建 | -- | skipped |
| 9 | current_focus.md | -- | 待创建 | -- | skipped |
| 10 | audit_drift.md | -- | 待创建 | -- | skipped |
| 11 | volume_summaries.md | -- | 待创建 | -- | skipped |
| 12 | chapter-001.md | tests/fixtures/multi-chapter-example/chapter-1.md | 真实数据 | 214 | 408cd7815a20656c |

**完整 Checksum 记录（python3 hashlib sha256）**:

| # | 文件名 | SHA256 完整值 |
|---|--------|--------------|
| 1 | current_state.md | `18ad5599f993b56201971203449bc00d7394c7ce51a5858748b6538d6fe712e2` |
| 2 | pending_hooks.md | `8faa499b28ca82817ccf6a8f6c924904309860938f4ac310324a48e609d56048` |
| 3 | chapter_summaries.md | `ee8b44b79dcbad9bcf728d305fd2934a89f2ef6ac717b15141ae84230ec982b5` |
| 4 | character_matrix.md | `0b2006cb8249b53fbf4bfacf15b3b34d2472a3a3e2c220012141d1a5144f8295` |
| 5 | emotional_arcs.md | `cb282051486ee019328900ea4d535d00db604e17df1c415177d1d814d56634a8` |
| 6 | particle_ledger.md | `eac5be1c89bef5c6d5862eee4daff2a1007c98b9ecf962e96180e47820fec9a4` |
| 7 | subplot_board.md | skipped (file not in fixtures) |
| 8 | author_intent.md | skipped (file not in fixtures) |
| 9 | current_focus.md | skipped (file not in fixtures) |
| 10 | audit_drift.md | skipped (file not in fixtures) |
| 11 | volume_summaries.md | skipped (file not in fixtures) |
| 12 | chapter-001.md | `408cd7815a20656c8fe0f3a39297085a29df8602082c1a9109217a2a04385752` |

**缺失标记**: 5 个 truth 文件（#7-#11）尚未在 fixture 中存在。在真实执行中这些文件应由 state-settling 在章节完成后生成，随后纳入快照。当前为最小可行快照 -- 6 个核心 truth 文件已覆盖状态追踪的核心维度。

**快照摘要**:
- **第1章核心事件**: 林烽穿越至梅德兰帝国矿区熔炉边，觉醒灵能分解天赋，面对灵能修炼贷款催收（42灵晶），制定"五步躺平计划"，目睹贵族鞭打矿工后选择"不管闲事"
- **关键状态**: 林烽位于矿区熔炉区，灵能感知层已激活（分解能力），债务 42 灵晶（3天期限），无盟友
- **活跃伏笔**: PLANTED = 3 个（债务机制 hook-ch1-001、灵能感知 hook-ch1-002、外部势力暗示 hook-ch1-003）
- **情感基调**: 麻木(地球失业) -> 震惊(穿越) -> 计算性冷静(债务建模) -> 压抑愤怒(催收) -> 阴暗决心(章末)
