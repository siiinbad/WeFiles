-- Day 3: admin read/write access to all profiles, via a security-definer
-- helper (avoids RLS recursion), plus a fix to the Day 2 trigger so it
-- blocks self-escalation specifically, not admin-issued approvals.
-- Run this once in the Supabase SQL Editor, after auth.sql.

-- Returns true if the calling user's own profile has role = 'admin'.
-- security definer + fixed search_path so it can read profiles even
-- though the caller's own SELECT policy wouldn't normally let it look
-- at other rows (it only reads its own row here, so this is safe).
create or replace function public.is_admin()
returns boolean
language sql
security definer
set search_path = public
stable
as $$
  select exists (
    select 1 from public.profiles
    where id = auth.uid() and role = 'admin'
  );
$$;

-- Admins can read every profile (combines with profiles_select_own via OR).
create policy "profiles_select_admin_all"
  on public.profiles for select
  using (public.is_admin());

-- Admins can update any profile row (e.g. approve/reject/disable, change
-- another user's role). Combines with profiles_update_own via OR.
create policy "profiles_update_admin_all"
  on public.profiles for update
  using (public.is_admin());

-- Fix: the Day 2 trigger blocked role/status changes on ANY row, which
-- would have also blocked admins from approving other users. It should
-- only block a user from changing their OWN role/status.
create or replace function public.prevent_role_status_self_edit()
returns trigger as $$
begin
  if auth.uid() = old.id and (new.role <> old.role or new.status <> old.status) then
    raise exception 'Not allowed to change your own role or status';
  end if;
  return new;
end;
$$ language plpgsql security definer;