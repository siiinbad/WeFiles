import { createContext } from 'react';
import type { Session } from '@supabase/supabase-js';
import type { Profile } from '../types';

export interface AuthContextValue {
  session: Session | null;
  profile: Profile | null;
  loading: boolean;
  refreshProfile: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
