# 触发测试：伏笔生命周期（3技能路由区分）

测试目标：验证 `using-shenbi` 能正确区分伏笔的三个阶段（种植/追踪/兑现），分别路由到对应的技能。

## 测试用例 A：种植阶段

### 用户输入

```
章节备忘里说要在这里埋一条伏笔，关于师姐的真正身世。帮我种下这条hook。
```

### 期望路由: `shenbi-foreshadowing-plant`

## 测试用例 B：追踪阶段

### 用户输入

```
第20章写完了，帮我检查一下伏笔池的状态，看看哪些hook需要推进了。
```

### 期望路由: `shenbi-foreshadowing-track`

## 测试用例 C：兑现阶段

### 用户输入

```
hook-003已经到TRIGGERED状态了，是时候收线了。帮我在这一章兑现它。
```

### 期望路由: `shenbi-foreshadowing-resolve`

## 通过条件

- [ ] 用例 A 路由到 `shenbi-foreshadowing-plant`
- [ ] 用例 B 路由到 `shenbi-foreshadowing-track`
- [ ] 用例 C 路由到 `shenbi-foreshadowing-resolve`
- [ ] 三个用例不互相混淆

## 失败条件

- 任何用例路由到 `shenbi-review-foreshadowing`（那是审计，不是操作） → FAIL
- 用例 A 路由到 track 或 resolve → FAIL
- 用例 B 路由到 plant 或 resolve → FAIL
- 用例 C 路由到 plant 或 track → FAIL
