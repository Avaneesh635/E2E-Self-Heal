import pytest
from langgraph.graph import END

import app.nodes.patch_generator as patch_node
from app.graph import route_after_patch
from app.nodes.patch_generator import PatchApplicationError, _apply
from app.schemas import PatchInstruction, PatchOutput
from app.state import AgentState


def _instruction(
    line: int,
    original: str,
    replacement: str,
    selector: str = "#new",
) -> PatchInstruction:
    return PatchInstruction(
        line=line,
        original=original,
        replacement=replacement,
        reason="test",
        selector=selector,
    )


def _state() -> AgentState:
    return {
        "test_script_path": "test.spec.ts",
        "original_code": "await page.click('#old')\n",
        "current_code": "await page.click('#old')\n",
        "error_log": "",
        "dom_diff_context": [],
        "dom_snapshot": "",
        "analysis_report": "selector changed",
        "patch_instructions": {},
        "verification_report": {},
        "loop_count": 0,
        "is_success": False,
    }


def test_replaces_target_line_only() -> None:
    code = "await page.click('#first')\nawait page.click('#old')\n"
    result = _apply(
        code,
        [_instruction(2, "await page.click('#old')", "await page.click('#new')")],
    )
    assert result == "await page.click('#first')\nawait page.click('#new')\n"


def test_preserves_trailing_newline_state() -> None:
    code = "await page.click('#old')"  # no trailing newline
    result = _apply(
        code,
        [_instruction(1, "await page.click('#old')", "await page.click('#new')")],
    )
    assert result == "await page.click('#new')"


def test_preserves_crlf_line_endings() -> None:
    code = "await page.click('#old')\r\n"
    result = _apply(
        code,
        [_instruction(1, "await page.click('#old')", "await page.click('#new')")],
    )
    assert result == "await page.click('#new')\r\n"


def test_rejects_out_of_range_line() -> None:
    with pytest.raises(PatchApplicationError, match="outside the current file"):
        _apply(
            "await page.click('#old')\n",
            [_instruction(99, "await page.click('#old')", "await page.click('#new')")],
        )


def test_rejects_mismatched_original_line() -> None:
    with pytest.raises(PatchApplicationError, match="no longer matches"):
        _apply(
            "await page.click('#actual')\n",
            [_instruction(1, "await page.click('#stale')", "await page.click('#new')")],
        )


def test_rejects_duplicate_line_targets() -> None:
    instructions = [
        _instruction(1, "await page.click('#old')", "await page.click('#first')"),
        _instruction(1, "await page.click('#old')", "await page.click('#second')"),
    ]
    with pytest.raises(PatchApplicationError, match="targeted more than once"):
        _apply("await page.click('#old')\n", instructions)


def test_rejects_entire_patch_set_when_one_instruction_is_stale() -> None:
    instructions = [
        _instruction(1, "await page.click('#one')", "await page.click('#new-one')"),
        _instruction(2, "await page.click('#stale')", "await page.click('#new-two')"),
    ]
    with pytest.raises(PatchApplicationError, match="no longer matches"):
        _apply("await page.click('#one')\nawait page.click('#two')\n", instructions)


def test_empty_instructions_is_noop() -> None:
    code = "x\ny\n"
    assert _apply(code, []) == code


def test_rejects_multiline_replacement() -> None:
    instruction = _instruction(
        1,
        "await page.click('#old')",
        "await page.click('#new')\nawait page.goto('/admin')",
    )
    with pytest.raises(PatchApplicationError, match="exactly one line"):
        _apply("await page.click('#old')\n", [instruction])


def test_rejects_assertion_edit() -> None:
    instruction = _instruction(
        1,
        "await expect(page.locator('#old')).toBeVisible()",
        "await expect(page.locator('#new')).toBeHidden()",
    )
    with pytest.raises(PatchApplicationError, match="targets an assertion"):
        _apply("await expect(page.locator('#old')).toBeVisible()\n", [instruction])


def test_rejects_unrelated_code_edit() -> None:
    instruction = _instruction(1, "const retries = 3;", "const retries = 4;", selector="")
    with pytest.raises(PatchApplicationError, match="not limited to a locator or wait"):
        _apply("const retries = 3;\n", [instruction])


def test_allows_wait_condition_edit() -> None:
    instruction = _instruction(
        1,
        "await page.waitForSelector('#old')",
        "await page.waitForSelector('#new')",
        selector="#new",
    )
    assert _apply("await page.waitForSelector('#old')\n", [instruction]) == (
        "await page.waitForSelector('#new')\n"
    )


def test_allows_selector_only_fill_edit() -> None:
    instruction = _instruction(
        1,
        "await page.fill('#old-email', 'user@example.com')",
        "await page.fill('#new-email', 'user@example.com')",
    )

    assert _apply("await page.fill('#old-email', 'user@example.com')\n", [instruction]) == (
        "await page.fill('#new-email', 'user@example.com')\n"
    )


