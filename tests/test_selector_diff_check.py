"""The diff check that tells the model a failing selector was not renamed (Issue #388)."""

from app.preprocess.selector_diff_check import untouched_failing_selector

CLICK_TIMEOUT = """    TimeoutError: page.click: Timeout 3000ms exceeded.
    Call log:
      - waiting for locator('.cta-primary')
"""

DELAYED_RENDER = """diff --git a/src/App.tsx b/src/App.tsx
--- a/src/App.tsx
+++ b/src/App.tsx
@@ -10,3 +10,4 @@ export function App() {
+  const [ready, setReady] = useState(false);
-      <CTAButton onClick={() => setStarted(true)} />
+      {ready && <CTAButton onClick={() => setStarted(true)} />}
"""

CLASS_RENAME = """diff --git a/src/CTAButton.tsx b/src/CTAButton.tsx
--- a/src/CTAButton.tsx
+++ b/src/CTAButton.tsx
@@ -1,3 +1,3 @@
-    <button className="cta-primary" type="button">
+    <button className="cta-main" type="button">
"""


def test_an_element_rendered_later_leaves_its_selector_untouched() -> None:
    assert untouched_failing_selector(CLICK_TIMEOUT, DELAYED_RENDER) == "locator('.cta-primary')"


def test_a_rename_is_never_reported_as_untouched() -> None:
    assert untouched_failing_selector(CLICK_TIMEOUT, CLASS_RENAME) == ""


def test_a_changed_accessible_name_counts_as_touching_the_locator() -> None:
    log = "  - waiting for getByRole('button', { name: 'Get started' })\n"
    diff = (
        "--- a/CTAButton.tsx\n+++ b/CTAButton.tsx\n"
        "@@ -1,3 +1,3 @@\n-      Get started\n+      Start now\n"
    )

    assert untouched_failing_selector(log, diff) == ""


def test_a_tag_in_a_structural_selector_counts_as_touching_it() -> None:
    # `form > button` broken by a wrapper: the diff removes the old `<button` line.
    log = "  - waiting for locator('form > button')\n"
    diff = (
        "--- a/SubmitButton.tsx\n+++ b/SubmitButton.tsx\n@@ -1,3 +1,5 @@\n"
        '-    <button id="submit-btn" type="submit">\n'
        '+    <div className="form-actions">\n'
        '+      <button id="submit-btn" type="submit">\n'
    )

    assert untouched_failing_selector(log, diff) == ""


def test_a_name_inside_a_longer_identifier_does_not_count() -> None:
    # `cta-primary-wrapper` is a different class; removing it says nothing about `.cta-primary`.
    diff = '--- a/A.tsx\n+++ b/A.tsx\n@@ -1 +1 @@\n-<div className="cta-primary-wrapper">\n+<div>\n'

    assert untouched_failing_selector(CLICK_TIMEOUT, diff) == "locator('.cta-primary')"


def test_undecidable_inputs_report_nothing() -> None:
    navigation = "Error: page.goto: net::ERR_CONNECTION_REFUSED at http://localhost:47/\n"

    assert untouched_failing_selector(navigation, DELAYED_RENDER) == ""
    assert untouched_failing_selector(CLICK_TIMEOUT, "") == ""
    assert (
        untouched_failing_selector("  - waiting for locator('text=\"\"')\n", DELAYED_RENDER) == ""
    )
