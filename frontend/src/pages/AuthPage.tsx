import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { login, me, register } from "../services/api";
import { useAuthStore } from "../store/authStore";

export default function AuthPage() {
  const navigate = useNavigate();
  const setAuth = useAuthStore((s) => s.setAuth);

  const [mode, setMode] = useState<"login" | "register">("login");
  const [loginIdentifier, setLoginIdentifier] = useState("player@demo.local");

  const [registerBy, setRegisterBy] = useState<"email" | "phone">("email");
  const [email, setEmail] = useState("player@demo.local");
  const [phone, setPhone] = useState("+79990000123");
  const [password, setPassword] = useState("player");
  const [role, setRole] = useState<"player" | "admin">("player");
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      const auth =
        mode === "login"
          ? await login(loginIdentifier, password)
          : await register({
              password,
              role,
              email: registerBy === "email" ? email : undefined,
              phone: registerBy === "phone" ? phone : undefined,
            });

      const profile = await me(auth.access_token);
      setAuth(auth.access_token, auth.refresh_token, profile.role, profile.identifier);
      navigate(profile.role === "admin" ? "/admin" : "/game");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка авторизации");
    }
  };

  return (
    <section className="panel panel-wide">
      <h2>Вход и регистрация</h2>
      <p className="muted">
        Вход возможен по почте или телефону. Демо: <code>player@demo.local / player</code>,{" "}
        <code>admin@demo.local / admin</code>.
      </p>

      <div className="segmented">
        <button type="button" className={mode === "login" ? "" : "secondary"} onClick={() => setMode("login")}>
          Вход
        </button>
        <button type="button" className={mode === "register" ? "" : "secondary"} onClick={() => setMode("register")}>
          Регистрация
        </button>
      </div>

      <form onSubmit={submit} className="list" style={{ marginTop: 16 }}>
        {mode === "login" && (
          <input
            value={loginIdentifier}
            onChange={(e) => setLoginIdentifier(e.target.value)}
            placeholder="Email или телефон"
            required
          />
        )}

        {mode === "register" && (
          <>
            <div className="segmented">
              <button
                type="button"
                className={registerBy === "email" ? "" : "secondary"}
                onClick={() => setRegisterBy("email")}
              >
                По почте
              </button>
              <button
                type="button"
                className={registerBy === "phone" ? "" : "secondary"}
                onClick={() => setRegisterBy("phone")}
              >
                По телефону
              </button>
            </div>
            {registerBy === "email" ? (
              <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" required />
            ) : (
              <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Телефон (+7999...)" required />
            )}
          </>
        )}

        <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Пароль" type="password" required />

        {mode === "register" && (
          <select value={role} onChange={(e) => setRole(e.target.value as "player" | "admin")}>
            <option value="player">Игрок</option>
            <option value="admin">Администратор</option>
          </select>
        )}
        <button type="submit">{mode === "login" ? "Войти" : "Создать аккаунт"}</button>
      </form>

      {mode === "login" && (
        <p className="muted">
          <Link to="/auth/forgot">Забыли пароль?</Link>
        </p>
      )}

      {error && <p className="error">{error}</p>}
    </section>
  );
}
