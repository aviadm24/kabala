from typing import TypedDict, Optional

class OCRState(TypedDict):
    file_url: str
    file_type: str
    raw_text: Optional[str]
    structured_data: Optional[dict]
    metadata: dict
