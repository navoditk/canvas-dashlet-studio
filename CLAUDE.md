# Claude instructions for Canvas Dashlet Studio

Read [`AGENTS.md`](AGENTS.md) first — it is canonical for architecture, the dashlet contract, framework rules, agent-tool rules, and the must/must-not list. This file only adds Claude-specific notes; it does not repeat AGENTS.md.

## Claude Code specifics

- Per `docs/AGENTIC_DEVELOPMENT.md` §2 and §10, Claude Code's primary role on this project is **independent architecture/security review and alternative implementation critique**, and it is also a sanctioned implementer for generated dashlets and framework work provided an independent review pass happens afterward (§10's review matrix names "Other agent" as reviewer, not self-review).
- When implementing (not reviewing): follow `AGENTS.md` in full, explain what's being changed and why as you go rather than delivering a large silent diff, verify with the real commands in `AGENTS.md` §3 (not just a subset), and say explicitly in the commit/PR description that the change should get an independent review pass before merge.
- When reviewing: check process safety, endpoint/tool exposure, provider restrictions, mount-relative paths, provenance, error handling, lifecycle cleanup and contract-test coverage, per the "Review task" prompt template in `docs/AGENTIC_DEVELOPMENT.md` §8. Report findings; do not silently fix them unless asked to.
- Favor small, independently-green commits over one large diff — this matches how work on this repository has actually been done (see git history from 2026-08-25 onward): CI-passing units, pushed incrementally, each with its own explanation.
