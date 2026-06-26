export type Issue = {
  kind: string;
  severity: string;
  message: string;
  source: string;
};

export type Routing = {
  accepted_tier: string | null;
  escalations: number;
  total_cost_usd: number;
  baseline_cost_usd: number;
};

export type AskResult = {
  question: string;
  verdict: string; // "pass" | "warn" | "fail"
  answer: string | null;
  summary: string;
  executed_sql: string | null;
  issues: Issue[];
  routing: Routing | null;
  receipt: Record<string, unknown> | null;
};

export type AskOptions = { route: boolean; sign: boolean };
