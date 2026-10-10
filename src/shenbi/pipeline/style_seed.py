"""Universal default for ``style/style_directives.md`` (session31 Q1).

The directives channel is opt-in but must not be a blank-page problem: a new
project gets a WORKING universal default seeded at ``pipeline-init`` — a
commercial web-novel band that raises the converged 7.6-char short-sentence
equilibrium toward the 起点/番茄 mainstream while staying INSIDE every hard
gate (transition words / AI markers / fatigueWords / chapter_word / paragraph
floor). Users edit freely; re-running the seed never clobbers an existing
file (``seed_style_directives`` is write-if-absent only).

Structure spec: docs/framework/style-directives.md.
"""

from __future__ import annotations

from pathlib import Path

from shenbi.logging import get_logger
from shenbi.safe_write import safe_write

log = get_logger(__name__)

DEFAULT_STYLE_DIRECTIVES = """\
# 文风目标（通用默认模板）

> 本文件由 pipeline-init 播种，可自由修改；删除整文件 = 回退到纯测量画像
> （style_profile 描述「现在是什么」，本文件设定「要什么」）。
> 结构说明与硬闸边界见 `docs/framework/style-directives.md`：转折词密度、
> AI 标记词、fatigueWords、字数契约、段落下限五道硬闸不因本文件松动。

## 节奏与句法

- 叙述句目标带：10-20 字/句；对白保持短促（4-12 字/句）
- 长短交替：连续 3 句短句后须出现 1 句 ≥16 字的收束长句；连续 2 句长句后回到短句
- 段落形态：段均 2-4 句；成段叙述与单行对白交替，避免连续 5 段以上同构断行

## 意象与修辞

- 感官细节密度：每千字 2-4 处（触觉/听觉优先于视觉）
- 比喻预算：每千字 ≤2 处，喻体取材当章场景物象，不用通用喻体（月光如水／如释重负类）

## 对白/叙述配比

- 对白占比目标：35-55%（引号内文字 / 正文总字）
- 对白带归属或动作拍的比例 ≥70%；连续裸对白（无归属无动作）≤4 轮
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
