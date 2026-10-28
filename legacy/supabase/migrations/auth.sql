-- Day 2: profiles table, auto-provisioning trigger, and baseline RLS.
-- Run this once in the Supabase SQL Editor.

create type user_role as enum ('admin', 'member');
create type user_status as enum ('pending', 'approved', 'rejected', 'disabled');

create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text not null,
  role user_role not null default 'member',
  status user_status not null default 'pending',
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

-- Every signed-in user can read their own profile (needed to check
-- their own status/role after login).
create policy "profiles_select_own"
  on public.profiles for select
  using (auth.uid() = id);

-- Users may update their own row, but role/status changes are blocked
-- below by the trigger — this policy alone would let them edit those
-- columns, so we enforce the real restriction in a BEFORE UPDATE trigger.
create policy "profiles_update_own"
  on public.profiles for update
  using (auth.uid() = id);

-- Prevent a user from changing their own role or status via any
-- direct update (frontend or raw API call). Only a separate admin
-- path (service_role or an admin-checked policy, added Day 3) can
-- change these columns.
create function public.prevent_role_status_self_edit()
returns trigger as $$
begin
  if new.role <> old.role or new.status <> old.status then
    raise exception 'Not allowed to change role or status';
  end if;
  return new;
end;
$$ language plpgsql security definer;

create trigger trg_prevent_role_status_self_edit
  before update on public.profiles
  for each row
  execute function public.prevent_role_status_self_edit();

-- Auto-create a profile row (status='pending', role='member') whenever
-- a new auth user signs up.
create function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$ language plpgsql security definer;

create trigger trg_handle_new_user
  after insert on auth.users
  for each row
  execute function public.handle_new_user();