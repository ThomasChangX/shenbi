"""Scene-level prose patch applier (spec #95 T6a,修 R7).

chapter-revision 输出「场景级替换清单」（``场景n: <全文>``——未列场景不动），
本模块提供确定性 applier：整章重写改为只重掷被替换的场景——修 3 行不再重掷
3400 字全章骰（R7：ch37 修订成功/ch41 漂移=同机制骰运）。

纯函数、幂等（重复应用同一 patch 集结果不变——场景定位键匹配后整体替换）。
未匹配的场景定位键返回 FAIL finding（不静默跳过——R6 教训：反馈必须可执行）。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: 场景定位键：``场景1``/``场景 2``（drafting 的 SCENE 分隔顺序号）。
_SCENE_KEY_RE = re.compile(r"^场景\s*(\d+)\s*[：:]\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ScenePatch:
    """One scene replacement: ``场景n:`` 定位键 + 该场景全文（替换后整体生效）。"""

    scene_no: int
    scene_text: str


@dataclass(frozen=True)
class ApplyResult:
    """应用结果：新章文 + 未匹配定位键（非空=FAIL finding,调用方必须拒收）。"""

    new_text: str
    unmatched: tuple[str, ...]


def parse_scene_replacements(payload: str) -> list[ScenePatch]:
    """Parse the ``场景n: <全文>`` replacement list from a revision output.

    段落形：``场景1：`` 行后跟该场景全文直到下一个 ``场景k：`` 行或文末。
    """
    patches: list[ScenePatch] = []
    seen_nos: set[int] = set()
    marks = list(_SCENE_KEY_RE.finditer(payload))
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(payload)
        scene_text = payload[m.end() : end].strip("\n")
        no = int(m.group(1))
        if not scene_text:
            raise ValueError(f"场景{no}：替换段为空——空体场景属格式错误（fail-loud，不静默丢弃）")
        if no in seen_nos:
            raise ValueError(f"场景{no}：重复定位键（fail-loud——last-wins 会静默丢改动）")
        seen_nos.add(no)
        patches.append(ScenePatch(scene_no=no, scene_text=scene_text))
    return patches


#: 章内场景分隔标记（与 scene_splitter 同一判据：独立行 ``<!--SCENE-->``）。
_SCENE_MARKER_LINE = re.compile(r"^<!--SCENE-->$", re.MULTILINE)


def apply_scene_replacements(chapter_text: str, patches: list[ScenePatch]) -> ApplyResult:
    """Apply patches to *chapter_text*: only listed scenes are replaced.

    场景序号=``<!--SCENE-->`` 分隔序（1 起）。未匹配序号收集进 ``unmatched``
    （fail-loud——不静默）。PRE/POST/章题不在场景段内,原样保留；场景钩随场景
    全文替换自然重生成（场景文含钩行——drafting 契约）。
    """
    if not patches:
        return ApplyResult(new_text=chapter_text, unmatched=())

    marks = list(_SCENE_MARKER_LINE.finditer(chapter_text))
    if not marks:
        return ApplyResult(
            new_text=chapter_text,
            unmatched=tuple(f"场景{p.scene_no}" for p in patches),
        )

    # 场景段：marker[i] 之后到 marker[i+1]（或文末）——段序号 1 起
    segments: list[tuple[int, int]] = []  # (start, end) 字符界
    for i, m in enumerate(marks):
        seg_start = m.end()
        seg_end = marks[i + 1].start() if i + 1 < len(marks) else len(chapter_text)
        segments.append((seg_start, seg_end))

    by_no = {p.scene_no: p for p in patches}
    unmatched = tuple(f"场景{n}" for n in sorted(by_no) if n < 1 or n > len(segments))
    if unmatched:
        return ApplyResult(new_text=chapter_text, unmatched=unmatched)

    out: list[str] = []
    cursor = 0
    for idx, (seg_start, seg_end) in enumerate(segments, start=1):
        patch = by_no.get(idx)
        if patch is None:
            continue  # 未列场景不动（R7 契约）
        out.append(chapter_text[cursor:seg_start])
        out.append("\n" + patch.scene_text + "\n")
        cursor = seg_end
    out.append(chapter_text[cursor:])
    return ApplyResult(new_text="".join(out), unmatched=())
