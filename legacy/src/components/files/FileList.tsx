import type { FileRecord, FolderRecord } from '../../types';
import { supabase } from '../../lib/supabaseClient';

interface Props {
  folders: FolderRecord[];
  files: FileRecord[];
  currentFolder: string;
  isAdmin: boolean;
  onOpenFolder: (path: string) => void;
  onRequestDelete: (file: FileRecord) => void;
  onRequestDeleteFolder: (folder: FolderRecord) => void;
  busyId: string | null;
}

function formatSize(bytes: number | null) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function FileList({
  folders,
  files,
  currentFolder,
  isAdmin,
  onOpenFolder,
  onRequestDelete,
  onRequestDeleteFolder,
  busyId,
}: Props) {
  async function handleDownload(f: FileRecord) {
    const { data, error } = await supabase.storage.from('files').download(f.storage_path);
    if (error || !data) {
      alert(error?.message ?? 'Download failed');
      return;
    }
    const url = URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url;
    a.download = f.file_name;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (folders.length === 0 && files.length === 0) {
    return (
      <p className="empty-placeholder">
        {currentFolder
          ? 'This folder is empty. Upload a file here or create a nested folder.'
          : 'No files or folders yet. Create a folder or upload a file to get started.'}
      </p>
    );
  }

  return (
    <ul className="admin-list vault-list">
      {folders.map((folder) => (
        <li key={folder.id} className="admin-list__row vault-list__folder">
          <button
            type="button"
            className="vault-list__folder-button"
            onClick={() => onOpenFolder(folder.path)}
          >
            <span className="vault-list__icon" aria-hidden="true">📁</span>
            <span>
              <strong>{folder.name}</strong>
              <span className="admin-list__tag">Folder</span>
            </span>
          </button>
          {isAdmin && (
            <div className="admin-list__actions vault-list__folder-actions">
              <button
                type="button"
                className="admin-list__danger"
                disabled={busyId === folder.id}
                onClick={() => onRequestDeleteFolder(folder)}
              >
                Delete
              </button>
            </div>
          )}
        </li>
      ))}
      {files.map((f) => (
        <li key={f.id} className="admin-list__row">
          <span className="vault-list__file-name">
            <span className="vault-list__icon" aria-hidden="true">📄</span>
            <span>
              <strong>{f.file_name}</strong>{' '}
              <span className="admin-list__tag">{formatSize(f.size_bytes)}</span>
            </span>
          </span>
          <div className="admin-list__actions">
            <button type="button" onClick={() => handleDownload(f)}>Download</button>
            {isAdmin && (
              <button
                type="button"
                className="admin-list__danger"
                disabled={busyId === f.id}
                onClick={() => onRequestDelete(f)}
              >
                Delete
              </button>
            )}
          </div>
        </li>
      ))}
    </ul>
  );
}