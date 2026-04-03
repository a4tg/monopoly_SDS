import type { CSSProperties } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  buyOrSkipCell,
  buySecretShop,
  GameState,
  getGameState,
  getUnreadNotifications,
  markNotificationsRead,
  roll,
} from "../services/api";
import { useAuthStore } from "../store/authStore";

type CubeRotation = { x: number; y: number };
type Point = { x: number; y: number };
type PerimeterSlot = { row: number; col: number; slot: number; className: string };

const FACE_TO_ROTATION: Record<number, CubeRotation> = {
  1: { x: 0, y: 0 },
  2: { x: 90, y: 0 },
  3: { x: 0, y: -90 },
  4: { x: 0, y: 90 },
  5: { x: -90, y: 0 },
  6: { x: 0, y: 180 },
};

const FACE_PIPS: Record<number, number[]> = {
  1: [5],
  2: [1, 9],
  3: [1, 5, 9],
  4: [1, 3, 7, 9],
  5: [1, 3, 5, 7, 9],
  6: [1, 3, 4, 6, 7, 9],
};

const tokenSrcCache = new Map<string, string>();
const assetBasePath = import.meta.env.BASE_URL || "/";

function assetUrl(path: string): string {
  const normalized = path.replace(/^\/+/, "");
  const base = assetBasePath.endsWith("/") ? assetBasePath : `${assetBasePath}/`;
  return `${base}${normalized}`;
}

function getSlotClass(row: number, col: number, edgeSpan: number): string {
  const isCorner = (row === 0 || row === edgeSpan) && (col === 0 || col === edgeSpan);
  if (isCorner) return "corner";
  if (row === edgeSpan) return "edge-bottom";
  if (col === 0) return "edge-left";
  if (row === 0) return "edge-top";
  return "edge-right";
}

function buildPerimeterSlots(totalSlots: number): { slots: PerimeterSlot[]; gridSize: number } {
  const count = Math.max(1, totalSlots);
  const edgeSpan = Math.max(1, Math.ceil(count / 4));
  const full: Array<{ row: number; col: number; className: string }> = [];

  full.push({ row: edgeSpan, col: edgeSpan, className: "corner" });
  for (let i = 1; i < edgeSpan; i += 1) {
    const row = edgeSpan;
    const col = edgeSpan - i;
    full.push({ row, col, className: getSlotClass(row, col, edgeSpan) });
  }
  full.push({ row: edgeSpan, col: 0, className: "corner" });
  for (let i = 1; i < edgeSpan; i += 1) {
    const row = edgeSpan - i;
    const col = 0;
    full.push({ row, col, className: getSlotClass(row, col, edgeSpan) });
  }
  full.push({ row: 0, col: 0, className: "corner" });
  for (let i = 1; i < edgeSpan; i += 1) {
    const row = 0;
    const col = i;
    full.push({ row, col, className: getSlotClass(row, col, edgeSpan) });
  }
  full.push({ row: 0, col: edgeSpan, className: "corner" });
  for (let i = 1; i < edgeSpan; i += 1) {
    const row = i;
    const col = edgeSpan;
    full.push({ row, col, className: getSlotClass(row, col, edgeSpan) });
  }

  const fullLength = full.length;
  const slots: PerimeterSlot[] = [];
  for (let i = 0; i < count; i += 1) {
    const idx = Math.floor((i * fullLength) / count);
    const pos = full[idx] ?? full[0];
    slots.push({
      row: pos.row,
      col: pos.col,
      slot: i,
      className: pos.className,
    });
  }

  return { slots, gridSize: edgeSpan + 1 };
}

function movementPath(from: number, to: number, total: number): number[] {
  if (total <= 0) return [];
  if (from === to) return [to];
  const steps: number[] = [];
  let current = from;
  while (current !== to) {
    current = (current + 1) % total;
    steps.push(current);
    if (steps.length > total * 2) break;
  }
  return steps;
}

function CubeFace({ face }: { face: number }) {
  const active = new Set(FACE_PIPS[face]);
  return (
    <div className="pip-grid">
      {Array.from({ length: 9 }, (_, idx) => {
        const pos = idx + 1;
        return <span key={pos} className={`pip ${active.has(pos) ? "on" : ""}`} />;
      })}
    </div>
  );
}

