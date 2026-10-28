import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import Layout from '../components/Layout';
import FileUpload from '../components/files/FileUpload';
import FileList from '../components/files/FileList';
import ConfirmDialog from '../components/ConfirmDialog';
import { supabase } from '../lib/supabaseClient';
import { useAuth } from '../context/useAuth';
import type { FileRecord, FolderRecord } from '../types';

function normalizeFolderName(value: string) {
  return value.trim().replace(/\s+/g, ' ').replace(/[\\/]+/g, '-');
}

function joinFolderPath(parentPath: string, name: string) {
  return parentPath ? `${parentPath}/${name}` : name;
}

function parentOf(path: string) {
  const parts = path.split('/').filter(Boolean);
  parts.pop();
  return parts.join('/');
}

function breadcrumbParts(path: string) {
  const parts = path.split('/').filter(Boolean);
  return parts.map((name, index) => ({ name, path: parts.slice(0, index + 1).join('/') }));
}

function isMissingFoldersTable(message: string) {
  return /public\.folders|schema cache|could not find the table|relation .*folders.* does not exist/i.test(message);
}

function isFolderPermissionError(message: string) {
  return /permission denied.*folders|folders.*permission denied/i.test(message);
}

export default function Files() {
  const { profile, session } = useAuth();
  const [files, setFiles] = useState<FileRecord[]>([]);
  const [folders, setFolders] = useState<FolderRecord[]>([]);
  const [currentFolder, setCurrentFolder] = useState('');
  const [folderName, setFolderName] = useState('');
  const [loading, setLoading] = useState(true);
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [foldersUnavailable, setFoldersUnavailable] = useState(false);
  const [pendingDelete, setPendingDelete] = useState<FileRecord | null>(null);
  const [pendingFolderDelete, setPendingFolderDelete] = useState<FolderRecord | null>(null);

  const load = useCallback(async () => {
    const [fileResult, folderResult] = await Promise.all([
      supabase.from('files').select('*').order('created_at', { ascending: false }),
      supabase.from('folders').select('*').order('name', { ascending: true }),
    ]);

    if (fileResult.error) setError(fileResult.error.message);
    else setFiles((fileResult.data ?? []) as FileRecord[]);

    if (folderResult.error) {
      if (isMissingFoldersTable(folderResult.error.message)) {
        setFoldersUnavailable(true);
        setFolders([]);
      } else if (isFolderPermissionError(folderResult.error.message)) {
        setError('Folder table permissions are missing. Run the latest supabase/migrations/folders.sql, then refresh this page.');
      } else {
        setError(folderResult.error.message);
      }
    } else {
      setFoldersUnavailable(false);
      setFolders((folderResult.data ?? []) as FolderRecord[]);
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    // Initial remote load on mount; the state updates happen inside the async loader.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load();
  }, [load]);

  const visibleFolders = useMemo(
    () => folders.filter((folder) => folder.parent_path === currentFolder),
    [folders, currentFolder]
  );

  const visibleFiles = useMemo(
    () => files.filter((file) => (file.folder_path ?? '') === currentFolder),
    [files, currentFolder]
  );

  async function handleCreateFolder(event: FormEvent) {
    event.preventDefault();
    if (!session) return;

    if (foldersUnavailable) {
      setError('Folder support is not installed yet. Run supabase/migrations/folders.sql in Supabase, then refresh this page.');
      return;
    }

    const name = normalizeFolderName(folderName);
    if (!name) {
      setError('Enter a folder name.');
      return;
    }

    const path = joinFolderPath(currentFolder, name);
    if (folders.some((folder) => folder.path.toLowerCase() === path.toLowerCase())) {
      setError('A folder with that name already exists here.');
      return;
    }

    setCreatingFolder(true);
    setError(null);
    const { error: insertError } = await supabase.from('folders').insert({
      owner_id: session.user.id,
      name,
      path,
      parent_path: currentFolder,
    });

    setCreatingFolder(false);
    if (insertError) {
      setError(
        isFolderPermissionError(insertError.message)
          ? 'Folder table permissions are missing. Run the latest supabase/migrations/folders.sql, then refresh this page.'
          : insertError.message
      );
      return;
    }

    setFolderName('');
    await load();
  }

  async function handleDelete(f: FileRecord) {
    setBusyId(f.id);
    setError(null);
    const { error: storageError } = await supabase.storage.from('files').remove([f.storage_path]);
    if (storageError) {
      setError(storageError.message);
      setBusyId(null);
      return;
    }
    const { error: rowError } = await supabase.from('files').delete().eq('id', f.id);
    setBusyId(null);
    if (rowError) {
      setError(rowError.message);
      return;
    }
    await load();
  }

  async function handleDeleteFolder(folder: FolderRecord) {
    if (profile?.role !== 'admin') {
      setError('Only admins can delete folders.');
      return;
    }

    const hasNestedFolders = folders.some((item) => item.parent_path === folder.path);
    const hasFiles = files.some((file) => (file.folder_path ?? '') === folder.path);
    if (hasNestedFolders || hasFiles) {
      setError('Only empty folders can be deleted. Move or delete the files and nested folders first.');
      return;
    }

    setBusyId(folder.id);
    setError(null);
    const { error: deleteError } = await supabase.from('folders').delete().eq('id', folder.id);
    setBusyId(null);

    if (deleteError) {
      setError(
        isFolderPermissionError(deleteError.message)
          ? 'Only admins can delete folders. If you are an admin, run the latest supabase/migrations/folders.sql and refresh this page.'
          : deleteError.message
      );
      return;
    }

    if (currentFolder === folder.path || currentFolder.startsWith(`${folder.path}/`)) {
      setCurrentFolder(folder.parent_path);
    }
    await load();
  }

  const breadcrumbs = breadcrumbParts(currentFolder);

  return (
    <Layout>
      <span className="eyebrow">Vault</span>
      <h1>Files</h1>
      <p className="page-lede">Shared documents for approved crew members. Create folders to keep the vault organized.</p>

      <nav className="vault-breadcrumbs" aria-label="Folder breadcrumb">
        <button type="button" onClick={() => setCurrentFolder('')} aria-current={!currentFolder ? 'page' : undefined}>
          Vault root
        </button>
        {breadcrumbs.map((crumb) => (
          <button key={crumb.path} type="button" onClick={() => setCurrentFolder(crumb.path)} aria-current={crumb.path === currentFolder ? 'page' : undefined}>
            {crumb.name}
          </button>
        ))}
      </nav>

      {currentFolder && (
        <button type="button" className="vault-up-button" onClick={() => setCurrentFolder(parentOf(currentFolder))}>
          ← Up one folder
        </button>
      )}

      {foldersUnavailable && (
        <p className="auth-page__error" role="alert">
          Folder support is not installed in Supabase yet. Run <code>supabase/migrations/folders.sql</code>, then refresh this page.
        </p>
      )}
      {error && <p className="auth-page__error" role="alert">{error}</p>}

      <section className="vault-toolbar panel" aria-label="Vault actions">
        <form className="folder-create" onSubmit={handleCreateFolder}>
          <label htmlFor="folder-name">New folder</label>
          <div>
            <input id="folder-name" type="text" value={folderName} onChange={(event) => setFolderName(event.target.value)} placeholder="Folder name" disabled={creatingFolder || foldersUnavailable} maxLength={80} />
            <button type="submit" disabled={creatingFolder || foldersUnavailable}>{creatingFolder ? 'Creating…' : 'Create folder'}</button>
          </div>
        </form>
        <p>Current folder: <strong>{currentFolder || 'Vault root'}</strong></p>
      </section>

      <FileUpload currentFolder={currentFolder} onUploaded={load} />
      {loading ? (
        <p className="empty-placeholder">Loading files…</p>
      ) : (
        <FileList
          folders={visibleFolders}
          files={visibleFiles}
          currentFolder={currentFolder}
          isAdmin={profile?.role === 'admin'}
          onOpenFolder={setCurrentFolder}
          onRequestDelete={setPendingDelete}
          onRequestDeleteFolder={setPendingFolderDelete}
          busyId={busyId}
        />
      )}
      {pendingDelete && (
        <ConfirmDialog
          title="Delete file?"
          message={`"${pendingDelete.file_name}" will be permanently removed for everyone.`}
          confirmLabel="Delete"
          onCancel={() => setPendingDelete(null)}
          onConfirm={() => {
            handleDelete(pendingDelete);
            setPendingDelete(null);
          }}
        />
      )}
      {pendingFolderDelete && (
        <ConfirmDialog
          title="Delete folder?"
          message={`"${pendingFolderDelete.name}" will be permanently removed. Only empty folders can be deleted.`}
          confirmLabel="Delete folder"
          onCancel={() => setPendingFolderDelete(null)}
          onConfirm={() => {
            handleDeleteFolder(pendingFolderDelete);
            setPendingFolderDelete(null);
          }}
        />
      )}
    </Layout>
  );
}
