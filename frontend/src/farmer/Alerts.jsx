import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../I18n.jsx";
import { CROPS } from "../shared/format.js";

export default function Alerts() {
  const { t } = useI18n();
  const [alerts, setAlerts] = useState([]);
  const [markets, setMarkets] = useState([]);
  const [f, setF] = useState({ crop: "paddy", market: "", threshold_pct: 5 });
  const [error, setError] = useState("");
  const load = () => api.alerts().then(setAlerts).catch((e) => setError(e.message));
  useEffect(() => { load(); api.markets().then(setMarkets); }, []);
  const add = async () => { setError(""); try { await api.createAlert({ ...f, crop: f.crop.trim().toLowerCase(), market: f.market || null, threshold_pct: +f.threshold_pct }); load(); } catch (e) { setError(e.message); } };
  const mname = (id) => markets.find((m) => m.id === id)?.name || "all markets";
  return (
    <section className="panel">
      <h2>{t("alerts_title", "Price alerts")}</h2>
      <p className="muted">Get an in-app message (and SMS/WhatsApp when enabled) when the expected price moves by more than your threshold.</p>
      <div className="row">
        <label>{t("crop", "Crop")}<input type="text" list="crop-list-alerts" placeholder="e.g. paddy" value={f.crop} onChange={(e) => setF({ ...f, crop: e.target.value })} /><datalist id="crop-list-alerts">{CROPS.map((c) => <option key={c} value={c} />)}</datalist></label>
        <label>Market<select value={f.market} onChange={(e) => setF({ ...f, market: e.target.value })}><option value="">All markets</option>{markets.map((m) => <option key={m.id}>{m.name}</option>)}</select></label>
      </div>
      <label>{t("threshold", "Change %")}<input type="number" min="1" max="50" value={f.threshold_pct} onChange={(e) => setF({ ...f, threshold_pct: e.target.value })} /></label>
      <button className="primary" onClick={add}>{t("add_alert", "Add alert")}</button>
      {error && <p className="error" role="alert">{error}</p>}
      <ul className="plain">{alerts.map((a) => (
        <li key={a.id}>{a.crop} · {mname(a.market_id)} · ±{a.threshold_pct}% <button className="link" onClick={() => api.deleteAlert(a.id).then(load)}>remove</button></li>))}</ul>
    </section>
  );
}
