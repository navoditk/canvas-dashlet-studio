"""Resolve every relative link and heading anchor in the repository's markdown.

Link rot is silent. A broken `[text](path)` still renders as a link, and a
broken `#anchor` still navigates -- to the top of the file -- so a reader
lands somewhere plausible and assumes the section moved. Ported from the pm-mechanics repository, where an equivalent sweep found
five live broken anchors -- three of them in one file's own table of
contents. This repository's 22 markdown files were all clean at the time of
porting, so this gate preserves that rather than repairing anything.

Two details decide whether this catches anything or quietly passes on broken
input, and both are the reason a hand-rolled version of this check failed
earlier:

- **Fences.** A `## Heading` inside a ``` block is example content, not a
  heading. Treating it as one invents anchors that do not exist and, worse,
  hides real misses behind phantom matches.
- **GitHub's slug rules.** Punctuation is stripped and then *each remaining
  space* becomes one hyphen, so `AWS Bedrock & AgentCore` yields
  `aws-bedrock--agentcore` with two hyphens. Collapsing whitespace -- the
  intuitive implementation -- reports every such heading as broken.

External URLs are deliberately not fetched: a network-dependent check turns
an unrelated outage into a failed build.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {
    ".venv",
    ".git",
    "__pycache__",
    "node_modules",
    "dist",
    "site",
    # Build caches are not documentation. CI runs pytest before this gate, and
    # pytest always writes .pytest_cache/README.md, so omitting these made the
    # scanned set depend on whether anything had run first.
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    "htmlcov",
}
LINK = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
FENCE = re.compile(r"^\s*(```|~~~)")


HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*$")


def heading_slugs(markdown: str) -> set[str]:
    """Slugify every real heading the way GitHub does.

    Four details decide whether this matches the real renderer. Fences and the
    space-to-hyphen rule are described above; two more are structural.

    ATX headings may be indented up to three spaces and may carry a closing
    run of hashes (`## Section ##`), both legal in CommonMark. Matching on a
    bare `startswith("#")` misses the first and leaves a trailing hyphen on
    the second, and a `#` with no following space is not a heading at all --
    each of which reports a working link as broken, or accepts a broken one.

    Repeated heading text is disambiguated by GitHub with a numeric suffix:
    three `### Using it` headings yield `using-it`, `using-it-1`, `using-it-2`.
    Collecting into a set without that collapses them, so a link to the second
    or third would be reported broken.
    """
    slugs: set[str] = set()
    seen: dict[str, int] = {}
    in_fence = False
    for line in markdown.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING.match(line)
        if not match:
            continue
        heading = match.group(2).rstrip("#").strip()
        heading = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading).replace("`", "")
        base = re.sub(r"[^\w\s-]", "", heading.lower()).replace(" ", "-")
        count = seen.get(base, 0)
        seen[base] = count + 1
        slugs.add(base if count == 0 else f"{base}-{count}")
    return slugs


def markdown_files(root: Path) -> list[Path]:
    return sorted(
        path for path in root.rglob("*.md") if not any(part in SKIP_DIRS for part in path.parts)
    )


def check_file(doc: Path, root: Path) -> list[str]:
    problems: list[str] = []
    text = doc.read_text(encoding="utf-8", errors="ignore")
    own_slugs = heading_slugs(text)

    for _, target in LINK.findall(text):
        target = target.strip()
        if target.startswith(("http://", "https://", "mailto:", "tel:")):
            continue

        fragment = ""
        if "#" in target:
            target, fragment = target.split("#", 1)

        relative = doc.relative_to(root)
        if not target:  # same-document anchor
            if fragment and fragment not in own_slugs:
                problems.append(f"{relative}: in-page #{fragment} matches no heading")
            continue

        resolved = (doc.parent / unquote(target)).resolve()
        if not resolved.exists():
            problems.append(f"{relative}: broken link -> {target}")
            continue
        if fragment and resolved.suffix == ".md":
            other = resolved.read_text(encoding="utf-8", errors="ignore")
            if fragment not in heading_slugs(other):
                problems.append(f"{relative}: {target}#{fragment} matches no heading")
    return problems


def main(argv: list[str]) -> int:
    root = Path(argv[0]).resolve() if argv else REPO_ROOT
    files = markdown_files(root)
    problems = [problem for doc in files for problem in check_file(doc, root)]

    if problems:
        print(f"{len(problems)} broken link(s) or anchor(s) in {len(files)} files:\n")
        for problem in problems:
            print(f"  {problem}")
        print(
            "\nAn anchor that matches no heading still navigates -- to the top "
            "of the file -- so a reader assumes the section moved rather than "
            "reporting it."
        )
        return 1

    print(f"All relative links and anchors resolve ({len(files)} markdown files).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
