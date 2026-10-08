import type { ReactNode } from "react";

import type { PlayerName, Reason, StageKey } from "../runs";
import type { NoteKey } from "./en";

export type MetricKey = "falseGreen" | "refusalAccuracy" | "correctRefusal" | "incorrectRefusal" | "precision";

export type ScenarioText = { title: string; summary: string; why: string; trap?: string; gap?: string };

/** Every locale implements this shape; a missing key is a type error. */
export type Dict = {
  pageTitle: string;
  language: string;
  nav: { demo: string; pairs: string; bench: string; arch: string };
  prov: { real: string; sim: string };
  hero: { eyebrow: string; title: ReactNode; lede: ReactNode; facts: [string, string][] };
  demo: {
    title: string;
    intro: ReactNode;
    scenariosLabel: string;
    pipelineLabel: string;
    stages: Record<StageKey, string>;
    expected: { repair: string; refuse: string };
    idle: ReactNode;
    domChanges: (n: number) => string;
    controls: { reset: string; prev: string; run: string; next: string; auto: string; pause: string; step: string };
    healedTitle: string;
    healedNote: string;
    refusedTitle: string;
    correctRefusal: string;
    incorrectRefusal: string;
    trapLabel: string;
    gapLabel: string;
    reasons: Record<Reason, string>;
  };
  pairs: {
    title: string;
    intro: string;
    sameError: { question: string; source: string; repair: string; refuse: string; answer: ReactNode };
    sameDiff: { question: string; source: string; repair: string; refuse: string; answer: ReactNode };
  };
  bench: {
    title: string;
    intro: ReactNode;
    banner: ReactNode;
    tiles: Record<MetricKey, { label: string; desc: string }>;
    classHead: [string, string, string, string, string, string];
    gateHead: [string, string, string, string, string];
    repair: string;
    refuse: string;
    caption: (minSample: number, regressions: number) => string;
  };
  arch: {
    title: string;
    intro: string;
    flowLabel: string;
    flow: [string, string, string][];
    loopNote: string;
    guardrailsTitle: string;
    guardrails: [string, ReactNode][];
    ciTitle: string;
    exits: [string, ReactNode][];
  };
  footer: { title: string; sources: [boolean, ReactNode][] };
  notes: Record<NoteKey, string>;
  scenarios: Record<PlayerName, ScenarioText>;
};
