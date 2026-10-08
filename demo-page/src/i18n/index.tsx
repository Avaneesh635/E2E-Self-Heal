import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { en } from "./en";
import { ja } from "./ja";
import { ko } from "./ko";
import type { Dict } from "./types";
import { zh } from "./zh";

export const LANGS = [
  { code: "en", label: "English", dict: en },
  { code: "ko", label: "한국어", dict: ko },
  { code: "ja", label: "日本語", dict: ja },
  { code: "zh", label: "中文", dict: zh },
] as const;
export type Lang = (typeof LANGS)[number]["code"];

const DEFAULT_LANG: Lang = "en";
const STORAGE_KEY = "e2e-healer-demo-lang";

function isLang(value: unknown): value is Lang {
  return LANGS.some((l) => l.code === value);
}

// A `?lang=ko` link wins (handy for sharing one language), then the viewer's last choice.
function initialLang(): Lang {
  const fromQuery = new URLSearchParams(window.location.search).get("lang");
  if (isLang(fromQuery)) return fromQuery;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (isLang(saved)) return saved;
  } catch {
    // Storage can be blocked; the default is fine.
  }
  return DEFAULT_LANG;
}

type I18n = { lang: Lang; t: Dict; setLang: (lang: Lang) => void };
const I18nContext = createContext<I18n | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(initialLang);
  const t = LANGS.find((l) => l.code === lang)!.dict;

  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = t.pageTitle;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // Not persisting the choice is acceptable.
    }
  }, [lang, t]);

  return <I18nContext.Provider value={{ lang, t, setLang }}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18n {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used inside <I18nProvider>");
  return ctx;
}
