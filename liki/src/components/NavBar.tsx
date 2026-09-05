import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/useAuth';
import { supabase } from '../lib/supabaseClient';
import ConfirmDialog from './ConfirmDialog';
import ThemeToggle from './ThemeToggle';

// Rendered once via Layout so it's present on every protected page.
export default function NavBar() {
  const { profile } = useAuth();
  const [confirmingLogout, setConfirmingLogout] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    await supabase.auth.signOut();
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    isActive ? 'nav-bar__link nav-bar__link--active' : 'nav-bar__link';

  return (
    <div className="nav-bar">
      <div className="nav-bar__brand" aria-label="Liki home">Liki</div>
      <nav className="nav-bar__links" aria-label="Primary navigation">
        <NavLink to="/dashboard" className={linkClass}>
          Dashboard
        </NavLink>
        <NavLink to="/files" className={linkClass}>
          Files
        </NavLink>
        <NavLink to="/profile" className={linkClass}>
          Profile
        </NavLink>
        {profile?.role === 'admin' && (
          <NavLink to="/admin" className={linkClass}>
            Admin panel
          </NavLink>
        )}
      </nav>
      <div className="nav-bar__actions">
        <ThemeToggle />
        <button type="button" onClick={() => setConfirmingLogout(true)} disabled={loggingOut}>
          {loggingOut ? 'Logging out…' : 'Log out'}
        </button>
      </div>

      {confirmingLogout && (
        <ConfirmDialog
          title="Log out?"
          message="You will be signed out of Liki and returned to the login screen."
          confirmLabel={loggingOut ? 'Logging out…' : 'Log out'}
          confirmDisabled={loggingOut}
          onCancel={() => setConfirmingLogout(false)}
          onConfirm={handleLogout}
        />
      )}
    </div>
  );
}