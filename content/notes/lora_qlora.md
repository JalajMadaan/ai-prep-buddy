---
title: "LoRA and QLoRA"
topic_ids: [ft.lora_qlora, serve.quantization]
source_url: null
licence: original
tags: [fine-tuning, lora, qlora, peft, quantization]
status: outline
---

<!-- OUTLINE — write in your own words. -->

# LoRA and QLoRA

## The problem
- Cover: full fine-tuning of a 7B model updates all weights → huge memory (optimizer states ~2-4×
  params) and a full checkpoint per task.

## LoRA
- Cover: freeze base weights; inject small low-rank matrices A (d×r) and B (r×d) so ΔW = B·A with
  rank r ≪ d; train only A, B.
- Number: at r=16 you train a tiny fraction (<1%) of parameters; adapters are a few MB.

## QLoRA
- Cover: quantize the frozen base to 4-bit (NF4), keep LoRA adapters in higher precision;
  double quantization + paged optimizers.
- Number/claim: lets you fine-tune a 7B model on a single ~16 GB GPU — the interview soundbite.

## Tradeoffs
- Cover: slight quality vs full FT; inference merges or keeps adapters; serving many adapters (M8).

## Interview angle
- "Explain LoRA." / "Why does QLoRA fit a 7B on 16 GB?" (4-bit base + rank-r adapters).

## Suggested source
- doc_lora_paper, doc_qlora_paper
