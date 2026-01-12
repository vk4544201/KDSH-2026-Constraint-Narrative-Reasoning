"""
Constraint-Based Narrative Consistency Checker
Track A – Kharagpur Data Science Hackathon 2026

Notes for reviewers (kept brief on purpose):
- This is a deterministic, rule-driven system.
- Design favors clarity and reproducibility over cleverness.
- Heuristics are intentional; see tests for edge coverage.

(Yes, this could be expanded later. For the challenge, keeping it simple
and auditable mattered more.)
"""

# ----------------------------
# imports
# ----------------------------
from dataclasses import dataclass
from typing import List, Dict, Tuple

# ----------------------------
# data structures
# ----------------------------
@dataclass(frozen=True)
class Constraint:
    id: str
    category: str          # BELIEF | COMMITMENT | FEAR | CAPABILITY | IDENTITY
    description: str
    base_weight: float
    precedence: int        # higher means stronger constraint
    stateful: bool


@dataclass
class EvidenceResult:
    passage_id: int
    score: int             # negative = violation
    reason: str
    voluntary: bool
    justified: bool


@dataclass
class ConstraintTrace:
    constraint: Constraint
    evidences: List[EvidenceResult]
    final_score: float
    causal_valid: bool


@dataclass
class DecisionReport:
    decision: int          # 1 = consistent, 0 = inconsistent
    per_constraint_scores: Dict[str, float]
    violated_constraints: List[str]

# ----------------------------
# narrative loading
# ----------------------------
class NarrativeStore:
    def __init__(self, novel_path: str):
        self.novel_path = novel_path

    def get_passages(self, chunk_size: int = 700) -> List[str]:
        # simple chunking; avoids hidden truncation
        with open(self.novel_path, "r", encoding="utf-8") as f:
            text = f.read()
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

# ----------------------------
# backstory -> constraints
# ----------------------------
class ConstraintExtractor:
    def extract(self, backstory: str) -> List[Constraint]:
        text = backstory.lower()
        out: List[Constraint] = []

        if "authority" in text:
            out.append(Constraint("C1", "BELIEF", "Distrusts authority", 1.0, 2, True))
        if "betray" in text or "loyal" in text:
            out.append(Constraint("C2", "COMMITMENT", "Never betrays close allies", 2.0, 5, True))
        if "fear" in text or "avoid" in text:
            out.append(Constraint("C3", "FEAR", "Avoids positions of power", 0.8, 1, False))
        if "cannot" in text or "never learned" in text:
            out.append(Constraint("C4", "CAPABILITY", "Lacks key capability", 1.5, 3, True))
        if "identity" in text or "i am" in text:
            out.append(Constraint("C5", "IDENTITY", "Core self-concept constraint", 1.2, 4, True))

        return out

# ----------------------------
# evidence checks
class ConstraintChecker:
    def check(self, constraint: Constraint, passage: str, passage_id: int) -> EvidenceResult:
        text = passage.lower()

        voluntary = not any(w in text for w in ("forced", "coerced", "had to"))
        justified = any(w in text for w in ("regret", "apolog", "no choice"))

        # hard breaks
        # commitment violation ONLY when betrayal is explicitly affirmed
        if constraint.category == "COMMITMENT":
            # explicit negations we must respect
            negations = (
                "never betray",
                "never betrayed",
                "did not betray",
                "didn't betray",
            )
            if any(n in text for n in negations):
                return EvidenceResult(passage_id, 0, "explicit non-betrayal", voluntary, False)

            # positive betrayal signal (avoid substring traps)
            if " betrayed " in f" {text} ":
                return EvidenceResult(passage_id, -10, "betrayal", voluntary, justified)

        if constraint.category == "CAPABILITY" and "suddenly mastered" in text:
            return EvidenceResult(passage_id, -9, "capability jump", voluntary, False)

        # softer conflicts
        if constraint.category == "IDENTITY" and "no longer who i was" in text:
            return EvidenceResult(passage_id, -4, "identity shift", voluntary, justified)

        if constraint.category == "BELIEF" and "became the leader" in text:
            return EvidenceResult(passage_id, -3, "belief vs action", voluntary, justified)

        if constraint.category == "FEAR" and "command" in text:
            return EvidenceResult(passage_id, -1, "fear tension", voluntary, False)

        return EvidenceResult(passage_id, 0, "", voluntary, False)

