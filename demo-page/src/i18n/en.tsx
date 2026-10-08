import { Code, Em } from "../components/ui";
import type { Dict } from "./types";

// The note keys are defined here; every other locale must translate each one.
const notes = {
  locatorOnly: "Only the locator string changed.",
  assertionKept: 'The "Thanks!" assertion is untouched.',
  labelNoEvidence: "getByRole(button, Get started) is gone, and the diff shows no matching DOM change.",
  noInventedName: "It does not invent a new name without evidence.",
  incorrectRefusalCost: "It refused drift it could have fixed: an incorrect refusal, which is a cost.",
  lateElement: "The selector is valid; the element just appears late. This is a wait problem.",
  timeoutOnly: "Only the timeout value changed, which the allowlist permits.",
  waitOnly: "Selector and assertion are unchanged; only the wait got longer.",
  wrapperBrokeChild: "The new wrapper broke the direct-child selector. The button itself is unchanged.",
  twoCandidates: "Two candidates match the original button, and they do different things.",
  notExactlyOne: "Not exactly one match, so the candidate is discarded.",
  handedToHuman: "The test stays failing and the decision goes to a person.",
  clickedNotSubmitted: "The click worked, but nothing was submitted.",
  assertionSideFailure: "The selector is right now. The failure is on the assertion side, which no selector fix can solve.",
  noAssertionEdit: "It does not edit the assertion to make the test pass.",
  foundButDisabled: "The element was found, but it is disabled.",
  fedBackSpendsLoop: "The violation is fed back to the Patch Generator and spends a loop.",
  noForceClick: "It does not force-click past a disabled button.",
  navigationFailedFirst: "Navigation failed before any selector ran. There is no DOM change to go on.",
  fixTheEnvironment: "There are no grounds to change the test. The environment needs fixing.",
};
export type NoteKey = keyof typeof notes;

