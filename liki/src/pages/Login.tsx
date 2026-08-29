import { Link } from 'react-router-dom';

export default function Login() {
  return (
    <div className="auth-page">
      <h1>Log In</h1>
      {/* Form wiring (Supabase auth call, error/loading state) lands Day 2 */}
      <form>
        <label>
          Email
          <input type="email" name="email" required />
        </label>
        <label>
          Password
          <input type="password" name="password" required />
        </label>
        <button type="submit">Log In</button>
      </form>
      <p>
        Need an account? <Link to="/register">Register</Link>
      </p>
    </div>
  );
}