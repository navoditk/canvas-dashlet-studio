@AGENTS.md

# Claude instructions for Canvas Dashlet Studio

`AGENTS.md` is canonical for architecture, the dashlet contract, framework rules, agent-tool rules, and the must/must-not list. The `@AGENTS.md` import above loads it; this file only adds Claude-specific notes and never repeats it.

The import matters more than it looks. Claude Code reads `AGENTS.md` directly **only when no `CLAUDE.md` exists** — the moment this file is present, it reads `CLAUDE.md` alone. So a prose "read AGENTS.md first" left those canonical rules unloaded and relied on the agent choosing to act on the instruction. An import loads them; a sentence asks nicely.

An import rather than a symlink is deliberate: the Edit and Write tools refuse to write through a symlink, and Git checks a committed symlink out as a plain text file on Windows clones unless `core.symlinks` is set.

## Claude Code specifics

- Per `docs/AGENTIC_DEVELOPMENT.md` §2 and §10, Claude Code's primary role on this project is **independent architecture/security review and alternative implementation critique**, and it is also a sanctioned implementer for generated dashlets and framework work provided an independent review pass happens afterward (§10's review matrix names "Other agent" as reviewer, not self-review).
- When implementing (not reviewing): follow `AGENTS.md` in full, explain what's being changed and why as you go rather than delivering a large silent diff, verify with the real commands in `AGENTS.md` §3 (not just a subset), and say explicitly in the commit/PR description that the change should get an independent review pass before merge.
- When reviewing: check process safety, endpoint/tool exposure, provider restrictions, mount-relative paths, provenance, error handling, lifecycle cleanup and contract-test coverage, per the "Review task" prompt template in `docs/AGENTIC_DEVELOPMENT.md` §8. Report findings; do not silently fix them unless asked to.
- Favor small, independently-green commits over one large diff — this matches how work on this repository has actually been done (see git history from 2026-08-25 onward): CI-passing units, pushed incrementally, each with its own explanation.
