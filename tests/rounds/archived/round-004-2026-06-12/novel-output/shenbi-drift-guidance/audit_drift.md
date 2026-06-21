---
chapter: 18
drift_items:
  - source_audit: review-character
    severity: warning
    issue: "'了'字密度过高——第1章邻居对白段落中连续6句含'了'字，与PRE_WRITE_CHECK规则冲突。虽然发生在配角对白中有口语化合理性，但密度超标趋势需要控制"
    guidance: "第19章起草时，对白段落（尤其配角对白）的'了'字密度目标为≤4句连续含'了'。对于口语化表达，优先用'过''着'等结构替代冗余'了'字。不要求消除所有'了'字——仅控制连续出现的密度"
    targeted_chapter: 19
    finding_id: "review-character#1"
  - source_audit: review-character
    severity: warning
    issue: "配角工具人风险——第1章中年人(邻居)为轻度工具人角色（仅提供信息和退场），虽然有非功能性行为细节（嚼碎屑）作为缓冲，但后续章节需避免重复此模式"
    guidance: "第19章引入新配角（如地下组织的其他成员）时，确保每个有对话的配角至少有1个独立于主线需求的个人动机或行为细节。具体建议：如果第19章有组织成员发言，给其中一个角色添加与转移决策无关的个人顾虑（如'我老婆还在矿场西区'）"
    targeted_chapter: 19
    finding_id: "review-character#配角检查"
  - source_audit: review-pacing
    severity: warning
    issue: "第1章为建立章，以认知和适应为主，缺少FIRE（读者可感知的阶段性成果）。作为首章可接受，但若连续多章无爆发点会累积节奏债"
    guidance: "第19章建议在章中安排一个可感知的小规模成果——如成功获取灵能融合文献的一段关键内容、或成功完成一次小规模的对巡逻队的声东击西。不需要大的战斗场面，但读者需要在连续的组织建设/对话章节后看到一个'事情在推进'的信号"
    targeted_chapter: 19
    finding_id: "review-pacing#FIRE节奏"
  - source_audit: review-foreshadowing
    severity: warning
    issue: "hook-ch15-001（梵光历史）和hook-ch18-001（暴露风险）在本章同时处于需要推进的状态，但第1章仅完成了基础世界观铺设——后续章节需要为伏笔推进预留空间"
    guidance: "第19章建议在决策讨论中由老政委主动释放一段梵光失败的关键教训（hook-ch15-001推进），并用这个历史教训直接服务于转移vs防御的决策——伏笔推进和情节推进二合一，避免'专门讲一段历史'的说明段落"
    targeted_chapter: 19
    finding_id: "review-foreshadowing#hook推进"
---
