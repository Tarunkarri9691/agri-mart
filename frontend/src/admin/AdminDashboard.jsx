import { useEffect, useState } from "react";
import { api } from "../api.js";

export default function AdminDashboard() {
  const [ov, setOv] = useState(null);
  const [disputes, setDisputes] = useState([]);
  const [msg, setMsg] = useState("");
  const [m, setM] = useState({ name: "", district: "", latitude: "", longitude: "" });
  const load = () => { api.admin.overview().then(setOv); api.admin.disputes().then(setDisputes); };
  useEffect(load, []);
  const say = (p) => p.then((r) => { setMsg(JSON.stringify(r)); load(); }).catch((e) => setMsg(e.message));
  if (!ov) return <p className="muted">Loading…</p>;
  const price7 = ov.model_metrics?.price_h7?.ensemble;
  const cov = ov.model_metrics?.price_h7?.interval;
  return (
    <div className="grid">
      <section className="panel header"><h2>Admin dashboard</h2><p>{Object.entries(ov.users).map(([k, v]) => `${v} ${k}s`).join(" · ")}</p></section>
      <section className="panel">
        <h2>Marketplace</h2>
        <p>Offers: {Object.entries(ov.offers).map(([k, v]) => `${k} ${v}`).join(", ") || "none yet"} · completion rate {ov.completion_rate ?? "n/a"}</p>
        <p>Decision feedback: {ov.decision_feedback.deals} deals, followed top recommendation {ov.decision_feedback.followed_top_recommendation ?? "n/a"}, average price gap {ov.decision_feedback.avg_price_gap_pct ?? "n/a"}%</p>
        {price7 && <p>Price model (7-day): MAPE {price7.MAPE.toFixed(2)}%{cov && `, interval coverage ${(cov.empirical_coverage * 100).toFixed(0)}%`}</p>}
      </section>
      <section className="panel">
        <h2>Data quality ({ov.data_quality.length})</h2>
        {ov.data_quality.length === 0 ? <p className="muted">No issues found.</p> :
          <ul className="plain">{ov.data_quality.slice(0, 15).map((d, i) => <li key={i}><strong>{d.type}</strong> {d.market} {d.crop} – {d.detail}</li>)}</ul>}
        <div className="actions">
          {["sync", "recompute", "alerts", "drift"].map((j) => <button key={j} onClick={() => say(api.admin.job(j))}>Run {j}</button>)}
          <button onClick={() => say(api.admin.retrain())}>Retrain models</button>
        </div>
        {msg && <p className="muted">{msg}</p>}
      </section>
      <section className="panel">
        <h2>Open disputes ({disputes.length})</h2>
        {disputes.map((d) => (
          <div key={d.offer_id} className="offer">
            <strong>#{d.offer_id} {d.crop}</strong> {d.farmer} ↔ {d.buyer} · payment {d.payment_status} {d.payment_reference}<p className="error">{d.reason}</p>
            <div className="actions"><button onClick={() => say(api.admin.resolve(d.offer_id, "complete"))}>Deal stands</button>
              <button onClick={() => say(api.admin.resolve(d.offer_id, "cancel"))}>Cancel deal</button></div>
          </div>))}
      </section>
      <section className="panel">
        <h2>Add market</h2>
        <div className="row"><input placeholder="Name" value={m.name} onChange={(e) => setM({ ...m, name: e.target.value })} />
          <input placeholder="District" value={m.district} onChange={(e) => setM({ ...m, district: e.target.value })} /></div>
        <div className="row"><input placeholder="Latitude" value={m.latitude} onChange={(e) => setM({ ...m, latitude: e.target.value })} />
          <input placeholder="Longitude" value={m.longitude} onChange={(e) => setM({ ...m, longitude: e.target.value })} /></div>
        <button className="primary" onClick={() => say(api.admin.addMarket({ ...m, latitude: +m.latitude, longitude: +m.longitude }))}>Add</button>
      </section>
    </div>
  );
}
