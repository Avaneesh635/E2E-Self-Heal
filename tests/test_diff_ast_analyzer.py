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
