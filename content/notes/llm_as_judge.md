---
title: "LLM-as-judge and calibration"
topic_ids: [eval.llm_judge, eval.stats]
source_url: null
licence: original
tags: [evaluation, judge, kappa, bias]
status: outline
---

<!-- OUTLINE — write in your own words. -->

# LLM-as-judge and calibration

## What it is
- Cover: using an LLM to score answers against a rubric (per-dimension 1–5 + evidence quote).

## Why you must calibrate it
- Cover: a judge is only trustworthy if it agrees with humans; measure agreement with
  quadratic-weighted Cohen's kappa (ordinal 1–5), not plain accuracy.
- Number: our gate is κ ≥ 0.70 per dimension; check human-vs-human agreement first.

## Known biases to test
- Cover: position bias (swap order in pairwise), length bias (verbose ≠ better), self-preference;
  evidence must be a verbatim transcript quote (verified) so scores aren't fabricated.

## Activation rule
- Cover: a new judge version ships only if it matches/beats the current one on a held-out set.

## Interview angle
- "How do you know your judge is right?" (kappa vs humans, bias tests, evidence verification).

## Suggested source
- (own knowledge; docs/05_EVALS.md §4)
