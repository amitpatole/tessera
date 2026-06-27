"use client";

import { useEffect, useState } from "react";

const SCENES = [
  { id: "ask", label: "Ask" },
  { id: "catch", label: "Catch" },
  { id: "attest", label: "Attest" },
  { id: "save", label: "Save" },
];
const DURATION_MS = 5200;

export default function DemoPlayer() {
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(true);

  // Allow ?scene=N to pin a beat (paused) — used for strict per-scene visual inspection.
  useEffect(() => {
    const s = new URLSearchParams(window.location.search).get("scene");
    if (s !== null) {
      setI(Math.max(0, Math.min(SCENES.length - 1, parseInt(s, 10) || 0)));
      setPlaying(false);
    }
  }, []);

  useEffect(() => {
    if (!playing) return;
    const t = setTimeout(() => setI((n) => (n + 1) % SCENES.length), DURATION_MS);
    return () => clearTimeout(t);
  }, [i, playing]);

  return (
    <div className="player">
      <div className="player-stage">
        {/* key forces the fade-up animation to replay on each scene change */}
        <div className="scene" key={i}>
          {i === 0 && (
            <>
              <div className="scene-q">
                &ldquo;What was consolidated net revenue in 2025<span className="qmark">?</span>&rdquo;
              </div>
              <div className="figure-row">
                <div className="figure-xl">$5,293,985.00</div>
                <span className="badge pass">PASS</span>
              </div>
              <div className="caption">
                Plain English in. The number out — <b>with the exact SQL that produced it</b>, run on a
                read-only governed warehouse.
              </div>
            </>
          )}

          {i === 1 && (
            <>
              <div className="scene-q">
                Same question — but the model wrote a <b>subtly wrong</b> query (forgot to eliminate
                intercompany on consolidation).
              </div>
              <div className="figure-row">
                <div className="figure-xl wrong">$5,439,001.00</div>
                <span className="badge fail">FAIL</span>
              </div>
              <div className="delta">
                off by $145,016.00 · [intercompany_double_count] — caught before it reached the report
              </div>
              <div className="caption">
                A typical assistant would have shown <b>$5,439,001 as fact.</b> Tessera re-derives the
                truth independently and <b>names the mistake.</b>
              </div>
            </>
          )}

          {i === 2 && (
            <>
              <div className="receipt-card">
                <div className="rrow"><span>metric</span><b>net_revenue · consolidated · 2025</b></div>
                <div className="rrow"><span>answer</span><b>$5,293,985.00</b></div>
                <div className="rrow"><span>verdict</span><b>PASS</b></div>
                <div className="rrow"><span>signer</span><b>ed25519 · key e1bc…ca53</b></div>
              </div>
              <span className="stamp">VALID ✓ verified offline</span>
              <div className="caption">
                Every answer ships a <b>signed receipt.</b> An auditor verifies it without the warehouse
                and without trusting Tessera. Tamper with any field → INVALID.
              </div>
            </>
          )}

          {i === 3 && (
            <>
              <div className="saverow">
                <span className="tag">always-strong</span>
                <div className="savebar base"><div className="fill" style={{ width: "100%" }} /></div>
              </div>
              <div className="saverow">
                <span className="tag">Tessera cascade</span>
                <div className="savebar"><div className="fill" style={{ width: "69.5%" }} /></div>
              </div>
              <div className="figure-row" style={{ marginTop: 14 }}>
                <div className="figure-xl" style={{ fontSize: 40 }}>30.5% cheaper</div>
                <span className="badge pass">100% accuracy</span>
              </div>
              <div className="caption">
                Cheap model first; <b>escalate only when the verifier isn&rsquo;t satisfied.</b> Safe
                because every accepted answer is independently checked.
              </div>
            </>
          )}
        </div>
      </div>

      <div className="player-bar">
        <div className="dots">
          {SCENES.map((s, n) => (
            <button
              key={s.id}
              className={`dot ${n === i ? "on" : ""}`}
              aria-label={`go to ${s.label}`}
              onClick={() => { setI(n); setPlaying(false); }}
            />
          ))}
          <span className="dot-label" style={{ marginLeft: 10 }}>
            {SCENES[i].label} — {i + 1} / {SCENES.length}
          </span>
        </div>
        <button className="player-ctrl" onClick={() => setPlaying((p) => !p)}>
          {playing ? "Pause" : "Play"}
        </button>
      </div>
    </div>
  );
}
