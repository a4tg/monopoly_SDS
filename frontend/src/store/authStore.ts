import { create } from "zustand";

type Role = "admin" | "player";

type AuthStore = {
  accessToken: string | null;
  refreshToken: string | null;
  role: Role | null;
  identifier: string | null;
  setAuth: (accessToken: string, refreshToken: string, role: Role, identifier: string) => void;
  logout: () => void;
};

const tokenFromStorage = localStorage.getItem("mono_token");
const refreshTokenFromStorage = localStorage.getItem("mono_refresh_token");
const roleFromStorage = localStorage.getItem("mono_role") as Role | null;
const identifierFromStorage = localStorage.getItem("mono_identifier");

export const useAuthStore = create<AuthStore>((set) => ({
  accessToken: tokenFromStorage,
  refreshToken: refreshTokenFromStorage,
  role: roleFromStorage,
  identifier: identifierFromStorage,
  setAuth: (accessToken, refreshToken, role, identifier) => {
    localStorage.setItem("mono_token", accessToken);
    localStorage.setItem("mono_refresh_token", refreshToken);
    localStorage.setItem("mono_role", role);
    localStorage.setItem("mono_identifier", identifier);
    set({ accessToken, refreshToken, role, identifier });
  },
  logout: () => {
    localStorage.removeItem("mono_token");
    localStorage.removeItem("mono_refresh_token");
    localStorage.removeItem("mono_role");
    localStorage.removeItem("mono_identifier");
    set({ accessToken: null, refreshToken: null, role: null, identifier: null });
  },
}));
