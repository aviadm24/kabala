from fastapi import APIRouter
from graph_factory import build_ocr_graph

router = APIRouter()
ocr_graph = build_ocr_graph()

@router.post("/ocr")
def ocr_endpoint(file_url: str, file_type: str):
    initial_state = {
        "file_url": file_url,
        "file_type": file_type,
        "raw_text": None,
        "structured_data": None,
        "metadata": {}
    }
    return ocr_graph.invoke(initial_state)
