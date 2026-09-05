import type { ReactNode } from 'react';
import ChatPanel from './ChatPanel';
import NavBar from './NavBar';
import './Layout.css';

// Layout is only ever rendered inside pages wrapped by ProtectedRoute, so
// it's safe to assume an approved, authenticated user here. NavBar makes
// every protected page reachable from every other one — previously only
// Dashboard had navigation. Chat sits on the right on desktop, stacks
// below content on mobile.
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app-layout">
      <main id="main-content" className="app-layout__main" tabIndex={-1}>
        <NavBar />
        {children}
      </main>
      <aside className="app-layout__side" aria-label="Team chat">
        <ChatPanel />
      </aside>
    </div>
  );
}