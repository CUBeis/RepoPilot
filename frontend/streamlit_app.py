from __future__ import annotations

from typing import Any

import httpx
import streamlit as st

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_REPOSITORY_ROOT = "D:/RepoPilot"
DEFAULT_ISSUE = "Improve safe patch apply error messages"


def main() -> None:
    st.set_page_config(
        page_title="RepoPilot Agentic AI Coding Backend",
        layout="wide",
    )

    st.title("RepoPilot Agentic AI Coding Backend")
    controls = render_sidebar()

    tabs = st.tabs(
        [
            "Overview",
            "Demo Workflow",
            "Agent Preview",
            "Repository Context",
            "Plan Preview",
            "Patch Preview",
            "Workflow Report",
            "Troubleshooting",
        ]
    )

    with tabs[0]:
        render_overview(controls)
    with tabs[1]:
        render_demo_workflow(controls)
    with tabs[2]:
        render_agent_preview(controls)
    with tabs[3]:
        render_repository_context(controls)
    with tabs[4]:
        render_plan_preview(controls)
    with tabs[5]:
        render_patch_preview(controls)
    with tabs[6]:
        render_workflow_report(controls)
    with tabs[7]:
        render_troubleshooting()


def render_sidebar() -> dict[str, Any]:
    with st.sidebar:
        st.header("Demo Controls")
        api_base_url = st.text_input("API base URL", value=DEFAULT_API_BASE_URL)
        root_path = st.text_input("Repository root", value=DEFAULT_REPOSITORY_ROOT)
        issue = st.text_area("Issue", value=DEFAULT_ISSUE, height=90)
        top_k = st.slider("top_k", min_value=1, max_value=20, value=5)
        max_preview_chars = st.slider(
            "max_preview_chars",
            min_value=100,
            max_value=5000,
            value=1000,
            step=100,
        )
        use_llm = st.checkbox("Use OpenRouter LLM planning", value=False)
        st.info(
            "OpenRouter requires OPENROUTER_API_KEY to be set in the FastAPI "
            "server environment. Keep use_llm disabled for the safest demo path."
        )

    return {
        "api_base_url": api_base_url.strip() or DEFAULT_API_BASE_URL,
        "root_path": root_path.strip(),
        "issue": issue.strip(),
        "top_k": top_k,
        "max_preview_chars": max_preview_chars,
        "use_llm": use_llm,
    }


def render_overview(controls: dict[str, Any]) -> None:
    st.subheader("What RepoPilot Demonstrates")
    st.markdown(
        """
        RepoPilot is an agentic coding backend built around a safe engineering
        workflow:

        `scan -> retrieve -> plan -> propose -> approve -> apply -> validate`
        `-> repair -> report`
        """
    )
    st.subheader("Safety Principles")
    st.markdown(
        """
        - Read-only previews
        - Approval-gated mutation
        - Command allowlisting
        - No hidden self-correction
        - Deterministic reporting
        """
    )

    if st.button("Check API Health", type="primary"):
        result = request_json(controls["api_base_url"], "GET", "/health")
        if result["ok"]:
            st.success("FastAPI is reachable.")
            st.json(result["data"])
        else:
            render_error(result["error"])


def render_demo_workflow(controls: dict[str, Any]) -> None:
    st.subheader("Safe In-Memory Demo Workflow")
    st.caption("This is the fastest first click for a reviewer.")

    if st.button("Run Safe Demo Workflow", type="primary"):
        result = request_json(controls["api_base_url"], "GET", "/demo/workflow")
        if not result["ok"]:
            render_error(result["error"])
            return

        data = result["data"]
        render_workflow_summary(data)


