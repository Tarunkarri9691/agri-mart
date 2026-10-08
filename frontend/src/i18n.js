// English / Telugu strings. Missing keys fall back to English. Have a native Telugu speaker review before release.
export const STRINGS = {
  en: {},
  te: {
    tagline: "మీకు ఎక్కువ మిగిలే చోట అమ్మండి.",
    login: "లాగిన్", create_account: "ఖాతా సృష్టించండి", logout: "లాగౌట్",
    phone: "ఫోన్ నంబర్", password: "పాస్‌వర్డ్", name: "పేరు", i_am_a: "నేను",
    farmer: "రైతు", buyer: "కొనుగోలుదారు", village: "గ్రామం / పట్టణం",
    new_here: "కొత్తవారా? ఖాతా సృష్టించండి", have_account: "ఖాతా ఉందా? లాగిన్",
    crop: "పంట", quality: "నాణ్యత", qty: "పరిమాణం (క్వింటాళ్లు)",
    sell_from: "అమ్మకం ప్రారంభం", sell_until: "అమ్మకం ముగింపు",
    list_crop: "అమ్మకానికి పంటను నమోదు చేయండి", find_best: "ఉత్తమ కొనుగోలుదారులను కనుగొనండి",
    comparing: "కొనుగోలుదారులు, మార్కెట్లను పోలుస్తున్నాం…", no_matches: "ఇంకా సరిపోయే కొనుగోలుదారులు లేరు.",
    best_option: "ఉత్తమ ఎంపిక", you_keep: "మీకు మిగిలేది", all_options: "అన్ని ఎంపికలు (ర్యాంక్ ప్రకారం)",
    why_rank: "ఈ ర్యాంక్ ఎందుకు?", hide_why: "దాచండి", direct_buyer: "నేరుగా కొనుగోలుదారు", mandi: "మండి",
    net: "నికరం", per_quintal: "క్వింటాల్‌కు", km: "కి.మీ",
    risk_low: "తక్కువ రిస్క్", risk_moderate: "మధ్యస్థ రిస్క్", risk_high: "ఎక్కువ రిస్క్",
    timing_title: "ఇప్పుడే అమ్మాలా లేక వేచి ఉండాలా?", sell_now: "ఇప్పుడే అమ్మండి", wait: "వేచి ఉండండి",
    days: "రోజులు", expected_gain: "అంచనా లాభం", range: "అంచనా పరిధి",
    below_msp: "కనీస మద్దతు ధర కంటే తక్కువ", trips: "ట్రిప్పులు",
    tab_sell: "అమ్మకం", tab_offers: "ఆఫర్లు", tab_groups: "గ్రూపులు", tab_alerts: "హెచ్చరికలు",
    make_offer: "ఆఫర్ పంపండి", price_per_q: "ధర (₹/క్వింటాల్)", send_offer: "పంపండి",
    accept: "అంగీకరించు", reject: "తిరస్కరించు", counter: "ప్రతి ఆఫర్", cancel: "రద్దు",
    paid: "నేను చెల్లించాను", confirm_payment: "చెల్లింపు అందింది", dispute: "వివాదం", rate: "రేటింగ్",
    notifications: "నోటిఫికేషన్లు", mark_read: "అన్నీ చదివినట్లు", no_notifications: "నోటిఫికేషన్లు లేవు",
    speak: "మాట్లాడండి", listening: "వింటున్నాం…", language: "భాష",
    offers_empty: "ఇంకా ఆఫర్లు లేవు.", groups_title: "రైతు గ్రూపులు", create_group: "గ్రూప్ సృష్టించండి",
    join_group: "చేరండి", pooled_gain: "కలిసి అమ్మితే అదనపు లాభం",
    alerts_title: "ధర హెచ్చరికలు", add_alert: "హెచ్చరిక జోడించండి", threshold: "మార్పు %",
    post_requirement: "అవసరాన్ని నమోదు చేయండి", your_requirements: "మీ అవసరాలు", matching_farmers: "సరిపోయే రైతులు",
  },
};

export function translate(lang, key, vars = {}) {
  const raw = (STRINGS[lang] && STRINGS[lang][key]) || null;
  return raw ?? null;
}