def test_rejects_fill_value_edit() -> None:
    instruction = _instruction(
        1,
        "await page.fill('#email', 'user@example.com')",
        "await page.fill('#email', 'admin@example.com')",
    )

    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.fill('#email', 'user@example.com')\n", [instruction])


def test_rejects_fill_value_edit_when_value_reads_changed_test_id() -> None:
    instruction = _instruction(
        1,
        "await page.fill('#email', await page.getByTestId('old-name').textContent())",
        "await page.fill('#email', await page.getByTestId('new-name').textContent())",
    )

    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply(
            "await page.fill('#email', await page.getByTestId('old-name').textContent())\n",
            [instruction],
        )


def test_rejects_locator_fill_value_edit() -> None:
    instruction = _instruction(
        1,
        "await page.locator('#email').fill('user@example.com')",
        "await page.locator('#email').fill('admin@example.com')",
    )

    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.locator('#email').fill('user@example.com')\n", [instruction])


def test_allows_locator_selector_edit_without_changing_fill_value() -> None:
    instruction = _instruction(
        1,
        "await page.locator('#old-email').fill('user@example.com')",
        "await page.locator('#new-email').fill('user@example.com')",
    )

    assert (
        _apply("await page.locator('#old-email').fill('user@example.com')\n", [instruction])
        == "await page.locator('#new-email').fill('user@example.com')\n"
    )


def test_rejects_click_force_option_edit() -> None:
    instruction = _instruction(
        1,
        "await page.click('#a', { force: true })",
        "await page.click('#a', { force: false })",
    )
    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.click('#a', { force: true })\n", [instruction])


def test_rejects_click_trial_option_edit() -> None:
    instruction = _instruction(
        1,
        "await page.click('#a', { trial: true })",
        "await page.click('#a', { trial: false })",
    )
    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.click('#a', { trial: true })\n", [instruction])


def test_rejects_dblclick_delay_option_edit() -> None:
    instruction = _instruction(
        1,
        "await page.dblclick('#a', { delay: 100 })",
        "await page.dblclick('#a', { delay: 500 })",
    )
    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.dblclick('#a', { delay: 100 })\n", [instruction])


def test_rejects_check_no_wait_after_option_edit() -> None:
    instruction = _instruction(
        1,
        "await page.check('#a', { noWaitAfter: true })",
        "await page.check('#a', { noWaitAfter: false })",
    )
    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.check('#a', { noWaitAfter: true })\n", [instruction])


def test_rejects_locator_bound_click_force_option_edit() -> None:
    instruction = _instruction(
        1,
        "await page.getByRole('button').click({ force: true })",
        "await page.getByRole('button').click({ force: false })",
    )
    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.getByRole('button').click({ force: true })\n", [instruction])


def test_rejects_hover_position_option_edit() -> None:
    instruction = _instruction(
        1,
        "await page.hover('#a', { position: { x: 1, y: 2 } })",
        "await page.hover('#a', { position: { x: 3, y: 4 } })",
    )
    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.hover('#a', { position: { x: 1, y: 2 } })\n", [instruction])


def test_allows_click_selector_only_edit() -> None:
    instruction = _instruction(
        1,
        "await page.click('#old', { force: true })",
        "await page.click('#new', { force: true })",
    )
    assert _apply("await page.click('#old', { force: true })\n", [instruction]) == (
        "await page.click('#new', { force: true })\n"
    )


def test_allows_locator_selector_edit_on_click() -> None:
    instruction = _instruction(
        1,
        "await page.getByRole('button', { name: 'Old' }).click()",
        "await page.getByRole('button', { name: 'New' }).click()",
    )
    assert (
        _apply("await page.getByRole('button', { name: 'Old' }).click()\n", [instruction])
        == "await page.getByRole('button', { name: 'New' }).click()\n"
    )


def test_ignores_action_call_in_line_comment() -> None:
    instruction = _instruction(
        1,
        "await page.click('#old') // page.click('#x",
        "await page.click('#new') // page.click('#x",
    )
    assert _apply("await page.click('#old') // page.click('#x\n", [instruction]) == (
        "await page.click('#new') // page.click('#x\n"
    )


def test_ignores_action_call_in_block_comment() -> None:
    instruction = _instruction(
        1,
        "await page.click('#old') /* page.click('#x */",
        "await page.click('#new') /* page.click('#x */",
    )
    assert _apply("await page.click('#old') /* page.click('#x */\n", [instruction]) == (
        "await page.click('#new') /* page.click('#x */\n"
    )


def test_rejects_value_edit_when_value_string_mentions_action() -> None:
    instruction = _instruction(
        1,
        "await page.fill('#msg', 'page.click(\"#x\")')",
        "await page.fill('#msg', 'page.click(\"#y\")')",
    )
    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.fill('#msg', 'page.click(\"#x\")')\n", [instruction])


