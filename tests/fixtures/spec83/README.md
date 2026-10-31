# spec #83 fixture 包（G0.9 真实产物拷贝）

- **来源**：`novel-xinghuo-vol1/`（gitignored 卷一真实运行项目，磁盘直读拷贝）
- **拷贝日期**：2026-10-31（Task 0，commit 45c597d9）
- **清单**：
  - `chapters/chapter-{1,2,6,13,16,17,19,23,25,26,28,30,31,33,35}.md` —— drafting 产物（15 章：T1 嵌套/截断/归并实证、T2 两臂基线、T3 转折词/字数行、T10 余额锚 ch26/ch23/ch1、T9 锚定负例 ch30）
  - `plans/chapter-{1,28}-plan.md` —— planning 产物（ch28 @hold/物象/计数双声明）
  - `truth/particle_ledger.md`（余额现值行）+ `truth/prop_registry.md`（三列表）+ `truth/facts/{counters,props}.json`（facts 键嵌套形）
  - `outline/volume_map.md`（:88 四件清单一把哨）+ `genesis-context/chapter_outline.md`（:370 还账进度表首批六行）
  - `characters/{major/*,minor/*,protagonist.md}`（≥5 张带卡面标记卡；relationships.md 非卡面不拷）
- **已知偏差**：end-of-file-fixer 为 4 个文件补尾换行（counters.json/chapter-31.md/chapter_outline.md/props.json）——内容保真，非字节级精确；无测试依赖尾字节（spec-deviations T0 已记）
- **修订对账**：四件清单/来历/档案卡/五欠账的卷一回灌随 #84 T0 执行（本包为只读取证面）
