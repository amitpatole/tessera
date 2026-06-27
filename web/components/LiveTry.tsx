"use client";

import { useState } from "react";
import QuestionBar from "./QuestionBar";
import AnswerCard from "./AnswerCard";
import type { AskOptions, AskResult } from "@/lib/types";

export default function LiveTry() {
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
    <>
      <QuestionBar onAsk={ask} loading={loading} />
      {error && (
        <p style={{ color: "var(--fail)", fontSize: 14, marginTop: 20 }}>
          Could not reach the verifier: {error}
        </p>
      )}
      {result && <AnswerCard result={result} />}
    </>
  );
}
