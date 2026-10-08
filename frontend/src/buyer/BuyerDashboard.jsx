import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../I18n.jsx";
import { CROPS, inDays, rupees, today } from "../shared/format.js";
import Offers from "../shared/Offers.jsx";

export default function BuyerDashboard({ user }) {
  const { t } = useI18n();
  const [tab, setTab] = useState("req");
  const [reqs, setReqs] = useState([]);
  const [matches, setMatches] = useState([]);
  const [error, setError] = useState("");
  const [f, setF] = useState({ crop: "paddy", quantity_quintals: 100, offered_price: 2300, quality_required: "C", buy_from: today(), buy_to: inDays(30) });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const load = () => Promise.all([api.requirements(), api.matches()]).then(([r, m]) => { setReqs(r); setMatches(m); }).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function submit(e) {
    e.preventDefault(); setError("");
    try { await api.createRequirement({ ...f, crop: f.crop.trim().toLowerCase(), quantity_quintals: +f.quantity_quintals, offered_price: +f.offered_price }); load(); }
    catch (err) { setError(err.message); }
  }
  async function offer(m, price) {
    setError("");
    try { await api.createOffer({ listing_id: m.listing_id, requirement_id: m.requirement_id, price, quantity: m.quantity_quintals }); setTab("offers"); }
    catch (err) { setError(err.message); }
  }

  return (
    <div className="grid">
      <section className="panel header"><h2>{user.name}</h2><p>{user.location} · ★ {user.reliability?.toFixed?.(1) ?? "4.0"} ({user.rating_count || 0})</p></section>
      <nav className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "req"} className={tab === "req" ? "on" : ""} onClick={() => setTab("req")}>{t("your_requirements", "Requirements")}</button>
        <button role="tab" aria-selected={tab === "offers"} className={tab === "offers" ? "on" : ""} onClick={() => setTab("offers")}>{t("tab_offers", "Offers")}</button>
      </nav>
      {error && <p className="error" role="alert">{error}</p>}
      {tab === "offers" && <section className="panel"><Offers role="buyer" /></section>}
      {tab === "req" && (
        <>
          <form className="panel" onSubmit={submit}>
            <h2>{t("post_requirement", "Post a requirement")}</h2>
            <div className="row">
              <label>{t("crop", "Crop")}<input type="text" list="crop-list-buyer" placeholder="e.g. paddy" value={f.crop} onChange={set("crop")} /><datalist id="crop-list-buyer">{CROPS.map((c) => <option key={c} value={c} />)}</datalist></label>
              <label>Minimum quality<select value={f.quality_required} onChange={set("quality_required")}><option>A</option><option>B</option><option>C</option></select></label>
            </div>
            <div className="row">
              <label>{t("qty", "Quantity (quintals)")}<input type="number" min="1" value={f.quantity_quintals} onChange={set("quantity_quintals")} /></label>
              <label>{t("price_per_q", "Price offered (₹/quintal)")}<input type="number" min="1" value={f.offered_price} onChange={set("offered_price")} /></label>
            </div>
            <div className="row">
              <label>Buy from<input type="date" value={f.buy_from} onChange={set("buy_from")} /></label>
              <label>Buy until<input type="date" value={f.buy_to} onChange={set("buy_to")} /></label>
            </div>
            <button className="primary">{t("post_requirement", "Post requirement")}</button>
          </form>
          <section className="panel">
            <h2>{t("your_requirements", "Your requirements")}</h2>
            {reqs.length === 0 ? <p className="muted">Nothing posted yet.</p> : (
              <ul className="plain">{reqs.map((r) => <li key={r.id}>{r.crop} · {r.quantity_quintals} q at {rupees(r.offered_price)}/q · grade {r.quality_required}+ · {r.status}</li>)}</ul>)}
          </section>
          <section className="panel">
            <h2>{t("matching_farmers", "Farmers with matching crops")}</h2>
            {matches.length === 0 ? <p className="muted">No matching farmers right now.</p> : (
              <ul className="plain">{matches.map((m) => (
                <li key={`${m.requirement_id}-${m.listing_id}`}>
                  <strong>{m.farmer}</strong> · {m.crop} · {m.quantity_quintals} q grade {m.quality} · {m.distance_km} km · {Math.round(m.compatibility * 100)}% match
                  {" "}<button className="link" onClick={() => offer(m, reqs.find((r) => r.id === m.requirement_id)?.offered_price || 0)}>{t("make_offer", "Make offer")}</button>
                </li>))}</ul>)}
          </section>
        </>
      )}
    </div>
  );
}
