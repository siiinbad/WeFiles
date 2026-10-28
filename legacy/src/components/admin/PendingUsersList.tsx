import type { Profile } from '../../types';

interface Props {
  pending: Profile[];
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  busyId: string | null;
}

export default function PendingUsersList({ pending, onApprove, onReject, busyId }: Props) {
  if (pending.length === 0) {
    return <p className="empty-placeholder">No pending registrations.</p>;
  }

  return (
    <ul className="admin-list">
      {pending.map((p) => (
        <li key={p.id} className="admin-list__row">
          <span>{p.email}</span>
          <div className="admin-list__actions">
            <button disabled={busyId === p.id} onClick={() => onApprove(p.id)}>
              Approve
            </button>
            <button
              className="admin-list__danger"
              disabled={busyId === p.id}
              onClick={() => onReject(p.id)}
            >
              Reject
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}