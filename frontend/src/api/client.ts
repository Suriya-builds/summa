// Typed API client. The session lives in an HTTP-only cookie, so no token is handled here.

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(method: string, path: string, body?: unknown, isForm = false): Promise<T> {
  const init: RequestInit = { method, credentials: "same-origin", headers: {} };
  if (body !== undefined) {
    if (isForm) init.body = body as FormData;
    else {
      (init.headers as Record<string, string>)["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
  }
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError(0, "Could not reach the server. Check that it is running and try again.");
  }
  if (res.status === 401 && !path.startsWith("/api/auth/")) {
    window.dispatchEvent(new Event("summa:unauthorized"));
  }
  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = data && typeof data.detail === "string" ? data.detail : `Request failed (${res.status}).`;
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export const api = {
  get: <T>(p: string) => request<T>("GET", p),
  post: <T>(p: string, b?: unknown) => request<T>("POST", p, b ?? {}),
  put: <T>(p: string, b?: unknown) => request<T>("PUT", p, b),
  patch: <T>(p: string, b?: unknown) => request<T>("PATCH", p, b),
  del: <T>(p: string) => request<T>("DELETE", p),
  upload: <T>(p: string, form: FormData) => request<T>("POST", p, form, true),
};

// ---- types -----------------------------------------------------------------

export interface User { id: number; name: string; email: string; is_demo: boolean }

export interface Txn {
  id: number; date: string; amount: number; direction: "debit" | "credit"; counterparty: string;
  category: string; category_label: string; category_source: string; category_confidence: number;
  channel: string; account_tail: string | null; balance: number | null; reference: string | null;
  note: string | null; message_id: number | null;
}

export interface CategoryRow {
  category: string; label: string; amount: number; count: number; share: number;
  previous_amount: number; change_pct: number | null; counts_as_spend: boolean;
}

export interface Summary {
  month: string; has_data: boolean;
  progress: { days_total: number; days_elapsed: number; is_current: boolean; is_complete: boolean };
  income: number; spend: number; invested: number; saved: number; savings_rate: number | null;
  transaction_count: number; average_daily_spend: number;
  previous: { month: string; income: number; spend: number; same_period_spend: number; compared_days: number | null };
  spend_change_pct: number | null;
  by_category: CategoryRow[];
  daily: { date: string; spend: number; income: number; cumulative_spend: number }[];
  top_merchants: { counterparty: string; amount: number; count: number; category: string; category_label: string }[];
  by_channel: { channel: string; amount: number }[];
  largest_expense: Txn | null;
}

export interface Insight { kind: string; tone: "good" | "warn" | "info"; title: string; detail: string; data: Record<string, unknown> }

export interface RecurringItem {
  counterparty: string; category: string; category_label: string; amount: number; occurrences: number;
  last_date: string; next_expected: string; overdue: boolean; kind: "subscription" | "bill" | "commitment";
}

export interface BudgetItem {
  category: string; label: string; limit: number; spent: number; remaining: number | null;
  percent: number | null; projected: number; status: "ok" | "warning" | "over" | "unbudgeted";
}
export interface BudgetStatus {
  month: string; progress: Summary["progress"]; has_budget: boolean; total_limit: number; total_spent: number;
  budgeted_spent: number; total_remaining: number; daily_allowance: number | null; items: BudgetItem[];
}
export interface BudgetSuggestions {
  basis_months: string[]; basis_is_partial: boolean; excluded_one_offs: { counterparty: string; amount: number; date: string }[];
  items: { category: string; label: string; average: number; suggested: number; saving: number; reason: string }[];
  total_suggested: number; total_average: number; monthly_saving: number; average_income: number;
  left_after_budget: number; exceeds_income: boolean;
}

export interface ScamReason { code: string; weight: number; text: string }
export interface ScamAlert {
  id: number; sender: string; body: string; received_at: string; score: number;
  level: "safe" | "suspicious" | "dangerous"; reasons: ScamReason[]; advice: string; dismissed: boolean;
}
export interface ScamVerdict {
  score: number; level: "safe" | "suspicious" | "dangerous"; reasons: ScamReason[]; rule_score: number;
  ml_probability: number | null; advice: string; links: string[]; ai_explanation: string | null; ai_error: string | null;
}

export interface ImportResult {
  received: number; imported: number; duplicates: number; skipped_over_limit: number; transactions: number;
  scams: number; otps: number; promos: number; others: number; llm_parsed: number; llm_error: string | null;
  first_date: string | null; last_date: string | null; unparsed_money_messages: number;
}

export interface ChatTurn {
  id: number; role: "user" | "assistant"; content: string; created_at: string;
  citations?: Txn[]; tools?: { name: string; input: Record<string, unknown>; ok: boolean; error?: string }[];
  figure_check?: { checked: number; verified: number; unverified: string[] };
}

export interface Meta {
  categories: { expense: { id: string; label: string; counts_as_spend: boolean; discretionary: boolean }[]; income: { id: string; label: string }[] };
  llm: { enabled: boolean; provider: string; model: string | null; setup_hint: string | null };
  models: Record<string, Record<string, unknown>>;
}
