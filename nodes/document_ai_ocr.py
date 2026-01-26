from google.cloud import documentai

PROJECT_ID = "YOUR_PROJECT_ID"
LOCATION = "us"
PROCESSOR_ID = "YOUR_PROCESSOR_ID"

def document_ai_ocr_node(state):
    client = documentai.DocumentProcessorServiceClient()
    name = client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)
    request = documentai.ProcessRequest(
        name=name,
        document_uri=state["file_url"]
    )
    result = client.process_document(request=request)
    doc = result.document
    state["raw_text"] = doc.text
    state["structured_data"] = {
        ent.type_: ent.mention_text for ent in doc.entities
    }
    state["metadata"]["engine"] = "document_ai"
    return state