def render_agent_preview(controls: dict[str, Any]) -> None:
    st.subheader("Agent Preview")
    st.caption(
        "Build context, create a plan, and preview a proposal without applying it."
    )

    if st.button("Run Agent Preview", type="primary"):
        payload = build_repository_payload(controls)
        payload["use_llm"] = controls["use_llm"]
        result = request_json(
            controls["api_base_url"],
            "POST",
            "/agent/preview",
            json=payload,
        )
        if result["ok"]:
            render_agent_preview_result(result["data"])
            return

        render_error(result["error"])
        if controls["use_llm"]:
            st.warning(
                "Try disabling use_llm or check OPENROUTER_MODEL / model JSON "
                "compatibility."
            )

    if controls["use_llm"] and st.button("Run Deterministic Fallback"):
        payload = build_repository_payload(controls)
        payload["use_llm"] = False
        result = request_json(
            controls["api_base_url"],
            "POST",
            "/agent/preview",
            json=payload,
        )
        if result["ok"]:
            render_agent_preview_result(result["data"])
        else:
            render_error(result["error"])


def render_repository_context(controls: dict[str, Any]) -> None:
    st.subheader("Repository Context")
    if st.button("Retrieve Context", type="primary"):
        result = request_json(
            controls["api_base_url"],
            "POST",
            "/repositories/context-preview",
            json=build_repository_payload(controls),
        )
        if not result["ok"]:
            render_error(result["error"])
            return

        data = result["data"]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Scanned files", data.get("scanned_file_count", 0))
        col2.metric("Skipped files", data.get("skipped_file_count", 0))
        col3.metric("Total chunks", data.get("total_chunks", 0))
        col4.metric("Retrieved", data.get("retrieved_count", 0))
        render_chunk_cards(data.get("chunks", []))


def render_plan_preview(controls: dict[str, Any]) -> None:
    st.subheader("Deterministic Plan Preview")
    if st.button("Generate Deterministic Plan", type="primary"):
        result = request_json(
            controls["api_base_url"],
            "POST",
            "/repositories/plan-preview",
            json={
                "root_path": controls["root_path"],
                "issue": controls["issue"],
                "top_k": controls["top_k"],
            },
        )
        if result["ok"]:
            render_plan(result["data"].get("plan", {}))
        else:
            render_error(result["error"])


def render_patch_preview(controls: dict[str, Any]) -> None:
    st.subheader("Deterministic Patch Preview")
    st.info("This endpoint previews proposed changes only. It does not apply patches.")

    if st.button("Generate Patch Preview", type="primary"):
        result = request_json(
            controls["api_base_url"],
            "POST",
            "/repositories/patch-preview",
            json=build_repository_payload(controls),
        )
        if result["ok"]:
            render_plan(result["data"].get("plan", {}))
            render_patch_proposal(result["data"].get("proposal"))
        else:
            render_error(result["error"])


def render_workflow_report(controls: dict[str, Any]) -> None:
    st.subheader("Workflow Report")
    if st.button("Run In-Memory Demo Report", type="primary"):
        result = request_json(controls["api_base_url"], "GET", "/demo/workflow")
        if not result["ok"]:
            render_error(result["error"])
            return

        data = result["data"]
        st.metric("Status", data.get("status", "unknown"))
        st.markdown(data.get("markdown_summary", "No markdown summary returned."))
        st.text_area(
            "Markdown summary",
            value=data.get("markdown_summary", ""),
            height=420,
        )


def render_troubleshooting() -> None:
    st.subheader("Troubleshooting")
    st.markdown(
        """
        - FastAPI server not running: start it with
          `uvicorn repopilot.main:app --reload`.
        - Wrong API base URL: check the sidebar value.
        - Missing `OPENROUTER_API_KEY`: disable use_llm or set it in the
          FastAPI server shell.
        - OpenRouter model returned invalid JSON: try deterministic fallback.
        - OpenRouter response content was not text: show the backend error and
          switch models.
        - Free models may be unreliable for structured JSON planning responses.
        - `use_llm=false` works without any API key.
        - Swagger is optional; this Streamlit UI is the preferred demo surface.
        """
    )


def render_agent_preview_result(data: dict[str, Any]) -> None:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Used LLM", str(data.get("used_llm", False)))
    col2.metric("Repository", data.get("root_name", "unknown"))
    col3.metric("Scanned files", data.get("scanned_file_count", 0))
    col4.metric("Retrieved chunks", data.get("retrieved_count", 0))

    render_plan(data.get("plan", {}))
    render_patch_proposal(data.get("patch_proposal"))
    st.subheader("Markdown Summary")
    st.markdown(data.get("markdown_summary", "No markdown summary returned."))
    st.subheader("Safety Note")
    st.info(data.get("safety_note", "Preview-only endpoint."))


