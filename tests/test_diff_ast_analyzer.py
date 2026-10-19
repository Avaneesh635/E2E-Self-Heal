"""Tests for the diff AST analyzer with new-file line number tracking (Issue #224)."""

import pytest

import app.preprocess.diff_ast_analyzer as analyzer_module
from app.preprocess.diff_ast_analyzer import analyze_diff


class TestDiffLineNumberTracking:
    """Test that line numbers are correctly tracked through diff hunks."""

    def test_single_hunk_added_element(self) -> None:
        """Added element should get the correct new-file line number."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -10,6 +10,7 @@ export const App = () => {
   return (
     <div>
       <p>Hello</p>
+      <button>Click me</button>
     </div>
   );
 };
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 1
        assert diffs[0].file == "test.tsx"
        assert diffs[0].line == 13
        assert diffs[0].current.get("tag") == "button"
        assert diffs[0].previous == {}

    def test_single_hunk_modified_element(self) -> None:
        """Modified element should get the new-file line number."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -5,5 +5,5 @@ export const App = () => {
   return (
     <div>
-      <button className="old">Click</button>
+      <button className="new">Click</button>
     </div>
   );
 };
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 1
        assert diffs[0].file == "test.tsx"
        assert diffs[0].line == 7
        assert diffs[0].current.get("attributes", {}).get("className") == "new"
        assert diffs[0].previous.get("attributes", {}).get("className") == "old"

    def test_multiple_hunks(self) -> None:
        """Multiple hunks should each track their own line numbers."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -1,3 +1,4 @@
+<Header />
 <div>
   <p>First</p>
 </div>
@@ -20,3 +21,4 @@ export const App = () => {
 <div>
   <p>Second</p>
+  <Footer />
 </div>
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 2
        assert diffs[0].line == 1
        assert diffs[0].current.get("tag") == "Header"
        assert diffs[1].line == 23
        assert diffs[1].current.get("tag") == "Footer"

    def test_deleted_element_line_zero(self) -> None:
        """Deleted elements should have line=0 (unknown in new file)."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -5,5 +5,4 @@ export const App = () => {
   return (
     <div>
-      <button>Delete me</button>
       <p>Keep me</p>
     </div>
   );
 };
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 1
        assert diffs[0].file == "test.tsx"
        assert diffs[0].line == 0
        assert diffs[0].previous.get("tag") == "button"
        assert diffs[0].current == {}

    def test_multiline_jsx_element(self) -> None:
        """Multi-line JSX elements should use the opening tag's line number."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -10,6 +10,10 @@ export const App = () => {
   return (
     <div>
+      <div
+        className="wrapper"
+        id="main"
+      >
         <p>Content</p>
+      </div>
     </div>
   );
 };
"""
        diffs = analyze_diff(diff)
        div_diffs = [d for d in diffs if d.current.get("tag") == "div"]
        assert len(div_diffs) >= 1
        assert div_diffs[0].line == 12
        assert div_diffs[0].current.get("attributes", {}).get("className") == "wrapper"

    def test_new_file_dev_null(self) -> None:
        """New file (from /dev/null) should track lines correctly."""
        diff = """diff --git a/new.tsx b/new.tsx
new file mode 100644
--- /dev/null
+++ b/new.tsx
@@ -0,0 +1,5 @@
+export const NewComponent = () => {
+  return (
+    <button>New</button>
+  );
+};
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 1
        assert diffs[0].file == "new.tsx"
        assert diffs[0].line == 3
        assert diffs[0].current.get("tag") == "button"

    def test_deleted_file_dev_null(self) -> None:
        """Deleted file (to /dev/null) should still parse but deletions have line=0."""
        diff = """diff --git a/old.tsx b/old.tsx
