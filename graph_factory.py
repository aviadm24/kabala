from langgraph.graph import StateGraph, END
from graph_state import OCRState
from nodes.vision_ocr import vision_ocr_node
from nodes.document_ai_ocr import document_ai_ocr_node
from nodes.router import ocr_router

def build_ocr_graph():
    graph = StateGraph(OCRState)
    graph.add_node("vision", vision_ocr_node)
    graph.add_node("document_ai", document_ai_ocr_node)
    graph.set_conditional_entry_point(
        ocr_router,
        {
            "vision": "vision",
            "document_ai": "document_ai"
        }
    )
    graph.add_edge("vision", END)
    graph.add_edge("document_ai", END)
    return graph.compile()
