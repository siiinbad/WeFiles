import type { ReactElement } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/useAuth';

// UI-level convenience only — real enforcement is the is_admin() RLS
// policies on the profiles table (see supabase/migrations/admin.sql).
// Even if someone bypassed this guard entirely, direct Supabase calls
// as a non-admin would still be rejected by the database.
export default function AdminRoute({ children }: { children: ReactElement }) {
  const { profile } = useAuth();

  if (profile?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}