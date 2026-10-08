// Voice input: turn a spoken phrase ("paddy 120 quintals" / "వరి 120 క్వింటాళ్లు") into form values.
export const CROP_WORDS = {
  paddy: ["paddy", "rice", "వరి", "ధాన్యం"], maize: ["maize", "corn", "మొక్కజొన్న"],
  chilli: ["chilli", "chili", "chillies", "మిరప", "మిర్చి"], cotton: ["cotton", "పత్తి"], banana: ["banana", "అరటి"],
};

const TELUGU_DIGITS = "౦౧౨౩౪౫౬౭౮౯";

export function parseSpeech(text) {
  const norm = (text || "").toLowerCase().replace(/[౦-౯]/g, (d) => String(TELUGU_DIGITS.indexOf(d)));
  let crop = null;
  for (const [name, words] of Object.entries(CROP_WORDS)) if (words.some((w) => norm.includes(w))) { crop = name; break; }
  const m = norm.match(/\d+(?:\.\d+)?/);
  const quality = (norm.match(/\bgrade\s*([abc])\b/) || norm.match(/\b([abc])\s*grade\b/) || [])[1]?.toUpperCase() || null;
  return { crop, quantity: m ? Number(m[0]) : null, quality };
}

export function speechSupported() {
  return typeof window !== "undefined" && !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}

export function listen(lang, onText, onEnd) {
  const R = window.SpeechRecognition || window.webkitSpeechRecognition;
  const rec = new R();
  rec.lang = lang === "te" ? "te-IN" : "en-IN";
  rec.onresult = (e) => onText(e.results[0][0].transcript);
  rec.onend = onEnd;
  rec.onerror = onEnd;
  rec.start();
  return rec;
}
