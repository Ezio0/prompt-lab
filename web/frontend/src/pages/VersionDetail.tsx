/**
 * VersionDetail — shows prompt text + metadata, and a diff selector to
 * compare this version against any other version.
 */
import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { ReactNode } from "react";
import { getDiff, getVersion, listVersions } from "../api/client";
import type { VersionListItem } from "../types";
import DiffViewer from "../components/DiffViewer";

export default function VersionDetail(): ReactNode {
  const { id } = useParams<{ id: string }>();
  const [version, setVersion] = useState<Awaited<ReturnType<typeof getVersion>> | null>(null);
  const [others, setOthers] = useState<VersionListItem[]>([]);
  const [otherId, setOtherId] = useState<string>("");
  const [diff, setDiff] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [diffLoading, setDiffLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setDiff(null);
      try {
        const [v, all] = await Promise.all([
          getVersion(id),
          listVersions().catch(() => [] as VersionListItem[]),
        ]);
        if (cancelled) return;
        setVersion(v);
        const filtered = all.filter((x) => x.id !== id);
        setOthers(filtered);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // Fetch diff whenever otherId changes
  useEffect(() => {
    if (!id || !otherId) {
      setDiff(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setDiffLoading(true);
      try {
        // order ids so request path is stable; API returns unified diff
        const res = await getDiff(id, otherId);
        if (!cancelled) setDiff(res.diff ?? "");
      } catch (e) {
        if (!cancelled)
          setDiff(
            `--- error fetching diff ---\n${e instanceof Error ? e.message : String(e)}`,
          );
      } finally {
        if (!cancelled) setDiffLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id, otherId]);

  const promptLines = useMemo(() => {
    return version?.prompt_text?.split("\n").length ?? 0;
  }, [version]);

  if (loading) {
    return (
      <div className="flex h-48 items-center justify-center text-[var(--text-muted)]">
        Loading version…
      </div>
    );
  }

  if (error || !version) {
    return (
      <div className="space-y-4">
        <Link to="/versions" className="text-sm text-indigo-400 hover:underline">
          ← back to versions
        </Link>
        <div className="rounded-md border border-rose-800 bg-rose-950/40 px-4 py-3 text-sm text-rose-300">
          {error ?? "Version not found."}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <Link to="/versions" className="text-sm text-indigo-400 hover:underline">
          ← versions
        </Link>
      </div>

      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-baseline gap-3">
          <h1 className="font-mono text-xl font-semibold text-indigo-300">
            {version.id}
          </h1>
          <span className="text-xs text-[var(--text-muted)]">
            {version.name}
          </span>
        </div>
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-[var(--text-secondary)]">
          <span>
            <span className="text-[var(--text-muted)]">hash:</span>{" "}
            <span className="font-mono">{version.content_hash}</span>
          </span>
          <span>
            <span className="text-[var(--text-muted)]">author:</span>{" "}
            {version.author || "—"}
          </span>
          <span>
            <span className="text-[var(--text-muted)]">timestamp:</span>{" "}
            {version.timestamp}
          </span>
          <span>
            <span className="text-[var(--text-muted)]">lines:</span>{" "}
            {promptLines}
          </span>
          {version.changed_var && (
            <span>
              <span className="text-[var(--text-muted)]">changed_var:</span>{" "}
              <span className="font-mono text-amber-300">{version.changed_var}</span>
            </span>
          )}
          {version.changed_from && (
            <span>
              <span className="text-[var(--text-muted)]">from:</span>{" "}
              <Link
                to={`/versions/${encodeURIComponent(version.changed_from)}`}
                className="font-mono text-indigo-400 hover:underline"
              >
                {version.changed_from}
              </Link>
            </span>
          )}
        </div>
        {version.change_note && (
          <p className="text-sm italic text-[var(--text-secondary)]">
            “{version.change_note}”
          </p>
        )}
      </div>

      {/* Prompt text */}
      <div className="overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--bg-panel)]">
        <div className="border-b border-[var(--border-default)] px-4 py-2 text-xs font-medium uppercase tracking-wider text-[var(--text-muted)]">
          prompt_text
        </div>
        <pre
          className="max-h-[480px] overflow-auto px-4 py-3 text-[12.5px] leading-relaxed text-[var(--text-primary)]"
          style={{ fontFamily: "var(--mono)" }}
        >
          {version.prompt_text}
        </pre>
      </div>

      {/* Diff selector */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <label
            htmlFor="diff-select"
            className="text-sm font-medium text-[var(--text-secondary)]"
          >
            Compare with:
          </label>
          <select
            id="diff-select"
            value={otherId}
            onChange={(e) => setOtherId(e.target.value)}
            className="rounded-md border border-[var(--border-default)] bg-[var(--bg-elevated)] px-3 py-1.5 text-sm text-[var(--text-primary)] outline-none focus:border-indigo-500"
          >
            <option value="">— select version —</option>
            {others.map((o) => (
              <option key={o.id} value={o.id}>
                {o.id} {o.change_note ? `(${o.change_note})` : ""}
              </option>
            ))}
          </select>
          {diffLoading && (
            <span className="text-xs text-[var(--text-muted)]">computing diff…</span>
          )}
        </div>

        {otherId && !diffLoading && diff !== null && (
          <DiffViewer
            diff={diff}
            title={`${version.id} ← → ${otherId}`}
          />
        )}
      </div>
    </div>
  );
}
