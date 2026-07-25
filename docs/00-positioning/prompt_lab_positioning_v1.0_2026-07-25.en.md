# Prompt Lab Positioning

**Project**: Prompt Lab
**Date**: 2026-07-25
**Version**: v1.0

---

## WHO

Developers who tune prompts in LLM application projects, plus non-technical roles (PMs, operators) who need to modify prompts.

Typical scenario: A developer has built an LLM application with prompts running in production. One day a bad case surfaces, or they want to trim prompts to reduce token costs. They edit the prompt text but have no way to verify whether the new version degrades output quality — they eyeball a few outputs, feel it's "close enough," and ship. The PM next to them wants to tweak the output style in the prompt but can't run code, so they toss the idea to the developer to implement.

## WHY

Prompt changes are ad-hoc. There is no version management or A/B testing. Whether things get better or worse is a guess.

The pain exists independent of any tool: developers edit prompt strings in production without validation sets, version history, or quantitative metrics. The result might improve, or it might degrade severely — then they have to change it again. This is not a rare scenario; it is the daily reality of every team shipping LLM applications.

## WHY NOW

Three converging changes make this matter today and not three years ago:

1. **LLM applications truly exploded in 2023** — Three years ago, few teams ran LLMs in production. The concept of a prompt as a "software asset" didn't exist. Prompt changes were casual because prompts themselves were experimental scripts.

2. **Model providers change frequently, parameters interact** — Model upgrades (e.g., DeepSeek defaulting to thinking mode, causing empty content returns), parameter complexity (thinking, reasoning_effort, max_tokens coupling) — changing one variable can break prompt output entirely. Three years ago, there were only one or two API providers with simple parameters.

3. **Open-source ecosystem covers only half the loop; the full closed loop is all closed-source** — DeepEval built evaluation metrics, Promptfoo built testing, Langfuse built tracing. But the "change prompt → version comparison → data-driven decision to ship or not" closed loop has not been built completely by any open-source project.

## UNDERLYING LOGIC

The problem with prompts isn't that "changing prompts is hard" — anyone can edit a string. The problem is that after changing, you don't know what happened. What's missing between one prompt version and the next is "quantifiable comparison."

Prompt Lab's mechanism: transform a prompt from a string in code into a controlled experimental variable. Each change is automatically bound to a version, both versions are run against a fixed validation set, and a structured comparison report is produced (token consumption, latency, quality scores, output diff). The core is making "did the prompt change make things better or worse" a data-driven judgment, not a subjective feeling.

Three principles of scientific methodology:
- **Define the ideal state first** — Before changing a prompt, specify what "good output" looks like
- **Control single variable** — Change only one dimension at a time, otherwise you can't attribute the effect
- **Introduce validation set** — Fixed inputs ensure you're comparing prompt quality, not input variance

## ANTI-POSITIONING

1. **Not a prompt auto-optimization tool (currently)** — v1 focuses on "scientific comparison," letting humans make data-driven judgments about whether a change improved or degraded output. Auto-optimization is a possible future direction, but not the starting point — without version management and validation set infrastructure, auto-optimization has no foundation to stand on.

2. **Not an LLM observability platform** — No production trace monitoring, real-time alerting, or request log analysis. That's Langfuse / Phoenix's domain. We focus on the "pre-deployment decision" — change it, compare it, confirm it's better, then ship.

3. **Not an evaluation framework** — We don't invent evaluation metrics. DeepEval already has 50+ metrics; we use them directly. What we build is wrapping evaluation into the comparison workflow, making run-eval → view-comparison → make-decision one continuous action.

4. **Not a SaaS platform** — Open-source tool. Data stays on the developer's own machine. No third-party servers involved.

---

## Self-Check Questions

**1. How would you explain this at a dinner party in 30 seconds?**

"You changed your LLM's prompt but don't know if the new version is better. Prompt Lab lets you A/B test two versions — fixed test data, quantified quality differences, data-driven decision on whether to ship."

**2. What's the cheapest validation you've done?**

Done. The EgoZone recommendation prompt simplification scenario is the first real use case: wanted to cut prompt length by 50% but had no validation set to compare old vs. new quality. Ran it manually once but couldn't systematically reproduce.

**3. What would have to happen for this project to FAIL even if done well?**

LLM models become strong enough that prompt wording no longer matters — the model produces ideal output regardless of prompt. If models completely eliminate prompt sensitivity, version management and comparison lose their meaning. Unlikely in the short term, but a long-term risk.

---

Sign-off: Pending Ezio review
