import React, { type ReactNode } from "react";
import styles from "./styles.module.css";

/**
 * HealingDiff — before (broken) vs after (healed) selector, side by side.
 *
 * Reference implementation for DESIGN.md §3.3. Props-driven: it renders whatever
 * selector strings it is given and never hardcodes copy. "Broken" always uses
 * --eeh-broken and "healed" always uses --eeh-healed (semantic colors are locked
 * in DESIGN.md rule §1.5).
 *
 * The changed part is highlighted automatically: a small, dependency-free
 * token-level diff between `before` and `after` marks removed fragments red in
 * the Before panel and added fragments green in the After panel. Pass the
 * optional `highlight` substring only when you want to override the auto-diff
 * and pinpoint an exact fragment.
 *
 * Example:
 *   <HealingDiff
 *     before={`await page.click('#submit-btn')`}
 *     after={`await page.click('#submit')`}
 *     reason="id changed: submit-btn → submit"
 *   />
 */
export interface HealingDiffProps {
    /** The failing / old selector line (rendered red). */
    before: string;
    /** The repaired / new selector line (rendered green). */
    after: string;
    /** Optional one-line explanation of what changed. */
    reason?: string;
    /** Optional override: pinpoint an exact substring instead of the auto-diff. */
    highlight?: string;
    /** Optional labels; default to "Before" / "After". */
    beforeLabel?: string;
    afterLabel?: string;
}

interface DiffPart {
    text: string;
    changed: boolean;
}

/**
 * Split a selector line into diff tokens: selector-ish identifiers (letters,
 * digits, `_ - # . $`) stay whole so we highlight `#submit-btn`/`.btn` as a
 * unit, while whitespace runs and any other single char are their own tokens.
 */
function tokenize(value: string): string[] {
    return value.match(/[\w#$.-]+|\s+|[^\w\s]/g) ?? [];
}

/** Collapse consecutive tokens that share the same changed flag into one part. */
function mergeAdjacent(parts: DiffPart[]): DiffPart[] {
    return parts.reduce<DiffPart[]>((acc, part) => {
        const last = acc[acc.length - 1];
        if (last && last.changed === part.changed) {
            last.text += part.text;
            return acc;
        }
        acc.push({ ...part });
        return acc;
    }, []);
}

/**
 * Token-level LCS diff. Returns the parts to render in each panel: unchanged
 * tokens are shared, removed tokens surface only in `before`, added tokens only
 * in `after`. Both strings are short (single selector lines) so O(n·m) is fine.
 */
function diffTokens(before: string, after: string): {
    before: DiffPart[];
    after: DiffPart[];
} {
    const a = tokenize(before);
    const b = tokenize(after);
    const n = a.length;
    const m = b.length;

    const dp: number[][] = Array.from({ length: n + 1 }, () =>
        new Array<number>(m + 1).fill(0),
    );
    for (let i = n - 1; i >= 0; i--) {
        for (let j = m - 1; j >= 0; j--) {
            dp[i][j] =
                a[i] === b[j]
                    ? dp[i + 1][j + 1] + 1
                    : Math.max(dp[i + 1][j], dp[i][j + 1]);
        }
    }

    const beforeParts: DiffPart[] = [];
    const afterParts: DiffPart[] = [];
    let i = 0;
    let j = 0;
    while (i < n && j < m) {
        if (a[i] === b[j]) {
            beforeParts.push({ text: a[i], changed: false });
            afterParts.push({ text: b[j], changed: false });
            i++;
            j++;
        } else if (dp[i + 1][j] >= dp[i][j + 1]) {
            beforeParts.push({ text: a[i], changed: true });
            i++;
        } else {
            afterParts.push({ text: b[j], changed: true });
            j++;
        }
    }
    while (i < n) beforeParts.push({ text: a[i++], changed: true });
    while (j < m) afterParts.push({ text: b[j++], changed: true });

    return {
        before: mergeAdjacent(beforeParts),
        after: mergeAdjacent(afterParts),
    };
}

/** Render diff parts, wrapping changed fragments in the variant highlight span. */
function renderParts(parts: DiffPart[], variant: "broken" | "healed"): ReactNode {
    const highlightClass =
        variant === "broken" ? styles.highlightBroken : styles.highlightHealed;
    return parts.map((part, index) =>
        part.changed ? (
            <span key={index} className={highlightClass}>
                {part.text}
            </span>
        ) : (
            <React.Fragment key={index}>{part.text}</React.Fragment>
        ),
    );
}

/** Manual override: wrap every occurrence of `highlight` in the variant span. */
function renderHighlightedText(
    text: string,
    highlight: string,
    variant: "broken" | "healed",
): ReactNode {
    if (!text.includes(highlight)) {
        return text;
    }

    const parts = text.split(highlight);
    const highlightClass =
        variant === "broken" ? styles.highlightBroken : styles.highlightHealed;

    return (
        <>
            {parts.map((part, index) => (
                <React.Fragment key={index}>
                    {part}
                    {index < parts.length - 1 && (
                        <span className={highlightClass}>{highlight}</span>
                    )}
                </React.Fragment>
            ))}
        </>
    );
}

/** Choose the highlighting strategy: manual override when `highlight` is set,
 *  otherwise the automatic token-level diff. */
function buildCode(
    before: string,
    after: string,
    highlight?: string,
): { before: ReactNode; after: ReactNode } {
    if (highlight) {
        return {
            before: renderHighlightedText(before, highlight, "broken"),
            after: renderHighlightedText(after, highlight, "healed"),
        };
    }
    const diff = diffTokens(before, after);
    return {
        before: renderParts(diff.before, "broken"),
        after: renderParts(diff.after, "healed"),
    };
}

function Panel({
    variant,
    label,
    code,
}: {
    variant: "broken" | "healed";
    label: string;
    code: ReactNode; // Changed from 'string' to 'ReactNode' so it accepts our <span>
}): ReactNode {
    const panelClass =
        variant === "broken" ? styles.panelBroken : styles.panelHealed;
    return (
        <div className={`${styles.panel} ${panelClass}`}>
            <span className={styles.panelLabel}>{label}</span>
            <pre className={styles.code}>
                <code>{code}</code>
            </pre>
        </div>
    );
}

export default function HealingDiff({
    before,
    after,
    reason,
    highlight,
    beforeLabel = "Before",
    afterLabel = "After",
}: HealingDiffProps): ReactNode {
    const code = buildCode(before, after, highlight);
    return (
        <figure className={styles.wrapper}>
            <div className={styles.panels}>
                <Panel variant="broken" label={beforeLabel} code={code.before} />
                <Panel variant="healed" label={afterLabel} code={code.after} />
            </div>
            {reason ? (
                <figcaption className={styles.reason}>{reason}</figcaption>
            ) : null}
        </figure>
    );
}
