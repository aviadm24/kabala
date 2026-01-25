import os

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = (
    "/Users/aviadmoshe/Documents/code_projects/kabala/secrets/ocr-fastapi-project-485023-25fcdbfefb27.json"
)
from google.cloud import vision

# Create client
client = vision.ImageAnnotatorClient()

# Load local image
with open("/Users/aviadmoshe/Documents/code_projects/kabala/overflow/test_image.jpeg", "rb") as f:
    content = f.read()

image = vision.Image(content=content)

# Perform OCR
response = client.text_detection(image=image)

# Print full text
if response.text_annotations:
    print(response.text_annotations[0].description)
else:
    print("No text detected")

