import { Link } from 'react-router-dom';

export default function Register() {
  return (
    <div className="auth-page">
      <h1>Register</h1>
      {/* Signup call + "pending" status messaging lands Day 2 */}
      <form>
        <label>
          Email
          <input type="email" name="email" required />
        </label>
        <label>
          Password
          <input type="password" name="password" required />
        </label>
        <button type="submit">Register</button>
      </form>
      <p>
        Already have an account? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}