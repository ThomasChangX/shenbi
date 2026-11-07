# Spec #98 T0 档位探测报告（2026-11-07）

**探测人**：SDD 协调者（plan Task 1，`/sdd-next 98` 会话）｜**预算**：spec §2 ≤$0.5，实际 **<$0.01**（§成本）
**对象**：`SHENBI_LLM_BASE_URL` 缺省 `https://api.deepseek.com/v1`（与 dispatch_helper.py:104-105 同源）

---

## §1 目录探测（GET /models）

目录**仅两档**：

| id | name | context_window | max_output_tokens | effort | 默认 effort |
|---|---|---|---|---|---|
| `deepseek-flash` | DeepSeek-**V4.1**-Flash | 1,048,576 | 393,216 | low/high/max | high |
| `deepseek-v4-pro` | DeepSeek-V4-Pro | 1,048,576 | 393,216 | low/high/max | high |

### 重要发现 A：`deepseek-v4-flash` 系退役别名

官方文档（api-docs.deepseek.com/quick_start/pricing，WebFetch 2026-11-07）：`deepseek-v4-flash` 与 `deepseek-v4-flash-vision-exp` 为 legacy 名——**仍被接受但模型已退役**，请求由 DeepSeek-V4.1-Flash-1017 服务、**按 Flash 价计费**。推论：①生产控制组（束5/束6）的 `deepseek-v4-flash` 派发实际跑在 V4.1-Flash 硬件上、计费不变——束6 基线语义与 PRICING 现键计价均不受影响；②现役 flash id=`deepseek-flash`。

### 重要发现 B：谱系高档仅一档，备档位实质空缺

提供方谱系=flash（控制组级）+pro（高档）两档。spec §4 明文「不降级回 flash 重跑——控制组证据已足」→ flash 系 id 不得作实验回退档。**裁定：主档=`deepseek-v4-pro`（谱系最高档，spec r2.1 ✓）；备档位=空缺**——pro 不可用时走 spec §4 出口「回用户重定档」，无备档可降。r2.2「主+备两档同批入表」按现实修订为：**pro（实验主档）+deepseek-flash（现役 flash id，接线占位——仅保成本护栏键完备与未来切 id 时不失明，明示不作实验回退档）**双键入表。deviation 记 `.superpowers/sdd/spec-deviations.md`。

## §2 thinking 行为探测（主档 pro，探针纪律 ≤512/≤200 tokens）

| 形 | 参数 | 结果 | 证据 |
|---|---|---|---|
| (a) 默认 | 无 thinking 参数 | **200**；content=7 字+reasoning_content 85 字；usage: prompt 93/completion 57（reasoning_tokens=50）；1.9s | /tmp/spec98-probe/a.json |
| (b) disabled | `{"thinking":{"type":"disabled"}}`（extra_body 形） | **200**；content 非空、completion=2（**零 reasoning——官方开关生效**） | b.json |
| (c) low | `{"reasoning_effort":"low"}` | **200**；content 7 字、reasoning_tokens=40 | c.json |

**session30 病理判定：未触发**——(a) 形 content 与 reasoning 并存（content 通道在小预算下正常产出），无 pinned-at-cap 形态；无需 4096 重探。MiniMax 教训面（参数被拒 2013 型）**未复现**：三形全 200。

## §3 max_tokens/超时面（stream 形，首块即断）

`max_tokens: 65536, stream: true` → **HTTP 200+流打开**（65536 接受，无 400/钳制声明）；首块延迟 ≈0.9s。目录另证 `max_output_tokens=393,216`（≥`_MODEL_OUTPUT_CEILING=65536`，不构成约束）。**900s base 超时风险评估：低**（探针级延迟 ~2s；生产 45K prompt+effort high 仍留 T2 观察点兜底——spec §4 风险行）。

## §4 rates 来源（官方，cache-miss 口径=现表约定）

DeepSeek 官方平台页（www.deepseek.com/en/platform，2026-11-07 WebFetch 逐行引用）：

| 模型 | input (cache miss)/M | output/M | cache hit/M（备注，不入表） |
|---|---|---|---|
| DeepSeek-V4-Pro | **$0.435** | **$0.87** | $0.003625 |
| DeepSeek-V4-Flash（=V4.1 Flash 价） | $0.14 | $0.28 | $0.0028 |

注：现 PRICING 表仅 input/output 两键（cache-miss 口径，与既有 flash 键一致）；cache-hit 价不入表（estimate_cost 按 prompt_tokens 全量计费=保守方向，护栏安全）。

## §5 锁定档位表（Task 2 直接抄录）

| 槽位 | 模型 id | input USD/M | output USD/M | context limit |
|---|---|---|---|---|
| **主档（实验组）** | `deepseek-v4-pro` | 0.435 | 0.87 | 1_048_576 |
| 次档（接线占位，非回退档） | `deepseek-flash` | 0.14 | 0.28 | 1_048_576 |

## §6 预注册决议（spec §1 ③）

**实验口径=启用（容量满配=provider 默认，effort high）**。依据：三形全 200（可用性✓）+(a) 形默认 thinking 下 content 正常产出（病理未触发）→ 按 spec r2.1「两口径皆可用时默认启用」。**Task 2 执行动作：删 `[overrides."shenbi-chapter-planning"]` 节**（fallthrough `[default]`=provider 默认；`[default]` 无 thinking 键已核）+ 注释块（含 kill 臂恢复条款与 T3 回滚条款）。disabled 形 (b) 探针结果留档：T3 FAIL 分支若需诊断派（disabled 口径核对）可直接引用本报告 (b) 形可用性证据。

## §7 夹具撞名判定（spec r2.2 / plan Task 2 Step 5）

**撞名实锤**：`deepseek-v4-pro` 现为真实目录模型 ≠ unknown。`tests/unit/test_pricing_fail_loud.py:21` 夹具改 `no-such-model-x`（Task 2 Step 5 触发）。

## §8 成本（探针累计）

| 探针 | tokens（prompt+completion） | 估算成本 |
|---|---|---|
| (a) 默认 | 93+57 | $0.000090 |
| (b) disabled | ~93+2 | $0.000042 |
| (c) low | ~93+47 | $0.000082 |
| stream（首块断开） | ~30+≈20 | <$0.00002 |
| **合计** | — | **≈$0.0002（≪$0.5 ✓）** |

## §9 附录：脚本形态（复现用）

探针均为 curl 直调（`-H "Authorization: Bearer $SHENBI_LLM_API_KEY"`，body 见 §2/§3 各形 JSON）；原始响应存 /tmp/spec98-probe/{a,b,c}.json（临时，不入库）。目录与 rates 引用：GET /models（§1 全录）、www.deepseek.com/en/platform（§4）、api-docs.deepseek.com/quick_start/pricing（发现 A）。
