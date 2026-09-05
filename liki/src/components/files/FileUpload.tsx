import { useRef, useState } from 'react';
import type { ChangeEvent, DragEvent, KeyboardEvent } from 'react';
import { supabase } from '../../lib/supabaseClient';
import { useAuth } from '../../context/useAuth';

interface Props {
  currentFolder: string;
  onUploaded: () => void;
}

function cleanFileName(name: string) {
  return name.replace(/[\\/]+/g, '-');
}

export default function FileUpload({ currentFolder, onUploaded }: Props) {
  const { session } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function upload(file: File) {
    if (!session) return;

    setUploading(true);
    setError(null);

    const safeName = cleanFileName(file.name);
    const folderPrefix = currentFolder ? `${currentFolder}/` : '';
    const path = `${session.user.id}/${folderPrefix}${Date.now()}-${safeName}`;
    const { error: uploadError } = await supabase.storage.from('files').upload(path, file);

    if (uploadError) {
      setError(uploadError.message);
      setUploading(false);
      return;
    }

    const { error: insertError } = await supabase.from('files').insert({
      owner_id: session.user.id,
      storage_path: path,
      file_name: file.name,
      folder_path: currentFolder,
      size_bytes: file.size,
      content_type: file.type || null,
    });

    setUploading(false);
    if (insertError) {
      await supabase.storage.from('files').remove([path]);
      setError(insertError.message);
      return;
    }
    onUploaded();
  }

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (file) await upload(file);
  }

  function handleDrag(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    if (uploading) return;
    setDragActive(event.type === 'dragenter' || event.type === 'dragover');
  }

  async function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    if (!uploading && event.dataTransfer.files[0]) await upload(event.dataTransfer.files[0]);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (!uploading && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      inputRef.current?.click();
    }
  }

  return (
    <div className="file-upload">
      <div
        className={`file-upload__dropzone${dragActive ? ' file-upload__dropzone--active' : ''}`}
        role="button"
        tabIndex={uploading ? -1 : 0}
        aria-disabled={uploading}
        onClick={() => !uploading && inputRef.current?.click()}
        onKeyDown={handleKeyDown}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
      >
        <input
          ref={inputRef}
          type="file"
          onChange={handleChange}
          disabled={uploading}
          aria-label="Choose a file to upload"
          hidden
        />
        <span className="file-upload__icon" aria-hidden="true">{uploading ? '↻' : '↑'}</span>
        <strong>{uploading ? 'Uploading file…' : dragActive ? 'Drop file here' : 'Upload a file'}</strong>
        <span>
          {uploading
            ? 'Please keep this page open.'
            : `Drag and drop, or click to browse. Destination: ${currentFolder || 'Vault root'}.`}
        </span>
      </div>
      {error && <p className="auth-page__error" role="alert">{error}</p>}
    </div>
  );
}
