# 伏笔生命周期状态机

## 状态转换图

~~~dot
digraph hook_lifecycle {
    PLANTED -> RELEVANT [label="REINFORCE (培育强化)"];
    PLANTED -> PLANTED [label="PROMOTE (提升微妙度)"];
    RELEVANT -> TRIGGERED [label="TRIGGER (触发)"];
    RELEVANT -> RELEVANT [label="REINFORCE (继续强化)"];
    RELEVANT -> RELEVANT [label="DEFER (延迟兑现)" style=dashed];
    TRIGGERED -> RESOLVED [label="RESOLVE (兑现)"];
    TRIGGERED -> EXPIRED [label="EXPIRE (超时)" style=dashed color=orange];
    RESOLVED -> ARCHIVED [label="ARCHIVE (归档)"];
    PLANTED -> ABANDONED [label="ABANDON (放弃)" style=dashed color=red];
    RELEVANT -> ABANDONED [label="ABANDON" style=dashed color=red];
}
~~~

## 操作定义

| 操作 | 适用状态 | 效果 | 成本 |
|------|---------|------|------|
| REINFORCE | PLANTED, RELEVANT | 强化读者对该线索的印象，推进 escalation_curve | 1 |
| PROMOTE | PLANTED | 降低 subtlety（让伏笔更明显），准备进入 RELEVANT | 1 |
| TRIGGER | RELEVANT | 触发伏笔，进入兑现准备 | 1 |
| DEFER | RELEVANT | 延迟兑现（重置 max_distance 倒计时，不推进状态） | 1 |
| RESOLVE | TRIGGERED | 兑现伏笔 | 1 |
| ARCHIVE | RESOLVED | 归档已完成伏笔 | 0 |
| ABANDON | PLANTED, RELEVANT | 放弃伏笔（增加 Chase Power 债务） | 0 (+debt) |
| EXPIRE | TRIGGERED | 超过 max_distance 未兑现（自动触发，标记为需紧急处理） | 0 |

## 晋升规则

- PROMOTE 后 subtlety 降低 0.1-0.2
- subtlety 降至 < 0.3 时自动进入 RELEVANT
- core_hook = true 的伏笔不允许 ABANDON

## 培育间隔检查

- `current_chapter - last_reinforced > cultivation_interval` → 培育过期
- 培育过期不处理 → 下次检查标记为 OVERDUE
- 连续 2 次 OVERDUE → 标记为 CRITICAL，需人工决定（ABANDON 或 DEFER）。core_hook 不允许 ABANDON
