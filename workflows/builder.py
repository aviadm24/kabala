"""
LangGraph builder for claim email processing workflow.

This constructs the workflow graph with:
1. Outbound email flow: Generate → Send → Wait for response
2. Inbound response flow: Process → Parse intent → Decide action → Update status
"""

from langgraph.graph import StateGraph, END
from workflows.claim_state import ClaimWorkflowState
from workflows.nodes import (
    generate_documents_node,
    send_email_node,
    process_inbound_response_node,
    parse_intent_node,
    decide_next_action_node,
    update_claim_status_node,
)


def build_claim_workflow_graph():
    """
    Build the claim email processing workflow graph.
    
    The workflow has two main flows:
    
    1. Outbound (sending email to insurance):
       generate_documents → send_email → (wait for inbound)
    
    2. Inbound (processing response):
       process_inbound → parse_intent → decide_action → update_status → END
    """
    graph = StateGraph(ClaimWorkflowState)
    
    # Add nodes
    graph.add_node("generate_documents", generate_documents_node)
    graph.add_node("send_email", send_email_node)
    graph.add_node("process_inbound", process_inbound_response_node)
    graph.add_node("parse_intent", parse_intent_node)
    graph.add_node("decide_action", decide_next_action_node)
    graph.add_node("update_status", update_claim_status_node)
    
    # Outbound flow edges
    graph.add_edge("generate_documents", "send_email")
    graph.add_edge("send_email", END)  # Transitions to waiting for inbound webhook
    
    # Inbound flow edges (triggered by webhook)
    graph.add_edge("process_inbound", "parse_intent")
    graph.add_edge("parse_intent", "decide_action")
    graph.add_edge("decide_action", "update_status")
    graph.add_edge("update_status", END)
    
    # Set entry points
    # Note: In practice, you'll invoke with start_node parameter
    graph.set_entry_point("generate_documents")
    
    return graph.compile()


def build_inbound_response_workflow():
    """
    Build a specialized workflow for processing inbound emails only.
    
    This is triggered by the webhook when an inbound email arrives.
    """
    graph = StateGraph(ClaimWorkflowState)
    
    graph.add_node("process_inbound", process_inbound_response_node)
    graph.add_node("parse_intent", parse_intent_node)
    graph.add_node("decide_action", decide_next_action_node)
    graph.add_node("update_status", update_claim_status_node)
    
    graph.add_edge("process_inbound", "parse_intent")
    graph.add_edge("parse_intent", "decide_action")
    graph.add_edge("decide_action", "update_status")
    graph.add_edge("update_status", END)
    
    graph.set_entry_point("process_inbound")
    
    return graph.compile()


# Build graphs on module load
claim_workflow = build_claim_workflow_graph()
inbound_workflow = build_inbound_response_workflow()
