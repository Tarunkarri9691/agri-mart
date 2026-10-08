import { useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../I18n.jsx";
import { CROPS, inDays, today } from "../shared/format.js";
import VoiceButton from "../shared/VoiceButton.jsx";

export default function ListingForm({ onCreated }) {
  const { t } = useI18n();
  const [f, setF] = useState({ crop: "paddy", quantity_quintals: 100, quality: "B", sell_from: today(), sell_to: inDays(14) });
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const fromVoice = (p) => setF((cur) => ({ ...cur, ...(p.crop && { crop: p.crop }), ...(p.quantity && { quantity_quintals: p.quantity }), ...(p.quality && { quality: p.quality }) }));

  async function submit(e) {
    e.preventDefault();
    setError("");
    try { onCreated(await api.createListing({ ...f, crop: f.crop.trim().toLowerCase(), quantity_quintals: +f.quantity_quintals })); }
    catch (err) { setError(err.message); }
  }

  return (
    <form className="panel" onSubmit={submit}>
      <div className="opt-head"><h2>{t("list_crop", "List a crop for sale")}</h2><VoiceButton onParsed={fromVoice} /></div>
      <div className="row">
        <label>{t("crop", "Crop")}<input type="text" list="crop-list-listing" placeholder="e.g. paddy" value={f.crop} onChange={set("crop")} /><datalist id="crop-list-listing">{CROPS.map((c) => <option key={c} value={c} />)}</datalist></label>
        <label>{t("quality", "Quality")}<select value={f.quality} onChange={set("quality")}><option>A</option><option>B</option><option>C</option></select></label>
      </div>
      <label>{t("qty", "Quantity (quintals)")}<input type="number" min="1" value={f.quantity_quintals} onChange={set("quantity_quintals")} /></label>
      <div className="row">
        <label>{t("sell_from", "Sell from")}<input type="date" value={f.sell_from} onChange={set("sell_from")} /></label>
        <label>{t("sell_until", "Sell until")}<input type="date" value={f.sell_to} onChange={set("sell_to")} /></label>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary">{t("find_best", "Find best buyers")}</button>
    </form>
  );
}
