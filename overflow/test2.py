import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    "/Users/aviadmoshe/Documents/code_projects/kabala/secrets/ocr-fastapi-project-485023-25fcdbfefb27.json"
)

from google.cloud import documentai

client = documentai.DocumentProcessorServiceClient()

PROJECT_ID = "your-project-id"
LOCATION = "eu"  # or "us"
PROCESSOR_ID = "your-processor-id"

name = client.processor_path(PROJECT_ID, LOCATION, PROCESSOR_ID)

with open("/Users/aviadmoshe/Documents/code_projects/kabala/overflow/test.pdf", "rb") as f:
    document = f.read()

request = documentai.ProcessRequest(
    name=name,
    raw_document=documentai.RawDocument(
        content=document,
        mime_type="application/pdf",
    ),
)

result = client.process_document(request=request)

print(result.document.text[:500])