deleted file mode 100644
--- a/old.tsx
+++ /dev/null
@@ -1,5 +0,0 @@
-export const OldComponent = () => {
-  return (
-    <button>Old</button>
-  );
-};
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 1
        assert diffs[0].file == "old.tsx"
        assert diffs[0].line == 0
        assert diffs[0].previous.get("tag") == "button"

    def test_renamed_file(self) -> None:
        """Renamed file should continue tracking line numbers under the new name."""
        diff = """diff --git a/old.tsx b/new.tsx
similarity index 100%
rename from old.tsx
rename to new.tsx
--- a/old.tsx
+++ b/new.tsx
@@ -1,3 +1,4 @@
 export const Component = () => {
+  <button>Added</button>
   return <div>Content</div>;
 };
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 1
        assert diffs[0].file == "new.tsx"
        assert diffs[0].line == 2
        assert diffs[0].current.get("tag") == "button"

    def test_context_lines_increment_counters(self) -> None:
        """Context lines (starting with space) should increment both line counters."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -1,6 +1,7 @@
 export const App = () => {
   return (
     <div>
       <p>Context line 1</p>
       <p>Context line 2</p>
+      <button>Added</button>
     </div>
   );
 };
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 1
        assert diffs[0].line == 6

    def test_multiple_elements_same_hunk(self) -> None:
        """Consecutive added elements should each get correct line numbers."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -10,4 +10,6 @@ export const App = () => {
   return (
     <div>
+      <button id="btn1">First</button>
+      <button id="btn2">Second</button>
     </div>
   );
 };
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 2
        assert sorted(d.line for d in diffs) == [12, 13]

    def test_replace_with_multiple_changes(self) -> None:
        """Replace operation should pair elements correctly with line numbers."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -5,5 +5,5 @@ export const App = () => {
   return (
     <div>
-      <button className="old1">First</button>
-      <button className="old2">Second</button>
+      <button className="new1">First</button>
+      <button className="new2">Second</button>
     </div>
   );
 };
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 2
        assert sorted(d.line for d in diffs) == [7, 8]
        classes = sorted(d.current.get("attributes", {}).get("className") for d in diffs)
        assert classes == ["new1", "new2"]
        assert all(d.previous.get("tag") == "button" for d in diffs)

    def test_regex_fallback_line_tracking(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Line tracking must hold when tree-sitter is unavailable (regex backend)."""
        monkeypatch.setattr(analyzer_module, "_HAS_TREE_SITTER", False)
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -10,4 +10,6 @@ export const App = () => {
   return (
     <div>
+      <button id="btn1">First</button>
+      <button id="btn2">Second</button>
     </div>
   );
 };
"""
        diffs = analyzer_module.analyze_diff(diff)
        assert len(diffs) == 2
        assert sorted(d.line for d in diffs) == [12, 13]

    def test_dotted_and_hyphenated_tags(self) -> None:
        """Dotted (member) and hyphenated (custom element) tags are extracted with lines."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -1,2 +1,4 @@
 <div>
+  <Form.Field name="email" />
+  <my-widget id="w1">Hi</my-widget>
 </div>
"""
        diffs = analyze_diff(diff)
        by_tag = {d.current.get("tag"): d.line for d in diffs}
        assert by_tag == {"Form.Field": 2, "my-widget": 3}

    def test_removed_content_line_starting_with_dashes(self) -> None:
        """A removed line like '---custom-prop' must not be read as a --- header."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -1,4 +1,3 @@
 <div>
---custom-prop
-  <button id="old">Old</button>
+  <button id="new">New</button>
 </div>
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 1
        assert diffs[0].current.get("tag") == "button"
        assert diffs[0].line == 2

    def test_blank_context_line_keeps_counters_aligned(self) -> None:
        """Blank context lines must advance both line counters."""
        diff = """diff --git a/test.tsx b/test.tsx
--- a/test.tsx
+++ b/test.tsx
@@ -1,4 +1,5 @@
 <div>

   <p>a</p>
+  <button id="b">B</button>
 </div>
"""
        diffs = analyze_diff(diff)
        assert len(diffs) == 1
        assert diffs[0].current.get("tag") == "button"
        assert diffs[0].line == 4

    @pytest.mark.parametrize(
        ("scenario", "removed_id", "added_attribute", "added_value"),
        [
            (
                "settings-notifications-drift",
                "notifications-toggle",
                "name",
                "email-notifications",
            ),
            ("account-password-drift", "password-input", "name", "new-password"),
            ("checkout-quantity-drift", "quantity", "id", "item-quantity"),
            ("account-avatar-drift", "avatar-input", "id", "avatar-file"),
        ],
    )
    def test_multiline_attribute_replacements(
        self,
        scenario: str,
        removed_id: str,
        added_attribute: str,
        added_value: str,
    ) -> None:
        """Attribute-only edits in multiline opening tags report one input change."""
        patches = {
            "settings-notifications-drift": """diff --git a/examples/demo-app/src/components/settings/SettingsNotifications.tsx b/examples/demo-app/src/components/settings/SettingsNotifications.tsx
--- a/examples/demo-app/src/components/settings/SettingsNotifications.tsx
+++ b/examples/demo-app/src/components/settings/SettingsNotifications.tsx
@@ -9,7 +9,7 @@ export function SettingsNotifications() {
       <label>
         Email notifications
         <input
-          id="notifications-toggle"
+          name="email-notifications"
           type="checkbox"
           checked={enabled}
           onChange={(event) => setEnabled(event.target.checked)}
""",
            "account-password-drift": """diff --git a/examples/demo-app/src/components/account/AccountPassword.tsx b/examples/demo-app/src/components/account/AccountPassword.tsx
--- a/examples/demo-app/src/components/account/AccountPassword.tsx
+++ b/examples/demo-app/src/components/account/AccountPassword.tsx
@@ -8,7 +8,7 @@ export function AccountPassword() {
     <section aria-labelledby="account-password-heading">
       <h2 id="account-password-heading">Password</h2>
       <input
-        id="password-input"
+        name="new-password"
         aria-label="New password"
         type="password"
         value={password}
""",
            "checkout-quantity-drift": """diff --git a/examples/demo-app/src/components/checkout/CheckoutQuantity.tsx b/examples/demo-app/src/components/checkout/CheckoutQuantity.tsx
--- a/examples/demo-app/src/components/checkout/CheckoutQuantity.tsx
+++ b/examples/demo-app/src/components/checkout/CheckoutQuantity.tsx
@@ -12,7 +12,7 @@ export function CheckoutQuantity() {
       <label>
         Quantity
         <input
-          id="quantity"
+          id="item-quantity"
           type="number"
           min="1"
           value={quantity}
""",
            "account-avatar-drift": """diff --git a/examples/demo-app/src/components/account/AccountAvatar.tsx b/examples/demo-app/src/components/account/AccountAvatar.tsx
--- a/examples/demo-app/src/components/account/AccountAvatar.tsx
+++ b/examples/demo-app/src/components/account/AccountAvatar.tsx
@@ -7,7 +7,7 @@ export function AccountAvatar() {
     <section aria-labelledby="account-avatar-heading">
       <h2 id="account-avatar-heading">Avatar</h2>
       <input
-        id="avatar-input"
+        id="avatar-file"
         aria-label="Avatar image"
         type="file"
         onChange={(event) => setFileName(event.target.files?.[0]?.name ?? "No file")}
""",
        }

        diffs = analyze_diff(patches[scenario])

        assert len(diffs) == 1
        assert diffs[0].previous.get("tag") == "input"
        assert diffs[0].previous.get("attributes", {}).get("id") == removed_id
        assert diffs[0].current.get("tag") == "input"
        assert diffs[0].current.get("attributes", {}).get(added_attribute) == added_value

    def test_multiline_tag_widening_leaves_unchanged_neighbours_out(self) -> None:
        """Only the edited multi-line tag is parsed; sibling elements in context are not."""
        diff = """diff --git a/Form.tsx b/Form.tsx
--- a/Form.tsx
+++ b/Form.tsx
@@ -3,10 +3,10 @@ export function Form() {
     <label htmlFor="email">Email</label>
     <input
-      id="email"
+      id="email-address"
       type="email"
       onChange={(event) => setEmail(event.target.value)}
     />
     <p id="hint">We never share it.</p>
     <button type="submit">Save</button>
"""
        diffs = analyze_diff(diff)

        assert len(diffs) == 1
        assert diffs[0].line == 4
        assert diffs[0].previous["attributes"]["id"] == "email"
        assert diffs[0].current["attributes"]["id"] == "email-address"
        assert diffs[0].current["attributes"]["type"] == "email"

    def test_wrapping_an_element_reports_the_new_wrapper(self) -> None:
        """A wrapper added around an unchanged element is still reported as added."""
        diff = """diff --git a/SubmitButton.tsx b/SubmitButton.tsx
--- a/SubmitButton.tsx
+++ b/SubmitButton.tsx
@@ -1,7 +1,9 @@
 export function SubmitButton() {
   return (
-    <button id="submit-btn" className="btn" type="submit">
-      Submit
-    </button>
+    <div className="form-actions">
+      <button id="submit-btn" className="btn" type="submit">
+        Submit
+      </button>
+    </div>
   );
 }
"""
        diffs = analyze_diff(diff)

        added = [d for d in diffs if not d.previous]
        assert any(
            d.current.get("tag") == "div"
            and d.current.get("attributes", {}).get("className") == "form-actions"
            for d in added
        )
        assert any(d.current.get("tag") == "button" and d.previous for d in diffs)
