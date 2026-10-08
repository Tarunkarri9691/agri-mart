import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";
import { useI18n } from "../I18n.jsx";

export default function Notifications() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const load = useCallback(() => api.notifications().then(setItems).catch(() => {}), []);

  useEffect(() => {
    load();
    const onLive = (e) => e.detail.type === "notification" && load();
    window.addEventListener("agri:live", onLive);
    return () => window.removeEventListener("agri:live", onLive);
  }, [load]);

  const unread = items.filter((n) => !n.read).length;
  const markRead = async () => { await api.readAll(); load(); };

  return (
    <div className="bell">
      <button className="link" aria-expanded={open} aria-label={t("notifications", "Notifications")} onClick={() => setOpen(!open)}>
        🔔{unread > 0 && <span className="count">{unread}</span>}
      </button>
      {open && (
        <div className="dropdown" role="dialog" aria-label={t("notifications", "Notifications")}>
          <div className="opt-head"><strong>{t("notifications", "Notifications")}</strong>
            <button className="link" onClick={markRead}>{t("mark_read", "Mark all read")}</button></div>
          {items.length === 0 ? <p className="muted">{t("no_notifications", "No notifications")}</p> : (
            <ul className="plain">{items.slice(0, 12).map((n) => (
              <li key={n.id} className={n.read ? "read" : "unread"}><strong>{n.title}</strong><br />{n.body}</li>
            ))}</ul>
          )}
        </div>
      )}
    </div>
  );
}
