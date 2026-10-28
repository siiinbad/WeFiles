import { useState } from 'react';
import type { FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import PasswordInput from '../components/PasswordInput';

// Reached from the emailed reset link. supabase-js reads the recovery
// token out of the URL fragment automatically and establishes a
// temporary session — updateUser() below applies to that session.
export default function ResetPassword() {
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: updateError } = await supabase.auth.updateUser({ password });

    setLoading(false);
    if (updateError) {
      setError(updateError.message);
      return;
    }
    setDone(true);
    setTimeout(() => navigate('/login'), 1500);
  }

  if (done) {
    return (
      <div className="auth-page">
        <div className="auth-page__header">
          <span className="eyebrow">Recovery Complete</span>
          <h1>Password updated</h1>
          <p className="auth-page__subtitle">Redirecting to login…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-page__header">
        <span className="eyebrow">Recovery</span>
        <h1>Set a new password</h1>
        <p className="auth-page__subtitle">Choose a password at least 6 characters long.</p>
      </div>
      {error && (
        <div className="auth-page__error" role="alert" aria-live="polite">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <PasswordInput
          id="reset-password"
          label="New password"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          minLength={6}
          required
          placeholder="Enter a new password"
        />
        <button type="submit" disabled={loading} aria-busy={loading}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden="true"></span>
              Saving…
            </>
          ) : (
            'Save new password'
          )}
        </button>
      </form>
    </div>
  );
}