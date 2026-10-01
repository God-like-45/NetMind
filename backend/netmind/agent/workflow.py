from langgraph.graph import StateGraph, START, END
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
import json

from netmind.agent.state import WorkflowState, AgentStateEnum, PlanOutput, EvidenceValidation, RecommendationOutput
from netmind.agent.tools import (
    get_device_telemetry, get_anomaly_history, get_failure_risk, 
    get_topology, get_dependencies, get_configuration_changes, 
    search_incidents, search_runbooks
)

import os
ollama_host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
llm = ChatOllama(model="llama3.2:3b", temperature=0, base_url=ollama_host)
# We can use llm.with_structured_output for precise outputs

def planner_node(state: WorkflowState) -> WorkflowState:
    state["iteration_count"] = state.get("iteration_count", 0)
    state["status"] = AgentStateEnum.PLANNING
    state["audit_log"].append({"action": "planning", "entity": state.get("entity_id")})
    
    planner_llm = llm.with_structured_output(PlanOutput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert telecom network planner. Generate a step-by-step investigation plan for incident {incident_id} on entity {entity_id}."),
        ("user", "Please provide the plan.")
    ])
    chain = prompt | planner_llm
    
    try:
        res = chain.invoke({"incident_id": state.get("incident_id"), "entity_id": state.get("entity_id")})
        state["plan"] = res.steps
    except Exception as e:
        state["plan"] = ["1. Telemetry", "2. Topology", "3. Knowledge Base"]
    return state

def re_planner_node(state: WorkflowState) -> WorkflowState:
    state["iteration_count"] = state.get("iteration_count", 0) + 1
    state["status"] = AgentStateEnum.PLANNING
    state["audit_log"].append({"action": "re_planning", "iteration": state["iteration_count"], "feedback": state.get("validation_feedback")})
    
    planner_llm = llm.with_structured_output(PlanOutput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert telecom network planner. The previous investigation failed because: {feedback}. Generate a revised step-by-step investigation plan for incident {incident_id} on entity {entity_id}."),
        ("user", "Please provide the revised plan.")
    ])
    chain = prompt | planner_llm
    
    try:
        res = chain.invoke({
            "incident_id": state.get("incident_id"), 
            "entity_id": state.get("entity_id"),
            "feedback": state.get("validation_feedback", "Unknown reasons")
        })
        state["plan"] = res.steps
    except Exception as e:
        state["plan"] = ["1. Deeper Telemetry", "2. Alternative Knowledge Search"]
    return state

def investigate_telemetry_node(state: WorkflowState) -> WorkflowState:
    state["status"] = AgentStateEnum.INVESTIGATING
    state["audit_log"].append({"action": "telemetry_investigation"})
    
    roles = ["engineer"] # Mocked roles for the agent context
    
    state["telemetry_data"] = get_device_telemetry(state["entity_id"], roles)
    state["ml_predictions"] = {
        "history": get_anomaly_history(state["entity_id"]),
        "risk": get_failure_risk(state["entity_id"])
    }
    # Also fetch config changes as it's directly tied to the device state
    state["telemetry_data"]["config_changes"] = get_configuration_changes(state["entity_id"])
    return state

def investigate_topology_node(state: WorkflowState) -> WorkflowState:
    state["audit_log"].append({"action": "topology_investigation"})
    state["topology_data"] = {
        "neighbors": get_topology(state["entity_id"]),
        "dependencies": get_dependencies(state["entity_id"])
    }
    return state

def investigate_knowledge_node(state: WorkflowState) -> WorkflowState:
    state["audit_log"].append({"action": "knowledge_retrieval"})
    roles = ["engineer"]
    # Provide a simple search query based on current findings
    query = f"troubleshooting {state['entity_id']}"
    
    state["historical_incidents"] = search_incidents(query, roles)
    state["engineering_docs"] = search_runbooks(query, roles)
    return state

