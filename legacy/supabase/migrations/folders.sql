-- Shared folders for the file vault. Run after files.sql.

-- Add a logical folder path to file metadata. Empty string means the vault root.
alter table public.files
  add column if not exists folder_path text not null default '';

create index if not exists files_folder_path_idx on public.files (folder_path);

create table if not exists public.folders (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users (id) on delete cascade,
  name text not null check (
    char_length(trim(name)) between 1 and 80
    and name !~ '[\\/]'
  ),
  path text not null unique check (path <> '' and path !~ '(^/|/$|//)'),
  parent_path text not null default '' check (parent_path !~ '(^/|/$|//)'),
  created_at timestamptz not null default now(),
  constraint folders_path_matches_parent_name check (
    path = case
      when parent_path = '' then name
      else parent_path || '/' || name
    end
  )
);

alter table public.folders enable row level security;

-- Supabase/PostgREST calls still need table privileges in addition to RLS.
-- RLS decides which rows are visible/writable after these grants allow access
-- to the table itself.
grant select, insert on public.folders to authenticated;
grant delete on public.folders to authenticated;

create policy "folders_select_approved"
  on public.folders for select
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid() and status = 'approved'
    )
  );

create policy "folders_insert_own"
  on public.folders for insert
  with check (
    owner_id = auth.uid()
    and exists (
      select 1 from public.profiles
      where id = auth.uid() and status = 'approved'
    )
  );

-- Admins may clean up folder records. The app only allows deleting empty
-- folders so files/nested folders are not stranded under an invisible path.
create policy "folders_delete_admin_only"
  on public.folders for delete
  using (public.is_admin());

-- Ask PostgREST/Supabase API to refresh its schema cache immediately.
notify pgrst, 'reload schema';
