import { useEffect, useState, useCallback } from 'react';
import Layout from '../components/Layout';
import PendingUsersList from '../components/admin/PendingUsersList';
import MemberList from '../components/admin/MemberList';
import ConfirmDialog from '../components/ConfirmDialog';
import { supabase } from '../lib/supabaseClient';
import { useAuth } from '../context/useAuth';
import type { Profile } from '../types';

interface PendingAction {
  title: string;
  message: string;
  confirmLabel: string;
  run: () => void;
}

export default function Admin() {
  const { session, refreshProfile } = useAuth();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);

  const load = useCallback(async () => {
    // RLS's admin policy lets this return every row; a non-admin calling
    // the same query would only ever get their own row back.
    const { data, error: fetchError } = await supabase
      .from('profiles')
      .select('*')
      .order('created_at', { ascending: true });

    if (fetchError) setError(fetchError.message);
    else setProfiles((data ?? []) as Profile[]);
    setLoading(false);
  }, []);

  useEffect(() => {
    // Initial remote load on mount; the state updates happen inside the async loader.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  async function setStatus(id: string, status: Profile['status']) {
    setBusyId(id);
    setError(null);
    const { error: updateError } = await supabase
      .from('profiles')
      .update({ status })
      .eq('id', id);

    if (updateError) setError(updateError.message);
    else await load();

    setBusyId(null);
    await refreshProfile();
  }

  async function setRole(id: string, role: Profile['role']) {
    setBusyId(id);
    setError(null);
    const { error: updateError } = await supabase
      .from('profiles')
      .update({ role })
      .eq('id', id);

    if (updateError) setError(updateError.message);
    else await load();

    setBusyId(null);
    await refreshProfile();
  }

  const pending = profiles.filter((p) => p.status === 'pending');
  const others = profiles.filter((p) => p.status !== 'pending');

  return (
    <Layout>
      <span className="eyebrow">Control</span>
      <h1>Admin</h1>
      <p className="page-lede">Approve new registrations and manage existing members.</p>
      {error && (
        <p className="auth-page__error" role="alert">
          {error}
        </p>
      )}

      <section className="admin-section">
        <h2>Pending registrations</h2>
        {loading ? (
          <p className="empty-placeholder">Loading pending registrations…</p>
        ) : (
          <PendingUsersList
            pending={pending}
            busyId={busyId}
            onApprove={(id) => setStatus(id, 'approved')}
            onReject={(id) =>
              setPendingAction({
                title: 'Reject registration?',
                message: 'This user will not be able to log in.',
                confirmLabel: 'Reject',
                run: () => setStatus(id, 'rejected'),
              })
            }
          />
        )}
      </section>

      <section className="admin-section">
        <h2>Members</h2>
        {loading ? (
          <p className="empty-placeholder">Loading members…</p>
        ) : (
          <MemberList
            members={others}
            currentUserId={session?.user.id}
            busyId={busyId}
            onSetStatus={(id, status) => {
              if (status === 'disabled') {
                setPendingAction({
                  title: 'Disable member?',
                  message: 'They will be logged out and unable to access the app.',
                  confirmLabel: 'Disable',
                  run: () => setStatus(id, status),
                });
              } else {
                setStatus(id, status);
              }
            }}
            onSetRole={(id, role) =>
              setPendingAction({
                title: role === 'admin' ? 'Promote to admin?' : 'Demote to member?',
                message:
                  role === 'admin'
                    ? 'They will gain full admin access, including approving/rejecting users and deleting files.'
                    : 'They will lose admin access.',
                confirmLabel: role === 'admin' ? 'Promote' : 'Demote',
                run: () => setRole(id, role),
              })
            }
          />
        )}
      </section>

      {pendingAction && (
        <ConfirmDialog
          title={pendingAction.title}
          message={pendingAction.message}
          confirmLabel={pendingAction.confirmLabel}
          onCancel={() => setPendingAction(null)}
          onConfirm={() => {
            pendingAction.run();
            setPendingAction(null);
          }}
        />
      )}
    </Layout>
  );
}