import type { Profile } from '../../types';

interface Props {
  members: Profile[];
  currentUserId: string | undefined;
  onSetStatus: (id: string, status: Profile['status']) => void;
  onSetRole: (id: string, role: Profile['role']) => void;
  busyId: string | null;
}

export default function MemberList({
  members,
  currentUserId,
  onSetStatus,
  onSetRole,
  busyId,
}: Props) {
  if (members.length === 0) {
    return <p className="empty-placeholder">No members yet.</p>;
  }

  return (
    <ul className="admin-list">
      {members.map((m) => {
        const isSelf = m.id === currentUserId;
        return (
          <li key={m.id} className="admin-list__row">
            <span>
              {m.email} — <span className="admin-list__tag">{m.role}</span> ·{' '}
              <span className="admin-list__tag">{m.status}</span>
              {isSelf && ' (you)'}
            </span>
            <div className="admin-list__actions">
              {/* Self role/status changes are also blocked server-side by
                  the RLS trigger — disabling here just avoids a round-trip
                  error and confusing the admin about their own account. */}
              {!isSelf && (
                <>
                  {m.status === 'approved' ? (
                    <button
                      className="admin-list__danger"
                      disabled={busyId === m.id}
                      onClick={() => onSetStatus(m.id, 'disabled')}
                    >
                      Disable
                    </button>
                  ) : (
                    <button
                      disabled={busyId === m.id}
                      onClick={() => onSetStatus(m.id, 'approved')}
                    >
                      Approve
                    </button>
                  )}
                  <button
                    disabled={busyId === m.id}
                    onClick={() => onSetRole(m.id, m.role === 'admin' ? 'member' : 'admin')}
                  >
                    {m.role === 'admin' ? 'Demote to member' : 'Promote to admin'}
                  </button>
                </>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}