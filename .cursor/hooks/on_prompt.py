"""beforeSubmitPrompt hook — classify prompt and emit enrichment payload.

Classifies the user prompt against agent configs, selects the best-match
agent, and writes a ``{"systemMessage": ...}`` JSON payload to stdout
containing the agent name, confidence score, and routing reason.

Falls back to ``polymorphic-agent`` with score 0.0 when no agent matches.
Always exits 0 and always emits valid JSON.
"""

from __future__ import annotations

import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# Ensure _common is importable from the same directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (
    LEARNED_PATTERNS_FILE,
    load_agent_configs,
    log_event,
    read_stdin,
    write_stdout,
)
from pattern_loader import get_pattern_cache


# ---------------------------------------------------------------------------
# Routing constants (aligned with src/omnicursor/agents.py)
# ---------------------------------------------------------------------------

HARD_FLOOR: float = 0.55

_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "has", "have", "i", "in", "is", "it", "my", "not", "of", "on",
    "or", "the", "this", "that", "to", "was", "we", "with", "you",
})


# ---------------------------------------------------------------------------
# Prompt classification — multi-strategy scoring
# ---------------------------------------------------------------------------


def _extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from *text*, filtering stopwords."""
    return [
        w for w in re.findall(r"\b\w+\b", text.lower())
        if w not in _STOPWORDS and len(w) > 2
    ]


def _fuzzy_threshold(trigger: str) -> float:
    """Dynamic threshold: shorter triggers need higher similarity."""
    n = len(trigger)
    if n <= 6:
        return 0.85
    elif n <= 10:
        return 0.78
    return 0.72


def _score_agent(
    prompt_lower: str,
    prompt_words: Set[str],
    agent: Dict[str, Any],
) -> Tuple[float, str]:
    """Multi-strategy scoring for a single agent config.

    Strategies (evaluated in order, best score wins):
      1. Exact substring match on explicit/context triggers
      2. Fuzzy SequenceMatcher on explicit triggers
      3. Keyword overlap (activation_keywords or auto-extracted)

    Returns ``(score, reason)``.  Score 0.0 means no match.
    """
    activation = agent.get("activation_patterns", {})
    explicit: List[str] = activation.get("explicit_triggers", [])
    context: List[str] = activation.get("context_triggers", [])

    best_score = 0.0
    best_reason = ""

    # --- Strategy 1: exact substring match (highest confidence) ---
    for trigger in explicit:
        if trigger.lower() in prompt_lower:
            if 0.95 > best_score:
                best_score = 0.95
                best_reason = "Exact trigger: '{}'".format(trigger)

    for trigger in context:
        if trigger.lower() in prompt_lower:
            score = 0.80
            if score > best_score:
                best_score = score
                best_reason = "Context trigger: '{}'".format(trigger)

    # --- Strategy 2: fuzzy matching via SequenceMatcher ---
    if best_score < 0.90:
        words_in_prompt = re.findall(r"\b\w+\b", prompt_lower)
        for trigger in explicit:
            trigger_lower = trigger.lower()
            threshold = _fuzzy_threshold(trigger_lower)
            for word in words_in_prompt:
                ratio = SequenceMatcher(None, trigger_lower, word).ratio()
                if ratio >= threshold and ratio > best_score:
                    best_score = ratio
                    best_reason = "Fuzzy match: '{}' ({:.0%})".format(
                        trigger, ratio,
                    )

    # --- Strategy 3: keyword overlap ---
    if best_score < 0.70:
        keywords_raw: List[str] = activation.get("activation_keywords", [])
        if not keywords_raw:
            keywords_raw = []
            for t in explicit:
                keywords_raw.extend(t.lower().split())
        keyword_set = {k.lower() for k in keywords_raw if len(k) > 2} - _STOPWORDS
        if keyword_set:
            overlap = prompt_words & keyword_set
            if len(overlap) >= 2:
                keyword_ratio = len(overlap) / len(keyword_set)
                scaled = 0.55 + (keyword_ratio * 0.30)
                if scaled > best_score:
                    best_score = scaled
                    best_reason = "Keywords: {{{}}}".format(
                        ", ".join(sorted(overlap)),
                    )

    return (best_score, best_reason)


def classify_prompt(
    prompt: str, agents: List[Dict[str, Any]],
) -> Tuple[str, float, str]:
    """Return ``(agent_name, score, reason)``.

    Only agents scoring at or above ``HARD_FLOOR`` are considered.
    Falls back to ``('polymorphic-agent', 0.0, 'No agent matched')``.
    """
    if not prompt or not agents:
        return ("polymorphic-agent", 0.0, "No agent matched")

    prompt_lower = prompt.lower()
    prompt_words = set(_extract_keywords(prompt))
    best_name = "polymorphic-agent"
    best_score = 0.0
    best_reason = "No agent matched"

    for agent in agents:
        name = agent.get("name", "")
        if not name:
            continue
        score, reason = _score_agent(prompt_lower, prompt_words, agent)
        if score >= HARD_FLOOR and score > best_score:
            best_score = score
            best_name = name
            best_reason = reason

    return (best_name, best_score, best_reason)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


MAX_PATTERNS_TO_INJECT = 5


def _format_system_message(
    agent_name: str,
    score: float,
    reason: str,
    patterns: List[Dict[str, Any]],
) -> str:
    """Build the enrichment block injected via ``systemMessage``."""
    lines = [
        "<!-- OmniCursor Agent: {name} (confidence: {score:.2f}) -->".format(
            name=agent_name, score=score,
        ),
        "<!-- Routing reason: {reason} -->".format(reason=reason),
    ]

    if patterns:
        lines.append("")
        lines.append("<!-- Learned Patterns (from previous sessions): -->")
        for p in patterns[:MAX_PATTERNS_TO_INJECT]:
            pid = p.get("pattern_id", "?")
            desc = p.get("description", "")
            lines.append("<!-- - [{pid}] {desc} -->".format(pid=pid, desc=desc))

    return "\n".join(lines)


def _agent_domain(agent_name: str) -> str:
    """Derive a pattern-cache domain key from the agent name.

    Strips common prefixes and normalises hyphens to underscores so that
    an agent named ``debug-intelligence`` maps to domain ``debug_intelligence``.
    """
    domain = agent_name.lower()
    for prefix in ("agent-", "omnicursor-"):
        if domain.startswith(prefix):
            domain = domain[len(prefix):]
            break
    return domain.replace("-", "_")


def main() -> None:
    # Defaults — used if anything goes wrong so we always emit valid JSON.
    agent_name = "polymorphic-agent"
    score = 0.0
    reason = "No agent matched"
    patterns: List[Dict[str, Any]] = []

    try:
        data = read_stdin()
        prompt = data.get("prompt", "")
        conversation_id = data.get("conversation_id", "")
        generation_id = data.get("generation_id", "")

        agents = load_agent_configs()
        agent_name, score, reason = classify_prompt(prompt, agents)

        # --- Pattern loading (Task 2) ---
        cache = get_pattern_cache()
        if not cache.is_warm() or cache.is_stale():
            cache.warm_from_json(LEARNED_PATTERNS_FILE)

        domain = _agent_domain(agent_name)
        patterns = cache.get(domain)
        # Fall back to "general" if nothing domain-specific.
        if not patterns:
            patterns = cache.get("general")

        log_event(
            {
                "event": "prompt_classified",
                "conversation_id": conversation_id,
                "generation_id": generation_id,
                "matched_agent": agent_name,
                "score": round(score, 4),
                "reason": reason,
                "patterns_injected": len(patterns[:MAX_PATTERNS_TO_INJECT]),
                "prompt_snippet": prompt[:100],
            }
        )
    except Exception:
        pass

    write_stdout({
        "systemMessage": _format_system_message(agent_name, score, reason, patterns),
    })


if __name__ == "__main__":
    main()
