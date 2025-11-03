"""Prompt templates for DeepThink/UltraThink.
These are concise, math/proof oriented, and designed to be model-agnostic.
"""
from typing import Any

DEEP_THINK_INITIAL_PROMPT = (
    "You are a careful mathematician. Read the problem, reason step-by-step, and produce a fully"
    " rigorous solution with explicit lemmas. Keep derivations auditable."
)

DEEP_THINK_VERIFY_PROMPT = (
    "You are a strict proof checker. Check the solution for correctness, hidden assumptions,"
    " and gaps. If incorrect, identify the first concrete error and explain why."
)

DEEP_THINK_CORRECT_PROMPT = (
    "Fix the solution strictly based on the verification feedback. Provide corrected steps only."
)

ULTRA_THINK_PLAN_PROMPT = (
    "Produce a minimal plan for solving the problem, enumerating distinct approaches"
    " (algebraic, geometric, combinatorial, number-theoretic) with 1-2 bullets each."
)

GENERATE_AGENT_PROMPTS_PROMPT = (
    "Given the plan, produce N diverse agent-specific prompts that enforce diversity of approach"
    " and detail their constraints. Output as a numbered list of short system prompts."
)

SYNTHESIZE_RESULTS_PROMPT = (
    "Synthesize multiple candidate solutions. Prefer the most rigorous argument."
    " Resolve conflicts and produce a single coherent proof."
)


def build_final_summary_prompt(problem_text: str, synthesis_text: str) -> str:
    return (
        "Write a concise final answer for the user, summarizing the key steps and final result.\n\n"
        f"Problem:\n{problem_text}\n\nSynthesized Solution:\n{synthesis_text}\n"
    )

