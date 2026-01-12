# Kharagpur Data Science Hackathon 2026 – Track A

## Constraint-Based Narrative Consistency Checker

This repository contains a deterministic, rule-based system designed to
evaluate whether a hypothetical character backstory is globally consistent
with a long-form narrative.

Rather than focusing on text generation, the task is framed as a decision
problem over long contexts, where meaning emerges from how events,
commitments, and constraints accumulate over time.

---

## Core Idea

A backstory is treated as a set of constraints on what can plausibly happen
later in the story. As the narrative unfolds, events are checked against these
constraints to determine whether the observed future remains causally and
logically compatible with the proposed past.

The system explicitly distinguishes between:
- hard, irreversible violations (e.g. voluntary betrayal),
- softer tensions that may be context-dependent,
- early noise versus later, causally relevant actions.

---

## System Overview

- Backstories are converted into structured constraints such as beliefs,
  commitments, fears, capabilities, and identity traits.
- The full narrative is processed sequentially without truncation.
- Evidence is evaluated over time using temporal weighting.
- Voluntary hard violations act as vetoes.
- Softer conflicts are aggregated using constraint precedence.

The design is intentionally deterministic and auditable, prioritizing clarity
and reproducibility over black-box behavior.

---

## How to Run


---

## Output

- `1` → Backstory is consistent with the narrative  
- `0` → Backstory is inconsistent with the narrative  

---

## Notes

This implementation was built for the Kharagpur Data Science Hackathon 2026
(Track A). The focus was on careful reasoning, robustness to edge cases
(such as negation), and transparent decision logic rather than model scale
or generative fluency.
