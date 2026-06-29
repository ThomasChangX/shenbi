"""门阈值单一源（spec 支柱二）。所有数值阈值集中此处；门 import 具名常量，
ruff 禁裸魔法数。值以 spec 为准：>=94 tier 推进、>=90 单测通过、100 收敛。
"""

from __future__ import annotations

T1_PASS: int = 94  # T1 tier advancement threshold (acceptance.json fallback)
T2_PASS: int = 94  # T2 phase advancement threshold
T3_PASS: int = 94  # T3 pipeline advancement threshold
TEST_PASS: int = 90  # individual test pass threshold
CONVERGENCE: int = 100  # convergence target
