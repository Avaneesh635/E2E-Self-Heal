import { Code, Em } from "../components/ui";
import type { Dict } from "./types";

export const ko: Dict = {
  pageTitle: "E2E Self-Heal 시연",
  language: "언어",
  nav: { demo: "시연", pairs: "같은 증상, 다른 정답", bench: "안전성 지표", arch: "구조" },
  prov: { real: "실측", sim: "예시" },
  hero: {
    eyebrow: "AI-driven Playwright self-healing",
    title: (
      <>
        <Em tone="healed">깨진 셀렉터</Em>는 고치고, <Em tone="broken">깨진 제품</Em>은 고치지 않는다.
      </>
    ),
    lede: (
      <>
        UI 변경으로 E2E 테스트가 깨지면 엔진이 실패 로그와 <Code>git diff</Code>를 읽고 원인을 진단합니다. 셀렉터와 대기 조건만 고친 뒤 테스트를
        다시 돌립니다. 제품 동작이 실제로 바뀐 경우에는 테스트를 통과시키지 않고 실패를 그대로 남깁니다.
      </>
    ),
    facts: [
      ["12", "라벨 붙은 시나리오 · 6개 클래스"],
      ["≤ 3", "수리 루프 상한"],
      ["셀렉터 · 대기", "수정 허용 범위 (AST lock)"],
      ["exit 0 / 1", "CI가 분기하는 결과 코드"],
    ],
  },
  demo: {
    title: "시나리오 재생",
    intro: (
      <>
        왼쪽에서 시나리오를 고르고 <b>다음 단계</b>로 진행합니다. 테스트 코드, <Code>change.patch</Code>, Playwright 실패 로그, 전처리 결과는
        저장소와 로컬 실행에서 가져온 실측입니다. 엔진의 진단·패치 단계는 <Code>id-rename</Code>만 실측이고, 나머지는 엔진 로그 형식을 따른
        예시입니다.
      </>
    ),
    scenariosLabel: "시나리오",
    pipelineLabel: "파이프라인 단계",
    stages: {
      fail: "Playwright 실패",
      prep: "전처리",
      diag: "Diagnoser",
      patch: "Patch Generator",
      verify: "Verifier · AST lock",
      run: "Test Runner",
      end: "결과",
    },
    expected: { repair: "고쳐야 함", refuse: "거부해야 함" },
    idle: (
      <>
        패치가 적용되어 테스트가 깨진 상태입니다.
        <br />
        <b>엔진 실행</b>을 눌러 시작하세요.
      </>
    ),
    domChanges: (n) => `dom_diff_context (${n}개 변경)`,
    controls: { reset: "처음부터", prev: "이전", run: "엔진 실행", next: "다음 단계", auto: "자동 재생", pause: "일시정지", step: "단계" },
    healedTitle: "테스트 수리 완료",
    healedNote: "CI 래퍼가 이 패치로 PR을 엽니다. 단언은 바뀌지 않았습니다.",
    refusedTitle: "수리 거부",
    correctRefusal: "올바른 거부",
    incorrectRefusal: "잘못된 거부 (고칠 수 있었음)",
    trapLabel: "단순 수정을 했다면:",
    gapLabel: "발견된 한계:",
    reasons: {
      ambiguous_target: "대상이 모호함",
      loop_cap_reached: "루프 상한 도달",
      guardrail_violation: "가드레일 위반",
      insufficient_evidence: "근거 부족",
    },
  },
  pairs: {
    title: "같은 증상, 다른 정답",
    intro:
      "단순한 자가 치유 도구는 실패 메시지만 보고 셀렉터를 바꿉니다. 아래 두 쌍은 증상만 보면 구별이 안 되지만 정답은 정반대입니다. 코퍼스는 일부러 이런 쌍으로 구성했습니다.",
    sameError: {
      question: "① 실패 메시지가 한 글자도 다르지 않다",
      source: "Playwright 실측 로그",
      repair: "고쳐야 함 · 대기 시간",
      refuse: "거부해야 함 · 핸들러 삭제",
      answer: (
        <>
          둘 다 <Code>waiting for locator('.cta-primary')</Code>에서 3초 타임아웃입니다. 왼쪽은 버튼이 4초 뒤에 나타나므로 timeout만 늘리면
          됩니다. 오른쪽은 클래스가 바뀌었고 <b>클릭 핸들러도 사라졌습니다</b>. 셀렉터를 고치면 클릭은 되지만 <Code>Welcome!</Code>은 나타나지
          않습니다. 둘을 가르는 건 에러가 아니라 <b>diff</b>입니다.
        </>
      ),
    },
    sameDiff: {
      question: "② diff가 같은 모양이다",
      source: "실제 change.patch",
      repair: "고쳐야 함",
      refuse: "거부해야 함",
      answer: (
        <>
          둘 다 <Code>submit-btn → submit</Code>입니다. 오른쪽은 같은 줄에서 <Code>type="submit"</Code>이 <Code>type="button"</Code>으로
          바뀌어 버튼이 폼을 제출하지 않습니다. 셀렉터를 고친 뒤에도 테스트가 실패하면, 엔진은 단언을 건드리는 대신 루프 상한에서 멈춥니다.{" "}
          <b>단순한 치유 도구가 놓치는 지점이 바로 여기입니다.</b>
        </>
      ),
    },
  },
  bench: {
    title: "안전성 벤치마크",
    intro: (
      <>
        수리를 했는지가 아니라 <b>안전하게</b> 했는지를 잽니다. 지표를 하나의 정확도로 합치지 않습니다. 고장 난 제품을 통과시키는 실패와, 고칠
        수 있는 걸 거부하는 실패는 무게가 다르기 때문입니다.
      </>
    ),
    banner: (
      <>
        아래 결과는 위 시나리오 재생과 같은 <b>예시 결과</b>로 계산했습니다. 지표 정의, 임계값, 표본 규칙은 실제 코드(
        <Code>app/safety_benchmark.py</Code>)와 같습니다. 실제 모델 측정 수치는 아닙니다.
      </>
    ),
    tiles: {
      falseGreen: { label: "False-green rate", desc: "고장 난 제품을 통과시킨 비율. 목표 0%" },
      refusalAccuracy: { label: "Refusal accuracy", desc: "올바른 거부 ÷ (올바른 거부 + 잘못된 수리 + 잘못된 거부)" },
      correctRefusal: { label: "Correct-refusal rate", desc: "거부해야 할 때 거부한 비율" },
      incorrectRefusal: { label: "Incorrect-refusal rate", desc: "고칠 수 있는 걸 거부한 비율 (비용)" },
      precision: { label: "Repair precision", desc: "수리한 것 중 수리가 맞았던 비율" },
    },
    classHead: ["클래스", "시나리오", "기대", "수리", "거부", "정답"],
    gateHead: ["릴리스 게이트", "기준", "값", "n", "상태"],
    repair: "수리",
    refuse: "거부",
    caption: (min, regressions) =>
      `게이트는 머지가 아니라 릴리스만 막습니다. 표본이 ${min}개 미만이면 insufficient_sample로 표시만 하고 적용하지 않습니다. 단, false green은 1건만 나와도 표본 수와 관계없이 실패입니다. 지금 코퍼스는 product_regression이 ${regressions}개라서 "false-green 0%"를 주장하기에는 아직 부족합니다.`,
  },
  arch: {
    title: "구조",
    intro: "수리 로직은 CLI 코어 하나에만 있습니다. 개발자가 로컬에서 실행하는 명령과 CI가 실행하는 명령이 같습니다.",
    flowLabel: "수리 루프",
    flow: [
      ["input", "실패 로그 + git diff", "Playwright 원본 로그와 UI 변경분"],
      ["preprocess", "Error Log Parser · Diff AST Analyzer", "에러 핵심 줄과 DOM 변경 JSON만 남긴다"],
      ["node", "Diagnoser", "실패한 셀렉터와 DOM 변경을 매핑"],
      ["node", "Patch Generator", "Structured Outputs로 줄 번호와 교체 코드만 반환"],
      ["gate", "Selector Verifier · AST lock", "실제 DOM에서 정확히 1개 매칭, 셀렉터·timeout 외 변경 거부"],
      ["node", "Test Runner", "npx playwright test 재실행"],
      ["router", "통과 또는 loop 3 → 종료", "그 외에는 Diagnoser로 복귀"],
    ],
    loopNote: "LangGraph StateGraph · 종료 판단은 Router 한 곳에서만 · loop_count는 3을 넘지 않는다",
    guardrailsTitle: "가드레일",
    guardrails: [
      ["코드 무결성", "셀렉터와 대기 조건만 수정합니다. 단언과 테스트 흐름은 프롬프트와 JSON 스키마 양쪽에서 막습니다."],
      [
        "AST lock",
        <>
          패치된 파일 전체를 구문 트리로 비교합니다. 로케이터 문자열, timeout, wait 이름 외의 변경은 <Code>guardrail_violation</Code>으로
          거부합니다. 파싱에 실패해도 거부합니다.
        </>,
      ],
      ["Selector Verifier", "실제 페이지에서 0개(지어낸 셀렉터)나 2개 이상(모호한 셀렉터)이 매칭되면 테스트를 돌리기 전에 되돌립니다."],
      ["LLM 출력 실패 처리", "JSON 파싱 실패는 그래프를 멈추지 않고 Patch Generator에 피드백합니다."],
    ],
    ciTitle: "CLI 코어 + CI 래퍼",
    exits: [
      ["exit 0", "테스트가 고쳐짐 → CI가 패치 PR을 연다"],
      ["exit ≠ 0", "여전히 실패 / 거부 → RefusalReport JSON을 남긴다"],
      [
        "outcome",
        <>
          <Code>passed</Code> · <Code>healed</Code> · <Code>unhealed</Code> · <Code>reviewed</Code> · <Code>errored</Code>
        </>,
      ],
    ],
  },
  footer: {
    title: "데이터 출처",
    sources: [
      [
        true,
        <>
          테스트 코드, <Code>change.patch</Code>, <Code>meta.json</Code>: <Code>examples/scenarios/</Code>
        </>,
      ],
      [
        true,
        <>
          Playwright 실패 로그, 단순 수정 시 통과 여부: 데모 앱 대상 로컬 실행 (<Code>scripts/logs/</Code>)
        </>,
      ],
      [
        true,
        <>
          전처리 결과: 실제 <Code>parse_error_log</Code> · <Code>analyze_diff</Code> 출력
        </>,
      ],
      [
        true,
        <>
          <Code>id-rename</Code> 수리 과정: README에 기록된 NVIDIA NIM 실제 실행
        </>,
      ],
      [
        false,
        <>
          그 외 시나리오의 진단·패치·결과와 벤치마크 수치: 엔진의 실제 거부 사유 분기(<Code>app/graph.py</Code>)에 맞춘 시뮬레이션
        </>,
      ],
    ],
  },
  notes: {
    locatorOnly: "로케이터 문자열만 바뀌었습니다.",
    assertionKept: '"Thanks!" 단언은 그대로입니다.',
    labelNoEvidence: "getByRole(button, Get started)를 찾지 못했고, diff에도 대응하는 DOM 변경이 없습니다.",
    noInventedName: "근거 없이 새 이름을 지어내지 않습니다.",
    incorrectRefusalCost: "고칠 수 있었던 드리프트를 거부했습니다. 잘못된 거부이고, 비용으로 집계됩니다.",
    lateElement: "셀렉터는 유효하고 요소가 늦게 나타날 뿐입니다. 대기 조건 문제입니다.",
    timeoutOnly: "timeout 값만 바뀌었고, 허용 목록에 있는 변경입니다.",
    waitOnly: "셀렉터와 단언은 그대로이고 대기 시간만 늘었습니다.",
    wrapperBrokeChild: "새 래퍼 때문에 직계 자식 셀렉터가 끊겼습니다. 버튼 자체는 그대로입니다.",
    twoCandidates: "원래 버튼에 대응하는 후보가 둘이고, 둘의 동작이 다릅니다.",
    notExactlyOne: "정확히 1개가 매칭되지 않아 후보를 버립니다.",
    handedToHuman: "테스트는 실패 상태로 남고, 판단은 사람에게 넘어갑니다.",
    clickedNotSubmitted: "클릭은 됐지만 아무것도 제출되지 않았습니다.",
    assertionSideFailure: "이제 셀렉터는 맞습니다. 실패 원인은 단언 쪽이라 셀렉터 수정으로는 해결할 수 없습니다.",
    noAssertionEdit: "테스트를 통과시키려고 단언을 고치지 않습니다.",
    foundButDisabled: "요소는 찾았지만 비활성 상태입니다.",
    fedBackSpendsLoop: "위반 내용을 Patch Generator에 피드백하고, 루프를 1회 소모합니다.",
    noForceClick: "비활성 버튼을 강제 클릭으로 우회하지 않습니다.",
    navigationFailedFirst: "셀렉터가 실행되기 전에 네비게이션이 실패했습니다. 근거로 삼을 DOM 변경이 없습니다.",
    fixTheEnvironment: "테스트를 바꿀 근거가 없습니다. 환경을 고쳐야 합니다.",
  },
  scenarios: {
    "id-rename": {
      title: "버튼 id 변경",
      summary: "id가 submit-btn에서 submit으로 바뀌었다. 동작은 그대로다.",
      why: "버튼 id만 바뀌었고 동작은 그대로라서 셀렉터만 고쳤습니다.",
    },
    "label-rename": {
      title: "버튼 라벨 변경",
      summary: "Get started가 Start now로 바뀌었다. role과 핸들러는 그대로다.",
      why: "라벨만 바뀐 드리프트라 고쳤어야 했지만, 엔진이 새 이름의 근거를 받지 못했습니다.",
      gap: "Diff AST Analyzer는 속성 변경만 추출하고 텍스트 노드 변경은 놓칩니다 (실제 출력: dom_changes=0). 라벨이 바뀌어도 LLM은 새 이름을 볼 수 없습니다. 안전하지만 비용이 드는 실패입니다.",
    },
    "delayed-cta": {
      title: "늦게 뜨는 버튼",
      summary: "CTA가 약 4초 뒤에 렌더링된다. 셀렉터는 맞고, 기다리는 시간이 짧다.",
      why: "셀렉터는 맞고 요소가 늦게 나타날 뿐이라 대기 시간만 늘렸습니다.",
    },
    "wrapper-added": {
      title: "레이아웃 래퍼 추가",
      summary: "버튼이 div로 감싸져 form > button 구조 셀렉터가 깨졌다.",
      why: "레이아웃 래퍼가 구조 셀렉터를 끊었을 뿐, 버튼과 제출 동작은 그대로입니다.",
    },
    "split-submit": {
      title: "버튼 하나가 둘로",
      summary: "Submit이 Save draft와 Publish로 갈라졌다. 어느 쪽을 눌러도 테스트는 통과한다.",
      why: "기존 버튼이 서로 다른 의미의 버튼 둘로 갈라졌습니다. 어느 쪽을 골라도 추측입니다.",
      trap: "#publish로 바꾸면 테스트가 통과합니다 (로컬 Playwright로 확인). 그게 맞는 흐름인지는 아무도 모릅니다.",
    },
    "id-rename-submit-dropped": {
      title: "id 변경 + 제출 기능 삭제",
      summary: "diff는 id-rename과 같은 모양이다. 그런데 버튼이 더 이상 폼을 제출하지 않는다.",
      why: "id는 id-rename처럼 바뀌었지만 버튼이 더 이상 폼을 제출하지 않습니다. 제품 회귀입니다.",
      trap: "#submit으로 고쳐도 테스트는 계속 실패합니다 (로컬 Playwright로 확인). 셀렉터 문제가 아니라는 증거입니다.",
    },
    "disabled-submit": {
      title: "비활성화된 제출 버튼",
      summary: "버튼에 disabled가 붙었다. 에러는 타이밍 문제처럼 보인다.",
      why: "버튼이 비활성화되어 폼을 제출할 수 없습니다. 타임아웃은 증상일 뿐 대기 문제가 아닙니다.",
      trap: "강제 클릭을 해도 비활성 버튼은 폼을 제출하지 않습니다 (로컬 Playwright로 확인).",
    },
    "wrong-base-url": {
      title: "잘못된 baseURL",
      summary: "Playwright 설정의 포트가 틀렸다. 앱도 테스트도 문제없다.",
      why: "base URL 설정이 틀려 네비게이션이 실패했습니다. 테스트를 고치는 것은 정답이 아닙니다.",
      trap: "goto를 http://localhost:4173/ 절대 주소로 바꾸면 통과합니다 (로컬 Playwright로 확인). 설정 오류를 테스트 안에 묻어 버리는 셈입니다.",
    },
  },
};