def render_workflow_summary(data: dict[str, Any]) -> None:
    col1, col2 = st.columns(2)
    col1.metric("Status", data.get("status", "unknown"))
    col2.metric("Validation passed", str(data.get("validation_passed")))
    st.write("Issue:", data.get("issue", ""))
    render_list("Planned files", data.get("planned_files", []))
    render_list("Proposed files", data.get("proposed_files", []))
    render_list("Changed files", data.get("changed_files", []))
    st.markdown(data.get("markdown_summary", "No markdown summary returned."))


def render_plan(plan: dict[str, Any]) -> None:
    st.subheader("Plan")
    st.write("Objective:", plan.get("objective", ""))
    st.progress(float(plan.get("confidence", 0.0)))
    render_list("Relevant files", plan.get("relevant_files", []))
    st.markdown("**Steps**")
    for step in plan.get("steps", []):
        with st.expander(f"Step {step.get('order')}: {step.get('description')}"):
            render_list("Target files", step.get("target_files", []))
    render_list("Risks", plan.get("risks", []))
    render_list("Assumptions", plan.get("assumptions", []))


def render_patch_proposal(proposal: dict[str, Any] | None) -> None:
    st.subheader("Patch Proposal Preview")
    if not proposal:
        st.info("No patch proposal preview was returned.")
        return

    st.write("Summary:", proposal.get("summary", ""))
    st.write("Requires approval:", proposal.get("requires_approval", True))
    render_list("Target files", proposal.get("target_files", []))
    render_list("Risks", proposal.get("risks", []))
    for change in proposal.get("changes", []):
        label = (
            f"{change.get('path')} lines "
            f"{change.get('start_line')}-{change.get('end_line')}"
        )
        with st.expander(label):
            st.write("Reason:", change.get("reason", ""))
            st.markdown("**Original preview**")
            st.code(change.get("original_preview", ""), language="text")
            st.markdown("**Proposed preview**")
            st.code(change.get("proposed_preview", ""), language="text")


def render_chunk_cards(chunks: list[dict[str, Any]]) -> None:
    st.subheader("Retrieved Chunks")
    if not chunks:
        st.info("No chunks were retrieved.")
        return

    for chunk in chunks:
        label = (
            f"{chunk.get('path')} lines "
            f"{chunk.get('start_line')}-{chunk.get('end_line')}"
        )
        with st.expander(label):
            col1, col2, col3 = st.columns(3)
            col1.metric("Language", chunk.get("language") or "unknown")
            col2.metric("Score", chunk.get("score", 0))
            col3.write("Matched terms:", ", ".join(chunk.get("matched_terms", [])))
            st.code(chunk.get("preview", ""), language="text")


def render_list(title: str, values: list[Any]) -> None:
    st.markdown(f"**{title}**")
    if not values:
        st.caption("None")
        return
    for value in values:
        st.write(f"- {value}")


def render_error(error: str) -> None:
    st.error(error)


def build_repository_payload(controls: dict[str, Any]) -> dict[str, Any]:
    return {
        "root_path": controls["root_path"],
        "query": controls["issue"],
        "issue": controls["issue"],
        "top_k": controls["top_k"],
        "max_preview_chars": controls["max_preview_chars"],
    }


def request_json(
    api_base_url: str,
    method: str,
    endpoint: str,
    *,
    json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{api_base_url.rstrip('/')}{endpoint}"
    try:
        response = httpx.request(method, url, json=json, timeout=30.0)
    except httpx.RequestError as error:
        return {"ok": False, "error": f"Could not reach FastAPI: {error}"}

    if response.status_code >= 400:
        return {"ok": False, "error": format_api_error(response)}

    try:
        return {"ok": True, "data": response.json()}
    except ValueError:
        return {"ok": False, "error": "API response was not valid JSON."}


def format_api_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"API returned {response.status_code}: {response.text}"

    detail = payload.get("detail", payload)
    return f"API returned {response.status_code}: {detail}"


if __name__ == "__main__":
    main()
