"use client";

import { useState } from "react";
import type { AskOptions } from "@/lib/types";

const EXAMPLES = [
  "What was consolidated net revenue in 2025?",
  "net revenue for ACME Brazil in 2025",
  "consolidated EBITDA in 2025",
];

export default function QuestionBar({
  onAsk,
  loading,
}: {
  onAsk: (question: string, opts: AskOptions) => void;
  loading: boolean;
}) {
  const [question, setQuestion] = useState("");
  const [route, setRoute] = useState(false);
  const [sign, setSign] = useState(true);

  const submit = (q: string) => {
    const value = q.trim();
    if (value) onAsk(value, { route, sign });
  };

  return (
    <div className="qbar">
      <div className="qrow">
        <input
          type="text"
          placeholder="Ask a finance question…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit(question)}
          aria-label="finance question"
        />
        <button onClick={() => submit(question)} disabled={loading}>
          {loading ? "Verifying…" : "Ask"}
        </button>
      </div>
      <div className="toggles">
        <label>
          <input type="checkbox" checked={route} onChange={(e) => setRoute(e.target.checked)} />
          cost cascade
        </label>
        <label>
          <input type="checkbox" checked={sign} onChange={(e) => setSign(e.target.checked)} />
          signed receipt
        </label>
      </div>
      <div className="examples">
        {EXAMPLES.map((ex) => (
          <button key={ex} onClick={() => { setQuestion(ex); submit(ex); }}>
            {ex}
          </button>
        ))}
      </div>
    </div>
  );
}
