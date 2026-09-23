"""Incident Chat page — free-text incident intake that runs the full
LangGraph workflow and displays every agent's findings plus final
recommendations. Also supports uploading a report as PDF."""
from __future__ import annotations

import streamlit as st

from workflows.incident_workflow import IncidentWorkflow


@st.cache_resource(show_spinner=False)
def _get_workflow() -> IncidentWorkflow:
    return IncidentWorkflow()


def _priority_badge(priority: str) -> str:
    colors = {
        "P1-Critical": "🔴",
        "P2-High": "🟠",
        "P3-Medium": "🟡",
        "P4-Low": "🟢",
    }
    return f"{colors.get(priority, '⚪')} {priority}"


def render() -> None:
    st.title("💬 Incident Chat")
    st.caption("Describe an incident in plain language. The agent pipeline classifies it, "
               "pulls logs, queries the service graph, retrieves SOPs, and recommends next steps.")

    with st.form("incident_form"):
        incident_text = st.text_area(
            "Incident description",
            placeholder="e.g. Payment API is timing out for ~15% of checkout requests since 10:42 UTC.",
            height=100,
        )
        col1, col2 = st.columns(2)
        with col1:
            log_path = st.text_input("Log file path (optional)", value="sample_data/logs/app.log")
        with col2:
            graph_question = st.text_input("Graph question override (optional)")
        submitted = st.form_submit_button("Run Incident Analysis", type="primary", use_container_width=True)

    if not submitted:
        return

    if not incident_text.strip():
        st.warning("Please describe the incident first.")
        return

    workflow = _get_workflow()
    with st.spinner("Running multi-agent analysis..."):
        try:
            result = workflow.run(
                incident_text=incident_text,
                log_path=log_path or None,
                graph_question=graph_question or None,
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Workflow failed to run: {exc}")
            st.info("Make sure Ollama and Neo4j are running (see README / docker-compose).")
            return

    classification = result.get("classification", {})
    rca = result.get("rca", {})
    recommendation = result.get("recommendation", {})

    st.divider()
    st.subheader("Classification")
    c1, c2, c3 = st.columns(3)
    c1.metric("Category", classification.get("category", "—"))
    c2.metric("Priority", _priority_badge(classification.get("priority", "—")))
    c3.metric("Affected Service", classification.get("affected_service", "—"))
    if classification.get("reasoning"):
        st.caption(classification["reasoning"])

    tabs = st.tabs(["🧠 Root Cause", "✅ Recommendations", "📜 Logs", "🕸️ Graph", "📚 Knowledge Base", "🐞 Raw / Errors"])

    with tabs[0]:
        st.write(rca.get("summary", "No root cause synthesis available."))
        for h in rca.get("hypotheses", []):
            st.progress(h.get("confidence", 0), text=f"{h.get('cause')} ({h.get('confidence', 0):.0%})")
            st.caption(h.get("evidence", ""))

    with tabs[1]:
        if recommendation.get("escalation_needed"):
            st.error(f"⚠️ Escalation recommended: {recommendation.get('escalation_reason')}")
        st.markdown("**Immediate actions**")
        for a in recommendation.get("immediate_actions", []) or ["—"]:
            st.checkbox(a, key=f"imm_{a}")
        st.markdown("**Verification steps**")
        for a in recommendation.get("verification_steps", []) or ["—"]:
            st.write(f"- {a}")
        st.markdown("**Preventive actions**")
        for a in recommendation.get("preventive_actions", []) or ["—"]:
            st.write(f"- {a}")

    with tabs[2]:
        log_findings = result.get("log_findings", {})
        st.json(log_findings, expanded=False)
        if log_findings.get("summary"):
            st.write(log_findings["summary"])

    with tabs[3]:
        graph_findings = result.get("graph_findings", {})
        st.code(graph_findings.get("cypher", ""), language="cypher")
        st.dataframe(graph_findings.get("rows", []), use_container_width=True)

    with tabs[4]:
        sop_findings = result.get("sop_findings", {})
        st.write(sop_findings.get("summary", "No relevant SOPs found."))
        for src in sop_findings.get("cited_sources", []):
            st.caption(f"📄 {src}")

    with tabs[5]:
        if result.get("errors"):
            st.warning("Some agents reported errors (pipeline still completed with partial data):")
            for e in result["errors"]:
                st.code(e)
        st.json(result, expanded=False)
