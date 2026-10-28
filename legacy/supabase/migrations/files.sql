-- Day 4: file storage. Run once in the Supabase SQL Editor, after admin.sql.

-- Metadata table. The actual bytes live in Storage; this row tracks who
-- uploaded what and lets us list/query without hitting Storage directly.
create table public.files (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users (id) on delete cascade,
  storage_path text not null unique,
  file_name text not null,
  size_bytes bigint,
  content_type text,
  created_at timestamptz not null default now()
);

alter table public.files enable row level security;

-- Any approved member or admin can see the full file list (it's a shared
-- team drive, not per-user folders). Approval status still gates access
-- to the app at all via ProtectedRoute + the fact that Storage checks
-- the same "approved" condition below.
create policy "files_select_approved"
  on public.files for select
  using (
    exists (
      select 1 from public.profiles
      where id = auth.uid() and status = 'approved'
    )
  );

-- Only the uploader can insert a row for themselves — owner_id must
-- match the caller, so no one can claim a file as uploaded by someone
-- else, and only approved users can upload at all.
create policy "files_insert_own"
  on public.files for insert
  with check (
    owner_id = auth.uid()
    and exists (
      select 1 from public.profiles
      where id = auth.uid() and status = 'approved'
    )
  );

-- Only admins can delete file metadata rows. Members cannot delete their
-- own uploads, per the spec.
create policy "files_delete_admin_only"
  on public.files for delete
  using (public.is_admin());

-- No update policy is created — file metadata is immutable after upload,
-- which is intentional (re-uploading creates a new row/file instead).

-- Storage bucket. Private (not public) — access is controlled entirely
-- by the storage policies below, not by a public URL.
insert into storage.buckets (id, name, public)
values ('files', 'files', false);

-- Approved users (admin or member) can read any object in the bucket.
create policy "storage_files_select_approved"
  on storage.objects for select
  using (
    bucket_id = 'files'
    and exists (
      select 1 from public.profiles
      where id = auth.uid() and status = 'approved'
    )
  );

-- Approved users can upload, but only into a path prefixed with their
-- own user id (storage_path = '<uid>/<filename>'), enforced here so
-- ownership can't be spoofed at the storage layer either.
create policy "storage_files_insert_own_prefix"
  on storage.objects for insert
  with check (
    bucket_id = 'files'
    and (storage.foldername(name))[1] = auth.uid()::text
    and exists (
      select 1 from public.profiles
      where id = auth.uid() and status = 'approved'
    )
  );

-- Only admins can delete storage objects — mirrors the files table policy,
-- so a member can't bypass the metadata-row restriction by deleting the
-- underlying object directly.
create policy "storage_files_delete_admin_only"
  on storage.objects for delete
  using (bucket_id = 'files' and public.is_admin());