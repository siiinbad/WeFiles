-- Day 5: global chat. Run once in the Supabase SQL Editor, after files.sql.

-- sender_email is denormalized at insert time rather than joined from
-- profiles at read time — profiles' SELECT policy only exposes a user's
-- own row (plus admin), so members couldn't otherwise resolve other
-- senders' emails for display. The insert check below still ties it to
-- the caller's real profile, so it can't be spoofed.
create table public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  sender_id uuid not null references auth.users (id) on delete cascade,
  sender_email text not null,
  content text not null check (char_length(trim(content)) > 0),
  created_at timestamptz not null default now()
);

alter table public.chat_messages enable row level security;

-- One global room: any approved user (admin or member) can read every
-- message. There's no per-conversation scoping — by design, no DMs.
create policy "chat_select_approved"
  on public.chat_messages for select
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid() and status = 'approved'
    )
  );

-- Sender must be the caller, and the email must match their own profile
-- row — prevents posting as someone else even if the client sends a
-- different sender_email.
create policy "chat_insert_own"
  on public.chat_messages for insert
  with check (
    sender_id = auth.uid()
    and exists (
      select 1 from public.profiles
      where id = auth.uid()
        and status = 'approved'
        and email = sender_email
    )
  );

-- No update/delete policy for anyone (including admins) — messages are
-- immutable, matching "no private messaging, no inbox" simplicity; add
-- an admin-delete policy later if moderation is needed.

-- Enable Realtime broadcasts for INSERTs on this table.
alter publication supabase_realtime add table public.chat_messages;