def aggregate_evidence_node(state: WorkflowState) -> WorkflowState:
    state["status"] = AgentStateEnum.ANALYZING
    state["audit_log"].append({"action": "aggregate_evidence"})
    
    evidence = []
    evidence.append(f"Telemetry: {json.dumps(state['telemetry_data'])}")
    evidence.append(f"ML Predictions: {json.dumps(state['ml_predictions'])}")
    evidence.append(f"Topology: {json.dumps(state['topology_data'])}")
    evidence.append(f"Historical: {json.dumps(state['historical_incidents'])}")
    evidence.append(f"Docs: {json.dumps(state['engineering_docs'])}")
    
    state["evidence"] = evidence
    return state

def validate_evidence_node(state: WorkflowState) -> WorkflowState:
    state["status"] = AgentStateEnum.VALIDATING
    state["audit_log"].append({"action": "validate_evidence"})
    
    validator_llm = llm.with_structured_output(EvidenceValidation)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an AI auditor. Validate if the provided evidence points to a clear root cause. Evidence: {evidence}"),
        ("user", "Is the evidence valid?")
    ])
    chain = prompt | validator_llm
    
    try:
        res = chain.invoke({"evidence": "\n".join(state.get("evidence", []))})
        state["is_evidence_valid"] = res.is_valid
        state["validation_feedback"] = res.reason
    except Exception:
        state["is_evidence_valid"] = True
        state["validation_feedback"] = ""
    return state

def recommendation_node(state: WorkflowState) -> WorkflowState:
    state["status"] = AgentStateEnum.RECOMMENDING
    state["audit_log"].append({"action": "generate_recommendation"})
    
    recommender_llm = llm.with_structured_output(RecommendationOutput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Based on the evidence, provide a root cause finding, confidence score, recommended action, and risk. Evidence: {evidence}"),
        ("user", "Generate the recommendation.")
    ])
    chain = prompt | recommender_llm
    
    try:
        res = chain.invoke({"evidence": "\n".join(state["evidence"])})
        state["recommendation"] = res.model_dump()
    except Exception:
        state["recommendation"] = {
            "finding": "Unable to generate via LLM",
            "confidence": 0.0,
            "recommended_action": "Manual review required",
            "risk": "UNKNOWN"
        }
    
    state["status"] = AgentStateEnum.WAITING_FOR_APPROVAL
    return state

def escalate_node(state: WorkflowState) -> WorkflowState:
    state["status"] = AgentStateEnum.ESCALATED
    state["audit_log"].append({"action": "escalate_to_L2"})
    state["recommendation"] = {
        "finding": "Automated investigation exhausted without conclusive evidence. Escalating to L2 support.",
        "confidence": 0.0,
        "recommended_action": "Manual review required by Tier 2 Network Engineer.",
        "risk": "UNKNOWN"
    }
    return state

def build_investigation_graph():
    builder = StateGraph(WorkflowState)
    
    builder.add_node("planner", planner_node)
    builder.add_node("re_planner", re_planner_node)
    builder.add_node("telemetry", investigate_telemetry_node)
    builder.add_node("topology", investigate_topology_node)
    builder.add_node("knowledge", investigate_knowledge_node)
    builder.add_node("aggregate", aggregate_evidence_node)
    builder.add_node("validate", validate_evidence_node)
    builder.add_node("recommend", recommendation_node)
    builder.add_node("escalate", escalate_node)
    
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "telemetry")
    builder.add_edge("re_planner", "telemetry")
    builder.add_edge("telemetry", "topology")
    builder.add_edge("topology", "knowledge")
    builder.add_edge("knowledge", "aggregate")
    builder.add_edge("aggregate", "validate")
    
    # Conditional edge based on validation
    def check_validation(state: WorkflowState):
        if state.get("is_evidence_valid", False):
            return "recommend"
            
        iteration = state.get("iteration_count", 0)
        if iteration >= 2:
            return "escalate"
        return "re_planner"
        
    builder.add_conditional_edges("validate", check_validation)
    builder.add_edge("recommend", END)
    builder.add_edge("escalate", END)
    
    return builder.compile()
