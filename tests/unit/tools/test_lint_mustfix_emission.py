"""lint_mustfix_emission grammar unit tests (spec #88 T1)."""

from __future__ import annotations

import ast

from tools.lint_mustfix_emission import is_legal_argument


def _arg(src: str) -> ast.expr:
    # plan 审查轮1 I3：返回 Call 的**首实参**（is_legal_argument 保持纯表达式谓词）
    call = ast.parse(src.strip(), mode="eval").body
    assert isinstance(call, ast.Call)
    return call.args[0]


class TestGrammar:
    def test_finding_call_legal(self):
        assert is_legal_argument(_arg('mf.append(finding("cd.no_hook", file=fp))'))

    def test_g4_constant_legal(self):
        assert is_legal_argument(_arg('mf.append("G4.file_not_found:x")'))

    def test_joinedstr_g4_first_legal(self):
        assert is_legal_argument(_arg('mf.append(f"G4.{issue}")'))

    def test_joinedstr_path_first_illegal(self):
        assert not is_legal_argument(_arg('mf.append(f"{fp}:{issue}")'))

    def test_joinedstr_bare_family_illegal(self):
        assert not is_legal_argument(_arg('mf.append(f"cp.prop_decl:{fp}:x")'))

    def test_variable_prefix_illegal(self):
        assert not is_legal_argument(_arg('mf.append(f"{code_prefix}.not_found:{fp}")'))

    def test_generator_element_judged(self):
        assert is_legal_argument(_arg('mf.extend(f"G4.XC.x:{n}:{i}" for n, i in pairs)'))

    def test_binop_not_judged_registered_blind(self):
        # BinOp 形态不判（登记盲区）——返回 True（不报）但 docstring 登记
        assert is_legal_argument(_arg('mf.append("G4.a" + var)'))

    def test_name_arg_not_judged_registered_blind(self):
        # 轮2 I2：跨函数间接（mf.extend(变量)）不判——登记盲区
        assert is_legal_argument(_arg("mf.extend(_issues)"))

    def test_helper_call_arg_not_judged_registered_blind(self):
        # 轮2 I2：非 finding() Call 实参（helper 产列表）不判——登记盲区
        assert is_legal_argument(_arg("mf.extend(_check_hooks_structure(x))"))
