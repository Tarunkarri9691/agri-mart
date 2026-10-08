import { useState } from "react";
import { useI18n } from "../I18n.jsx";
import { listen, parseSpeech, speechSupported } from "./speech.js";

/* Speak "paddy 120 quintals grade A" (English or Telugu) to fill the form. Hidden where the browser has no speech API. */
export default function VoiceButton({ onParsed }) {
  const { t, lang } = useI18n();
  const [on, setOn] = useState(false);
  if (!speechSupported()) return null;
  return (
    <button type="button" className="mic" aria-pressed={on} disabled={on}
      onClick={() => { setOn(true); listen(lang, (txt) => onParsed(parseSpeech(txt), txt), () => setOn(false)); }}>
      🎤 {on ? t("listening", "Listening…") : t("speak", "Speak")}
    </button>
  );
}
