import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import PasswordInput from '../components/PasswordInput';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });

    setLoading(false);
    if (signInError) {
      setError(signInError.message);
      return;
    }
    navigate('/dashboard');
  }

  return (
    <div className="auth-page">
      <div className="auth-page__header">
        <h1>Log In</h1>
        <p className="auth-page__subtitle">Welcome back to Liki</p>
      </div>
      {error && (
        <div className="auth-page__error" role="alert" aria-live="polite">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <label htmlFor="login-email">
          Email
          <input
            id="login-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="your@email.com"
          />
        </label>
        <label htmlFor="login-password">
          Password
          <PasswordInput
            id="login-password"
            value={password}
            onChange={setPassword}
            required
            autoComplete="current-password"
            placeholder="Enter your password"
          />
        </label>
        <div className="auth-page__forgot">
          <Link to="/forgot-password">Forgot password?</Link>
        </div>
        <button type="submit" disabled={loading} aria-busy={loading}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden="true"></span>
              Logging in…
            </>
          ) : (
            'Log In'
          )}
        </button>
      </form>
      <p className="auth-page__link">
        Need an account? <Link to="/register">Register</Link>
      </p>
    </div>
  );
}