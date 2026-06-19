# Changelog

All notable changes to RepoPilot are documented here.

## v1.0.0 - 2026-06-19

RepoPilot v1.0.0 is the first portfolio-ready release candidate. It presents a
safe, modular backend for an agentic AI software engineer without relying on
hidden mutation, real provider calls, or unbounded tool execution.

### Added

- FastAPI backend with health checks and interactive API documentation.
- Deterministic repository scanner with ignored directories, file metadata,
  line counts, and content hashes.
- Deterministic line-based code chunker with overlap and chunk hashes.
- Keyword retriever with explainable scoring and stable ordering.
- Repository context builder that composes scan, chunk, and retrieval.
- Deterministic planning layer and LLM-backed planning path using injected
  clients.
- Provider-independent LLM client abstraction and deterministic `FakeLLMClient`.
- Safe read-only file tools for whole-file and line-range reads.
- Deterministic and LLM-backed patch proposal layers.
- Approval-gated patch applier with path safety and original-content matching.
- Safe command runner with exact allowlists and no shell execution.
- Apply-and-validate pipeline with structured validation checks.
- Validation failure analyzer for agent-readable failure summaries.
- Bounded self-correction orchestrator that accepts supplied repair proposals.
- LLM repair proposal generator and approval-gated repair workflow.
- Repair apply API with optional validation.
- Reporting endpoints for run reports, repair apply results, unified workflow
  reports, and deterministic demo workflows.
- CLI `repopilot report-demo` command.
- Portfolio documentation: demo guide, API examples, interview script,
  architecture summary, learning notes, and release checklist.

### Safety

- Read-only preview endpoints for repository scan, context, plan, and patch
  proposal previews.
- Mutating endpoints require explicit approval.
- Validation commands are allowlisted.
- Reporting endpoints are deterministic and do not execute workflow tools.
- No real LLM provider calls are made in the current API surface.
- No automatic repair application or hidden self-correction.
- Bounded previews and command output summaries.

### Verification

- Full pytest suite passes.
- Ruff linting passes.
- Documentation has been prepared for GitHub portfolio presentation.

### Deferred

- Real OpenAI, Anthropic, or local model provider integrations.
- Embeddings and vector database retrieval.
- Persistent run storage.
- Authentication, authorization, and audit logging.
- Frontend approval UI.
- Docker deployment.
- Autonomous end-to-end repair generation and application.
