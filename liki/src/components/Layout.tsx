import { ReactNode } from 'react';
import './Layout.css';

// Day 1: static shell only. The 15% panel becomes the global chat on Day 5;
// for now it's a placeholder so the layout proportions are locked in early.
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="app-layout">
      <aside className="app-layout__side">
        <div className="app-layout__side-placeholder">Chat (Day 5)</div>
      </aside>
      <main className="app-layout__main">{children}</main>
    </div>
  );
}