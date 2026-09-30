"""Hard-budget line selection from per-line knowledge-type distributions.

Unlike ``ContextProjector``, which protects every EXACT item and signals unsafe when they do
not fit, this selector always returns text within ``char_budget``: it ranks lines by argmax
type tier (constraint < procedure < belief < preference < episodic), then by descending
P(constraint), then document order; fills the budget greedily, skipping lines that do not
fit; and emits the chosen lines in document order.
"""

_TIER = {"constraint": 0, "procedure": 1, "belief": 2, "preference": 3, "episodic": 4}


def select_lines(lines: list[str], distributions: list[dict[str, float]], char_budget: int) -> str:
    if len(lines) != len(distributions):
        raise ValueError("one distribution per line is required")

    def priority(i: int) -> tuple[int, float, int]:
        dist = distributions[i]
        top = max(dist, key=dist.get) if dist else "belief"
        return _TIER.get(top, 2), -dist.get("constraint", 0.0), i

    chosen: list[int] = []
    used = 0
    for i in sorted(range(len(lines)), key=priority):
        cost = len(lines[i]) + (1 if chosen else 0)
        if used + cost <= char_budget:
            chosen.append(i)
            used += cost
    return "\n".join(lines[i] for i in sorted(chosen))
