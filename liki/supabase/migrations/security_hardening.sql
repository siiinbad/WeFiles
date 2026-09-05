-- Security hardening migration:
-- 1. Pin explicit search_path on all SECURITY DEFINER functions to prevent search-path injection.
-- 2. Add database-level max content length constraint on chat messages.
-- 3. Set a file upload size limit (50 MB) on the storage bucket.
-- 4. Reload PostgREST schema cache.

-- 1. Secure functions with explicit search_path
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email);
  return new;
end;
$$;

create or replace function public.prevent_role_status_self_edit()
returns trigger
language plpgsql
security definer
set search_path = public, auth
as $$
begin
  if auth.uid() = old.id and (new.role <> old.role or new.status <> old.status) then
    raise exception 'Not allowed to change your own role or status';
  end if;
  return new;
end;
$$;

-- 2. Database-level length limit on chat messages (matching frontend max 2000 chars)
do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'chat_messages_content_len_check'
  ) then
    alter table public.chat_messages
      add constraint chat_messages_content_len_check
      check (char_length(content) <= 2000);
  end if;
end;
$$;

-- 3. Set storage bucket size limit (e.g. 50 MB per file)
update storage.buckets
set file_size_limit = 52428800
where id = 'files';

-- 4. Refresh PostgREST schema cache
notify pgrst, 'reload schema';