def ocr_router(state):
    if state["file_type"] == "pdf":
        return "document_ai"
    return "vision"
