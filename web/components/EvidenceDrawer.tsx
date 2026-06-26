"use client";

import { useState } from "react";
import type { AskResult } from "@/lib/types";

export default function EvidenceDrawer({ result }: { result: AskResult }) {
  const [verify, setVerify] = useState<{ valid: boolean; reason: string } | null>(null);
  const [verifying, setVerifying] = useState(false);

  const verifyReceipt = async () => {
    if (!result.receipt) return;
    setVerifying(true);
    try {
      const res = await fetch("/api/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ receipt: result.receipt }),
      });
      const data = await res.json();
      setVerify({ valid: !!data.valid, reason: data.reason ?? "" });
    } catch (e) {
      setVerify({ valid: false, reason: String(e) });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <details className="drawer" open>
      <summary>Evidence — SQL, checks, receipt</summary>
      <div className="body">
        {result.executed_sql && (
          <>
            <div className="label">Executed SQL</div>
            <pre className="sql">{result.executed_sql}</pre>
          </>
        )}

        {result.routing && (
          <>
            <div className="label">Cost cascade</div>
            <div style={{ fontSize: 13, color: "var(--ink-muted)" }}>
              accepted by <b>{result.routing.accepted_tier ?? "—"}</b>, {result.routing.escalations}{" "}
              escalation(s) · ${result.routing.total_cost_usd.toFixed(6)} vs $
              {result.routing.baseline_cost_usd.toFixed(6)} always-strong
            </div>
          </>
        )}

        {result.issues.length > 0 && (
          <>
            <div className="label">Issues</div>
            <ul className="issues">
              {result.issues.map((i, n) => (
                <li key={n}>
                  <span className="kind">[{i.kind}]</span> {i.message}
                </li>
              ))}
            </ul>
          </>
        )}

        {result.receipt && (
          <>
            <div className="label">Signed receipt</div>
            <div className="receipt-row">
              <button onClick={verifyReceipt} disabled={verifying}>
                {verifying ? "Verifying…" : "Verify offline"}
              </button>
              {verify && (
                <span className={`verify-result ${verify.valid ? "valid" : "invalid"}`}>
                  {verify.valid ? "VALID" : "INVALID"} — {verify.reason}
                </span>
              )}
            </div>
          </>
        )}
      </div>
    </details>
  );
}
