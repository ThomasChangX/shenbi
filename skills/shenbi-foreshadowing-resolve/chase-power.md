# Chase Power 期望债务管理

## 概念

Chase Power 是读者对伏笔兑现的期待强度。每个伏笔种植时有一个初始 Chase Power，随着时间推移增长，兑现时释放。未兑现的伏笔累积 Chase Power 债务，债务过高导致读者信任崩塌。

## 债务公式

```
Chase Power = Σ (hook_power × time_since_plant × escalation_factor)
```

- hook_power: 伏笔在叙事中的重要度（core_hook=2.0, 普通=1.0, 支线=0.5）
- time_since_plant: 种植后经过的章数
- escalation_factor: 对应 escalation_curve (FLAT=1.0, RISING=1.5, EXPONENTIAL=2.0)

## 债务等级

| 等级 | CP 债务 | 行动 |
|------|---------|------|
| GREEN | < 50 | 正常 |
| YELLOW | 50-100 | 下3章内需要有伏笔兑现 |
| ORANGE | 100-200 | 下章必须有伏笔兑现 |
| RED | > 200 | 立即安排伏笔兑现或考虑放弃部分支线 |

## 兑现质量

| 兑现类型 | 说明 | CP 影响 |
|---------|------|---------|
| FULL_PAYOFF | 完全满足读者期待 | CP 释放 100% |
| PARTIAL_PAYOFF | 部分满足 | CP 释放 50%，剩余转入新伏笔 |
| TWIST_PAYOFF | 出乎预期但合理 | CP 释放 120%（超额满足） |
| FLAT_PAYOFF | 草草兑现 | CP 释放 30%，增加读者不满 |
