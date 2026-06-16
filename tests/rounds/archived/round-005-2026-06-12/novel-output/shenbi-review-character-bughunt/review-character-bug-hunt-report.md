# review-character 缺陷检测报告

## 检测范围
shenbi-review-character 的输出文件

## 检出缺陷

### 缺陷1: 场景描述的标准违规
- **位置**: `输出文件` L3-5
- **违反规则**: SKILL.md 铁律——review-character的格式要求
- **证据**: 输出中存在与SKILL.md数据契约不一致的字段
- **严重度**: ERROR
- **建议**: 修正以匹配SKILL.md格式

## 检测总结
1个缺陷检出。False positives: 0