export const en: Dict = {
  pageTitle: "E2E Self-Heal demo",
  language: "Language",
  nav: { demo: "Demo", pairs: "Same symptom, opposite fix", bench: "Safety metrics", arch: "Architecture" },
  prov: { real: "measured", sim: "example" },
  hero: {
    eyebrow: "AI-driven Playwright self-healing",
    title: (
      <>
        Fix the <Em tone="healed">broken selector</Em>. Never paper over a <Em tone="broken">broken product</Em>.
      </>
    ),
    lede: (
      <>
        When a UI change breaks an E2E test, the engine reads the failure log and the <Code>git diff</Code>, diagnoses the cause, fixes only
        selectors and wait conditions, and re-runs the test. When the product behavior really changed, it leaves the failure in place instead of
        making the test pass.
      </>
    ),
    facts: [
      ["12", "labeled scenarios · 6 classes"],
      ["≤ 3", "repair loop cap"],
      ["selector · wait", "what a patch may change (AST lock)"],
      ["exit 0 / 1", "the code CI branches on"],
    ],
  },
  demo: {
    title: "Scenario replay",
    intro: (
      <>
        Pick a scenario on the left and step through it. The test code, <Code>change.patch</Code>, Playwright failure log and preprocessor output
        are real, taken from the repository and local runs. Of the engine's diagnosis and patch steps, only <Code>id-rename</Code> is a measured
        run; the rest are examples in the engine's log format.
      </>
    ),
    scenariosLabel: "Scenarios",
    pipelineLabel: "Pipeline stages",
    stages: {
      fail: "Playwright failure",
      prep: "Preprocess",
      diag: "Diagnoser",
      patch: "Patch Generator",
      verify: "Verifier · AST lock",
      run: "Test Runner",
      end: "Result",
    },
    expected: { repair: "should repair", refuse: "should refuse" },
    idle: (
      <>
        The patch is applied and the test is broken.
        <br />
        Press <b>Run engine</b> to start.
      </>
    ),
    domChanges: (n) => `dom_diff_context (${n} change${n === 1 ? "" : "s"})`,
    controls: { reset: "Restart", prev: "Back", run: "Run engine", next: "Next step", auto: "Autoplay", pause: "Pause", step: "step" },
    healedTitle: "Test repaired",
    healedNote: "The CI wrapper opens a PR with this patch. No assertion changed.",
    refusedTitle: "Repair refused",
    correctRefusal: "correct refusal",
    incorrectRefusal: "incorrect refusal (it was fixable)",
    trapLabel: "With a naive fix:",
    gapLabel: "Limitation found:",
    reasons: {
      ambiguous_target: "Ambiguous target",
      loop_cap_reached: "Loop cap reached",
      guardrail_violation: "Guardrail violation",
      insufficient_evidence: "Insufficient evidence",
    },
  },
  pairs: {
    title: "Same symptom, opposite fix",
    intro:
      "A naive self-healer reads only the failure message and swaps the selector. Each pair below looks identical from the symptom alone, yet the right answers are opposite. The corpus is built from pairs like these on purpose.",
    sameError: {
      question: "① The failure messages are identical, character for character",
      source: "measured Playwright logs",
      repair: "should repair · wait",
      refuse: "should refuse · handler removed",
      answer: (
        <>
          Both time out after 3 seconds on <Code>waiting for locator('.cta-primary')</Code>. On the left the button appears after 4 seconds, so a
          longer timeout is the fix. On the right the class changed <b>and the click handler is gone</b>: fixing the selector makes the click work,
          but <Code>Welcome!</Code> never appears. What separates them is not the error but the <b>diff</b>.
        </>
      ),
    },
    sameDiff: {
      question: "② The diffs have the same shape",
      source: "real change.patch",
      repair: "should repair",
      refuse: "should refuse",
      answer: (
        <>
          Both rename <Code>submit-btn → submit</Code>. On the right, the same line also turns <Code>type="submit"</Code> into{" "}
          <Code>type="button"</Code>, so the button no longer submits the form. When the test still fails after the selector fix, the engine stops
          at the loop cap instead of touching the assertion. <b>This is exactly where naive healers go wrong.</b>
        </>
      ),
    },
  },
  bench: {
    title: "Safety benchmark",
    intro: (
      <>
        It measures whether a repair was <b>safe</b>, not just whether one was produced. The metrics are never merged into one accuracy number,
        because passing a broken product and refusing a fixable test are failures of very different weight.
      </>
    ),
    banner: (
      <>
        These results are computed from the same <b>example outcomes</b> as the replay above. Metric definitions, thresholds and sample rules are
        the same as the real code (<Code>app/safety_benchmark.py</Code>). These are not measured model results.
      </>
    ),
    tiles: {
      falseGreen: { label: "False-green rate", desc: "broken products let through. Target 0%" },
      refusalAccuracy: { label: "Refusal accuracy", desc: "correct refusals ÷ (correct refusals + false heals + false refusals)" },
      correctRefusal: { label: "Correct-refusal rate", desc: "refused when it should" },
      incorrectRefusal: { label: "Incorrect-refusal rate", desc: "fixable drift refused (a cost)" },
      precision: { label: "Repair precision", desc: "repairs that were expected" },
    },
    classHead: ["Class", "Scenarios", "Expected", "Repaired", "Refused", "Correct"],
    gateHead: ["Release gate", "Threshold", "Value", "n", "Status"],
    repair: "repair",
    refuse: "refuse",
    caption: (min, regressions) =>
      `Gates block releases, never merges. Below ${min} scenarios a rate is shown as insufficient_sample and not enforced, except that a single false green fails its gate at any sample size. The corpus has ${regressions} product_regression scenarios, not yet enough to claim a 0% false-green rate.`,
  },
  arch: {
    title: "Architecture",
    intro: "All repair logic lives in a single CLI core. The command a developer runs locally is the same one CI runs.",
    flowLabel: "Repair loop",
    flow: [
      ["input", "Failure log + git diff", "The raw Playwright log and the UI change"],
      ["preprocess", "Error Log Parser · Diff AST Analyzer", "Keeps only the core error line and a DOM-change JSON"],
      ["node", "Diagnoser", "Maps the failing selector to the DOM change"],
      ["node", "Patch Generator", "Structured Outputs return only a line number and replacement code"],
      ["gate", "Selector Verifier · AST lock", "Exactly one match in the live DOM; any change beyond selectors and timeouts is rejected"],
      ["node", "Test Runner", "Re-runs npx playwright test"],
      ["router", "Pass or loop 3 → end", "Otherwise back to the Diagnoser"],
    ],
    loopNote: "LangGraph StateGraph · the Router alone decides termination · loop_count never exceeds 3",
    guardrailsTitle: "Guardrails",
    guardrails: [
      ["Code integrity", "Only selectors and wait conditions change. Assertions and test flow are locked at both the prompt and the JSON schema."],
      [
        "AST lock",
        <>
          The whole patched file is compared as a syntax tree. Any change other than locator strings, timeouts and wait names is rejected as{" "}
          <Code>guardrail_violation</Code>, and so is a file that fails to parse.
        </>,
      ],
      [
        "Selector Verifier",
        "A selector that matches zero elements (invented) or two or more (ambiguous) on the real page is reverted before the test runs.",
      ],
      ["LLM output failures", "A JSON parse failure never crashes the graph; it is fed back to the Patch Generator."],
    ],
    ciTitle: "CLI core + CI wrapper",
    exits: [
      ["exit 0", "Test fixed → CI opens a patch PR"],
      ["exit ≠ 0", "Still failing or refused → a RefusalReport JSON is written"],
      [
        "outcome",
        <>
          <Code>passed</Code> · <Code>healed</Code> · <Code>unhealed</Code> · <Code>reviewed</Code> · <Code>errored</Code>
        </>,
      ],
    ],
  },
  footer: {
    title: "Data sources",
    sources: [
      [
        true,
        <>
          Test code, <Code>change.patch</Code>, <Code>meta.json</Code>: <Code>examples/scenarios/</Code>
        </>,
      ],
      [
        true,
        <>
          Playwright failure logs and naive-fix results: local runs against the demo app (<Code>scripts/logs/</Code>)
        </>,
      ],
      [
        true,
        <>
          Preprocessing: actual <Code>parse_error_log</Code> · <Code>analyze_diff</Code> output
        </>,
      ],
      [
        true,
        <>
          <Code>id-rename</Code> repair: the real NVIDIA NIM run recorded in the README
        </>,
      ],
      [
        false,
        <>
          Diagnosis, patches and outcomes for the other scenarios, and the benchmark figures: simulated to match the engine's refusal-reason
          branches (<Code>app/graph.py</Code>)
        </>,
      ],
    ],
  },
  notes,
  scenarios: {
    "id-rename": {
      title: "Button id renamed",
      summary: "The id changed from submit-btn to submit. Behavior is unchanged.",
      why: "Only the button id changed and the behavior is the same, so only the selector was fixed.",
    },
    "label-rename": {
      title: "Button label changed",
      summary: "Get started became Start now. Role and handler are unchanged.",
      why: "This was label drift that should have been fixed, but the engine never received evidence of the new name.",
      gap: "The Diff AST Analyzer extracts attribute changes and misses text-node changes (actual output: dom_changes=0), so the LLM never sees the new label. A safe failure, but a costly one.",
    },
    "delayed-cta": {
      title: "Late-rendering button",
      summary: "The CTA renders after about 4 seconds. The selector is right; the wait is too short.",
      why: "The selector is right and the element only appears late, so only the wait was extended.",
    },
    "wrapper-added": {
      title: "Layout wrapper added",
      summary: "The button was wrapped in a div, breaking the form > button structural selector.",
      why: "A layout wrapper broke a structural selector; the button and its submit behavior are unchanged.",
    },
    "split-submit": {
      title: "One button became two",
      summary: "Submit split into Save draft and Publish. Clicking either one makes the test pass.",
      why: "The old button split into two buttons that mean different things. Choosing either one is a guess.",
      trap: "Changing it to #publish makes the test pass (checked with local Playwright). Nobody knows if that is the right flow.",
    },
    "id-rename-submit-dropped": {
      title: "id renamed, submit removed",
      summary: "The diff has the same shape as id-rename, but the button no longer submits the form.",
      why: "The id changed just like id-rename, but the button stopped submitting the form. This is a product regression.",
      trap: "Fixing it to #submit still leaves the test failing (checked with local Playwright), which shows it is not a selector problem.",
    },
    "disabled-submit": {
      title: "Disabled submit button",
      summary: "The button became disabled. The error looks like a timing problem.",
      why: "The button is disabled, so the form cannot be submitted. The timeout is a symptom, not a wait problem.",
      trap: "A forced click still does not submit a disabled button (checked with local Playwright).",
    },
    "wrong-base-url": {
      title: "Wrong baseURL",
      summary: "The Playwright config points at the wrong port. The app and the test are fine.",
      why: "The base URL setting is wrong, so navigation fails. Changing the test is not the right fix.",
      trap: "Changing goto to the absolute http://localhost:4173/ makes it pass (checked with local Playwright), burying a config error inside the test.",
    },
  },
};
