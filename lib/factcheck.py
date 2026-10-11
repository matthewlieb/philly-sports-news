"""Second-pass fact check: every claim must be supported by the material the writer was given."""
import json
import os

_SYSTEM = """You are a strict sports fact-checker. You get numbered items of published text and the evidence the writer
had. For each item, decide whether every factual detail (names, numbers, scores, stats, dates, opponents, who said what,
injuries, transactions) is directly supported by the evidence. Opinions and framing are fine; facts are not.

If an item has an unsupported or contradicted detail, rewrite it so it only states supported facts, keeping the same
voice and roughly the same length. If nothing in it can be saved, return an empty rewrite.

Return JSON: {"items": [{"n": <item number>, "supported": true/false, "problem": "what was wrong", "rewrite": "..."}]}
Only list items that are NOT supported."""


def check(items: list[str], evidence: str) -> dict[int, str]:
    """Returns {item index: corrected text} for items that needed fixing ('' means drop it)."""
    from openai import OpenAI

    numbered = "\n".join(f"[{i}] {t}" for i, t in enumerate(items, 1))
    resp = OpenAI().chat.completions.create(
        model=os.environ.get("FACTCHECK_MODEL", "gpt-5.4"),
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": _SYSTEM},
                  {"role": "user", "content": f"EVIDENCE:\n{evidence}\n\nITEMS TO CHECK:\n{numbered}"}],
    )
    fixes = {}
    for item in json.loads(resp.choices[0].message.content or "{}").get("items") or []:
        n = item.get("n")
        if isinstance(n, int) and 1 <= n <= len(items) and not item.get("supported", True):
            print(f"Fact check fixed item {n}: {item.get('problem')}")
            fixes[n - 1] = (item.get("rewrite") or "").strip()
    return fixes
