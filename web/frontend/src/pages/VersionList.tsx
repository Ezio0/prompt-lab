/**
 * VersionList — table of all prompt versions; click row → detail.
 */
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { listVersions } from "../api/client";
import type { VersionListItem } from "../types";

function fmtTime(ts: string): string {
  try {
    const d = new Date(ts);
    if (Number.isNaN(d.getTime())) return ts;
    return d.toLocaleString(undefined, {
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return ts;
  }
}

function shortHash(h: string): string {
  return h ? h.slice(0, 10) : "—";
}

export default function VersionList(): ReactNode {
  const navigate = useNavigate();
  const [items, setItems] = useState<VersionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await listVersions();
        if (!cancelled) setItems(data ?? []);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">
            Versions
          </h1>
          <p className="text-xs text-[var(--text-muted)]">
            {items.length} prompt {items.length === 1 ? "version" : "versions"}
          </p>
        </div>
        <Link
          to="/editor"
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-indigo-500"
        >
          + New Version
        </Link>
      </div>

      {error && (
        <div className="rounded-md border border-rose-800 bg-rose-950/40 px-4 py-3 text-sm text-rose-300">
          <span className="font-mono">error:</span> {error}
        </div>
      )}

      <div className="overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--bg-panel)]">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[var(--border-default)] bg-[var(--bg-elevated)] text-xs uppercase tracking-wider text-[var(--text-muted)]">
            <tr>
              <th className="px-4 py-2 font-medium">Version</th>
              <th className="px-4 py-2 font-medium">Hash</th>
              <th className="px-4 py-2 font-medium">Timestamp</th>
              <th className="px-4 py-2 font-medium">Author</th>
              <th className="px-4 py-2 font-medium">Changed Var</th>
              <th className="px-4 py-2 font-medium">Note</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[var(--text-muted)]">
                  Loading…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && !error && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-[var(--text-muted)]">
                  No versions yet — create one in the Editor.
                </td>
              </tr>
            )}
            {items.map((v) => (
              <tr
                key={v.id}
                onClick={() => navigate(`/versions/${encodeURIComponent(v.id)}`)}
                className="cursor-pointer border-b border-[var(--border-subtle)] transition-colors last:border-0 hover:bg-[var(--bg-elevated)]"
              >
                <td className="px-4 py-2 font-mono text-indigo-300">{v.id}</td>
                <td className="px-4 py-2 font-mono text-xs text-[var(--text-secondary)]">
                  {shortHash(v.content_hash)}
                </td>
                <td className="px-4 py-2 text-[var(--text-secondary)]">
                  {fmtTime(v.timestamp)}
                </td>
                <td className="px-4 py-2 text-[var(--text-secondary)]">
                  {v.author || "—"}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-amber-300">
                  {v.changed_var || "—"}
                </td>
                <td className="max-w-xs truncate px-4 py-2 text-[var(--text-secondary)]">
                  {v.change_note || "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
