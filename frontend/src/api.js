const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

let token = localStorage.getItem("token");
export const setToken = (t) => {
  token = t;
  t ? localStorage.setItem("token", t) : localStorage.removeItem("token");
};

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join(", ") : body.detail;
    throw new Error(detail || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}
const post = (path, body = {}) => request(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  register: (b) => post("/auth/register", b),
  login: (b) => post("/auth/login", b),
  me: () => request("/auth/me"),
  setLanguage: (l) => request(`/me/language?lang=${l}`, { method: "PATCH" }),
  listings: () => request("/farmer/listings"),
  createListing: (b) => post("/farmer/listings", b),
  recommendations: (id) => request(`/recommendations/${id}`),
  explain: (id, rank) => request(`/recommendations/${id}/explain?rank=${rank}`),
  timing: (id) => request(`/recommendations/${id}/timing`),
  requirements: () => request("/buyer/requirements"),
  createRequirement: (b) => post("/buyer/requirements", b),
  matches: () => request("/buyer/matches"),
  markets: () => request("/markets"),
  offers: () => request("/offers"),
  createOffer: (b) => post("/offers", b),
  respond: (id, b) => post(`/offers/${id}/respond`, b),
  cancelOffer: (id) => post(`/offers/${id}/cancel`),
  pay: (id, b) => post(`/offers/${id}/payment`, b),
  confirmPayment: (id) => post(`/offers/${id}/confirm-payment`),
  dispute: (id, reason) => post(`/offers/${id}/dispute`, { reason }),
  rate: (id, score) => post(`/offers/${id}/rate`, { score }),
  groups: (crop) => request(`/groups${crop ? `?crop=${crop}` : ""}`),
  createGroup: (b) => post("/groups", b),
  joinGroup: (id, listing_id) => post(`/groups/${id}/join`, { listing_id }),
  groupRecs: (id) => request(`/groups/${id}/recommendations`),
  alerts: () => request("/alerts"),
  createAlert: (b) => post("/alerts", b),
  deleteAlert: (id) => request(`/alerts/${id}`, { method: "DELETE" }),
  notifications: () => request("/notifications"),
  readAll: () => post("/notifications/read-all"),
  admin: {
    overview: () => request("/admin/overview"),
    disputes: () => request("/admin/disputes"),
    resolve: (id, outcome) => post(`/admin/disputes/${id}/resolve?outcome=${outcome}`),
    addMarket: (b) => post("/admin/markets", b),
    job: (name) => post(`/admin/jobs/${name}`),
    retrain: () => post("/admin/retrain"),
  },
};

// Live updates: the server pushes notifications and "recommendation_update" events.
export function connectLive() {
  if (!token) return () => {};
  let ws, closed = false, timer;
  const open = () => {
    ws = new WebSocket(`${BASE.replace(/^http/, "ws")}/ws?token=${token}`);
    ws.onmessage = (e) => window.dispatchEvent(new CustomEvent("agri:live", { detail: JSON.parse(e.data) }));
    ws.onclose = () => { if (!closed) timer = setTimeout(open, 5000); };
  };
  open();
  const ping = setInterval(() => ws?.readyState === 1 && ws.send("ping"), 30000);
  return () => { closed = true; clearTimeout(timer); clearInterval(ping); ws?.close(); };
}
