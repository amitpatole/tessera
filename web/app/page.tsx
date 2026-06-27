import DemoPlayer from "@/components/DemoPlayer";
import LiveTry from "@/components/LiveTry";

const REPO = "https://github.com/amitpatole/tessera";

function Mosaic() {
  // Crisp, on-brand tessera-tile motif (shapes only — no text to clip).
  const tiles: { x: number; y: number; o: number }[] = [];
  for (let r = 0; r < 7; r++)
    for (let c = 0; c < 5; c++)
      if ((r * 5 + c) % 3 !== 0) tiles.push({ x: c * 84, y: r * 60, o: 0.06 + ((r + c) % 4) * 0.05 });
  return (
    <svg className="mosaic" viewBox="0 0 420 420" aria-hidden="true">
      {tiles.map((t, i) => (
        <rect key={i} x={t.x} y={t.y} width="72" height="48" rx="3" fill="#4f8a7b" opacity={t.o} />
      ))}
    </svg>
  );
}

export default function Home() {
  return (
    <main className="landing">
      {/* HERO */}
      <section className="hero">
        <div className="wrap">
          <Mosaic />
          <div className="inner">
            <div className="kicker">Attested analytics · regulated finance</div>
            <h1>
              Every number, <span className="accent-word">proven</span> — not promised.
            </h1>
            <p className="hero-sub">
              Ask a finance question in plain English. Get the answer <b>with the evidence it&rsquo;s
              right</b>: the executed SQL, an independent runtime verdict, and a signed receipt your
              auditors verify offline. <b>A confidently wrong number is worse than no number</b> — so
              we prove every one.
            </p>
            <div className="cta-row">
              <a className="btn btn-primary" href="#demo">Watch it catch a wrong number</a>
              <a className="btn btn-ghost" href="#try">Try it live</a>
            </div>
            <div className="trust-strip">
              <span>Deploy in your VPC or fully air-gapped</span>
              <span>No data leaves your boundary</span>
              <span>Audit-ready by default</span>
            </div>
          </div>
        </div>
      </section>

      {/* KPI BAND */}
      <section className="wrap" style={{ paddingTop: 8 }}>
        <div className="kpis">
          <div className="kpi">
            <div className="kpi-num">100%</div>
            <div className="kpi-label">accuracy on accepted answers</div>
            <div className="kpi-foot">the verifier guarantees it</div>
          </div>
          <div className="kpi">
            <div className="kpi-num">8 / 8</div>
            <div className="kpi-label">finance error classes caught</div>
            <div className="kpi-foot">intercompany, FX, grain, sign…</div>
          </div>
          <div className="kpi">
            <div className="kpi-num">30.5%</div>
            <div className="kpi-label">model cost saved</div>
            <div className="kpi-foot">cheap-first, escalate on doubt</div>
          </div>
          <div className="kpi">
            <div className="kpi-num">$145K</div>
            <div className="kpi-label">error caught in the demo</div>
            <div className="kpi-foot">before it reached a report</div>
          </div>
        </div>
      </section>

      {/* THE PLAYER */}
      <section className="section" id="demo">
        <div className="wrap">
          <div className="kicker">See it work</div>
          <h2>The whole pitch, in four beats</h2>
          <p className="sub">
            The third beat is the one that sells it: a wrong number, caught by name, before anyone
            acts on it.
          </p>
          <DemoPlayer />
        </div>
      </section>

      {/* THE PROBLEM */}
      <section className="section">
        <div className="wrap-narrow">
          <div className="kicker">Why it matters</div>
          <h2>Finance already has chatbots. It doesn&rsquo;t have trust.</h2>
          <p className="sub">
            Today&rsquo;s assistants prove themselves <b>offline</b> — &ldquo;95% accurate on a
            benchmark.&rdquo; In a regulated report that means <b>5% is wrong and you don&rsquo;t know
            which 5%</b>, and the cost of that 5% is a restatement or an audit finding — not a shrug.
            So finance either distrusts the tool or pays an analyst to re-check every number, which
            kills self-service. Tessera removes the blocker: it proves <b>each answer, at runtime.</b>
          </p>
        </div>
      </section>

      {/* DIFFERENTIATOR */}
      <section className="section">
        <div className="wrap">
          <div className="kicker">The difference is structural</div>
          <h2>Not a better chatbot — the trust layer underneath it</h2>
          <table className="compare">
            <thead>
              <tr>
                <th></th>
                <th>Generic copilot</th>
                <th>Text-to-SQL assistant</th>
                <th className="col-us">Tessera</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>Runs real SQL on governed data</td><td className="no">no</td><td className="yes">yes</td><td className="col-us yes">yes</td></tr>
              <tr><td>Proves <i>this</i> answer correct, at runtime</td><td className="no">no</td><td className="no">offline only</td><td className="col-us yes">yes — per answer</td></tr>
              <tr><td>Catches named finance mistakes</td><td className="no">no</td><td className="no">no</td><td className="col-us yes">8 failure classes</td></tr>
              <tr><td>Auditor-verifiable evidence</td><td className="no">no</td><td className="no">no</td><td className="col-us yes">signed receipt</td></tr>
              <tr><td>Fails honest (no number vs. a wrong one)</td><td className="no">no</td><td className="no">partial</td><td className="col-us yes">WARN, never fabricates</td></tr>
              <tr><td>Runs fully air-gapped</td><td className="no">rarely</td><td className="no">rarely</td><td className="col-us yes">yes</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="section">
        <div className="wrap">
          <div className="kicker">How it works</div>
          <h2>Ask → verify independently → attest</h2>
          <div className="steps">
            <div className="step">
              <div className="step-num">01</div>
              <h3>Ask</h3>
              <p>Your question resolves to a certified metric and runs as parameterized, read-only SQL — never string-built, never free-form.</p>
            </div>
            <div className="step">
              <div className="step-num">02</div>
              <h3>Verify — independently</h3>
              <p>A separate engine re-derives the answer and checks it against the named ways a ledger number goes wrong. Re-running the model&rsquo;s own SQL would be circular; this never does.</p>
            </div>
            <div className="step">
              <div className="step-num">03</div>
              <h3>Attest</h3>
              <p>The verdict, SQL and answer are bound into an Ed25519 receipt. Anyone re-checks it offline — they trust the receipt, not the assistant.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ROI / MODELS */}
      <section className="section">
        <div className="wrap">
          <div className="kicker">The economics</div>
          <h2>Verified trust, at a lower bill</h2>
          <p className="sub">
            The verifier makes &ldquo;cheap model first&rdquo; safe — so you only pay for the expensive
            model on the questions that actually need it.
          </p>
          <div className="cards">
            <div className="card">
              <div className="big">30.5%</div>
              <div className="lab">lower model spend vs. always using the strong model, at 100% accuracy on the benchmark mix.</div>
            </div>
            <div className="card">
              <div className="big">Your models</div>
              <div className="lab">Pluggable tiers — run it the way your security team allows:</div>
              <div className="chips">
                <span className="chip">Ollama · air-gapped</span>
                <span className="chip">OpenAI</span>
                <span className="chip">AWS Bedrock</span>
              </div>
            </div>
            <div className="card">
              <div className="big">$0 / answer to audit</div>
              <div className="lab">The signed receipt is the evidence trail — generated automatically, no extra reconciliation work.</div>
            </div>
          </div>
        </div>
      </section>

      {/* LIVE TRY */}
      <section className="section" id="try">
        <div className="wrap-narrow">
          <div className="kicker">Try it live</div>
          <h2>Ask the real system</h2>
          <p className="sub">
            This talks to the live verifier. Toggle the cost cascade and a signed receipt; open the
            evidence drawer and verify the receipt yourself.
          </p>
          <LiveTry />
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="section final">
        <div className="wrap-narrow">
          <h2>See the proof for yourself.</h2>
          <p className="sub" style={{ margin: "0 auto 24px" }}>
            Open-source, deploy-anywhere, and every answer carries its own evidence.
          </p>
          <div className="cta-row" style={{ justifyContent: "center" }}>
            <a className="btn btn-primary" href="#try">Try it live</a>
            <a className="btn btn-ghost" href={REPO}>View the code</a>
          </div>
        </div>
      </section>
    </main>
  );
}
