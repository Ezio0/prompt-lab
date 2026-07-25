# Prompt Lab

> Open-source prompt versioning, A/B testing, and evaluation workflow for LLM applications.

**⚠️ Early stage — Positioning defined, PRD/Spec in progress. No code yet.**

## The Problem

Every team using LLMs in production faces the same issue: changing a prompt is a gamble. You edit a string, eyeball a few outputs, and ship it — hoping nothing breaks. There's no version history, no validation set, no quantitative comparison. Sometimes it gets better, sometimes it gets much worse, and you can't tell which.

## What We're Building

Prompt Lab turns prompt iteration from guesswork into controlled experimentation:

1. **Define the ideal state** — Before changing a prompt, specify what "good output" looks like
2. **Change one variable at a time** — Each modification is isolated and tracked
3. **Validate against a test set** — Fixed inputs ensure you're comparing prompt quality, not input variance

## How It Works

```
prompt-lab init                          # Initialize project
prompt-lab add version v2 --file prompt.txt   # Register new version
prompt-lab run --baseline v1 --candidate v2 --dataset cases.json  # A/B test
prompt-lab compare v1 v2                 # View comparison report
prompt-lab promote v2                    # Promote the winner
```

## Positioning

- **For**: Developers building LLM applications + PMs/operators who iterate on prompts
- **Not**: An auto-optimizer, observability platform, eval framework, or SaaS
- **Built on**: [DeepEval](https://github.com/confident-ai/deepeval) for evaluation metrics

## Why Now

- LLM apps exploded in 2023+ — prompts are now production assets, not throwaway scripts
- Model providers change behavior frequently (thinking modes, parameter coupling)
- Open-source ecosystem covers testing (Promptfoo), metrics (DeepEval), tracing (Langfuse) — but no one has built the complete **change → compare → decide** loop

## Status

- [x] Positioning Memo
- [ ] PRD
- [ ] Technical Spec
- [ ] Implementation Plan
- [ ] Test Plan
- [ ] v0.1 Release

## License

MIT
