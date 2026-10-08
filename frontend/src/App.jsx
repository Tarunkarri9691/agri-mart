import { useEffect, useState } from "react";
import { api, connectLive, setToken } from "./api.js";
import { useI18n } from "./I18n.jsx";
import AdminDashboard from "./admin/AdminDashboard.jsx";
import BuyerDashboard from "./buyer/BuyerDashboard.jsx";
import FarmerDashboard from "./farmer/FarmerDashboard.jsx";
import Auth from "./shared/Auth.jsx";
import Notifications from "./shared/Notifications.jsx";

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const { lang, setLang, t } = useI18n();

  useEffect(() => {
    api.me().then(setUser).catch(() => setToken(null)).finally(() => setReady(true));
  }, []);
  useEffect(() => (user ? connectLive() : undefined), [user]);

  const logout = () => { setToken(null); setUser(null); };
  const changeLang = (l) => { setLang(l); if (user) api.setLanguage(l).catch(() => {}); };
  const offline = !navigator.onLine;

  if (!ready) return null;
  if (!user) return <Auth onLogin={(u) => { setUser(u); if (u.language) setLang(u.language); }} />;

  const Dash = { farmer: FarmerDashboard, buyer: BuyerDashboard, admin: AdminDashboard }[user.role];
  return (
    <div className="shell">
      <header className="topbar">
        <strong className="brand">AgriMarket</strong>
        <select aria-label={t("language", "Language")} className="lang" value={lang} onChange={(e) => changeLang(e.target.value)}>
          <option value="en">English</option><option value="te">తెలుగు</option>
        </select>
        <Notifications />
        <span className="who">{user.name}</span>
        <button className="link" onClick={logout}>{t("logout", "Log out")}</button>
      </header>
      {offline && <p className="offline" role="status">You are offline. Showing the last saved results.</p>}
      <main><Dash user={user} /></main>
    </div>
  );
}