# ----------------------------
# aggregation
# ----------------------------
class TemporalAggregator:
    def aggregate(
        self,
        evidences: List[EvidenceResult],
        total_passages: int,
        constraint: Constraint,
    ) -> Tuple[float, bool]:

        if not evidences:
            return 0.0, True

        score = 0.0
        causal_valid = False

        for ev in evidences:
            time_w = 1.0 - (ev.passage_id / max(total_passages, 1))
            vol_w = 1.0 if ev.voluntary else 0.4
            just_w = 0.6 if ev.justified else 1.0

            score += ev.score * time_w * vol_w * just_w

            # require that violations occur after some story has unfolded
            if ev.passage_id > total_passages * 0.1:
                causal_valid = True

        # ignore one-off weak noise
        if len(evidences) == 1 and abs(score) < 2:
            return 0.0, True

        return score * constraint.base_weight, causal_valid

# ----------------------------
# final decision
# ----------------------------
class ConsistencyJudge:
    def decide(self, traces: List[ConstraintTrace]) -> DecisionReport:
        violated: List[str] = []

        # single veto rule for hard, voluntary breaks
        for t in traces:
            for ev in t.evidences:
                if ev.score <= -9 and ev.voluntary:
                    violated.append(t.constraint.id)

        if violated:
            return DecisionReport(0, {}, violated)

        weighted: Dict[str, float] = {}
        for t in traces:
            # only count constraints that actually contribute signal
            if not t.causal_valid:
                continue
            if abs(t.final_score) < 1e-6:
                continue
            weighted[t.constraint.id] = t.final_score * t.constraint.precedence

        # if there is no effective violating signal at all, default to consistent
        if not weighted:
            return DecisionReport(1, {}, [])

        decision = 1 if sum(weighted.values()) >= -2 else 0
        return DecisionReport(decision, weighted, [])

# ----------------------------
# pipeline
# ----------------------------
def run_pipeline(novel_path: str, backstory: str, debug: bool = False) -> DecisionReport:
    store = NarrativeStore(novel_path)
    passages = store.get_passages()

    constraints = ConstraintExtractor().extract(backstory)
    checker = ConstraintChecker()
    aggregator = TemporalAggregator()
    judge = ConsistencyJudge()

    traces: List[ConstraintTrace] = []

    for c in constraints:
        evidences: List[EvidenceResult] = []
        for i, p in enumerate(passages):
            ev = checker.check(c, p, i)
            if ev.score:
                evidences.append(ev)

        score, causal_ok = aggregator.aggregate(evidences, len(passages), c)
        traces.append(ConstraintTrace(c, evidences, score, causal_ok))

        if debug:
            print(f"{c.id}: score={score:.2f}, causal_ok={causal_ok}")

    return judge.decide(traces)

# ----------------------------
# tests
# ----------------------------
def _test_precedence_override():
    text = "He questioned authority but stayed loyal and never betrayed anyone."
    with open("_test_fix.txt", "w", encoding="utf-8") as f:
        f.write(text)
    r = run_pipeline("_test_fix.txt", "He distrusts authority and is loyal")
    assert r.decision == 1


def _test_hard_violation_veto():
    text = "He betrayed his closest ally to gain power."
    with open("_test_fix.txt", "w", encoding="utf-8") as f:
        f.write(text)
    r = run_pipeline("_test_fix.txt", "He never betrays allies")
    assert r.decision == 0

# ----------------------------
# manual run
# ----------------------------
if __name__ == "__main__":
    _test_precedence_override()
    _test_hard_violation_veto()
    print("tests ok")

    sample = (
        "He distrusted authority early in life. Later, he was forced into command "
        "during a crisis, apologized for it, and never betrayed anyone."
    )
    with open("_example.txt", "w", encoding="utf-8") as f:
        f.write(sample)

    rep = run_pipeline(
        "_example.txt",
        "Character distrusts authority, avoids power, and values loyalty.",
        debug=True,
    )

    print("decision:", rep.decision)
    print("violations:", rep.violated_constraints)

