import { FormEvent, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { confirmPasswordReset } from "../services/api";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const tokenFromQuery = useMemo(() => params.get("token") || "", [params]);
  const [token, setToken] = useState(tokenFromQuery);
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");
    setMessage("");
    try {
      await confirmPasswordReset(token, password);
      setMessage("Пароль обновлен. Теперь можно войти с новым паролем.");
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сбросить пароль");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="panel panel-wide">
      <h2>Новый пароль</h2>
      <p className="muted">Откройте страницу по ссылке из письма или вставьте токен вручную.</p>
      <form onSubmit={submit} className="list" style={{ marginTop: 16 }}>
        <input
          value={token}
          onChange={(e) => setToken(e.target.value)}
          placeholder="Токен восстановления"
          required
        />
        <input
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Новый пароль"
          type="password"
          minLength={6}
          required
        />
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Сохранение..." : "Сохранить пароль"}
        </button>
      </form>
      {message && <p className="ok">{message}</p>}
      {error && <p className="error">{error}</p>}
      <p className="muted">
        <Link to="/auth">Вернуться ко входу</Link>
      </p>
    </section>
  );
}
