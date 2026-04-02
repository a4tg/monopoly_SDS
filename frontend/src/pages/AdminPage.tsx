import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import {
  AdminSession,
  createCell,
  createSecretShopItem,
  createSession,
  downloadSessionResultsCsv,
  endSessionNow,
  getCells,
  getParticipants,
  getSecretShopItems,
  getSessionParticipants,
  getSessionResultsJson,
  getSessions,
  manualAccrual,
  setSessionParticipants,
  setSessionStatus,
  updateCell,
  updateSessionSchedule,
} from "../services/api";
import { useAuthStore } from "../store/authStore";

type Participant = { id: number; email: string; balance: number; sessions_joined: number };
type Cell = {
  id: number;
  cell_index: number;
  title: string;
  description: string;
  reward_name: string;
  image_url: string | null;
  price_points: number;
  stock: number;
  status: string;
};

function isoToLocalInput(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (x: number) => `${x}`.padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function localInputToIso(value: string): string | undefined {
  if (!value.trim()) return undefined;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString();
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Не удалось прочитать файл"));
    reader.readAsDataURL(file);
  });
}

export default function AdminPage() {
  const token = useAuthStore((s) => s.accessToken);

  const [sessions, setSessions] = useState<AdminSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [cells, setCells] = useState<Cell[]>([]);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [assignedPlayerIds, setAssignedPlayerIds] = useState<number[]>([]);
  const [resultsPreview, setResultsPreview] = useState<
    Array<{ user_id: number; identifier: string; balance: number; moves_count: number; inventory_count: number; position: number }>
  >([]);
  const [shopItems, setShopItems] = useState<Array<{ id: number; name: string; price_points: number; stock: number; is_active: number }>>([]);

  const [sessionName, setSessionName] = useState("Апрельская кампания");
  const [rollStart, setRollStart] = useState("09:00");
  const [rollEnd, setRollEnd] = useState("21:00");
  const [boardSize, setBoardSize] = useState(40);
  const [maxRollsPerWindow, setMaxRollsPerWindow] = useState(1);
  const [createStartsAt, setCreateStartsAt] = useState("");
  const [createEndsAt, setCreateEndsAt] = useState("");

  const [scheduleStartsAt, setScheduleStartsAt] = useState("");
  const [scheduleEndsAt, setScheduleEndsAt] = useState("");
  const [scheduleRollStart, setScheduleRollStart] = useState("09:00");
  const [scheduleRollEnd, setScheduleRollEnd] = useState("21:00");
  const [scheduleBoardSize, setScheduleBoardSize] = useState(40);
  const [scheduleMaxRolls, setScheduleMaxRolls] = useState(1);

  const [cellIndex, setCellIndex] = useState(0);
  const [cellTitle, setCellTitle] = useState("Точка продаж");
  const [cellDescription, setCellDescription] = useState("");
  const [cellReward, setCellReward] = useState("Брендированный набор");
  const [cellImageUrl, setCellImageUrl] = useState("");
  const [cellPrice, setCellPrice] = useState(50);
  const [cellStock, setCellStock] = useState(10);

  const [editingCellId, setEditingCellId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editReward, setEditReward] = useState("");
  const [editImageUrl, setEditImageUrl] = useState("");
  const [editPrice, setEditPrice] = useState(0);
  const [editStock, setEditStock] = useState(0);

  const [accrualPlayerId, setAccrualPlayerId] = useState(0);
  const [accrualPoints, setAccrualPoints] = useState(100);
  const [accrualReason, setAccrualReason] = useState("План продаж за месяц");

  const [shopName, setShopName] = useState("Кофейный сертификат");
  const [shopPrice, setShopPrice] = useState(20);
  const [shopStock, setShopStock] = useState(100);

  const [ok, setOk] = useState("");
  const [error, setError] = useState("");

  const activeSession = useMemo(() => sessions.find((s) => s.status === "active") ?? null, [sessions]);
  const selectedSession = useMemo(() => sessions.find((s) => s.id === selectedSessionId) ?? null, [sessions, selectedSessionId]);

  const loadBase = async () => {
    if (!token) return;
    const [ss, ps, shop] = await Promise.all([getSessions(token), getParticipants(token), getSecretShopItems(token)]);
    setSessions(ss);
    setParticipants(ps);
    setShopItems(shop);
    setSelectedSessionId((prev) => {
      if (prev && ss.some((x) => x.id === prev)) return prev;
      return ss[0]?.id ?? null;
    });
  };

  const loadSessionDetails = async (sessionId: number) => {
    if (!token) return;
    const [cc, assigned] = await Promise.all([getCells(token, sessionId), getSessionParticipants(token, sessionId)]);
    setCells(cc);
    setAssignedPlayerIds(assigned.items.map((x) => x.user_id));
  };

  useEffect(() => {
    loadBase().catch((e) => setError(e instanceof Error ? e.message : "Ошибка загрузки"));
  }, [token]);

  useEffect(() => {
    if (!selectedSessionId || !token) {
      setCells([]);
      setAssignedPlayerIds([]);
      setResultsPreview([]);
      return;
    }
    loadSessionDetails(selectedSessionId).catch((e) => setError(e instanceof Error ? e.message : "Ошибка загрузки сессии"));
  }, [selectedSessionId, token]);

  useEffect(() => {
    if (!selectedSession) return;
    setScheduleStartsAt(isoToLocalInput(selectedSession.starts_at));
    setScheduleEndsAt(isoToLocalInput(selectedSession.ends_at));
    setScheduleMaxRolls(selectedSession.max_rolls_per_window);
    setScheduleBoardSize(selectedSession.board_size);
    const firstWindow = selectedSession.roll_window_config[0];
    setScheduleRollStart(firstWindow?.start ?? "09:00");
    setScheduleRollEnd(firstWindow?.end ?? "21:00");
  }, [selectedSession]);

  const onCreateSession = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError("");
    setOk("");
    try {
      const created = await createSession(token, {
        name: sessionName,
        board_size: boardSize,
        max_rolls_per_window: maxRollsPerWindow,
        starts_at: localInputToIso(createStartsAt),
        ends_at: localInputToIso(createEndsAt),
        roll_window_config: [{ days: [0, 1, 2, 3, 4, 5, 6], start: rollStart, end: rollEnd }],
      });
      setSelectedSessionId(created.session.id);
      setOk("Сессия создана");
      await loadBase();
      await loadSessionDetails(created.session.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания сессии");
    }
  };

  const onActivateSession = async () => {
    if (!token || !selectedSessionId) return;
    setError("");
    try {
      if (activeSession && activeSession.id !== selectedSessionId) {
        await setSessionStatus(token, activeSession.id, "closed");
      }
      await setSessionStatus(token, selectedSessionId, "active");
      setOk("Сессия активирована");
      await loadBase();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка активации");
    }
  };

  const onEndSessionNow = async () => {
    if (!token || !selectedSessionId) return;
    setError("");
    try {
      await endSessionNow(token, selectedSessionId);
      setOk("Сессия завершена вручную");
      await loadBase();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка завершения сессии");
    }
  };

  const onSaveSchedule = async (e: FormEvent) => {
    e.preventDefault();
    if (!token || !selectedSessionId) return;
    setError("");
    try {
      await updateSessionSchedule(token, selectedSessionId, {
        starts_at: localInputToIso(scheduleStartsAt),
        ends_at: localInputToIso(scheduleEndsAt),
        board_size: scheduleBoardSize,
        max_rolls_per_window: scheduleMaxRolls,
        roll_window_config: [{ days: [0, 1, 2, 3, 4, 5, 6], start: scheduleRollStart, end: scheduleRollEnd }],
      });
      setOk("Расписание сессии сохранено");
      await loadBase();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка обновления расписания");
    }
  };

  const toggleAssigned = (playerId: number) => {
    setAssignedPlayerIds((prev) => (prev.includes(playerId) ? prev.filter((x) => x !== playerId) : [...prev, playerId]));
  };

  const onSaveParticipants = async () => {
    if (!token || !selectedSessionId) return;
    setError("");
    try {
      await setSessionParticipants(token, selectedSessionId, assignedPlayerIds);
      setOk("Назначение игроков сохранено");
      await loadSessionDetails(selectedSessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка назначения игроков");
    }
  };

  const onExportJson = async () => {
    if (!token || !selectedSessionId) return;
    setError("");
    try {
      const data = await getSessionResultsJson(token, selectedSessionId);
      setResultsPreview(data.results);
      setOk(`JSON выгружен: ${data.results.length} строк`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка выгрузки JSON");
    }
  };

  const onExportCsv = async () => {
    if (!token || !selectedSessionId) return;
    setError("");
    try {
      const blob = await downloadSessionResultsCsv(token, selectedSessionId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `session_${selectedSessionId}_results.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setOk("CSV выгружен");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка выгрузки CSV");
    }
  };

  const onPickCellImage = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const dataUrl = await readFileAsDataUrl(file);
      setCellImageUrl(dataUrl);
      setOk("Картинка клетки загружена");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки картинки клетки");
    }
  };

  const onPickEditCellImage = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const dataUrl = await readFileAsDataUrl(file);
      setEditImageUrl(dataUrl);
      setOk("Картинка для редактирования загружена");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка загрузки картинки");
    }
  };

  const onCreateCell = async (e: FormEvent) => {
    e.preventDefault();
    if (!token || !selectedSessionId) return;
    setError("");
    try {
      await createCell(token, selectedSessionId, {
        cell_index: cellIndex,
        title: cellTitle,
        description: cellDescription,
        reward_name: cellReward,
        image_url: cellImageUrl || undefined,
        price_points: cellPrice,
        stock: cellStock,
      });
      setOk("Клетка добавлена");
      setCellDescription("");
      await loadSessionDetails(selectedSessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка создания клетки");
    }
  };

  const startEditCell = (cell: Cell) => {
    setEditingCellId(cell.id);
    setEditTitle(cell.title);
    setEditDescription(cell.description || "");
    setEditReward(cell.reward_name);
    setEditImageUrl(cell.image_url || "");
    setEditPrice(cell.price_points);
    setEditStock(cell.stock);
  };

  const onSaveCellEdit = async () => {
    if (!token || !editingCellId || !selectedSessionId) return;
    setError("");
    try {
      await updateCell(token, editingCellId, {
        title: editTitle,
        description: editDescription,
        reward_name: editReward,
        image_url: editImageUrl,
        price_points: editPrice,
        stock: editStock,
      });
      setEditingCellId(null);
      setOk("Клетка обновлена");
      await loadSessionDetails(selectedSessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка обновления клетки");
    }
  };

  const onAccrual = async (e: FormEvent) => {
    e.preventDefault();
    if (!token || !accrualPlayerId) return;
    setError("");
    try {
      await manualAccrual(token, accrualPlayerId, { points: accrualPoints, reason: accrualReason });
      setOk("Баллы начислены");
      await loadBase();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка начисления");
    }
  };

  const onCreateShopItem = async (e: FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError("");
    try {
      await createSecretShopItem(token, { name: shopName, price_points: shopPrice, stock: shopStock });
      setOk("Позиция добавлена в секретный магазин");
      await loadBase();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка добавления в магазин");
    }
  };

  return (
    <section className="stack-lg">
      <div className="panel panel-wide">
        <h2>Админ-панель</h2>
        <p className="muted">Управление сессиями, участниками, расписанием, полем, начислениями и каталогом наград.</p>
        {ok && <p className="ok">{ok}</p>}
        {error && <p className="error">{error}</p>}
      </div>

      <div className="panel">
        <h3>1. Создать игровую сессию</h3>
        <form className="actions" onSubmit={onCreateSession}>
          <input value={sessionName} onChange={(e) => setSessionName(e.target.value)} placeholder="Название сессии" />
          <input type="datetime-local" value={createStartsAt} onChange={(e) => setCreateStartsAt(e.target.value)} />
          <input type="datetime-local" value={createEndsAt} onChange={(e) => setCreateEndsAt(e.target.value)} />
          <input value={rollStart} onChange={(e) => setRollStart(e.target.value)} placeholder="Начало окна HH:MM" />
          <input value={rollEnd} onChange={(e) => setRollEnd(e.target.value)} placeholder="Конец окна HH:MM" />
          <input type="number" min={4} max={40} value={boardSize} onChange={(e) => setBoardSize(Number(e.target.value))} placeholder="Размер поля" />
          <input type="number" min={1} max={20} value={maxRollsPerWindow} onChange={(e) => setMaxRollsPerWindow(Number(e.target.value))} />
          <button type="submit">Создать</button>
        </form>
      </div>

      <div className="panel">
        <h3>2. Выбрать сессию и управление статусом</h3>
        <div className="actions">
          <select value={selectedSessionId ?? ""} onChange={(e) => setSelectedSessionId(Number(e.target.value))}>
            {sessions.map((s) => (
              <option key={s.id} value={s.id}>
                #{s.id} {s.name} ({s.status}, поле: {s.board_size}, ходов/окно: {s.max_rolls_per_window})
              </option>
            ))}
          </select>
          <button type="button" onClick={onActivateSession}>Сделать активной</button>
          <button type="button" className="secondary" onClick={onEndSessionNow}>Завершить вручную</button>
        </div>
      </div>

      <div className="panel">
        <h3>3. Расписание выбранной сессии</h3>
        <form className="actions" onSubmit={onSaveSchedule}>
          <input type="datetime-local" value={scheduleStartsAt} onChange={(e) => setScheduleStartsAt(e.target.value)} />
          <input type="datetime-local" value={scheduleEndsAt} onChange={(e) => setScheduleEndsAt(e.target.value)} />
          <input value={scheduleRollStart} onChange={(e) => setScheduleRollStart(e.target.value)} placeholder="Начало окна HH:MM" />
          <input value={scheduleRollEnd} onChange={(e) => setScheduleRollEnd(e.target.value)} placeholder="Конец окна HH:MM" />
          <input type="number" min={4} max={40} value={scheduleBoardSize} onChange={(e) => setScheduleBoardSize(Number(e.target.value))} placeholder="Размер поля" />
          <input type="number" min={1} max={20} value={scheduleMaxRolls} onChange={(e) => setScheduleMaxRolls(Number(e.target.value))} />
          <button type="submit">Сохранить расписание</button>
        </form>
      </div>

      <div className="panel">
        <h3>4. Назначение игроков на сессию</h3>
        <div className="list">
          {participants.map((p) => (
            <label key={p.id} className="item" style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="checkbox" checked={assignedPlayerIds.includes(p.id)} onChange={() => toggleAssigned(p.id)} />
              <span>
                {p.email} (баланс: {p.balance}, сессий: {p.sessions_joined})
              </span>
            </label>
          ))}
        </div>
        <div className="actions" style={{ marginTop: 12 }}>
          <button type="button" onClick={onSaveParticipants}>Сохранить назначение</button>
          <button type="button" className="secondary" onClick={() => setAssignedPlayerIds([])}>Очистить выбор</button>
        </div>
      </div>

      <div className="panel">
        <h3>5. Выгрузка результатов сессии</h3>
        <div className="actions">
          <button type="button" onClick={onExportJson}>Выгрузить JSON</button>
          <button type="button" className="secondary" onClick={onExportCsv}>Скачать CSV</button>
        </div>
        {resultsPreview.length > 0 && (
          <div className="list" style={{ marginTop: 12 }}>
            {resultsPreview.map((r) => (
              <div key={r.user_id} className="item">
                <strong>{r.identifier}</strong>
                <div>Баланс: {r.balance}</div>
                <div>Ходы: {r.moves_count}</div>
                <div>Инвентарь: {r.inventory_count}</div>
                <div>Позиция: {r.position}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="panel">
        <h3>6. Добавить клетку на доску</h3>
        <form className="actions" onSubmit={onCreateCell}>
          <input type="number" value={cellIndex} onChange={(e) => setCellIndex(Number(e.target.value))} placeholder="Индекс" />
          <input value={cellTitle} onChange={(e) => setCellTitle(e.target.value)} placeholder="Название клетки" />
          <input value={cellReward} onChange={(e) => setCellReward(e.target.value)} placeholder="Награда" />
          <input value={cellDescription} onChange={(e) => setCellDescription(e.target.value)} placeholder="Описание клетки" />
          <input value={cellImageUrl} onChange={(e) => setCellImageUrl(e.target.value)} placeholder="URL/Data URL картинки (опционально)" />
          <input type="file" accept="image/*" onChange={onPickCellImage} />
          <input type="number" value={cellPrice} onChange={(e) => setCellPrice(Number(e.target.value))} placeholder="Цена" />
          <input type="number" value={cellStock} onChange={(e) => setCellStock(Number(e.target.value))} placeholder="Остаток" />
          <button type="submit">Добавить клетку</button>
        </form>
      </div>

      <div className="panel">
        <h3>7. Клетки текущей сессии</h3>
        <div className="grid-board">
          {cells.map((cell) => (
            <div key={cell.id} className="cell">
              <div className="cell-head">
                <span>#{cell.cell_index}</span>
                <span className={`badge ${cell.status === "active" ? "reward_points" : "penalty_points"}`}>
                  {cell.status === "active" ? "Активна" : "Пусто"}
                </span>
              </div>
              <strong>{cell.title}</strong>
              <div>{cell.reward_name}</div>
              <div>Цена: {cell.price_points}</div>
              <div>Остаток: {cell.stock}</div>
              {cell.description && <div className="muted">{cell.description}</div>}
              {cell.image_url && <img src={cell.image_url} alt={cell.title} style={{ width: "100%", maxHeight: 100, objectFit: "contain", marginTop: 6 }} />}
              <button type="button" style={{ marginTop: 8 }} onClick={() => startEditCell(cell)}>
                Редактировать
              </button>
            </div>
          ))}
        </div>
      </div>

      {editingCellId && (
        <div className="panel">
          <h3>Редактирование клетки #{editingCellId}</h3>
          <div className="actions">
            <input value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="Название" />
            <input value={editReward} onChange={(e) => setEditReward(e.target.value)} placeholder="Награда" />
            <input value={editDescription} onChange={(e) => setEditDescription(e.target.value)} placeholder="Описание" />
            <input value={editImageUrl} onChange={(e) => setEditImageUrl(e.target.value)} placeholder="URL/Data URL картинки" />
            <input type="file" accept="image/*" onChange={onPickEditCellImage} />
            <input type="number" value={editPrice} onChange={(e) => setEditPrice(Number(e.target.value))} placeholder="Цена" />
            <input type="number" value={editStock} onChange={(e) => setEditStock(Number(e.target.value))} placeholder="Остаток" />
            <button type="button" onClick={onSaveCellEdit}>Сохранить клетку</button>
            <button type="button" className="secondary" onClick={() => setEditingCellId(null)}>Отмена</button>
          </div>
        </div>
      )}

      <div className="panel">
        <h3>8. Ручное начисление баллов</h3>
        <form className="actions" onSubmit={onAccrual}>
          <select value={accrualPlayerId} onChange={(e) => setAccrualPlayerId(Number(e.target.value))}>
            <option value={0}>Выберите игрока</option>
            {participants.map((p) => (
              <option key={p.id} value={p.id}>
                {p.email} (баланс: {p.balance})
              </option>
            ))}
          </select>
          <input type="number" value={accrualPoints} onChange={(e) => setAccrualPoints(Number(e.target.value))} placeholder="Баллы" />
          <input value={accrualReason} onChange={(e) => setAccrualReason(e.target.value)} placeholder="Причина" />
          <button type="submit">Начислить</button>
        </form>
      </div>

      <div className="panel">
        <h3>9. Секретный магазин</h3>
        <form className="actions" onSubmit={onCreateShopItem}>
          <input value={shopName} onChange={(e) => setShopName(e.target.value)} placeholder="Название позиции" />
          <input type="number" value={shopPrice} onChange={(e) => setShopPrice(Number(e.target.value))} placeholder="Цена" />
          <input type="number" value={shopStock} onChange={(e) => setShopStock(Number(e.target.value))} placeholder="Остаток" />
          <button type="submit">Добавить в магазин</button>
        </form>
        <div className="list" style={{ marginTop: 12 }}>
          {shopItems.map((item) => (
            <div key={item.id} className="item">
              <strong>{item.name}</strong>
              <div>Цена: {item.price_points}</div>
              <div>Остаток: {item.stock}</div>
              <div>Активно: {item.is_active ? "да" : "нет"}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
