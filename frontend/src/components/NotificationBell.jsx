import { useEffect, useRef, useState } from "react";
import { api } from "../api";

export default function NotificationBell() {
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  async function refresh() {
    try {
      const list = await api.listNotifications();
      setNotifications(list);
    } catch {
      // silent: notifications are best-effort
    }
  }

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  async function handleOpen() {
    setOpen((v) => !v);
  }

  async function handleItemClick(n) {
    if (!n.read) {
      await api.markNotificationRead(n.id);
      refresh();
    }
  }

  async function handleMarkAll() {
    await api.markAllNotificationsRead();
    refresh();
  }

  return (
    <div className="notif-wrap" ref={ref}>
      <button onClick={handleOpen}>
        Alerts
        {unreadCount > 0 && <span className="bell-count">{unreadCount}</span>}
      </button>
      {open && (
        <div className="notif-dropdown">
          <div className="flex-between" style={{ padding: "8px 14px" }}>
            <strong style={{ fontSize: 13 }}>Notifications</strong>
            <button onClick={handleMarkAll} style={{ fontSize: 12, padding: "2px 8px" }}>
              Mark all read
            </button>
          </div>
          {notifications.length === 0 && <div className="notif-empty">No notifications yet</div>}
          {notifications.map((n) => (
            <div
              key={n.id}
              className={`notif-item ${n.read ? "" : "unread"}`}
              onClick={() => handleItemClick(n)}
            >
              <div>{n.message}</div>
              <div className="muted">{new Date(n.created_at).toLocaleString()}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
