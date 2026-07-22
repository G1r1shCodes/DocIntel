from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class PageData:
    page_number: int
    text: str
    blocks: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    headings: List[str] = field(default_factory=list)
    is_ocr: bool = False

@dataclass
class DocumentData:
    filename: str
    file_type: str
    text: str
    metadata: Dict[str, Any]
    pages: List[PageData]
