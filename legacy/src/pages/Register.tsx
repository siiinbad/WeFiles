import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import PasswordInput from '../components/PasswordInput';

const USERNAME_PATTERN = /^[a-zA-Z0-9_]{3,20}$/;

export default function Register() {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [usernameError, setUsernameError] = useState<string | null>(null);
  const [checkingUsername, setCheckingUsername] = useState(false);
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // Best-effort pre-check via a security-definer RPC (anon users have no
  // session yet, so they can't query `profiles` directly). This is a UX
  // nicety, not the real guarantee — the database's UNIQUE constraint on
  // profiles.username is what actually enforces uniqueness.
  async function checkUsername(value: string) {
    setUsernameError(null);
    if (!value) return;
    if (!USERNAME_PATTERN.test(value)) {
      setUsernameError('3-20 characters: letters, numbers, underscore only.');
      return;
    }
    setCheckingUsername(true);
    const { data, error: rpcError } = await supabase.rpc('is_username_taken', {
      check_username: value,
    });
    setCheckingUsername(false);
    if (!rpcError && data === true) {
      setUsernameError('That username is already taken.');
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!USERNAME_PATTERN.test(username)) {
      setUsernameError('3-20 characters: letters, numbers, underscore only.');
      return;
    }
    if (usernameError) return;

    setLoading(true);
    const { error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { username } },
    });

    setLoading(false);
    if (signUpError) {
      // A DB-level unique-constraint violation on username surfaces here
      // as a generic auth error — reword it into something actionable.
      const message = /database|constraint|duplicate/i.test(signUpError.message)
        ? 'That username may already be taken. Please choose another.'
        : signUpError.message;
      setError(message);
      return;
    }
    setSubmitted(true);
  }

  if (submitted) {
    return (
      <div className="auth-page">
        <div className="auth-page__header">
          <span className="eyebrow">Entry Filed</span>
          <h1>Check your email</h1>
          <p className="auth-page__subtitle">
            Confirm your email, then wait for an admin to approve your account before logging in.
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
        <span className="eyebrow">New Entry</span>
        <h1>Register</h1>
        <p className="auth-page__subtitle">Join the Liki community</p>
      </div>
      {error && (
        <div className="auth-page__error" role="alert" aria-live="polite">
          {error}
        </div>
      )}
      <form onSubmit={handleSubmit}>
        <label htmlFor="register-username">
          Username
          <input
            id="register-username"
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onBlur={(e) => checkUsername(e.target.value)}
            required
            autoComplete="username"
            aria-label="Username"
            aria-invalid={!!usernameError}
            aria-describedby={usernameError ? 'username-error' : undefined}
            placeholder="Choose a username"
          />
          {checkingUsername && (
            <span className="auth-page__hint" aria-live="polite">
              Checking availability…
            </span>
          )}
          {usernameError && (
            <span className="auth-page__field-error" id="username-error" role="alert">
              {usernameError}
            </span>
          )}
        </label>
        <label htmlFor="register-email">
          Email
          <input
            id="register-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            aria-label="Email address"
            placeholder="your@email.com"
          />
        </label>
        <PasswordInput
          id="register-password"
          label="Password"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          minLength={6}
          required
          placeholder="Create a password (min 6 characters)"
        />
        <button type="submit" disabled={loading || checkingUsername} aria-busy={loading}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden="true"></span>
              Registering…
            </>
          ) : (
            'Register'
          )}
        </button>
      </form>
      <p className="auth-page__link">
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}