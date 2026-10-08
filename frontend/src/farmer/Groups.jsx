import { useEffect, useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../I18n.jsx";
import { rupees } from "../shared/format.js";

export default function Groups() {
  const { t } = useI18n();
  const [groups, setGroups] = useState([]);
  const [listings, setListings] = useState([]);
  const [name, setName] = useState("");
  const [listingId, setListingId] = useState("");
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState("");
  const load = () => api.groups().then(setGroups).catch((e) => setError(e.message));
  useEffect(() => { load(); api.listings().then((l) => { const open = l.filter((x) => x.status === "open"); setListings(open); if (open[0]) setListingId(open[0].id); }); }, []);

  const chosen = listings.find((l) => l.id === +listingId);
  const run = async (fn) => { setError(""); try { await fn(); await load(); } catch (e) { setError(e.message); } };

  return (
    <>
      <section className="panel">
        <h2>{t("groups_title", "Farmer groups")}</h2>
        <p className="muted">Pool produce with nearby farmers for bigger buyers and cheaper transport per quintal.</p>
        <label>Your listing<select value={listingId} onChange={(e) => setListingId(e.target.value)}>
          {listings.map((l) => <option key={l.id} value={l.id}>{l.crop} · {l.quantity_quintals} q</option>)}</select></label>
        <div className="actions">
          <input placeholder="Group name" value={name} onChange={(e) => setName(e.target.value)} />
          <button className="primary" disabled={!name || !chosen} onClick={() => run(() => api.createGroup({ name, crop: chosen.crop, listing_id: chosen.id }))}>{t("create_group", "Create group")}</button>
        </div>
        {error && <p className="error" role="alert">{error}</p>}
        <ul className="plain">{groups.map((g) => (
          <li key={g.id}>
            <strong>{g.name}</strong> · {g.crop} · {g.members} farmers · {g.total_quintals} q
            {g.mine ? <button className="link" onClick={async () => setDetail(await api.groupRecs(g.id).catch((e) => ({ error: e.message })))}> view pooled result</button>
              : chosen?.crop === g.crop && <button className="link" onClick={() => run(() => api.joinGroup(g.id, chosen.id))}> {t("join_group", "Join")}</button>}
          </li>))}</ul>
      </section>
      {detail && !detail.error && (
        <section className="panel best">
          <h2>{detail.group.name}: {detail.group.total_quintals} q pooled</h2>
          <p className="big">{rupees(detail.pooled_net)}</p>
          <p className="muted">{t("pooled_gain", "Gain from selling together")}: <strong>{rupees(detail.pooling_gain)}</strong> vs {rupees(detail.solo_total_net)} selling alone.
            Best buyer for the pooled lot: {detail.recommendations[0]?.name}.</p>
          <ul className="plain">{detail.member_shares.map((s) => <li key={s.listing_id}>{s.quantity} q: your share {rupees(s.pooled_share)} (alone: {rupees(s.best_solo_net)})</li>)}</ul>
        </section>
      )}
      {detail?.error && <p className="error" role="alert">{detail.error}</p>}
    </>
  );
}
