import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    });

    setLoading(false);
    // Show the same success state regardless of whether the email exists,
    // so this can't be used to check which emails are registered.
    if (resetError) setError(resetError.message);
    else setSent(true);
  }

  if (sent) {
    return (
      <div className="auth-page">
        <div className="auth-page__header">
          <span className="eyebrow">Recovery Filed</span>
          <h1>Check your email</h1>
          <p className="auth-page__subtitle">
            If an account exists for that address, a reset link has been sent.
          </p>
        </div>
        <p className="auth-page__link">
          <Link to="/login">Back to login</Link>
        </p>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-page__header">
        <span className="eyebrow">Recovery</span>
        <h1>Forgot password</h1>
        <p className="auth-page__subtitle">We’ll send a reset link if that email is registered.</p>
      </div>
      {error && (
        <div className="auth-page__error" role="alert" aria-live="polite">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <label htmlFor="forgot-email">
          Email
          <input
            id="forgot-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            placeholder="your@email.com"
          />
        </label>
        <button type="submit" disabled={loading} aria-busy={loading}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden="true"></span>
              Sending…
            </>
          ) : (
            'Send reset link'
          )}
        </button>
      </form>
      <p className="auth-page__link">
        <Link to="/login">Back to login</Link>
      </p>
    </div>
  );
}