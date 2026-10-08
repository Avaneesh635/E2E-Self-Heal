import type { ReactNode } from "react";

import { useI18n } from "../i18n";

export function Prov({ real }: { real: boolean }) {
  const { t } = useI18n();
  return real ? (
    <span className="rounded-full border border-accent px-2 font-mono text-[0.72rem] tracking-wide whitespace-nowrap text-accent">
      {t.prov.real}
    </span>
  ) : (
    <span className="rounded-full border border-dashed border-muted px-2 font-mono text-[0.72rem] tracking-wide whitespace-nowrap text-muted">
      {t.prov.sim}
    </span>
  );
}

export function lineClass(line: string): string {
  if (line.startsWith("+")) return "bg-healed/12 text-healed";
  if (line.startsWith("-")) return "bg-broken/12 text-broken";
  if (line.startsWith("@@")) return "text-muted";
  return "";
}

/** A code pane body: one block per line, so highlighted lines span the full width. */
export function CodeBlock({ text, classFor }: { text: string; classFor?: (line: string) => string }) {
  return (
    <pre className="m-0 overflow-x-auto bg-code p-3 font-mono text-[0.8rem] leading-[1.55] text-fg">
      {text.split("\n").map((line, i) => (
        <span key={i} className={`-mx-2 block px-2 whitespace-pre ${classFor?.(line) ?? ""}`}>
          {line || " "}
        </span>
      ))}
    </pre>
  );
}

export function Pane({ title, badge, children }: { title: ReactNode; badge?: ReactNode; children: ReactNode }) {
  return (
    <div className="grid min-w-0 grid-rows-[auto_1fr] overflow-hidden rounded-lg border border-line bg-surface">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-3 py-2 font-mono text-[0.78rem] text-muted">
        <span>{title}</span>
        {badge}
      </div>
      {children}
    </div>
  );
}

export function Section({ id, title, intro, children }: { id: string; title: string; intro: ReactNode; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="grid gap-6 border-t border-line py-12">
      <div className="grid gap-2">
        <h2 id={`${id}-title`} className="text-[1.6rem] leading-tight font-bold">
          {title}
        </h2>
        <p className="max-w-[70ch] text-muted [&_b]:text-fg">{intro}</p>
      </div>
      {children}
    </section>
  );
}

export function Code({ children }: { children: ReactNode }) {
  return <code className="font-mono text-[0.92em]">{children}</code>;
}

/** Hero emphasis in a fixed semantic color: healed = what gets fixed, broken = what is left alone. */
export function Em({ tone, children }: { tone: "healed" | "broken"; children: ReactNode }) {
  return <span className={tone === "healed" ? "text-healed" : "text-broken"}>{children}</span>;
}
