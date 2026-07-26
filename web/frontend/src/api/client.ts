/**
 * Prompt Lab — axios-based API client.
 *
 * All endpoints are relative ("/api/..."), which Vite's dev server proxies to
 * http://127.0.0.1:8765 (see vite.config.ts). In production the same path is
 * served by the FastAPI backend directly.
 */
import axios, { type AxiosInstance, type AxiosResponse } from "axios";
import type {
  AppConfig,
  CaseListItem,
  CreateRunPayload,
  CreateVersionPayload,
  DiffResponse,
  RunListItem,
  RunResult,
  Version,
  VersionListItem,
} from "../types";

const http: AxiosInstance = axios.create({
  baseURL: "/api",
  timeout: 60_000,
  headers: { "Content-Type": "application/json" },
});

/** unwrap axios response -> data, keeping errors readable */
async function unwrap<T>(p: Promise<AxiosResponse<T>>): Promise<T> {
  try {
    const res = await p;
    return res.data;
  } catch (err: unknown) {
    if (axios.isAxiosError(err)) {
      const data = err.response?.data as { detail?: string } | undefined;
      const msg = data?.detail ?? err.message;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    throw err;
  }
}

/* ------------------------------------------------------------------ */
/* Versions                                                           */
/* ------------------------------------------------------------------ */

export function listVersions(): Promise<VersionListItem[]> {
  return unwrap(http.get<VersionListItem[]>("/versions"));
}

export function getVersion(id: string): Promise<Version> {
  return unwrap(http.get<Version>(`/versions/${encodeURIComponent(id)}`));
}

export function getDiff(idA: string, idB: string): Promise<DiffResponse> {
  return unwrap(
    http.get<DiffResponse>(
      `/versions/${encodeURIComponent(idA)}/${encodeURIComponent(idB)}/diff`,
    ),
  );
}

export function createVersion(
  payload: CreateVersionPayload,
): Promise<Version> {
  return unwrap(http.post<Version>("/versions", payload));
}

/* ------------------------------------------------------------------ */
/* Cases                                                              */
/* ------------------------------------------------------------------ */

export function listCases(
  collection?: string,
  type?: string,
): Promise<CaseListItem[]> {
  const params: Record<string, string> = {};
  if (collection) params.collection = collection;
  if (type) params.type = type;
  return unwrap(
    http.get<CaseListItem[]>("/cases", { params }),
  );
}

/* ------------------------------------------------------------------ */
/* Runs                                                               */
/* ------------------------------------------------------------------ */

export function listRuns(): Promise<RunListItem[]> {
  return unwrap(http.get<RunListItem[]>("/runs"));
}

export function getRun(id: string): Promise<RunResult> {
  return unwrap(http.get<RunResult>(`/runs/${encodeURIComponent(id)}`));
}

export function createRun(payload: CreateRunPayload): Promise<RunResult> {
  return unwrap(http.post<RunResult>("/runs", payload));
}

/* ------------------------------------------------------------------ */
/* Config                                                             */
/* ------------------------------------------------------------------ */

export function getConfig(): Promise<AppConfig> {
  return unwrap(http.get<AppConfig>("/config"));
}

/* ------------------------------------------------------------------ */
/* Convenience default export                                         */
/* ------------------------------------------------------------------ */

export const api = {
  listVersions,
  getVersion,
  getDiff,
  createVersion,
  listCases,
  listRuns,
  getRun,
  createRun,
  getConfig,
};

export default api;
