const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
};

export type MeResponse = {
  id: number;
  email: string | null;
  phone: string | null;
  identifier: string;
  token_asset: string;
  role: "admin" | "player";
};

export type NotificationItem = {
  id: number;
  type: string;
  title: string;
  body: string;
  created_at: string;
};

export type GameState = {
  session: {
    id: number;
    name: string;
    board_size: number;
    max_rolls_per_window: number;
    starts_at?: string | null;
    ends_at?: string | null;
    ended_at?: string | null;
    roll_window_config: Array<{ days: number[]; start: string; end: string }>;
  };
  player: {
    id: number;
    email: string;
    token_asset: string;
    position: number;
    balance: number;
    rolls_in_current_window: number;
    monthly_secret_shop_purchases: number;
    secret_shop_monthly_limit: number;
  };
  cells: Array<{
    id: number;
    cell_index: number;
    title: string;
    description: string;
    reward_name: string;
    image_url: string | null;
    price_points: number;
    stock: number;
    status: "active" | "depleted";
  }>;
  inventory: Array<{
    id: number;
    reward_name: string;
    paid_points: number;
    created_at: string;
  }>;
  secret_shop: Array<{
    id: number;
    name: string;
    price_points: number;
    stock: number;
  }>;
};

export type MarketPlayer = {
  id: number;
  identifier: string;
  balance: number;
};

export type MarketInventoryItem = {
  id: number;
  reward_name: string;
  paid_points: number;
  created_at: string;
};

export type MarketOffer = {
  id: number;
  from_user_id: number;
  from_identifier: string;
  to_user_id: number;
  to_identifier: string;
  offer_points: number;
  status: "pending" | "accepted" | "rejected" | "canceled";
  note: string;
  created_at: string;
  responded_at: string | null;
  item: { id: number; reward_name: string } | null;
};

export type AuctionLot = {
  id: number;
  inventory_item_id: number;
  item_name: string;
  seller_user_id: number;
  seller_identifier: string;
  status: "open" | "closed" | "closed_no_winner";
  starts_at: string | null;
  ends_at: string | null;
  closed_at: string | null;
  winner_user_id: number | null;
  winner_identifier: string | null;
  winning_bid_points: number | null;
  top_bid_points: number | null;
  top_bidder_user_id: number | null;
  top_bidder_identifier: string | null;
};

export type MarketActivity = {
  id: number;
  event_type: string;
  title: string;
  body: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type MarketRating = {
  user_id: number;
  identifier: string;
  balance: number;
  inventory_value: number;
  total_score: number;
  rank: number;
};

async function request<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // no-op
    }
    throw new Error(detail);
  }

  return response.json();
}

export function register(payload: { email?: string; phone?: string; password: string; role: "admin" | "player" }) {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(identifier: string, password: string) {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ identifier, password }),
  });
}

export function refresh(refreshToken: string) {
  return request<AuthResponse>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
}

export function me(token: string) {
  return request<MeResponse>("/auth/me", { method: "GET" }, token);
}

export function getUnreadNotifications(token: string) {
  return request<{ items: NotificationItem[] }>("/auth/notifications/unread", { method: "GET" }, token);
}

export function markNotificationsRead(token: string) {
  return request<{ status: string; updated: number }>("/auth/notifications/read-all", { method: "POST" }, token);
}

export function requestPasswordReset(email: string) {
  return request<{ status: string; message: string }>(
    "/auth/password-reset/request",
    {
      method: "POST",
      body: JSON.stringify({ email }),
    },
  );
}

export function confirmPasswordReset(token: string, newPassword: string) {
  return request<{ status: string }>(
    "/auth/password-reset/confirm",
    {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    },
  );
}

export function getGameState(token: string) {
  return request<GameState>("/game/state", { method: "GET" }, token);
}

export function roll(token: string) {
  return request<{ rolled: number; from_position: number; to_position: number; landed_cell: Record<string, unknown> | null }>(
    "/game/roll",
    { method: "POST" },
    token,
  );
}

export function buyOrSkipCell(token: string, cellId: number, action: "buy" | "skip") {
  return request<{ status: string; action: string; balance?: number }>(
    `/game/cell/${cellId}/purchase`,
    {
      method: "POST",
      body: JSON.stringify({ action }),
    },
    token,
  );
}

export function buySecretShop(token: string, itemId: number) {
  return request<{ status: string; balance: number; monthly_purchases: number }>(
    "/game/secret-shop/purchase",
    {
      method: "POST",
      body: JSON.stringify({ item_id: itemId }),
    },
    token,
  );
}

export function getMarketPlayers(token: string) {
  return request<{ items: MarketPlayer[] }>("/game/players", { method: "GET" }, token);
}

export function getPlayerInventory(token: string, playerId: number) {
  return request<{ items: MarketInventoryItem[] }>(`/game/players/${playerId}/inventory`, { method: "GET" }, token);
}

