import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import Layout from '../components/Layout';
import Badge from '../components/Badge';
import { useAuth } from '../context/useAuth';
import { supabase } from '../lib/supabaseClient';

const USERNAME_PATTERN = /^[a-zA-Z0-9_]{3,20}$/;

function initials(value: string) {
  return value.slice(0, 2).toUpperCase();
}

export default function Profile() {
  const { profile, refreshProfile } = useAuth();
  const [editing, setEditing] = useState(false);
  const [username, setUsername] = useState(profile?.username ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const profileStats = useMemo(() => {
    if (!profile) return null;
    const joined = new Date(profile.created_at);
    const days = Math.max(1, Math.ceil((Date.now() - joined.getTime()) / 86_400_000));
    return { joined, days };
  }, [profile]);

  if (!profile || !profileStats) return null;

  function startEditing() {
    setUsername(profile!.username);
    setError(null);
    setSuccess(false);
    setEditing(true);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    const nextUsername = username.trim();
    if (!USERNAME_PATTERN.test(nextUsername)) {
      setError('3-20 characters: letters, numbers, underscore only.');
      return;
    }
    if (nextUsername === profile!.username) {
      setEditing(false);
      return;
    }

    setSaving(true);
    const { error: updateError } = await supabase
      .from('profiles')
      .update({ username: nextUsername })
      .eq('id', profile!.id);

    setSaving(false);
    if (updateError) {
      const message = /duplicate|unique/i.test(updateError.message)
        ? 'That username is already taken.'
        : updateError.message;
      setError(message);
      return;
    }
    await refreshProfile();
    setUsername(nextUsername);
    setSuccess(true);
    setEditing(false);
  }

  function cancelEditing() {
    setUsername(profile!.username);
    setEditing(false);
    setError(null);
  }

  return (
    <Layout>
      <span className="eyebrow">Record</span>
      <h1>Profile</h1>
      <section className="profile-hero panel" aria-label="Profile summary">
        <div className="profile-avatar" aria-hidden="true">{initials(profile.username)}</div>
        <div>
          <p className="profile-kicker">Signed in as</p>
          <h2>{profile.username}</h2>
          <p>{profile.email}</p>
        </div>
        <div className="profile-badges">
          <Badge value={profile.role} />
          <Badge value={profile.status} />
        </div>
      </section>

      <section className="profile-grid" aria-label="Account details">
        <article className="profile-card panel">
          <h2>Identity</h2>
          <dl className="profile-fields">
            <dt>Username</dt>
            <dd>
              {editing ? (
                <form className="profile-edit" onSubmit={handleSave}>
                  <input type="text" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
                  <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
                  <button type="button" onClick={cancelEditing} disabled={saving}>Cancel</button>
                </form>
              ) : (
                <>
                  {profile.username}{' '}
                  <button type="button" onClick={startEditing}>Edit</button>
                </>
              )}
            </dd>
            <dt>Email</dt>
            <dd>{profile.email}</dd>
          </dl>
          {error && <p className="auth-page__error" role="alert">{error}</p>}
          {success && <p className="auth-page__hint" role="status">Username updated.</p>}
        </article>

        <article className="profile-card panel">
          <h2>Access</h2>
          <dl className="profile-fields">
            <dt>Role</dt>
            <dd><Badge value={profile.role} /></dd>
            <dt>Status</dt>
            <dd><Badge value={profile.status} /></dd>
            <dt>Member since</dt>
            <dd>{profileStats.joined.toLocaleDateString()}</dd>
            <dt>Tenure</dt>
            <dd>{profileStats.days} day{profileStats.days === 1 ? '' : 's'}</dd>
          </dl>
          <p className="profile-note">Role and status can only be changed by an admin from the admin panel.</p>
        </article>
      </section>
    </Layout>
  );
}
