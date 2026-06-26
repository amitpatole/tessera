"use client";

import type { AskResult } from "@/lib/types";
import EvidenceDrawer from "./EvidenceDrawer";

const VERDICT_CLASS: Record<string, string> = { pass: "pass", warn: "warn", fail: "fail" };

export default function AnswerCard({ result }: { result: AskResult }) {
  const cls = VERDICT_CLASS[result.verdict] ?? "warn";
  return (
    <section className="answer" aria-live="polite">
      <div className="answer-head">
        <div className={`figure ${result.answer ? "" : "none"}`}>
          {result.answer ?? "no certified answer"}
        </div>
        <span className={`badge ${cls}`}>{result.verdict.toUpperCase()}</span>
      </div>
      <div className="summary">{result.summary}</div>
      <EvidenceDrawer result={result} />
    </section>
  );
}