export function createTradeOffer(
  token: string,
  payload: { inventory_item_id: number; to_user_id: number; offer_points: number; note?: string },
) {
  return request<{ status: string; offer_id: number }>(
    "/game/market/offers",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function getTradeOffers(token: string) {
  return request<{ incoming: MarketOffer[]; outgoing: MarketOffer[] }>(
    "/game/market/offers",
    { method: "GET" },
    token,
  );
}

export function respondTradeOffer(token: string, offerId: number, action: "accept" | "reject") {
  return request<{ status: string; offer_status: string }>(
    `/game/market/offers/${offerId}/respond`,
    {
      method: "POST",
      body: JSON.stringify({ action }),
    },
    token,
  );
}

export function createAuctionLot(token: string, payload: { inventory_item_id: number; duration_minutes: number }) {
  return request<{ status: string; lot_id: number }>(
    "/game/market/auctions",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function placeAuctionBid(token: string, lotId: number, bidPoints: number) {
  return request<{ status: string }>(
    `/game/market/auctions/${lotId}/bid`,
    {
      method: "POST",
      body: JSON.stringify({ bid_points: bidPoints }),
    },
    token,
  );
}

export function getAuctionLots(token: string) {
  return request<{ items: AuctionLot[] }>(
    "/game/market/auctions",
    { method: "GET" },
    token,
  );
}

export function getMarketActivity(token: string) {
  return request<{ items: MarketActivity[] }>(
    "/game/market/activity",
    { method: "GET" },
    token,
  );
}

export function getMarketRating(token: string) {
  return request<{ items: MarketRating[] }>(
    "/game/market/rating",
    { method: "GET" },
    token,
  );
}

export function getParticipants(token: string) {
  return request<Array<{ id: number; email: string; balance: number; sessions_joined: number }>>(
    "/admin/participants",
    { method: "GET" },
    token,
  );
}

export type AdminSession = {
  id: number;
  name: string;
  status: "draft" | "active" | "closed";
  board_size: number;
  max_rolls_per_window: number;
  starts_at: string | null;
  ends_at: string | null;
  ended_at: string | null;
  roll_window_config: Array<{ days: number[]; start: string; end: string }>;
};

export function getSessions(token: string) {
  return request<AdminSession[]>(
    "/admin/sessions",
    { method: "GET" },
    token,
  );
}

export function createSession(
  token: string,
  payload: {
    name: string;
    board_size: number;
    max_rolls_per_window: number;
    starts_at?: string;
    ends_at?: string;
    roll_window_config: Array<{ days: number[]; start: string; end: string }>;
  },
) {
  return request<{ status: string; session: AdminSession }>(
    "/admin/sessions",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function setSessionStatus(token: string, sessionId: number, status: "draft" | "active" | "closed") {
  return request<{ status: string }>(
    `/admin/sessions/${sessionId}/status`,
    {
      method: "PATCH",
      body: JSON.stringify({ status }),
    },
    token,
  );
}

export function updateSessionSchedule(
  token: string,
  sessionId: number,
  payload: {
    starts_at?: string;
    ends_at?: string;
    board_size?: number;
    max_rolls_per_window?: number;
    roll_window_config?: Array<{ days: number[]; start: string; end: string }>;
  },
) {
  return request<{ status: string; session: AdminSession }>(
    `/admin/sessions/${sessionId}/schedule`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function endSessionNow(token: string, sessionId: number) {
  return request<{ status: string; session: AdminSession }>(
    `/admin/sessions/${sessionId}/end`,
    {
      method: "POST",
    },
    token,
  );
}

export function getSessionParticipants(token: string, sessionId: number) {
  return request<{ items: Array<{ user_id: number; identifier: string; assigned_at: string | null }> }>(
    `/admin/sessions/${sessionId}/participants`,
    { method: "GET" },
    token,
  );
}

export function setSessionParticipants(token: string, sessionId: number, playerIds: number[]) {
  return request<{ status: string; assigned: number }>(
    `/admin/sessions/${sessionId}/participants`,
    {
      method: "POST",
      body: JSON.stringify({ player_ids: playerIds }),
    },
    token,
  );
}

export function getSessionResultsJson(token: string, sessionId: number) {
  return request<{
    session: AdminSession;
    results: Array<{
      user_id: number;
      identifier: string;
      balance: number;
      moves_count: number;
      inventory_count: number;
      position: number;
    }>;
  }>(
    `/admin/sessions/${sessionId}/results?format=json`,
    { method: "GET" },
    token,
  );
}

export async function downloadSessionResultsCsv(token: string, sessionId: number): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/admin/sessions/${sessionId}/results?format=csv`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch {
      // no-op
    }
    throw new Error(detail);
  }
  return response.blob();
}

export function getCells(token: string, sessionId: number) {
  return request<Array<{ id: number; cell_index: number; title: string; description: string; reward_name: string; image_url: string | null; price_points: number; stock: number; status: string }>>(
    `/admin/sessions/${sessionId}/cells`,
    { method: "GET" },
    token,
  );
}

export function createCell(
  token: string,
  sessionId: number,
  payload: { cell_index: number; title: string; description?: string; reward_name: string; image_url?: string; price_points: number; stock: number },
) {
  return request<{ status: string }>(
    `/admin/sessions/${sessionId}/cells`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function updateCell(
  token: string,
  cellId: number,
  payload: { title?: string; description?: string; reward_name?: string; image_url?: string; price_points?: number; stock?: number },
) {
  return request<{ status: string }>(
    `/admin/cells/${cellId}`,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function manualAccrual(token: string, playerId: number, payload: { points: number; reason: string }) {
  return request<{ status: string; balance: number }>(
    `/admin/players/${playerId}/accrual`,
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}

export function getSecretShopItems(token: string) {
  return request<Array<{ id: number; name: string; price_points: number; stock: number; is_active: number }>>(
    "/admin/secret-shop/items",
    { method: "GET" },
    token,
  );
}

export function createSecretShopItem(token: string, payload: { name: string; price_points: number; stock: number }) {
  return request<{ status: string; item_id: number }>(
    "/admin/secret-shop/items",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
    token,
  );
}
