"use client";

import { useState } from "react";
import QuestionBar from "@/components/QuestionBar";
import AnswerCard from "@/components/AnswerCard";
import type { AskOptions, AskResult } from "@/lib/types";

export default function Home() {
  const [result, setResult] = useState<AskResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ask = async (question: string, opts: AskOptions) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, route: opts.route, sign: opts.sign }),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setResult((await res.json()) as AskResult);
    } catch (e) {
      setError(String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <div className="eyebrow">Attested analytics · regulated finance</div>
      <h1>Tessera</h1>
      <p className="lede">
        Ask a finance question in plain English. Get the number — and the evidence it is right: the
        executed SQL, an independent verdict, and a signed receipt you can verify offline.
      </p>

      <QuestionBar onAsk={ask} loading={loading} />

      {error && (
        <p style={{ color: "var(--fail)", fontSize: 14, marginTop: 20 }}>
          Could not reach the verifier: {error}
        </p>
      )}

      {result && <AnswerCard result={result} />}
    </main>
  );
}
