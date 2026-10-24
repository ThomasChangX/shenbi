"""Universal default for ``style/style_directives.md`` (session31 Q1).

The directives channel is opt-in but must not be a blank-page problem: a new
project gets a WORKING universal default seeded at ``pipeline-init`` — a
commercial web-novel band that raises the converged 7.6-char short-sentence
equilibrium toward the 起点/番茄 mainstream while staying INSIDE every hard
gate (transition words / AI markers / fatigueWords / chapter_word / paragraph
floor). Users edit freely; re-running the seed never clobbers an existing
file (``seed_style_directives`` is write-if-absent only).

spec #71 v2: re-anchored to the six-author common band (基带 12-25 /
奔涌-收割落差配额 / 比喻双向带 / 金句三写法 / 意象母题行).

Structure spec: docs/framework/style-directives.md.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write

log = get_logger(__name__)

DEFAULT_STYLE_DIRECTIVES = """\
# 文风目标（通用默认模板 v2）

> 本文件由 pipeline-init 播种，可自由修改；删除整文件 = 回退到纯测量画像
> （style_profile 描述「现在是什么」，本文件设定「要什么」）。
> 结构说明与硬闸边界见 `docs/framework/style-directives.md`：转折词密度、
> AI 标记词、fatigueWords、字数契约、段落下限五道硬闸不因本文件松动。

## 节奏与句法

- 叙述句基带：12-25 字/句；对白保持短促（4-12 字/句）
- 长短落差（惊艳主引擎）：每场景 ≥1 句 ≥35 字奔涌长句（铺陈蓄势），
  其后 3 句内落 1 句 ≤10 字收割短句；连续 4 句两两互差 ≤5 字 = 节奏平段，须打破
- 段落形态：段均 2-4 句；成段叙述与单行对白交替，避免连续 5 段以上同构断行

## 意象与修辞

- 感官细节密度：每千字 3-5 处（触觉/听觉优先于视觉）
- 比喻带（双向，叙述文字口径）：每千字 2-4 处，低于下限 = 干燥、高于上限 = 堆砌；
  喻体必须取材当章场景物象，通用喻体（月光如水／如释重负／隔层毛玻璃类）= 违规
- 意象母题：每卷 1-2 个核心物象（卷纲「金句、母题物象与梗位」行指定），
  每章 ≥1 次变奏复现，语境须不同

## 金句

- 每章 1 处候选金句位（对白内或叙述收束处）；写法三选一：
  对比（两个具象并置见张力，如「账上得有数。账上得有过磅这一下。」）／
  反差（语境错位：宏大词入琐事，或琐细词入宏大）／
  口诀化（短句可记诵，如「白天漏灰，夜里漏光。」）
- 禁对仗堆砌、禁「不是…而是…」变体；金句落位后 2 句内收，不解释不展开

## 对白/叙述配比

- 对白占比目标：35-55%（引号内文字 / 正文总字）
- 关键对白三层：信息／关系变化／潜台词至少推进其一
  （潜台词三法：答非所问／一语双关／反话克制）
- 连续裸对白（无归属无动作）≤4 轮；对白带归属或动作拍的比例 ≥70%

## 章型微调（自动，通常无需改动）

- 上述各带是全书基带；drafting 按备忘段 1 的 chapter_role/chapter_type 在带内
  自动调制重心——高潮 = 斩截与咏叹交替（短句连排后允许 1-2 句 ≥35 字咏叹长句）、
  过渡 = 长句与意象、battle = 动觉意象、dialogue = 对带上沿，见 drafting 创作原则 7
- 仅当某章型需要越出基带时才在此按章型覆写
"""


def seed_style_directives(project_dir: Path) -> bool:
    """Write the universal default directives file if (and only if) absent.

    Returns True when a file was seeded, False when one already exists (the
    user's authored target is never overwritten — style-learning 铁律 5's
    hands-off rule applies to the framework's own seeding path too).
    """
    path = project_dir / "style" / "style_directives.md"
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_write(path, DEFAULT_STYLE_DIRECTIVES.encode("utf-8"))
    log.info("style_directives_seeded", path=str(path))
    return True
