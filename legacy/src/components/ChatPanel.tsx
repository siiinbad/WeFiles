import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { supabase } from '../lib/supabaseClient';
import { useAuth } from '../context/useAuth';
import type { ChatMessage } from '../types';
import './ChatPanel.css';

const AVATAR_HUES = [210, 260, 320, 20, 160, 45, 285];

function avatarHue(email: string) {
  let hash = 0;
  for (let i = 0; i < email.length; i++) hash = (hash * 31 + email.charCodeAt(i)) % 997;
  return AVATAR_HUES[hash % AVATAR_HUES.length];
}

export default function ChatPanel() {
  const { session, profile } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      // RLS requires status='approved' to read at all; a pending/rejected
      // user gets an empty result here rather than an error.
      const { data, error: fetchError } = await supabase
        .from('chat_messages')
        .select('*')
        .order('created_at', { ascending: true })
        .limit(200);

      if (cancelled) return;
      if (fetchError) setError(fetchError.message);
      else setMessages((data ?? []) as ChatMessage[]);
      setLoading(false);
    }
    loadHistory();

    const channel = supabase
      .channel('chat_messages_stream')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'chat_messages' },
        (payload) => {
          setMessages((prev) => [...prev, payload.new as ChatMessage]);
        }
      )
      .subscribe();

    return () => {
      cancelled = true;
      supabase.removeChannel(channel);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    const trimmed = content.trim();
    if (!trimmed || !session || !profile || sending) return;

    setContent('');
    setError(null);
    setSending(true);

    const { error: insertError } = await supabase.from('chat_messages').insert({
      sender_id: session.user.id,
      sender_email: profile.email,
      content: trimmed,
    });
    setSending(false);
    if (insertError) {
      setContent(trimmed);
      setError(insertError.message);
    }
  }

  return (
    <div className="chat-panel">
      <h2 className="chat-panel__title">Chat</h2>
      <div className="chat-panel__messages" role="log" aria-live="polite" aria-label="Chat messages">
        {loading && <p className="empty-placeholder">Loading…</p>}
        {!loading && messages.length === 0 && (
          <p className="empty-placeholder">No messages yet.</p>
        )}
        {messages.map((m) => {
          const isOwn = m.sender_id === session?.user.id;
          return (
            <div
              key={m.id}
              className={`chat-panel__message${isOwn ? ' chat-panel__message--own' : ''}`}
            >
              <div
                className="chat-panel__avatar"
                style={{ background: `hsl(${avatarHue(m.sender_email)}, 55%, 42%)` }}
              >
                {m.sender_email.charAt(0).toUpperCase()}
              </div>
              <div className="chat-panel__bubble">
                <div className="chat-panel__meta">
                  <span className="chat-panel__sender">{m.sender_email}</span>
                  <span className="chat-panel__time">
                    {new Date(m.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </span>
                </div>
                <div className="chat-panel__content">{m.content}</div>
              </div>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
      {error && <p className="auth-page__error" role="alert">{error}</p>}
      <form className="chat-panel__form" onSubmit={handleSend}>
        <label className="sr-only" htmlFor="chat-message">Message</label>
        <input
          id="chat-message"
          type="text"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Message…"
          maxLength={2000}
        />
        <button type="submit" disabled={!content.trim() || sending} aria-busy={sending}>
          {sending ? 'Sending…' : 'Send'}
        </button>
      </form>
    </div>
  );
}