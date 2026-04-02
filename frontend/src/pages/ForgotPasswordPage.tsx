import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { requestPasswordReset } from "../services/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError("");
    setMessage("");
    try {
      const result = await requestPasswordReset(email);
      setMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить ссылку");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="panel panel-wide">
      <h2>Восстановление пароля</h2>
      <p className="muted">Введите email, и мы отправим ссылку для сброса пароля.</p>
      <form onSubmit={submit} className="list" style={{ marginTop: 16 }}>
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          type="email"
          required
        />
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Отправка..." : "Отправить ссылку"}
        </button>
      </form>
      {message && <p className="ok">{message}</p>}
      {error && <p className="error">{error}</p>}
      <p className="muted">
        <Link to="/auth">Назад ко входу</Link>
      </p>
    </section>
  );
}