def test_rejects_value_edit_when_value_template_mentions_action() -> None:
    instruction = _instruction(
        1,
        "await page.fill('#msg', `page.click(\"#x\")`)",
        "await page.fill('#msg', `page.click(\"#y\")`)",
    )
    with pytest.raises(PatchApplicationError, match="argument other than the selector"):
        _apply("await page.fill('#msg', `page.click(\"#x\")`)\n", [instruction])


def test_allows_selector_edit_when_value_mentions_action() -> None:
    instruction = _instruction(
        1,
        "await page.fill('#old', 'page.click(\"#x\")')",
        "await page.fill('#new', 'page.click(\"#x\")')",
    )
    assert _apply("await page.fill('#old', 'page.click(\"#x\")')\n", [instruction]) == (
        "await page.fill('#new', 'page.click(\"#x\")')\n"
    )


def test_rejects_edit_on_line_with_only_commented_locator() -> None:
    instruction = _instruction(
        1,
        "const retries = 3; // page.getByRole('button')",
        "const retries = 99; // page.getByRole('button')",
        selector="",
    )
    with pytest.raises(PatchApplicationError, match="not limited to a locator"):
        _apply("const retries = 3; // page.getByRole('button')\n", [instruction])


def test_rejects_edit_on_line_with_only_string_locator() -> None:
    instruction = _instruction(
        1,
        "const sel = \"page.getByRole('button')\";",
        "const sel = \"page.getByRole('button2')\";",
        selector="",
    )
    with pytest.raises(PatchApplicationError, match="not limited to a locator"):
        _apply("const sel = \"page.getByRole('button')\";\n", [instruction])


def test_rejects_edit_on_line_with_only_template_locator() -> None:
    instruction = _instruction(
        1,
        "const sel = `page.getByRole('button')`;",
        "const sel = `page.getByRole('button2')`;",
        selector="",
    )
    with pytest.raises(PatchApplicationError, match="not limited to a locator"):
        _apply("const sel = `page.getByRole('button')`;\n", [instruction])


def test_allows_selector_edit_with_assertion_token_in_comment() -> None:
    instruction = _instruction(
        1,
        "await page.click('#old') // expect(false)",
        "await page.click('#new') // expect(false)",
    )
    assert _apply("await page.click('#old') // expect(false)\n", [instruction]) == (
        "await page.click('#new') // expect(false)\n"
    )


def test_patch_generator_returns_rejection_feedback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = PatchOutput(
        instructions=[_instruction(1, "await page.click('#stale')", "await page.click('#new')")],
    )
    monkeypatch.setattr(patch_node, "generate_patch", lambda system, user: output)

    state = _state()
    result = patch_node.patch_generator(state)

    assert result["current_code"] == state["current_code"]
    assert result["patch_instructions"] == {}
    assert result["patch_application_report"]["ok"] is False
    assert result["loop_count"] == 1
    assert "[PATCH APPLICATION FEEDBACK]" in result["analysis_report"]

    state["patch_application_report"] = result["patch_application_report"]
    state["loop_count"] = result["loop_count"]
    assert route_after_patch(state) == "patch_generator"


def test_patch_generator_reports_success_and_routes_to_shadow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = PatchOutput(
        instructions=[_instruction(1, "await page.click('#old')", "await page.click('#new')")],
    )
    monkeypatch.setattr(patch_node, "generate_patch", lambda system, user: output)

    state = _state()
    result = patch_node.patch_generator(state)

    assert result["current_code"] == "await page.click('#new')\n"
    assert result["patch_application_report"] == {"ok": True}

    state["boundary_report"] = result["boundary_report"]
    state["patch_application_report"] = result["patch_application_report"]
    assert route_after_patch(state) == "shadow_verifier"


def test_generation_failure_clears_previous_rejection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_generation(system: str, user: str) -> PatchOutput:
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(patch_node, "generate_patch", fail_generation)
    state = _state()
    state["patch_application_report"] = {"ok": False, "error": "stale rejection"}

    result = patch_node.patch_generator(state)

    assert result["current_code"] == state["current_code"]
    assert result["patch_application_report"] == {"ok": True}

    state["patch_application_report"] = result["patch_application_report"]
    assert route_after_patch(state) == "shadow_verifier"


def test_boundary_violation_ends_immediately() -> None:
    # A boundary violation is permanent (the target path can't change mid-run), so the
    # router must end rather than loop back and burn the loop budget on a dead condition.
    state = _state()
    state["boundary_report"] = {"ok": False, "error": "outside architecture boundary"}
    state["patch_application_report"] = {"ok": True}
    assert route_after_patch(state) == END
    # Ends even well below the loop cap.
    state["loop_count"] = 0
    assert route_after_patch(state) == END
