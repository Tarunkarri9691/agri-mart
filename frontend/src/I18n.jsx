import { createContext, useCallback, useContext, useState } from "react";
import { translate } from "./i18n.js";

const Ctx = createContext({ lang: "en", setLang: () => {}, t: (k, fallback) => fallback ?? k });

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(localStorage.getItem("lang") || "en");
  const setLang = useCallback((l) => { localStorage.setItem("lang", l); setLangState(l); }, []);
  // t("key", "English fallback") - English text lives next to the component, Telugu comes from the dictionary
  const t = useCallback((key, fallback) => translate(lang, key) ?? fallback ?? key, [lang]);
  return <Ctx.Provider value={{ lang, setLang, t }}>{children}</Ctx.Provider>;
}

export const useI18n = () => useContext(Ctx);
