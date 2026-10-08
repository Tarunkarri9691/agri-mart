import { useState } from "react";
import { api, setToken } from "../api.js";
import { useI18n } from "../I18n.jsx";

const EMPTY = { name: "", phone: "", password: "", role: "farmer", location: "Eluru", latitude: 16.7107, longitude: 81.0952 };

export default function Auth({ onLogin }) {
  const { t, lang } = useI18n();
  const [mode, setMode] = useState("login");
  const [f, setF] = useState(EMPTY);
  const [error, setError] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  async function submit(e) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "register") await api.register({ ...f, latitude: +f.latitude, longitude: +f.longitude, language: lang });
      const res = await api.login({ phone: f.phone, password: f.password });
      setToken(res.access_token);
      onLogin(res.user);
    } catch (err) { setError(err.message); }
  }

  return (
    <div className="auth">
      <div className="auth-intro">
        <h1>{t("tagline", "Sell where you keep the most.")}</h1>
        <p>Prices, distance, transport and risk are weighed for every buyer and mandi near you, so you see what actually reaches your hands.</p>
      </div>
      <form className="panel" onSubmit={submit}>
        <h2>{mode === "login" ? t("login", "Log in") : t("create_account", "Create account")}</h2>
        {mode === "register" && (
          <>
            <label>{t("name", "Name")}<input value={f.name} onChange={set("name")} required /></label>
            <label>{t("i_am_a", "I am a")}
              <select value={f.role} onChange={set("role")}>
                <option value="farmer">{t("farmer", "Farmer")}</option><option value="buyer">{t("buyer", "Buyer")}</option>
              </select>
            </label>
            <label>{t("village", "Village / town")}<input value={f.location} onChange={set("location")} /></label>
            <div className="row">
              <label>Latitude<input type="number" step="any" value={f.latitude} onChange={set("latitude")} /></label>
              <label>Longitude<input type="number" step="any" value={f.longitude} onChange={set("longitude")} /></label>
            </div>
          </>
        )}
        <label>{t("phone", "Phone number")}<input inputMode="numeric" value={f.phone} onChange={set("phone")} required /></label>
        <label>{t("password", "Password")}<input type="password" minLength={6} value={f.password} onChange={set("password")} required /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary">{mode === "login" ? t("login", "Log in") : t("create_account", "Create account")}</button>
        <button type="button" className="link" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
          {mode === "login" ? t("new_here", "New here? Create an account") : t("have_account", "Have an account? Log in")}
        </button>
        {mode === "login" && <p className="hint">Demo: farmer 8000000001 / farmer123 · buyer 9000000001 / buyer123 · admin 9999999999 / admin123</p>}
      </form>
    </div>
  );
}
