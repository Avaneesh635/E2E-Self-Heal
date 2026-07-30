import React, { type ReactNode } from "react";
import CodeBlock from "@theme/CodeBlock";
import TabItem from "@theme/TabItem";
import Tabs from "@theme/Tabs";
import styles from "./styles.module.css";

/**
 * CodeCompare — the recurring "Python CLI command ↔ the JS/TS spec it operates
 * on" tab pair from Getting Started.
 *
 * Wraps @theme/Tabs so a page writes one component instead of ~20 lines of Tabs
 * boilerplate. Fully prop-driven: no product copy lives in here. The default
 * `groupId` keeps every CodeCompare on the site switching in sync, the same way
 * the hand-written `<Tabs groupId="cli-vs-spec">` blocks did.
 *
 * Example:
 *   <CodeCompare
 *     specFilename="tests/login.spec.ts"
 *     cli={`e2e-healer tests/login.spec.ts`}
 *     spec={`import { test } from '@playwright/test';`}
 *   />
 */
export interface CodeCompareProps {
    /** Source for the CLI tab. */
    cli: string;
    /** Source for the spec tab. */
    spec: string;
    /** Path shown as the spec code block's title, e.g. `tests/login.spec.ts`. */
    specFilename?: string;
    /** Tab label for the CLI side. */
    cliLabel?: string;
    /** Tab label for the spec side; defaults to include `specFilename`. */
    specLabel?: string;
    /** Highlight language for the CLI tab. */
    cliLanguage?: string;
    /** Highlight language for the spec tab. */
    specLanguage?: string;
    /** Docusaurus tab-sync group; share it so all pairs switch together. */
    groupId?: string;
}

const DEFAULT_GROUP_ID = "cli-vs-spec";
const DEFAULT_CLI_LABEL = "Engine (CLI)";
const DEFAULT_SPEC_LABEL = "Your test";

export default function CodeCompare({
    cli,
    spec,
    specFilename,
    cliLabel = DEFAULT_CLI_LABEL,
    specLabel,
    cliLanguage = "bash",
    specLanguage = "ts",
    groupId = DEFAULT_GROUP_ID,
}: CodeCompareProps): ReactNode {
    const resolvedSpecLabel =
        specLabel ??
        (specFilename
            ? `${DEFAULT_SPEC_LABEL} (${specFilename})`
            : DEFAULT_SPEC_LABEL);

    return (
        <div className={styles.wrapper}>
            <Tabs groupId={groupId}>
                <TabItem value="cli" label={cliLabel} default>
                    <CodeBlock language={cliLanguage}>{cli}</CodeBlock>
                </TabItem>
                <TabItem value="spec" label={resolvedSpecLabel}>
                    <CodeBlock language={specLanguage} title={specFilename}>
                        {spec}
                    </CodeBlock>
                </TabItem>
            </Tabs>
        </div>
    );
}
