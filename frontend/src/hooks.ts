import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "./api/client";

/** Fetch JSON for a path; re-fetches when the path changes. Pass null to skip. */
export function useApi<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(!!path);
  const seq = useRef(0);

  const load = useCallback(async () => {
    if (!path) { setLoading(false); return; }
    const id = ++seq.current;
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<T>(path);
      if (id === seq.current) setData(result);
    } catch (e) {
      if (id === seq.current) setError(e instanceof ApiError ? e.message : "Something went wrong.");
    } finally {
      if (id === seq.current) setLoading(false);
    }
  }, [path]);

  useEffect(() => { void load(); }, [load]);
  return { data, error, loading, reload: load, setData };
}

export function errorMessage(e: unknown): string {
  return e instanceof ApiError ? e.message : e instanceof Error ? e.message : "Something went wrong.";
}
