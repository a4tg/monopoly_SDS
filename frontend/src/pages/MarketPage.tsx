import { useEffect, useMemo, useState } from "react";
import {
  AuctionLot,
  createAuctionLot,
  createTradeOffer,
  getAuctionLots,
  getMarketPlayers,
  getPlayerInventory,
  getTradeOffers,
  MarketInventoryItem,
  MarketOffer,
  MarketPlayer,
  me,
  placeAuctionBid,
  respondTradeOffer,
} from "../services/api";
import { useAuthStore } from "../store/authStore";

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return value;
  return dt.toLocaleString("ru-RU");
}

export default function MarketPage() {
  const token = useAuthStore((s) => s.accessToken);
  const logout = useAuthStore((s) => s.logout);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [currentUserId, setCurrentUserId] = useState<number>(0);

  const [players, setPlayers] = useState<MarketPlayer[]>([]);
  const [incoming, setIncoming] = useState<MarketOffer[]>([]);
  const [outgoing, setOutgoing] = useState<MarketOffer[]>([]);
  const [lots, setLots] = useState<AuctionLot[]>([]);
  const [ownInventory, setOwnInventory] = useState<MarketInventoryItem[]>([]);

  const [targetUserId, setTargetUserId] = useState<number>(0);
  const [targetInventory, setTargetInventory] = useState<MarketInventoryItem[]>([]);
  const [itemId, setItemId] = useState<number>(0);
  const [offerPoints, setOfferPoints] = useState<number>(50);
  const [offerNote, setOfferNote] = useState<string>("");

  const [auctionItemId, setAuctionItemId] = useState<number>(0);
  const [auctionDurationMin, setAuctionDurationMin] = useState<number>(60);
  const [bidByLot, setBidByLot] = useState<Record<number, number>>({});

  const openLots = useMemo(() => lots.filter((l) => l.status === "open"), [lots]);
  const closedLots = useMemo(() => lots.filter((l) => l.status !== "open"), [lots]);

  const loadData = async () => {
    if (!token) return;
    const [profile, playersRes, offersRes, lotsRes] = await Promise.all([
      me(token),
      getMarketPlayers(token),
      getTradeOffers(token),
      getAuctionLots(token),
    ]);
    setCurrentUserId(profile.id);
    setPlayers(playersRes.items);
    setIncoming(offersRes.incoming);
    setOutgoing(offersRes.outgoing);
    setLots(lotsRes.items);
    const ownInv = await getPlayerInventory(token, profile.id);
    setOwnInventory(ownInv.items);
  };

  useEffect(() => {
    const boot = async () => {
      if (!token) return;
      setIsLoading(true);
      try {
        await loadData();
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Ошибка загрузки торговой площадки";
        if (msg.toLowerCase().includes("invalid token") || msg.toLowerCase().includes("missing bearer")) {
          logout();
          setError("Сессия истекла. Войдите снова.");
        } else {
          setError(msg);
        }
      } finally {
        setIsLoading(false);
      }
    };
    boot();
  }, [token, logout]);

  useEffect(() => {
    if (!token) return;
    const timer = window.setInterval(async () => {
      try {
        await loadData();
      } catch {
        // silent polling errors
      }
    }, 5000);
    return () => window.clearInterval(timer);
  }, [token]);

  if (isLoading) {
    return <section className="panel">Загрузка...</section>;
  }

  return (
    <section className="stack-lg">
      <div className="panel panel-wide">
        <h2>Торговая площадка</h2>
        <p className="muted">Офферы между игроками и аукционные лоты в рамках текущей сессии.</p>

        <h3>Прямой оффер игроку</h3>
        <div className="actions">
          <select
            value={targetUserId || ""}
            onChange={async (e) => {
              const nextId = Number(e.target.value);
              setTargetUserId(nextId);
              setItemId(0);
              setTargetInventory([]);
              if (!token || !nextId) return;
              try {
                const inv = await getPlayerInventory(token, nextId);
                setTargetInventory(inv.items);
              } catch (err) {
                setError(err instanceof Error ? err.message : "Ошибка загрузки инвентаря игрока");
              }
            }}
          >
            <option value="">Выберите игрока</option>
            {players
              .filter((p) => p.id !== currentUserId)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.identifier} (баланс: {p.balance})
                </option>
              ))}
          </select>
          <select value={itemId || ""} onChange={(e) => setItemId(Number(e.target.value))}>
            <option value="">Выберите предмет</option>
            {targetInventory.map((it) => (
              <option key={it.id} value={it.id}>
                {it.reward_name} (цена покупки: {it.paid_points})
              </option>
            ))}
          </select>
          <input
            type="number"
            min={1}
            value={offerPoints}
            onChange={(e) => setOfferPoints(Number(e.target.value))}
            placeholder="Предложение в баллах"
          />
          <input
            value={offerNote}
            onChange={(e) => setOfferNote(e.target.value)}
            placeholder="Комментарий к сделке (опционально)"
          />
          <button
            type="button"
            onClick={async () => {
              if (!token || !targetUserId || !itemId) return;
              try {
                await createTradeOffer(token, {
                  inventory_item_id: itemId,
                  to_user_id: targetUserId,
                  offer_points: offerPoints,
                  note: offerNote,
                });
                setMessage("Оффер отправлен");
                await loadData();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Ошибка отправки оффера");
              }
            }}
          >
            Отправить оффер
          </button>
        </div>
      </div>

      <div className="panel">
        <h3>Аукцион</h3>
        <p className="muted">Выставите предмет из своего инвентаря и задайте длительность лота.</p>
        <div className="actions">
          <select value={auctionItemId || ""} onChange={(e) => setAuctionItemId(Number(e.target.value))}>
            <option value="">Предмет из моего инвентаря</option>
            {ownInventory.map((it) => (
              <option key={it.id} value={it.id}>
                {it.reward_name} (цена покупки: {it.paid_points})
              </option>
            ))}
          </select>
          <input
            type="number"
            min={1}
            value={auctionDurationMin}
            onChange={(e) => setAuctionDurationMin(Number(e.target.value))}
            placeholder="Длительность (мин)"
          />
          <button
            type="button"
            onClick={async () => {
              if (!token || !auctionItemId) return;
              try {
                await createAuctionLot(token, { inventory_item_id: auctionItemId, duration_minutes: auctionDurationMin });
                setMessage("Аукционный лот создан");
                await loadData();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Ошибка создания лота");
              }
            }}
          >
            Открыть лот
          </button>
        </div>
      </div>

      <div className="panel">
        <h3>Открытые лоты</h3>
        <div className="list">
          {openLots.length === 0 && <p className="muted">Открытых лотов нет.</p>}
          {openLots.map((lot) => (
            <div key={lot.id} className="item">
              <strong>{lot.item_name}</strong>
              <div>Продавец: {lot.seller_identifier}</div>
              <div>Лот #{lot.id}</div>
              <div>Лидер: {lot.top_bidder_identifier || "-"}</div>
              <div>Текущая ставка: {lot.top_bid_points ?? 0}</div>
              <div>Закрытие: {formatDate(lot.ends_at)}</div>
              <div className="actions">
                <input
                  type="number"
                  min={1}
                  value={bidByLot[lot.id] ?? (lot.top_bid_points ? lot.top_bid_points + 1 : 1)}
                  onChange={(e) =>
                    setBidByLot((prev) => ({
                      ...prev,
                      [lot.id]: Number(e.target.value),
                    }))
                  }
                  placeholder="Ставка"
                />
                <button
                  type="button"
                  onClick={async () => {
                    if (!token) return;
                    const bid = bidByLot[lot.id] ?? (lot.top_bid_points ? lot.top_bid_points + 1 : 1);
                    try {
                      await placeAuctionBid(token, lot.id, bid);
                      setMessage("Ставка принята");
                      await loadData();
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Ошибка ставки");
                    }
                  }}
                >
                  Сделать ставку
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <h3>Закрытые лоты</h3>
        <div className="list">
          {closedLots.length === 0 && <p className="muted">Закрытых лотов нет.</p>}
          {closedLots.map((lot) => (
            <div key={lot.id} className="item">
              <strong>{lot.item_name}</strong>
              <div>Статус: {lot.status}</div>
              <div>Победитель: {lot.winner_identifier || "нет"}</div>
              <div>Финальная ставка: {lot.winning_bid_points ?? 0}</div>
              <div>Закрыт: {formatDate(lot.closed_at)}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="asset-row">
          <div className="asset-slot">
            <div className="asset-label">Входящие офферы</div>
            <div className="list">
              {incoming.length === 0 && <p className="muted">Пока нет входящих офферов.</p>}
              {incoming.map((offer) => (
                <div key={offer.id} className="item">
                  <strong>{offer.item?.reward_name ?? "Предмет"}</strong>
                  <div>От: {offer.from_identifier}</div>
                  <div>Цена: {offer.offer_points}</div>
                  <div>Статус: {offer.status}</div>
                  {offer.note && <div>Комментарий: {offer.note}</div>}
                  {offer.status === "pending" && (
                    <div className="actions">
                      <button
                        type="button"
                        onClick={async () => {
                          if (!token) return;
                          try {
                            await respondTradeOffer(token, offer.id, "accept");
                            setMessage("Сделка принята");
                            await loadData();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Ошибка принятия оффера");
                          }
                        }}
                      >
                        Принять
                      </button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={async () => {
                          if (!token) return;
                          try {
                            await respondTradeOffer(token, offer.id, "reject");
                            setMessage("Оффер отклонен");
                            await loadData();
                          } catch (err) {
                            setError(err instanceof Error ? err.message : "Ошибка отклонения оффера");
                          }
                        }}
                      >
                        Отклонить
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="asset-slot">
            <div className="asset-label">Исходящие офферы</div>
            <div className="list">
              {outgoing.length === 0 && <p className="muted">Пока нет исходящих офферов.</p>}
              {outgoing.map((offer) => (
                <div key={offer.id} className="item">
                  <strong>{offer.item?.reward_name ?? "Предмет"}</strong>
                  <div>Кому: {offer.to_identifier}</div>
                  <div>Цена: {offer.offer_points}</div>
                  <div>Статус: {offer.status}</div>
                  {offer.note && <div>Комментарий: {offer.note}</div>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {message && <p className="ok">{message}</p>}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
