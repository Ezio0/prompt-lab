/**
 * DiffViewer — thin wrapper around react-diff-viewer-continued.
 *
 * Accepts a unified-diff string from the API and renders it; if no diff
 * string is provided, accepts explicit oldText/newText for ad-hoc diffs.
 */
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";
import type { ReactNode } from "react";

interface DiffViewerProps {
  /** Unified diff string (from /api/versions/{a}/{b}/diff) */
  diff?: string;
  /** Explicit old text (used when diff string not provided) */
  oldText?: string;
  /** Explicit new text */
  newText?: string;
  /** Optional title above the viewer */
  title?: string;
}

/** Split a unified-diff string into old / new text for line-based rendering */
function splitUnifiedDiff(diff: string): { oldText: string; newText: string } {
  const oldLines: string[] = [];
  const newLines: string[] = [];
  const raw = diff.replace(/\r\n/g, "\n").split("\n");

  // Skip the header lines (--- / +++) but keep @@ hunk markers out of output
  for (const line of raw) {
    if (
      line.startsWith("---") ||
      line.startsWith("+++") ||
      line.startsWith("@@") ||
      line.startsWith("diff ") ||
      line.startsWith("index ")
    ) {
      continue;
    }
    if (line.startsWith("-")) {
      oldLines.push(line.slice(1));
    } else if (line.startsWith("+")) {
      newLines.push(line.slice(1));
    } else if (line.startsWith(" ")) {
      oldLines.push(line.slice(1));
      newLines.push(line.slice(1));
    } else {
      // context-free line (e.g. empty) appears in both
      oldLines.push(line);
      newLines.push(line);
    }
  }
  return { oldText: oldLines.join("\n"), newText: newLines.join("\n") };
}

const darkStyles = {
  variables: {
    dark: {
      diffViewerBackground: "#121214",
      diffViewerColor: "#ededf0",
      addedBackground: "rgba(34, 197, 94, 0.12)",
      addedColor: "#86efac",
      removedBackground: "rgba(239, 68, 68, 0.12)",
      removedColor: "#fca5a5",
      wordAddedBackground: "rgba(34, 197, 94, 0.30)",
      wordRemovedBackground: "rgba(239, 68, 68, 0.30)",
      addedGutterBackground: "rgba(34, 197, 94, 0.08)",
      removedGutterBackground: "rgba(239, 68, 68, 0.08)",
      gutterBackground: "#121214",
      gutterBackgroundDark: "#0a0a0b",
      highlightBackground: "rgba(99, 102, 241, 0.15)",
      highlightGutterBackground: "rgba(99, 102, 241, 0.10)",
      codeFoldGutterBackground: "#1a1a1e",
      codeFoldBackground: "rgba(99, 102, 241, 0.05)",
      emptyLineBackground: "#1a1a1e",
      gutterColor: "#6b6b75",
      addedGutterColor: "#6b6b75",
      removedGutterColor: "#6b6b75",
      codeFoldContentColor: "#6b6b75",
      diffViewerTitleBackground: "#1a1a1e",
      diffViewerTitleColor: "#9a9aa3",
      diffViewerTitleBorderColor: "#2e2e34",
    },
  },
  line: { padding: "2px 10px" },
  gutter: { padding: "2px 8px", minWidth: "2.5rem" },
};

export default function DiffViewer({
  diff,
  oldText,
  newText,
  title,
}: DiffViewerProps): ReactNode {
  let o = oldText ?? "";
  let n = newText ?? "";

  if (diff && diff.trim().length > 0) {
    const parsed = splitUnifiedDiff(diff);
    o = parsed.oldText;
    n = parsed.newText;
  }

  return (
    <div className="diff-viewer-wrap overflow-hidden rounded-lg border border-[var(--border-default)] bg-[var(--bg-panel)]">
      {title && (
        <div className="border-b border-[var(--border-default)] px-4 py-2 text-xs font-medium text-[var(--text-secondary)]">
          {title}
        </div>
      )}
      <div className="overflow-auto text-[12.5px]" style={{ fontFamily: "var(--mono)" }}>
        <ReactDiffViewer
          oldValue={o}
          newValue={n}
          splitView={false}
          useDarkTheme
          hideLineNumbers={false}
          compareMethod={DiffMethod.WORDS}
          styles={darkStyles}
        />
      </div>
    </div>
  );
}
