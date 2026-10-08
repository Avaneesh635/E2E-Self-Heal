from pathlib import Path

import pytest
from pydantic import ValidationError

from app.benchmark import (
    BenchmarkScenario,
    BenchmarkResult,
    _count_prompt_tokens,
    _benchmark_scenario,
    _line_containing,
    _tokenizer,
    example_scenarios,
    run_example_benchmark,
)
from app.config import settings
from app.preprocess.jsx_chunker import CodeChunk
from app.prompts.diagnoser import build_user_prompt


def test_prompt_builder_uses_chunk_metadata_and_optional_snapshot() -> None:
    prompt = build_user_prompt(
        "Error: timeout",
        [{"attribute": "id", "before": "old", "after": "new"}],
        "- role: button\n  name: Submit",
        CodeChunk(source="<button>Submit</button>\n", start_line=4, end_line=4),
    )

    assert "ARIA page snapshot (at failure)" in prompt
    assert "semantic JSX chunk, lines 4-4" in prompt
    assert "<button>Submit</button>" in prompt


def test_semantic_chunk_prompt_has_fewer_tokens_than_full_file_prompt() -> None:
    full_source = "\n".join(f"const unused{index} = {index};" for index in range(50))
    full_prompt = build_user_prompt(
        "Error: timeout",
        [],
        "",
        CodeChunk(source=full_source, start_line=1, end_line=50, is_fallback=True),
    )
    semantic_prompt = build_user_prompt(
        "Error: timeout",
        [],
        "",
        CodeChunk(source="<button>Submit</button>", start_line=25, end_line=25),
    )

    assert _count_prompt_tokens(semantic_prompt) < _count_prompt_tokens(full_prompt)


def _labeled(name: str, test_path: Path, diff_path: Path, selector: str) -> BenchmarkScenario:
    return BenchmarkScenario.model_validate(
        {
            "name": name,
            "class": "selector_drift",
            "expected_outcome": "repair",
            "failing_selector": selector,
            "rationale": "A labeled scenario.",
            "test_path": test_path,
            "diff_path": diff_path,
        }
    )


def _write_scenario(root: Path, name: str, meta: str | None) -> Path:
    directory = root / name
    directory.mkdir()
    (directory / "spec.ts").write_text("await page.click('#x')")
    (directory / "change.patch").write_text("")
    if meta is not None:
        (directory / "meta.json").write_text(meta)
    return directory


_META = '{"class":"selector_drift","expected_outcome":"repair","failing_selector":"#x","rationale":"ok"}'


def test_benchmark_reads_the_whole_labeled_corpus_with_unchanged_token_numbers() -> None:
    results = {result.name: result for result in run_example_benchmark()}

    assert set(results) == {scenario.name for scenario in example_scenarios()}
    # Pinned from before the corpus moved to meta.json: discovery must not change them.
    assert (results["id-rename"].full_prompt_tokens, results["id-rename"].tokens_saved) == (431, 0)
    assert results["id-rename"].context_strategy == "whole-file fallback"
    jsx = results["jsx-context"]
    assert (jsx.full_prompt_tokens, jsx.chunked_prompt_tokens) == (594, 290)
    assert jsx.context_strategy == "semantic JSX chunk (26-28)"


def _corpus(repository_root: Path) -> Path:
    root = repository_root / "examples" / "scenarios"
    root.mkdir(parents=True)
    return root


def test_scenario_metadata_is_loaded_into_the_benchmark_scenario(tmp_path: Path) -> None:
    _write_scenario(_corpus(tmp_path), "drift", _META)

    (scenario,) = example_scenarios(tmp_path)

    assert scenario.scenario_class.value == "selector_drift"
    assert scenario.expected_outcome.value == "repair"
    assert scenario.rationale == "ok"
    assert scenario.test_path == tmp_path / "examples" / "scenarios" / "drift" / "spec.ts"


@pytest.mark.parametrize(
    ("meta", "message"),
    [
        (None, "missing meta.json"),
        (_META.replace("selector_drift", "selector_dirft"), "class"),
        (_META.replace('"repair"', '"retry"'), "expected_outcome"),
        (_META.replace(',"rationale":"ok"', ""), "rationale"),
        (_META.replace(',"rationale":"ok"', ',"rationale":""'), "rationale"),
        (_META.replace("}", ',"runable":false}'), "runable"),
    ],
)
def test_malformed_scenario_metadata_fails_loudly_at_load_time(
    tmp_path: Path, meta: str | None, message: str
) -> None:
    root = _corpus(tmp_path)
    _write_scenario(root, "good", _META)
    _write_scenario(root, "bad", meta)

    with pytest.raises(ValueError, match=message):
        example_scenarios(tmp_path)


def test_scenario_missing_its_change_patch_fails_loudly(tmp_path: Path) -> None:
    root = _corpus(tmp_path)
    (_write_scenario(root, "no-patch", _META) / "change.patch").unlink()

    with pytest.raises(ValueError, match="missing change.patch"):
        example_scenarios(tmp_path)


def test_benchmark_result_rejects_a_chunk_larger_than_the_full_prompt() -> None:
    with pytest.raises(ValidationError, match="must not exceed"):
        BenchmarkResult(
            name="invalid",
            context_strategy="semantic JSX chunk",
            full_prompt_tokens=1,
            chunked_prompt_tokens=2,
        )


def test_benchmark_uses_configured_semantic_jsx_margin(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    test_path = tmp_path / "button.spec.tsx"
    test_path.write_text(
        "\n".join(
            [
                *(f"const unused{index} = {index};" for index in range(50)),
                "export function ButtonTest() {",
                "  return (",
                "    <section>",
                '      <button id="old-button">Submit</button>',
                "    </section>",
                "  );",
                "}",
            ]
        )
    )
    diff_path = tmp_path / "button.diff"
    diff_path.write_text(
        """diff --git a/button.tsx b/button.tsx
index 1111111..2222222 100644
--- a/button.tsx
+++ b/button.tsx
@@ -1,5 +1,5 @@
 export function Button() {
   return (
-    <button id="old-button">Submit</button>
+    <button id="new-button">Submit</button>
   );
 }
"""
    )

    monkeypatch.setattr(settings, "jsx_chunk_margin_lines", 0)
    result = _benchmark_scenario(_labeled("jsx-example", test_path, diff_path, "old-button"))

    assert result.context_strategy == "semantic JSX chunk (54-54)"
    assert result.chunked_prompt_tokens < result.full_prompt_tokens
    assert result.tokens_saved > 0


def test_line_containing_rejects_missing_selector() -> None:
    with pytest.raises(ValueError, match="not present"):
        _line_containing("await page.click('#present')", "#missing")


def test_result_calculates_token_savings() -> None:
    result = BenchmarkResult(
        name="example",
        context_strategy="semantic JSX chunk (1-1)",
        full_prompt_tokens=100,
        chunked_prompt_tokens=20,
    )

    assert result.tokens_saved == 80
    assert result.savings_percent == 80.0


def test_tokenizer_is_loaded_once(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeTokenizer:
        def encode(self, text: str) -> list[str]:
            return list(text)

    def fake_get_encoding(name: str) -> FakeTokenizer:
        calls.append(name)
        return FakeTokenizer()

    _tokenizer.cache_clear()
    monkeypatch.setattr("app.benchmark.tiktoken.get_encoding", fake_get_encoding)
    try:
        _count_prompt_tokens("first prompt")
        _count_prompt_tokens("second prompt")
    finally:
        _tokenizer.cache_clear()

    assert calls == ["cl100k_base"]
