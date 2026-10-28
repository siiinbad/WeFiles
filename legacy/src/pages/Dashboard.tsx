import { useEffect, useState } from 'react';
import Layout from '../components/Layout';
import Badge from '../components/Badge';
import { useAuth } from '../context/useAuth';
import { Link } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import type { FileRecord, ChatMessage } from '../types';

// Same hue function as ChatPanel for consistency
const AVATAR_HUES = [210, 260, 320, 20, 160, 45, 285];
function avatarHue(email: string) {
  let hash = 0;
  for (let i = 0; i < email.length; i++) hash = (hash * 31 + email.charCodeAt(i)) % 997;
  return AVATAR_HUES[hash % AVATAR_HUES.length];
}

export default function Dashboard() {
  const { profile, session } = useAuth();
  const [fileCount, setFileCount] = useState(0);
  const [recentFiles, setRecentFiles] = useState<FileRecord[]>([]);
  const [recentMessages, setRecentMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;

    async function loadDashboard() {
      setLoading(true);
      try {
        // File count
        const { count } = await supabase
          .from('files')
          .select('*', { count: 'exact', head: true });
        if (!cancelled) setFileCount(count ?? 0);

        // Recent files (last 3)
        const { data: files } = await supabase
          .from('files')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(3);
        if (!cancelled) setRecentFiles((files ?? []) as FileRecord[]);

        // Recent chat messages (last 3)
        const { data: messages } = await supabase
          .from('chat_messages')
          .select('*')
          .order('created_at', { ascending: false })
          .limit(3);
        if (!cancelled) setRecentMessages((messages ?? []).reverse() as ChatMessage[]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadDashboard();
    return () => { cancelled = true; };
  }, [session]);

  if (!profile) return null;

  return (
    <Layout>
      <header className="dashboard-header">
        <div>
          <span className="eyebrow">Crew Manifest</span>
          <h1>Dashboard</h1>
          <p className="page-lede">
            Welcome back, <strong>{profile.username}</strong>. Your vault, crew chat, and account record are ready.
          </p>
        </div>
        <Link className="dashboard-header__link" to="/files">Open Vault →</Link>
      </header>

      <section className="dashboard-hero panel" aria-label="Account overview">
        <div>
          <span className="eyebrow">Current Record</span>
          <dl className="status-card__meta">
            <div><dt>Email</dt><dd>{profile.email}</dd></div>
            <div><dt>Role</dt><dd><Badge value={profile.role} /></dd></div>
            <div><dt>Status</dt><dd><Badge value={profile.status} /></dd></div>
            <div><dt>Member since</dt><dd>{new Date(profile.created_at).toLocaleDateString()}</dd></div>
          </dl>
        </div>
      </section>

      <section className="stats-grid" aria-label="Quick statistics">
        <article className="stat-card"><span aria-hidden="true">📁</span><strong>{fileCount}</strong><small>Files in Vault</small></article>
        <article className="stat-card"><span aria-hidden="true">💬</span><strong>{recentMessages.length}</strong><small>Recent Messages</small></article>
        <article className="stat-card"><span aria-hidden="true">🛡️</span><strong>{profile.role === 'admin' ? 'Admin' : 'Member'}</strong><small>Access Level</small></article>
      </section>

      <section aria-labelledby="quick-actions-title">
        <h2 id="quick-actions-title" className="eyebrow">Quick Actions</h2>
        <div className="dashboard-cards">
          <Link className="dashboard-card" to="/files">
            <span className="dashboard-card__icon" aria-hidden="true">📁</span>
            <strong>Vault</strong>
            <span>Upload, browse, and share crew documents.</span>
          </Link>
          <Link className="dashboard-card" to="/profile">
            <span className="dashboard-card__icon" aria-hidden="true">👤</span>
            <strong>Profile</strong>
            <span>Review your account details and username.</span>
          </Link>
          {profile.role === 'admin' && (
            <Link className="dashboard-card" to="/admin">
              <span className="dashboard-card__icon" aria-hidden="true">⚙️</span>
              <strong>Admin Panel</strong>
              <span>Approve registrations and manage members.</span>
            </Link>
          )}
        </div>
      </section>

      <section className="activity-grid" aria-label="Recent activity">
        <div className="activity-panel">
          <div className="activity-panel__header"><h2 className="eyebrow">Recent Vault Files</h2><Link to="/files">View all →</Link></div>
          {loading ? <p className="empty-placeholder">Loading vault activity…</p> : recentFiles.length === 0 ? <p className="empty-placeholder">No files yet. <Link to="/files">Upload one</Link> to get started.</p> : (
            <ul className="activity-list">
              {recentFiles.map((file) => <li key={file.id}><span aria-hidden="true">📄</span><div><strong>{file.file_name}</strong><small>{formatBytes(file.size_bytes)} · {new Date(file.created_at).toLocaleDateString()}</small></div></li>)}
            </ul>
          )}
        </div>

        <div className="activity-panel">
          <div className="activity-panel__header"><h2 className="eyebrow">Recent Chat</h2><span>Sidebar</span></div>
          {loading ? <p className="empty-placeholder">Loading chat activity…</p> : recentMessages.length === 0 ? <p className="empty-placeholder">No messages yet. Start the conversation in the chat panel.</p> : (
            <ul className="activity-list activity-list--chat">
              {recentMessages.map((message) => <li key={message.id}><span className="activity-avatar" style={{ background: `hsl(${avatarHue(message.sender_email)}, 55%, 42%)` }}>{message.sender_email.charAt(0).toUpperCase()}</span><div><strong>{message.sender_email}</strong><small>{message.content}</small></div></li>)}
            </ul>
          )}
        </div>
      </section>
    </Layout>
  );
}

function formatBytes(bytes: number | null) {
  if (!bytes) return '0 KB';
  return `${(bytes / 1024).toFixed(1)} KB`;
}