import { useEffect, useId, useState, type ReactNode } from "react";
import Mermaid from "@theme/Mermaid";
import styles from "./styles.module.css";

/**
 * ArchitectureFlow — vertical pipeline of labeled stages (DESIGN.md §3.2).
 *
 * Props-driven: pass the stages you want to render. The default is the current
 * `heal` repair loop (Diagnoser → Patch Generator → Selector Verifier → Test
 * Runner). The DESIGN.md §3.2 wireframe also describes the roadmap's Shadow
 * Testing pipeline — feed those stages via the `stages` prop to render it.
 *
 * Two render paths draw the same stages in the same order with the same tokens:
 *
 * - `variant="dom"` (default): hand-rolled boxes. Every stage with a tooltip is
 *   keyboard-focusable, and the tooltip shows on hover and on `:focus-visible`.
 * - `variant="mermaid"`: a Mermaid flowchart through the Docusaurus Mermaid
 *   theme. SVG has no hover tooltips here, so each stage's tooltip is carried in
 *   the diagram's accessible description instead.
 */
export interface FlowStage {
    /** Short mono label shown in the box. */
    label: string;
    /** One-line description: shown on hover/focus, and as a `title` fallback. */
    tooltip?: string;
}

export type ArchitectureFlowVariant = "dom" | "mermaid";

export interface ArchitectureFlowProps {
    stages?: FlowStage[];
    /** Accessible label for the pipeline. */
    ariaLabel?: string;
    /** Render path. Defaults to the hand-rolled DOM boxes. */
    variant?: ArchitectureFlowVariant;
}

/** The current heal repair loop — the product as shipped today. */
export const HEAL_LOOP_STAGES: FlowStage[] = [
    {
        label: "Diagnoser",
        tooltip:
            "Maps the failing selector to the DOM change and infers the root cause.",
    },
    {
        label: "Patch Generator",
        tooltip:
            "Emits the target line + replacement via structured outputs — selectors/waits only.",
    },
    {
        label: "Selector Verifier",
        tooltip:
            "Checks the patched selector against the live DOM — exactly one match, or re-patch.",
    },
    {
        label: "Test Runner",
        tooltip:
            "Runs `npx playwright test`; on failure the Router loops back (max 3).",
    },
];

/**
 * Mermaid wraps a label that is wider than this many pixels, and sizes boxes within it. Its
 * default is narrow enough to wrap "Patch Generator" in a monospace font, so the stages would
 * come out two lines tall. Labels stay one line up to about 40 characters.
 */
const MERMAID_WRAPPING_WIDTH = 400;

const MERMAID_ESCAPES: Record<string, string> = {
    "#": "#35;",
    '"': "#quot;",
    "<": "#lt;",
    ">": "#gt;",
    "&": "#amp;",
};

/** Collapse whitespace and escape the characters Mermaid treats as syntax in a label. */
function mermaidLabel(value: string): string {
    return value
        .replace(/\s+/g, " ")
        .trim()
        .replace(/[#"<>&]/g, (char) => MERMAID_ESCAPES[char]);
}

/** Plain text for `accTitle` / `accDescr`: the description block ends at the first `}`. */
function mermaidDescription(value: string): string {
    return value.replace(/\s+/g, " ").replace(/[{}]/g, "").trim();
}

/**
 * Build the Mermaid flowchart for a list of stages.
 *
 * Colors, border and radius are applied to the rendered SVG from `styles.module.css` using
 * the `--eeh-*` tokens (Mermaid's `classDef` grammar cannot express `var(--token)`), so the
 * diagram follows the site's light and dark themes like the DOM variant does.
 *
 * Mermaid sizes each box from the label's measured width, so it has to measure with the font
 * that is finally drawn. `fontFamily` is the *resolved* `--eeh-font-mono` stack, passed as
 * per-diagram config; without it the boxes are sized for a narrower font and the longer
 * labels overflow (and so are clipped by) their boxes.
 */
export function toMermaidDefinition(
    stages: FlowStage[],
    ariaLabel: string,
    fontFamily?: string,
): string {
    const ids = stages.map((_, index) => `s${index}`);
    const description = stages
        .map((stage, index) => {
            const text = stage.tooltip
                ? `${stage.label}: ${stage.tooltip}`
                : stage.label;
            return `  ${index + 1}. ${mermaidDescription(text)}`;
        })
        .join("\n");
    const chain = stages
        .map((stage, index) => `${ids[index]}["${mermaidLabel(stage.label)}"]`)
        .join(" --> ");

    // JSON strings are valid YAML double-quoted scalars, so the font stack's quotes are safe.
    const config = [
        ...(fontFamily ? [`  fontFamily: ${JSON.stringify(fontFamily)}`] : []),
        "  flowchart:",
        `    wrappingWidth: ${MERMAID_WRAPPING_WIDTH}`,
    ];

    return [
        "---",
        "config:",
        ...config,
        "---",
        "flowchart TD",
        `  accTitle: ${mermaidDescription(ariaLabel)}`,
        "  accDescr {",
        description,
        "  }",
        `  ${chain}`,
    ].join("\n");
}

/**
 * The computed `--eeh-font-mono` stack, read once on the client. `null` until then, so the
 * diagram is not drawn (and sized) with a different font first. An empty string means the
 * token is missing, and the diagram renders with Mermaid's own font.
 */
function useMonoFontFamily(): string | null {
    const [fontFamily, setFontFamily] = useState<string | null>(null);
    useEffect(() => {
        const value = getComputedStyle(document.documentElement)
            .getPropertyValue("--eeh-font-mono")
            .replace(/\s+/g, " ")
            .trim();
        setFontFamily(value);
    }, []);
    return fontFamily;
}

function MermaidFlow({
    stages,
    ariaLabel,
}: {
    stages: FlowStage[];
    ariaLabel: string;
}): ReactNode {
    const fontFamily = useMonoFontFamily();
    return (
        <div className={styles.mermaidFlow}>
            {fontFamily === null ? null : (
                <Mermaid
                    value={toMermaidDefinition(
                        stages,
                        ariaLabel,
                        fontFamily || undefined,
                    )}
                />
            )}
        </div>
    );
}

function Stage({ stage }: { stage: FlowStage }): ReactNode {
    const tooltipId = useId();
    const hasTooltip = Boolean(stage.tooltip);
    return (
        <div
            className={styles.stageBox}
            title={stage.tooltip}
            // Focusable only when there is something to reveal, so keyboard users are
            // not stopped on boxes that do nothing.
            tabIndex={hasTooltip ? 0 : undefined}
            aria-describedby={hasTooltip ? tooltipId : undefined}
        >
            <span className={styles.stageLabel}>{stage.label}</span>
            {hasTooltip ? (
                <span
                    id={tooltipId}
                    role="tooltip"
                    className={styles.stageTooltip}
                >
                    {stage.tooltip}
                </span>
            ) : null}
        </div>
    );
}

export default function ArchitectureFlow({
    stages = HEAL_LOOP_STAGES,
    ariaLabel = "Repair pipeline",
    variant = "dom",
}: ArchitectureFlowProps): ReactNode {
    if (variant === "mermaid") {
        return <MermaidFlow stages={stages} ariaLabel={ariaLabel} />;
    }

    return (
        <ol className={styles.flow} aria-label={ariaLabel}>
            {stages.map((stage, i) => (
                <li key={stage.label} className={styles.stageItem}>
                    <Stage stage={stage} />
                    {i < stages.length - 1 ? (
                        <span className={styles.arrow} aria-hidden="true">
                            ▼
                        </span>
                    ) : null}
                </li>
            ))}
        </ol>
    );
}