function Token({
  tokenAsset,
  ghost = false,
  variant = "cell",
}: {
  tokenAsset: string;
  ghost?: boolean;
  variant?: "cell" | "preview";
}) {
  const [imgSrc, setImgSrc] = useState(assetUrl(`assets/tokens/${tokenAsset}`));
  const [imgBroken, setImgBroken] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const source = assetUrl(`assets/tokens/${tokenAsset}`);
    setImgBroken(false);

    const cached = tokenSrcCache.get(source);
    if (cached) {
      setImgSrc(cached);
      return () => {
        cancelled = true;
      };
    }

    setImgSrc(source);

    const img = new Image();
    img.onload = () => {
      if (cancelled) return;
      try {
        const w = img.naturalWidth;
        const h = img.naturalHeight;
        if (!w || !h) {
          tokenSrcCache.set(source, source);
          setImgSrc(source);
          return;
        }

        const canvas = document.createElement("canvas");
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          tokenSrcCache.set(source, source);
          setImgSrc(source);
          return;
        }

        ctx.drawImage(img, 0, 0);
        const data = ctx.getImageData(0, 0, w, h).data;
        let minX = w;
        let minY = h;
        let maxX = -1;
        let maxY = -1;

        for (let y = 0; y < h; y++) {
          for (let x = 0; x < w; x++) {
            const alpha = data[(y * w + x) * 4 + 3];
            if (alpha > 12) {
              if (x < minX) minX = x;
              if (y < minY) minY = y;
              if (x > maxX) maxX = x;
              if (y > maxY) maxY = y;
            }
          }
        }

        if (maxX < minX || maxY < minY) {
          tokenSrcCache.set(source, source);
          setImgSrc(source);
          return;
        }

        const pad = 6;
        const cropX = Math.max(0, minX - pad);
        const cropY = Math.max(0, minY - pad);
        const cropW = Math.min(w - cropX, maxX - minX + 1 + pad * 2);
        const cropH = Math.min(h - cropY, maxY - minY + 1 + pad * 2);

        const out = document.createElement("canvas");
        out.width = cropW;
        out.height = cropH;
        const outCtx = out.getContext("2d");
        if (!outCtx) {
          tokenSrcCache.set(source, source);
          setImgSrc(source);
          return;
        }

        outCtx.drawImage(canvas, cropX, cropY, cropW, cropH, 0, 0, cropW, cropH);
        const trimmed = out.toDataURL("image/png");
        tokenSrcCache.set(source, trimmed);
        setImgSrc(trimmed);
      } catch {
        tokenSrcCache.set(source, source);
        setImgSrc(source);
      }
    };
    img.onerror = () => {
      if (cancelled) return;
      setImgBroken(true);
      setImgSrc(source);
    };
    img.src = source;

    return () => {
      cancelled = true;
    };
  }, [tokenAsset]);

  return (
    <div className={`token ${variant === "preview" ? "preview" : ""} ${ghost ? "ghost" : ""}`}>
      {imgBroken ? (
        <span className="token-fallback">F</span>
      ) : (
        <img src={imgSrc} alt="Player token" onError={() => setImgBroken(true)} />
      )}
    </div>
  );
}

