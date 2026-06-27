# Why I built this

My background is twenty years in telecom, not finance. Tessera is a deliberate bridge between the two
— and the bridge is a single problem that turns out to be the same on both sides.

## The origin

The closest thing I'd shipped to this was an **air-gapped, on-prem LLM proof-of-concept for a telecom
carrier** (Claro Brazil). Self-hosted inference, natural-language analytics over governed data, inside
the customer's data boundary with no public AI services. What I learned there wasn't really about
models. It was that the hard part of putting an LLM in front of a non-technical user isn't fluency —
it's **trust**: *can the person believe the number it just gave them?* A confident, fluent, wrong
answer is worse than no answer, because someone acts on it.

Around the same time, I kept having the same conversation with a couple of friends who work in
finance. Not about anything internal or confidential — just the general, technology-shaped frustration
the whole industry shares: you can put a chatbot in front of a ledger, and it will answer, but you
**cannot trust a specific number enough to put it in front of an auditor or a board**. In finance the
stakes turn that trust problem from "annoying" into "expensive" — the cost of a wrong number is a
restatement or a compliance finding.

So the move from telecom to finance wasn't a pivot of convenience. It was taking the trust-verification
problem I'd already worked on in a regulated, air-gapped setting, and generalizing it to the domain
where that exact problem is most costly — and where it's still unsolved.

## What "unsolved" means here

Every natural-language analytics tool proves trust the same way: **offline**. A benchmark score, a
human who once blessed a similar query, or "here's the SQL — *you* check it." None of them ship, *with
each answer at runtime*, an **independent verdict** and an **auditable receipt**. That gap is the whole
reason text-to-SQL hasn't displaced the finance analyst despite years of demos. Tessera is built to
close exactly that gap.

## The honest boundary

Tessera proves a number *reconciles to the certified metric definition* — not cosmic truth. Governing
those definitions with the customer is human work, and it is *exactly the work a forward-deployed
engineer does*: embed, learn the customer's real definitions, encode them, and make the system prove
itself against them. That's not a footnote to the project. It's the point.

---

*Telecom was the origin story. Finance is where the problem is most expensive. The work is the same:
make the trust **verifiable**, not asserted.*
