import React, { type ReactNode } from "react";
import styles from "./styles.module.css";

/**
 * ScopeGuardrailCallout — the "we never touch your assertions" admonition.
 *
 * The scope guardrail is repeated across the docs, so the wording lives here
 * (once) instead of being retyped on every page. Pages may append page-specific
 * context via `children`, but the invariant sentence always comes from here.
 *
 * Styled like a Docusaurus admonition using only --eeh-* tokens (DESIGN.md §4).
 *
 * Example:
 *   <ScopeGuardrailCallout />
 *   <ScopeGuardrailCallout variant="review" />
 *   <ScopeGuardrailCallout>Nothing is merged automatically.</ScopeGuardrailCallout>
 */
export type ScopeGuardrailVariant = "heal" | "review";

export interface ScopeGuardrailCalloutProps {
    /**
     * Which mode's guarantee to state.
     * - `heal` (default): only selectors/waits are patched.
     * - `review`: the test is not edited at all.
     */
    variant?: ScopeGuardrailVariant;
    /** Optional admonition title; defaults to "Scope guardrail". */
    title?: string;
    /** Optional page-specific sentence appended after the default copy. */
    children?: ReactNode;
}

const DEFAULT_TITLE = "Scope guardrail";

/**
 * Default copy per variant. Kept in the component so every page states the
 * guardrail identically — pages add context through `children`, never by
 * restating the guarantee.
 */
const COPY: Record<ScopeGuardrailVariant, ReactNode> = {
    heal: (
        <>
            The engine <strong>only</strong> fixes failing{" "}
            <strong>locators</strong> and <strong>wait conditions</strong>. It{" "}
            <strong>never</strong> edits your assertions (<code>expect(...)</code>
            ), test flow, or business logic — enforced at both the prompt and
            JSON-schema level.
        </>
    ),
    review: (
        <>
            <code>review</code> mode <strong>never edits your test</strong> — not
            even the selector. It only diagnoses why the selector broke and
            suggests a fix at the source; what to change stays your call.
        </>
    ),
};

/** Shield-check glyph, sized in `em` so it tracks the title's font size. */
function GuardrailIcon(): ReactNode {
    return (
        <svg
            className={styles.icon}
            viewBox="0 0 24 24"
            width="1em"
            height="1em"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
        >
            <path d="M12 3 4 6v6c0 4.5 3.2 8.2 8 9 4.8-.8 8-4.5 8-9V6l-8-3Z" />
            <path d="m9 12 2 2 4-4" />
        </svg>
    );
}

export default function ScopeGuardrailCallout({
    variant = "heal",
    title = DEFAULT_TITLE,
    children,
}: ScopeGuardrailCalloutProps): ReactNode {
    const variantClass =
        variant === "review" ? styles.calloutReview : styles.calloutHeal;

    return (
        <aside className={`${styles.callout} ${variantClass}`} role="note">
            <p className={styles.heading}>
                <GuardrailIcon />
                <span className={styles.title}>{title}</span>
            </p>
            <div className={styles.body}>
                <p className={styles.copy}>{COPY[variant]}</p>
                {/* MDX wraps children in its own <p>, so this slot must not be one. */}
                {children ? <div className={styles.extra}>{children}</div> : null}
            </div>
        </aside>
    );
}
