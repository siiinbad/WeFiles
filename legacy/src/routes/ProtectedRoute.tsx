import type { ReactElement } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';

// UI-level convenience only. The real enforcement is RLS on every table
// and storage bucket — this guard just avoids flashing protected UI at
// people who aren't logged in or aren't approved yet.
export default function ProtectedRoute({ children }: { children: ReactElement }) {
  const { session, profile, loading } = useAuth();

  if (loading) return <p>Loading…</p>;
  if (!session) return <Navigate to="/login" replace />;
  if (!profile) return <p>Loading profile…</p>;

  if (profile.status === 'pending') {
    return <p>Your account is awaiting admin approval.</p>;
  }
  if (profile.status === 'rejected' || profile.status === 'disabled') {
    return <p>Your account does not have access. Contact an administrator.</p>;
  }

  return children;
}