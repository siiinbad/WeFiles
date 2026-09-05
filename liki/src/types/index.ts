export type UserRole = 'admin' | 'member';
export type UserStatus = 'pending' | 'approved' | 'rejected' | 'disabled';

// Mirrors the `profiles` table introduced on Day 2. Defined now so
// components can be typed correctly as they're built out.
export interface Profile {
  id: string;
  email: string;
  username: string;
  role: UserRole;
  status: UserStatus;
  created_at: string;
}

// Mirrors the `folders` table. Folders are shared across approved users
// and are represented by normalized slash-separated paths, e.g. "docs/hr".
export interface FolderRecord {
  id: string;
  owner_id: string;
  name: string;
  path: string;
  parent_path: string;
  created_at: string;
}

// Mirrors the `files` table introduced on Day 4.
export interface FileRecord {
  id: string;
  owner_id: string;
  storage_path: string;
  file_name: string;
  folder_path: string;
  size_bytes: number | null;
  content_type: string | null;
  created_at: string;
}

// Mirrors the `chat_messages` table introduced on Day 5.
export interface ChatMessage {
  id: string;
  sender_id: string;
  sender_email: string;
  content: string;
  created_at: string;
}