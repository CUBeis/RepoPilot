# RepoPilot Interview Script

## Short Explanation

"RepoPilot is a backend for an agentic AI software engineer. It can scan a
repository, retrieve relevant code, plan changes, propose patches, apply only
approved edits, run allowlisted validation commands, analyze failures, prepare
repairs for approval, and generate PR-ready reports. The interesting part is the
safety architecture: risky actions are separated, typed, tested, and
approval-gated."

## Longer Explanation

"I built RepoPilot as a production-style portfolio project to show the parts of
an AI coding agent that matter beyond prompting. Instead of a single chatbot
endpoint, the system has deterministic repository scanning, chunking, retrieval,
context building, planning, patch proposal, safe patch application, validation,
failure analysis, repair approval, and reporting. Each layer has Pydantic models
and tests. LLM-facing components use a provider-independent interface and fake
deterministic clients until real providers are added."

## Common Questions

### Why Agentic?

Because RepoPilot models a multi-step engineering workflow, not a one-shot chat
response. It prepares context, plans, proposes actions, waits for approval,
executes tools, observes results, and can prepare repairs. That is the shape of
an agentic system.

### How Is It Safe?

RepoPilot separates observation from mutation. Scan, context, plan, patch
preview, and report endpoints are read-only. Patch application requires explicit
approval. Validation commands are allowlisted. Self-correction does not happen
secretly; repair generation, approval, and application are separate steps.

### Where Are LLMs Used?

The project has an LLM client abstraction and fake deterministic clients. There
are LLM-backed planner, patch proposal, and repair proposal layers, but they use
injected clients. No real provider calls are hardcoded into the app yet.

### Why Approval-Gated?

AI-generated code changes can be wrong or risky. RepoPilot treats generated
patches as proposals. A separate approval signal is required before any write
happens, and the proposal itself must also declare that approval is required.

### How Do You Prevent Destructive Behavior?

File writes go through the safe patch applier. It rejects absolute paths, path
traversal, missing files, directories, binary files, and content mismatches. It
validates all changes before writing any file. Commands use `subprocess.run`
without `shell=True` and must match an allowlist.

### What Would You Add In Production?

I would add authentication, authorization, audit logs, repository allowlists,
Docker deployment, real provider adapters, embeddings, vector search, persistent
run storage, UI approval flows, rate limits, and evaluation benchmarks.

### What Was The Hardest Part?

The hardest part was keeping the workflow powerful while keeping safety
boundaries explicit. It is tempting to create one endpoint that does everything,
but production agent systems need separable stages so users can inspect,
approve, validate, and audit each action.

### Why Not Add A Real LLM Immediately?

Real LLMs add latency, cost, secret management, nondeterminism, and structured
output failures. I built deterministic contracts first so provider integration
can plug into tested boundaries later.

### How Do You Explain The Architecture Quickly?

"RepoPilot is a pipeline: repository metadata becomes chunks, chunks become
retrieved context, context becomes a plan, the plan becomes a patch proposal,
the proposal can be approved and applied, validation can run, failures can be
summarized, repairs can be proposed for approval, and reports summarize the
run."

## Strong Closing Statement

"This project shows I understand agentic AI as software architecture, not just
prompting. I focused on typed contracts, deterministic behavior, safety
boundaries, tool execution rules, and test coverage before adding production LLM
providers."
