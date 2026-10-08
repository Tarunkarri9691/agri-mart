import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../I18n.jsx";
import { rupees } from "./format.js";

export default function Offers({ role }) {
  const { t } = useI18n();
  const [offers, setOffers] = useState([]);
  const [error, setError] = useState("");
  const load = useCallback(() => api.offers().then(setOffers).catch((e) => setError(e.message)), []);

  useEffect(() => {
    load();
    const onLive = (e) => e.detail.type === "notification" && load();
    window.addEventListener("agri:live", onLive);
    return () => window.removeEventListener("agri:live", onLive);
  }, [load]);

  const run = (fn) => async (...a) => { setError(""); try { await fn(...a); await load(); } catch (e) { setError(e.message); } };
  if (offers.length === 0) return <p className="muted">{error || t("offers_empty", "No offers yet.")}</p>;
  return (
    <>
      {error && <p className="error" role="alert">{error}</p>}
      <ul className="options">{offers.map((o) => <OfferCard key={o.id} o={o} role={role} run={run} />)}</ul>
    </>
  );
}

function OfferCard({ o, role, run }) {
  const { t } = useI18n();
  const [counter, setCounter] = useState(o.price);
  const [ref, setRef] = useState("");
  const [method, setMethod] = useState("upi");
  const [reason, setReason] = useState("");
  const other = role === "farmer" ? o.buyer_name : o.farmer_name;
  return (
    <li className="offer">
      <div className="opt-head">
        <strong>{o.crop} · {other}</strong><span className={`status st-${o.status}`}>{o.status}</span>
      </div>
      <p className="muted">{o.quantity} q at {rupees(o.price)}/q = <strong>{rupees(o.price * o.quantity)}</strong>
        {o.payment_status !== "none" && <> · payment {o.payment_status}{o.payment_reference && ` (${o.payment_reference})`}</>}</p>
      {o.status === "disputed" && <p className="error">{o.dispute_reason}</p>}

      {o.status === "pending" && o.can_respond && (
        <div className="actions">
          <button className="primary" onClick={run(() => api.respond(o.id, { action: "accept" }))}>{t("accept", "Accept")}</button>
          <button onClick={run(() => api.respond(o.id, { action: "reject" }))}>{t("reject", "Reject")}</button>
          <input type="number" aria-label="Counter price" value={counter} onChange={(e) => setCounter(+e.target.value)} />
          <button onClick={run(() => api.respond(o.id, { action: "counter", price: counter }))}>{t("counter", "Counter")}</button>
        </div>
      )}
      {o.status === "pending" && !o.can_respond && (
        <div className="actions"><span className="muted">Waiting for the other party</span>
          <button className="link" onClick={run(() => api.cancelOffer(o.id))}>{t("cancel", "Cancel")}</button></div>
      )}
      {o.status === "accepted" && (
        <div className="actions">
          {role === "buyer" && o.payment_status === "none" && (
            <>
              <select value={method} onChange={(e) => setMethod(e.target.value)}><option value="upi">UPI</option><option value="bank">Bank</option><option value="cash">Cash</option></select>
              <input placeholder="Reference" value={ref} onChange={(e) => setRef(e.target.value)} />
              <button className="primary" onClick={run(() => api.pay(o.id, { method, reference: ref }))}>{t("paid", "I have paid")}</button>
            </>
          )}
          {role === "farmer" && o.payment_status === "paid" && (
            <button className="primary" onClick={run(() => api.confirmPayment(o.id))}>{t("confirm_payment", "Payment received")}</button>
          )}
          {o.payment_status === "none" && <button className="link" onClick={run(() => api.cancelOffer(o.id))}>{t("cancel", "Cancel")}</button>}
          <input placeholder="Dispute reason (min 5 chars)" value={reason} onChange={(e) => setReason(e.target.value)} />
          <button disabled={reason.length < 5} onClick={run(() => api.dispute(o.id, reason))}>{t("dispute", "Dispute")}</button>
        </div>
      )}
      {o.status === "completed" && (
        <div className="actions">{t("rate", "Rate")}: {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} aria-label={`${n} stars`} onClick={run(() => api.rate(o.id, n))}>{n}★</button>
        ))}</div>
      )}
    </li>
  );
}