export default function GamePage() {
  const token = useAuthStore((s) => s.accessToken);
  const logout = useAuthStore((s) => s.logout);

  const [state, setState] = useState<GameState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastCellId, setLastCellId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [lastRoll, setLastRoll] = useState<number | null>(null);
  const [trail, setTrail] = useState<number[]>([]);
  const [notifications, setNotifications] = useState<Array<{ id: number; title: string; body: string }>>([]);
  const [isRollingCube, setIsRollingCube] = useState(false);
  const [cubeRotation, setCubeRotation] = useState<CubeRotation>({ x: -24, y: 30 });
  const [animatedPosition, setAnimatedPosition] = useState<number | null>(null);
  const [pendingPosition, setPendingPosition] = useState<number | null>(null);
  const [isAnimatingMove, setIsAnimatingMove] = useState(false);
  const [movingTokenPos, setMovingTokenPos] = useState<Point | null>(null);
  const [selectedCellSlot, setSelectedCellSlot] = useState<number | null>(null);
  const [isBoardLogoMissing, setIsBoardLogoMissing] = useState(false);
  const timeoutsRef = useRef<number[]>([]);
  const boardRef = useRef<HTMLDivElement | null>(null);
  const cellRefs = useRef<Record<number, HTMLDivElement | null>>({});

  const clearMotionTimers = () => {
    for (const timer of timeoutsRef.current) {
      window.clearTimeout(timer);
    }
    timeoutsRef.current = [];
  };

  const getCellCenter = (cellIndex: number): Point | null => {
    const board = boardRef.current;
    const cell = cellRefs.current[cellIndex];
    if (!board || !cell) return null;
    const boardRect = board.getBoundingClientRect();
    const cellRect = cell.getBoundingClientRect();
    return {
      x: cellRect.left - boardRect.left + cellRect.width / 2,
      y: cellRect.top - boardRect.top + cellRect.height / 2,
    };
  };

  const load = async () => {
    if (!token) return;
    const data = await getGameState(token);
    setState(data);
  };

  useEffect(() => {
    return () => clearMotionTimers();
  }, []);

  useEffect(() => {
    const boot = async () => {
      if (!token) return;
      setIsLoading(true);
      try {
        await load();
        const unread = await getUnreadNotifications(token);
        setNotifications(unread.items.map((i) => ({ id: i.id, title: i.title, body: i.body })));
        if (unread.items.length > 0) {
          await markNotificationsRead(token);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Ошибка загрузки";
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

  const shownPosition = useMemo(() => {
    if (!state) return 0;
    return animatedPosition ?? pendingPosition ?? state.player.position;
  }, [animatedPosition, pendingPosition, state]);

  const orderedCells = useMemo(() => {
    if (!state) return [];
    return [...state.cells].sort((a, b) => a.cell_index - b.cell_index);
  }, [state]);

  const boardSize = state?.session.board_size ?? 40;
  const cellCount = orderedCells.length;
  const visibleBoardSize = Math.max(1, cellCount || boardSize);
  const { slots: visibleSlots, gridSize: boardGridSize } = useMemo(
    () => buildPerimeterSlots(visibleBoardSize),
    [visibleBoardSize],
  );

  const cellsByIndex = useMemo(() => {
    const map = new Map<number, (typeof orderedCells)[number]>();
    for (const c of orderedCells) {
      map.set(c.cell_index, c);
    }
    return map;
  }, [orderedCells]);

  const currentCell = useMemo(() => {
    return cellsByIndex.get(shownPosition) ?? null;
  }, [cellsByIndex, shownPosition]);

  const selectedCell = useMemo(() => {
    if (selectedCellSlot === null) return null;
    return cellsByIndex.get(selectedCellSlot) ?? null;
  }, [cellsByIndex, selectedCellSlot]);

  const animateTokenPath = (path: number[], from: number) => {
    const STEP_MS = 260;
    const start = getCellCenter(from);
    if (start) setMovingTokenPos(start);
    setIsAnimatingMove(true);

    path.forEach((pos, idx) => {
      const timer = window.setTimeout(() => {
        setAnimatedPosition(pos);
        const center = getCellCenter(pos);
        if (center) setMovingTokenPos(center);
      }, STEP_MS * (idx + 1));
      timeoutsRef.current.push(timer);
    });

    const finishTimer = window.setTimeout(() => {
      setIsAnimatingMove(false);
      setMovingTokenPos(null);
      setAnimatedPosition(null);
      setTrail([]);
    }, STEP_MS * (path.length + 1) + 120);
    timeoutsRef.current.push(finishTimer);
  };

  const onRoll = async () => {
    if (!token || !state) return;
    setError("");
    clearMotionTimers();
    try {
      setIsRollingCube(true);
      setCubeRotation((prev) => ({
        x: prev.x + 720 + Math.floor(Math.random() * 180),
        y: prev.y + 720 + Math.floor(Math.random() * 180),
      }));

      const result = await roll(token);
      const landed = result.landed_cell as { id: number; title: string; stock: number } | null;
      const path = movementPath(result.from_position, result.to_position, visibleBoardSize);

      setLastCellId(landed?.id ?? null);
      setLastRoll(result.rolled);
      setTrail(path);
      setAnimatedPosition(result.from_position);
      setPendingPosition(result.to_position);
      setMessage(`Бросок: ${result.rolled}. Позиция ${result.from_position + 1} -> ${result.to_position + 1}.`);
      setState((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          player: {
            ...prev.player,
            position: result.to_position,
          },
        };
      });

      // Wait one frame to ensure refs are ready for positioning.
      const raf = window.requestAnimationFrame(() => {
        animateTokenPath(path, result.from_position);
      });
      timeoutsRef.current.push(raf as unknown as number);

      const settle = FACE_TO_ROTATION[result.rolled] ?? FACE_TO_ROTATION[1];
      const settleTimer = window.setTimeout(() => {
        setCubeRotation((prev) => ({
          x: prev.x + 360 + settle.x,
          y: prev.y + 360 + settle.y,
        }));
        setIsRollingCube(false);
      }, 520);
      timeoutsRef.current.push(settleTimer);

      await load();
      setPendingPosition(null);
    } catch (err) {
      setIsRollingCube(false);
      setIsAnimatingMove(false);
      setMovingTokenPos(null);
      setTrail([]);
      setAnimatedPosition(null);
      setPendingPosition(null);
      setError(err instanceof Error ? err.message : "Ошибка броска");
    }
  };

  const onBuyOrSkip = async (action: "buy" | "skip") => {
    if (!token || !lastCellId) return;
    setError("");
    try {
      const result = await buyOrSkipCell(token, lastCellId, action);
      setMessage(action === "buy" ? "Награда куплена." : "Вы пропустили клетку.");
      if (result.balance !== undefined) {
        setMessage(`${action === "buy" ? "Награда куплена" : "Пропуск"}. Баланс: ${result.balance}`);
      }
      setLastCellId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка действия на клетке");
    }
  };

  const onSecretShopBuy = async (itemId: number) => {
    if (!token) return;
    setError("");
    try {
      const result = await buySecretShop(token, itemId);
      setMessage(`Покупка в секретном магазине. Баланс: ${result.balance}`);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка покупки в секретном магазине");
    }
  };

  if (isLoading) {
    return <section className="panel">Загрузка...</section>;
  }
  if (!state) {
    return (
      <section className="panel">
        <h3>Не удалось загрузить игровое состояние</h3>
        <p className="error">{error || "Проверьте активную сессию и авторизацию."}</p>
      </section>
    );
  }

  const cubeStyle = {
    "--cube-x": `${cubeRotation.x}deg`,
    "--cube-y": `${cubeRotation.y}deg`,
  } as CSSProperties;
  const boardStyle = {
    "--board-grid": `${boardGridSize}`,
  } as CSSProperties;

  return (
    <section className="stack-lg">
      {notifications.length > 0 && (
        <div className="panel">
          <h3>Новые уведомления</h3>
          {notifications.map((n) => (
            <div key={n.id} className="item">
              <strong>{n.title}</strong>
              <div>{n.body}</div>
            </div>
          ))}
        </div>
      )}

      <div className="panel panel-wide">
        <h2>Игровой стол</h2>
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-label">Сессия</div>
            <div className="kpi-value">{state.session.name}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Позиция</div>
            <div className="kpi-value">{shownPosition + 1}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Баланс</div>
            <div className="kpi-value">{state.player.balance}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Секретный магазин</div>
            <div className="kpi-value">
              {state.player.monthly_secret_shop_purchases}/{state.player.secret_shop_monthly_limit}
            </div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Ходы в текущем окне</div>
            <div className="kpi-value">
              {state.player.rolls_in_current_window}/{state.session.max_rolls_per_window}
            </div>
          </div>
        </div>

        <div className="asset-row">
          <div className="asset-slot">
            <div className="asset-label">Фигурка игрока</div>
            <p className="muted">
              Используется файл: <code>{state.player.token_asset}</code>
            </p>
            <Token tokenAsset={state.player.token_asset} variant="preview" />
          </div>
        </div>

        <div className="actions">
          {lastCellId && (
            <>
              <button type="button" onClick={() => onBuyOrSkip("buy")}>Купить награду</button>
              <button type="button" className="secondary" onClick={() => onBuyOrSkip("skip")}>Пропустить</button>
            </>
          )}
        </div>

        {currentCell && (
          <p className="muted">
            Текущая клетка: <strong>{currentCell.title}</strong> | Награда: {currentCell.reward_name} | Цена:{" "}
            {currentCell.price_points} | Остаток: {currentCell.stock}
          </p>
        )}
        {message && <p className="ok">{message}</p>}
        {error && <p className="error">{error}</p>}
      </div>

      <div className="panel">
        <h3>Клетки доски</h3>
        <div className="board-wrap" ref={boardRef}>
          {isAnimatingMove && movingTokenPos && (
            <div className="moving-token" style={{ left: movingTokenPos.x, top: movingTokenPos.y }}>
              <Token tokenAsset={state.player.token_asset} />
            </div>
          )}
          <div className="grid-board monopoly-board" style={boardStyle}>
            <div className="board-center">
              <div className="board-center-inner">
                <img
                  className="board-logo-image"
                  src={assetUrl("assets/logo/company-logo.png")}
                  alt="Логотип компании"
                  style={{ display: isBoardLogoMissing ? "none" : "block" }}
                  onLoad={() => setIsBoardLogoMissing(false)}
                  onError={() => {
                    setIsBoardLogoMissing(true);
                  }}
                />
                {isBoardLogoMissing && (
                  <>
                    <div className="board-logo-placeholder">ЛОГО КОМПАНИИ</div>
                    <p className="muted">Поместите логотип в `frontend/public/assets/logo/company-logo.png`</p>
                  </>
                )}
              </div>
            </div>
            {visibleSlots.map(({ row, col, slot, className }) => {
              const cell = cellsByIndex.get(slot) ?? null;
              const isCurrent = slot === shownPosition;
              const trailIdx = trail.indexOf(slot);
              const isTrail = trailIdx >= 0 && !isCurrent;
              return (
                <div
                  key={`slot-${slot}`}
                  ref={(el) => {
                    if (cell) {
                      cellRefs.current[slot] = el;
                    } else {
                      delete cellRefs.current[slot];
                    }
                  }}
                  className={`cell monopoly-cell ${className} ${cell ? "" : "empty"} ${isCurrent ? "active" : ""} ${isTrail ? "trail" : ""}`}
                  onClick={() => {
                    if (cell) setSelectedCellSlot(slot);
                  }}
                  style={{
                    gridRow: row + 1,
                    gridColumn: col + 1,
                    ...(isTrail ? { animationDelay: `${trailIdx * 90}ms` } : {}),
                  }}
                >
                  <div className="cell-content">
                    {cell ? (
                      <>
                        <div className="cell-head">
                          <span>#{cell.cell_index + 1}</span>
                          <span className={`badge ${cell.status === "active" ? "reward_points" : "penalty_points"}`}>
                            {cell.status === "active" ? "Активна" : "Пусто"}
                          </span>
                        </div>
                        <strong>{cell.title}</strong>
                        <div>{cell.reward_name}</div>
                        {cell.image_url && <img className="cell-thumb" src={cell.image_url} alt={cell.title} />}
                        <div>Цена: {cell.price_points}</div>
                        <div>Остаток: {cell.stock}</div>
                        <div className="token-lane">
                          {isCurrent && (
                            <Token
                              tokenAsset={state.player.token_asset}
                              ghost={isAnimatingMove && Boolean(movingTokenPos)}
                            />
                          )}
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="cell-empty-label">#{slot + 1}</div>
                        <div className="token-lane">
                          {isCurrent && (
                            <Token
                              tokenAsset={state.player.token_asset}
                              ghost={isAnimatingMove && Boolean(movingTokenPos)}
                            />
                          )}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="panel">
        <h3>Секретный магазин</h3>
        <div className="list">
          {state.secret_shop.map((item) => (
            <div key={item.id} className="item">
              <strong>{item.name}</strong>
              <div>Цена: {item.price_points}</div>
              <div>Остаток: {item.stock}</div>
              <button type="button" onClick={() => onSecretShopBuy(item.id)}>Купить</button>
            </div>
          ))}
        </div>
      </div>

      <div className="panel">
        <h3>Инвентарь</h3>
        <div className="list">
          {state.inventory.length === 0 && <p>Инвентарь пока пуст.</p>}
          {state.inventory.map((item) => (
            <div key={item.id} className="item">
              <strong>{item.reward_name}</strong>
              <div>Оплачено: {item.paid_points}</div>
              <div>{item.created_at}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="roll-dock">
        <div className="roll-dock-title">3D-кубик</div>
        <div className="dice-stage">
          <div className={`dice-cube ${isRollingCube ? "rolling" : ""}`} style={cubeStyle}>
            <div className="cube-face face-front"><CubeFace face={1} /></div>
            <div className="cube-face face-back"><CubeFace face={6} /></div>
            <div className="cube-face face-right"><CubeFace face={3} /></div>
            <div className="cube-face face-left"><CubeFace face={4} /></div>
            <div className="cube-face face-top"><CubeFace face={5} /></div>
            <div className="cube-face face-bottom"><CubeFace face={2} /></div>
          </div>
        </div>
        <p className="muted">
          Выпало: <strong>{lastRoll ?? "—"}</strong>
        </p>
        <button type="button" onClick={onRoll}>Бросить кубик</button>
      </div>

      {selectedCell && (
        <div className="modal-overlay" onClick={() => setSelectedCellSlot(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3>
              #{selectedCell.cell_index + 1} {selectedCell.title}
            </h3>
            {selectedCell.image_url && <img className="modal-cell-image" src={selectedCell.image_url} alt={selectedCell.title} />}
            <p>
              <strong>Тип:</strong> {selectedCell.status === "active" ? "Активная клетка" : "Пустая клетка"}
            </p>
            <p>
              <strong>Награда:</strong> {selectedCell.reward_name}
            </p>
            <p>
              <strong>Цена:</strong> {selectedCell.price_points}
            </p>
            <p>
              <strong>Остаток:</strong> {selectedCell.stock}
            </p>
            <p>
              <strong>Описание:</strong> {selectedCell.description || "Описание не задано"}
            </p>
            <div className="actions">
              <button type="button" onClick={() => setSelectedCellSlot(null)}>
                Закрыть
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
