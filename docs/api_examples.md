# RepoPilot API Examples

These examples are intentionally small. Start the app first:

```powershell
uvicorn repopilot.main:app --reload
```

Base URL:

```text
http://127.0.0.1:8000
```

## Health

```powershell
curl.exe http://127.0.0.1:8000/health
```

## Demo Workflow

```powershell
curl.exe http://127.0.0.1:8000/demo/workflow
```

This endpoint is fully in-memory.

## Repository Scan Summary

```powershell
curl.exe -X POST http://127.0.0.1:8000/repositories/scan-summary `
  -H "Content-Type: application/json" `
  -d "{\"root_path\":\"D:/RepoPilot\"}"
```

Body:

```json
{
  "root_path": "D:/RepoPilot"
}
```

## Context Preview

```json
{
  "root_path": "D:/RepoPilot",
  "query": "safe patch apply",
  "top_k": 5,
  "max_preview_chars": 500
}
```

## Plan Preview

```json
{
  "root_path": "D:/RepoPilot",
  "issue": "Improve safe patch apply docs",
  "top_k": 5
}
```

## Patch Preview

```json
{
  "root_path": "D:/RepoPilot",
  "issue": "Improve safe patch apply docs",
  "top_k": 5,
  "max_preview_chars": 500
}
```

This endpoint does not apply patches.

## Patch Apply

Use only against a prepared temporary repository.

```json
{
  "root_path": "D:/TempRepo",
  "approved": true,
  "proposal": {
    "summary": "Update app output.",
    "target_files": ["src/app.py"],
    "changes": [
      {
        "path": "src/app.py",
        "reason": "Reviewed change.",
        "start_line": 1,
        "end_line": 1,
        "original_content": "print('old')\n",
        "proposed_content": "print('new')\n"
      }
    ],
    "risks": ["May affect app output."],
    "requires_approval": true
  }
}
```

## Apply And Validate

```json
{
  "root_path": "D:/TempRepo",
  "approved": true,
  "validation_commands": [["pytest"], ["ruff", "check", "."]],
  "timeout_seconds": 30,
  "proposal": {
    "summary": "Update app output.",
    "target_files": ["src/app.py"],
    "changes": [
      {
        "path": "src/app.py",
        "reason": "Reviewed change.",
        "start_line": 1,
        "end_line": 1,
        "original_content": "print('old')\n",
        "proposed_content": "print('new')\n"
      }
    ],
    "risks": ["May affect app output."],
    "requires_approval": true
  }
}
```

Commands must be allowlisted.

## Failure Analysis

```json
{
  "max_excerpt_chars": 500,
  "validation_result": {
    "apply_result": {
      "applied_files": [],
      "changed_file_count": 0
    },
    "checks": [
      {
        "name": "pytest",
        "command": ["pytest"],
        "result": {
          "command": ["pytest"],
          "return_code": 1,
          "stdout": "test failed",
          "stderr": "",
          "timed_out": false
        },
        "passed": false
      }
    ],
    "passed": false
  }
}
```

## Repair Approval Request

This milestone uses fake LLM response JSON instead of real providers.

```json
{
  "llm_response_json": "{\"summary\":\"Repair login.\",\"target_files\":[\"src/auth.py\"],\"changes\":[],\"risks\":[],\"requires_approval\":true}",
  "model": "fake-repair-proposer",
  "temperature": 0.0,
  "file_reads": [],
  "failed_attempt": {
    "attempt_number": 1,
    "proposal": {
      "summary": "Initial patch failed.",
      "target_files": ["src/auth.py"],
      "changes": [],
      "risks": [],
      "requires_approval": true
    },
    "validation_result": {
      "apply_result": {
        "applied_files": [],
        "changed_file_count": 0
      },
      "checks": [],
      "passed": false
    },
    "failure_analysis": {
      "passed": false,
      "failed_check_count": 1,
      "failed_checks": [],
      "summary": "Validation failed.",
      "needs_self_correction": true
    }
  }
}
```

## Repair Apply Result Report

```json
{
  "issue": "Fix login bug",
  "repair_summary": "Repair login behavior.",
  "repair_result": {
    "changed_file_count": 1,
    "applied_files": [
      {
        "path": "src/auth.py",
        "changed": true
      }
    ],
    "validation": null
  }
}
```

## Unified Workflow Report

```json
{
  "issue": "Fix login bug",
  "plan": null,
  "patch_proposal": null,
  "apply_result": null,
  "validation_result": null,
  "failure_analysis": null,
  "repair_approval": null,
  "repair_apply_report": {
    "status": "repair_applied_validation_passed",
    "issue": "Fix login bug",
    "summary": "Repair login behavior.",
    "changed_file_count": 1,
    "changed_files": ["src/auth.py"],
    "validation_ran": true,
    "validation_passed": true,
    "validation_check_count": 1,
    "failed_check_count": 0,
    "failed_checks": [],
    "markdown_summary": "# RepoPilot Repair Apply Report"
  }
}
```
