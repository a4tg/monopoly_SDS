import { useEffect, useState } from "react";
import { getMarketActivity, getMarketRating, MarketActivity, MarketRating } from "../services/api";

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString("ru-RU");
}

export default function PlayerRealtimePanels({ token }: { token: string }) {
  const [activity, setActivity] = useState<MarketActivity[]>([]);
  const [rating, setRating] = useState<MarketRating[]>([]);

  const load = async () => {
    const [activityRes, ratingRes] = await Promise.all([getMarketActivity(token), getMarketRating(token)]);
    setActivity(activityRes.items);
    setRating(ratingRes.items);
  };

  useEffect(() => {
    let active = true;
    const boot = async () => {
      try {
        await load();
      } catch {
        // silent fail for sidebar
      }
    };
    boot();
    const timer = window.setInterval(async () => {
      if (!active) return;
      try {
        await load();
      } catch {
        // silent fail for sidebar
      }
    }, 5000);

    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [token]);

  return (
    <>
      <aside className="panel app-side">
        <h3>Рейтинг игроков</h3>
        <p className="muted">Баланс + суммарная стоимость призов в инвентаре</p>
        <div className="list">
          {rating.length === 0 && <p className="muted">Данных по рейтингу пока нет.</p>}
          {rating.map((row) => (
            <div key={row.user_id} className="item">
              <strong>
                #{row.rank} {row.identifier}
              </strong>
              <div>Итог: {row.total_score}</div>
              <div>Баланс: {row.balance}</div>
              <div>Инвентарь: {row.inventory_value}</div>
            </div>
          ))}
        </div>
      </aside>

      <aside className="panel app-side">
        <h3>Лента действий</h3>
        <p className="muted">Сделки, лоты и ставки в текущей сессии (live)</p>
        <div className="list">
          {activity.length === 0 && <p className="muted">Событий пока нет.</p>}
          {activity.map((event) => (
            <div key={event.id} className="item">
              <strong>{event.title}</strong>
              <div>{event.body}</div>
              <div className="muted">{formatDate(event.created_at)}</div>
            </div>
          ))}
        </div>
      </aside>
    </>
  );
}
