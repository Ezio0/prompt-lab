/**
 * App — top-level shell with nav + React Router routes.
 *
 * Routes:
 *   /versions        — version list
 *   /versions/:id    — version detail
 *   /runs            — run list
 *   /runs/:id        — run report
 *   /editor          — prompt editor
 *   /                — redirect to /versions
 */
import type { ReactNode } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import VersionList from "./pages/VersionList";
import VersionDetail from "./pages/VersionDetail";
import RunList from "./pages/RunList";
import RunReport from "./pages/RunReport";
import PromptEditor from "./pages/PromptEditor";

function NavLink({ to, label }: { to: string; label: string }): ReactNode {
  const { pathname } = useLocation();
  const active = pathname === to || pathname.startsWith(to + "/");
  return (
    <Link
      to={to}
      className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
        active
          ? "bg-[var(--accent-soft)] text-indigo-300"
          : "text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]"
      }`}
    >
      {label}
    </Link>
  );
}

function Layout(): ReactNode {
  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-primary)]">
      <header className="sticky top-0 z-20 flex h-12 items-center justify-between border-b border-[var(--border-subtle)] bg-[var(--bg-base)]/90 px-6 backdrop-blur">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-semibold tracking-tight text-indigo-400">
            prompt-lab
          </span>
          <span className="text-xs text-[var(--text-muted)]">v2.0</span>
        </div>
        <nav className="flex items-center gap-1">
          <NavLink to="/versions" label="Versions" />
          <NavLink to="/runs" label="Runs" />
          <NavLink to="/editor" label="Editor" />
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl px-6 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/versions" replace />} />
          <Route path="/versions" element={<VersionList />} />
          <Route path="/versions/:id" element={<VersionDetail />} />
          <Route path="/runs" element={<RunList />} />
          <Route path="/runs/:id" element={<RunReport />} />
          <Route path="/editor" element={<PromptEditor />} />
          <Route path="*" element={<Navigate to="/versions" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App(): ReactNode {
  return <Layout />;
}
