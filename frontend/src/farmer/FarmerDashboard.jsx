import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../I18n.jsx";
import { rupees } from "../shared/format.js";
import Offers from "../shared/Offers.jsx";
import RiskBadge from "../shared/RiskBadge.jsx";
import Alerts from "./Alerts.jsx";
import Groups from "./Groups.jsx";
import ListingForm from "./ListingForm.jsx";

/* Layout follows patent FIG. 4: profile header (410), crop listing card (420), matched buyer card (430),
   net realization & risk card (440), AI recommendation summary panel (450). */
export default function FarmerDashboard({ user }) {
  const { t } = useI18n();
  const [tab, setTab] = useState("sell");
  const tabs = [["sell", "tab_sell", "Sell"], ["offers", "tab_offers", "Offers"], ["groups", "tab_groups", "Groups"], ["alerts", "tab_alerts", "Alerts"]];
  return (
    <div className="grid">
      <section className="panel header"><h2>{user.name}</h2><p>{user.location}</p></section>
      <nav className="tabs" role="tablist">
        {tabs.map(([id, key, label]) => (
          <button key={id} role="tab" aria-selected={tab === id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>{t(key, label)}</button>
        ))}
      </nav>
      {tab === "sell" && <Sell />}
      {tab === "offers" && <section className="panel"><Offers role="farmer" /></section>}
      {tab === "groups" && <Groups />}
      {tab === "alerts" && <Alerts />}
    </div>
  );
}

function Sell() {
  const { t } = useI18n();
  const [listings, setListings] = useState([]);
  const [current, setCurrent] = useState(null);
  const [recs, setRecs] = useState([]);
  const [timing, setTiming] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [why, setWhy] = useState(null);

  const select = useCallback(async (listing) => {
    setCurrent(listing); setRecs([]); setWhy(null); setTiming(null); setError(""); setLoading(true);
    try {
      setRecs(await api.recommendations(listing.id));
      api.timing(listing.id).then(setTiming).catch(() => {});
    } catch (e) { setError(e.message); } finally { setLoading(false); }
  }, []);

  useEffect(() => {
    api.listings().then((l) => { setListings(l); if (l[0]) select(l[0]); }).catch((e) => setError(e.message));
  }, [select]);

  // server pushes "recommendation_update" when prices move: refresh the open listing
  useEffect(() => {
    const onLive = (e) => e.detail.type === "recommendation_update" && current && e.detail.listing_id === current.id && select(current);
    window.addEventListener("agri:live", onLive);
    return () => window.removeEventListener("agri:live", onLive);
  }, [current, select]);

  async function openWhy(rank) {
    if (why?.rank === rank) return setWhy(null);
    setWhy(await api.explain(current.id, rank));
  }
  const onCreated = (l) => { setListings([l, ...listings]); select(l); };
  const best = recs[0];
  const maxNet = Math.max(1, ...recs.map((r) => r.net_high ?? r.net_realization));

  return (
    <>
      <ListingForm onCreated={onCreated} />
      {listings.length > 0 && (
        <section className="panel">
          <h2>{t("crop", "Crop")}</h2>
          <select value={current?.id || ""} onChange={(e) => select(listings.find((l) => l.id === +e.target.value))}>
            {listings.map((l) => <option key={l.id} value={l.id}>{l.crop} · {l.quantity_quintals} q · {l.quality} · {l.sell_from} → {l.sell_to} · {l.status}</option>)}
          </select>
        </section>
      )}
      {loading && <p className="muted">{t("comparing", "Comparing buyers and markets…")}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {current && !loading && recs.length === 0 && !error && <p className="muted">{t("no_matches", "No matching buyers or markets yet.")}</p>}

      {best && (
        <>
          <section className="panel best">
            <p className="muted">{t("best_option", "Best option")} · {current.crop}</p>
            <h2>{best.name} <RiskBadge tag={best.risk_tag} /></h2>
            <p className="big">{rupees(best.net_realization)}</p>
            {best.net_low !== best.net_high && <p className="muted">{t("range", "Likely range")}: {rupees(best.net_low)} – {rupees(best.net_high)}</p>}
            <p className="muted">
              {t("you_keep", "You keep this")} after {rupees(best.transport_cost)} transport{best.trips > 1 && ` (${best.trips} trips)`}, {rupees(best.commission)} fees and {rupees(best.expected_loss)} expected loss. {best.distance_km} km · {rupees(best.price_used)}/q.
            </p>
            {best.below_msp && <p className="warn">⚠ {t("below_msp", "Below the minimum support price")} ({rupees(best.msp)}/q)</p>}
          </section>

          {timing && <Timing data={timing} />}

          <section className="panel">
            <h2>{t("all_options", "All options, ranked")}</h2>
            <ul className="options">
              {recs.map((r) => (
                <li key={r.candidate_type + r.candidate_id}>
                  <div className="opt-head">
                    <span><strong>{r.rank}. {r.name}</strong> <small>{r.candidate_type === "buyer" ? t("direct_buyer", "direct buyer") : t("mandi", "mandi")}</small></span>
                    <RiskBadge tag={r.risk_tag} />
                  </div>
                  <div className="bar" aria-hidden="true">
                    <span className="band" style={{ left: `${(r.net_low / maxNet) * 100}%`, width: `${((r.net_high - r.net_low) / maxNet) * 100}%` }} />
                    <span style={{ width: `${(r.net_realization / maxNet) * 100}%` }} />
                  </div>
                  <div className="opt-foot">
                    <span>{rupees(r.net_realization)} {t("net", "net")}</span>
                    <span>{r.distance_km} {t("km", "km")} · {rupees(r.price_used)}/q{r.below_msp && " ⚠"}</span>
                    <button className="link" onClick={() => openWhy(r.rank)}>{why?.rank === r.rank ? t("hide_why", "Hide") : t("why_rank", "Why this rank?")}</button>
                  </div>
                  {r.candidate_type === "buyer" && current.status === "open" && <OfferForm listing={current} rec={r} />}
                  {why?.rank === r.rank && <Explain data={why} />}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </>
  );
}

function Timing({ data }) {
  const { t } = useI18n();
  const wait = data.decision === "wait";
  return (
    <section className={`panel timing ${wait ? "wait" : ""}`}>
      <h2>{t("timing_title", "Sell now or wait?")}</h2>
      <p className="verdict">{wait ? `${t("wait", "Wait")} ${data.wait_days} ${t("days", "days")}` : t("sell_now", "Sell now")}</p>
      <p className="muted">{data.reason}</p>
      {data.options.length > 0 && (
        <table className="mini"><thead><tr><th>{t("days", "Days")}</th><th>Expected net</th><th>{t("range", "Range")}</th></tr></thead>
          <tbody>{data.options.map((o) => <tr key={o.days}><td>+{o.days}</td><td>{rupees(o.net)}</td><td>{rupees(o.net_low)} – {rupees(o.net_high)}</td></tr>)}</tbody></table>
      )}
    </section>
  );
}

function OfferForm({ listing, rec }) {
  const { t } = useI18n();
  const [open, setOpen] = useState(false);
  const [price, setPrice] = useState(Math.round(rec.price_used));
  const [msg, setMsg] = useState("");
  async function send() {
    try {
      await api.createOffer({ listing_id: listing.id, requirement_id: rec.candidate_id, price, quantity: Math.min(listing.quantity_quintals, rec.quantity_sold) });
      setMsg("Offer sent ✓"); setOpen(false);
    } catch (e) { setMsg(e.message); }
  }
  return (
    <div className="actions">
      {!open && <button onClick={() => setOpen(true)}>{t("make_offer", "Make offer")}</button>}
      {open && <><input type="number" aria-label={t("price_per_q", "Price per quintal")} value={price} onChange={(e) => setPrice(+e.target.value)} />
        <button className="primary" onClick={send}>{t("send_offer", "Send")}</button></>}
      {msg && <span className="muted">{msg}</span>}
    </div>
  );
}

function Explain({ data }) {
  const { price_factors: p, cost_factors: c, risk_factors: r, ranking: k } = data;
  return (
    <div className="explain">
      <h3>Price</h3>
      <p>Expected {rupees(p.predicted_price)} per quintal ({p.source.replace("_", " ")}). Demand index {p.demand_index ?? "n/a"}, recent price swing {p.volatility ? (p.volatility * 100).toFixed(1) + "%" : "n/a"}.</p>
      {p.top_drivers?.length > 0 && <ul>{p.top_drivers.slice(0, 3).map((d) => <li key={d.feature}>{d.label}: {d.impact_rs >= 0 ? "+" : "−"}{rupees(Math.abs(d.impact_rs))}/q</li>)}</ul>}
      <h3>Cost</h3>
      <p>{rupees(c.gross_value)} sale − {rupees(c.transport_cost)} transport − {rupees(c.commission)} fees − {rupees(c.expected_loss)} loss = <strong>{rupees(c.net_realization)}</strong> over {c.distance_km} km ({c.travel_hours} h).</p>
      <h3>Risk ({r.score})</h3>
      <ul>{Object.entries(r.components).map(([key, v]) => <li key={key}>{key.replace("_", " ")}: {Math.round(v * 100)}%</li>)}</ul>
      <h3>Ranking</h3>
      <p>Score {k.score} = {k.weights.net}×net ({k.net_normalized}) + {k.weights.compat}×match ({k.compatibility}) − {k.weights.risk}×risk ({r.score}).</p>
    </div>
  );
}
