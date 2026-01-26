from google.cloud import vision

def vision_ocr_node(state):
    client = vision.ImageAnnotatorClient()
    image = vision.Image()
    image.source.image_uri = state["file_url"]
    response = client.text_detection(image=image)
    texts = response.text_annotations
    state["raw_text"] = texts[0].description if texts else ""
    state["metadata"]["engine"] = "vision_api"
    return state
