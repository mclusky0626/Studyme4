from __future__ import annotations

import re

_RECALL_PATTERNS = (
    re.compile(r"(?:사진|이미지|그림|짤).*(?:보여|찾아|꺼내|불러|보내|올려|재전송)"),
    re.compile(r"(?:보여|찾아|꺼내|불러|보내|올려|재전송).*(?:사진|이미지|그림|짤)"),
)


def is_image_recall_request(content: str) -> bool:
    compact = " ".join(content.casefold().split())
    return any(pattern.search(compact) for pattern in _RECALL_PATTERNS)
