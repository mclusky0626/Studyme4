from __future__ import annotations

import re

from app.db.models import Visibility
from app.memory.schemas import MemoryCandidate, ValidatedMemory, ValidationContext


class MemoryRejected(ValueError):
    pass


_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:password|비밀번호|인증\s*코드|otp)\b"),
    re.compile(r"(?i)\b(?:sk|ghp|github_pat|gho)-?[a-z0-9_-]{16,}\b"),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
)

_LOW_SIGNAL = re.compile(r"^[\sㅋㅎㅠㅜㅇㄴㄱ!?~.]+$")


class MemoryValidator:
    def validate(self, candidate: MemoryCandidate, context: ValidationContext) -> ValidatedMemory:
        if not candidate.should_store:
            raise MemoryRejected("extractor opted out")
        if candidate.sensitive or any(p.search(candidate.content) for p in _SECRET_PATTERNS):
            raise MemoryRejected("sensitive or secret-like content")
        if _LOW_SIGNAL.fullmatch(candidate.content.strip()):
            raise MemoryRejected("low-signal content")
        if not candidate.is_explicit and candidate.confidence >= 0.8:
            raise MemoryRejected("inference confidence is too high")
        if (
            candidate.subject_discord_user_id != context.author_discord_user_id
            and candidate.sensitive
        ):
            raise MemoryRejected("third-party sensitive memory")

        if context.is_dm:
            visibility = Visibility.DM_PRIVATE
        else:
            if candidate.visibility == Visibility.DM_PRIVATE:
                raise MemoryRejected("DM visibility cannot originate in a guild")
            visibility = candidate.visibility
            if visibility == Visibility.USER_PRIVATE:
                # Private facts are stored but never injected into a guild conversation.
                visibility = Visibility.USER_PRIVATE

        return ValidatedMemory(candidate=candidate, visibility=visibility)
