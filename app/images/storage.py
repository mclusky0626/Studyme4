from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

_UNSAFE_FILENAME = re.compile(r"[^0-9A-Za-z가-힣._-]+")


@dataclass(frozen=True, slots=True)
class StoredFile:
    path: Path
    byte_size: int
    sha256: str


class LocalImageStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    @staticmethod
    def safe_filename(filename: str) -> str:
        name = Path(filename).name.strip() or "image"
        safe = _UNSAFE_FILENAME.sub("_", name).strip("._")
        return (safe or "image")[:180]

    async def save(
        self,
        *,
        data: bytes,
        guild_id: str | None,
        channel_id: str,
        message_id: str,
        attachment_id: str,
        filename: str,
    ) -> StoredFile:
        scope = f"guild-{guild_id}" if guild_id else "dm"
        directory = self.root / scope / f"channel-{channel_id}"
        safe_name = self.safe_filename(filename)
        path = directory / f"{message_id}_{attachment_id}_{safe_name}"

        def write() -> None:
            directory.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_bytes(data)

        await asyncio.to_thread(write)
        return StoredFile(
            path=path.resolve(),
            byte_size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )

    async def delete(self, stored_path: str) -> bool:
        def validated_path() -> Path | None:
            candidate = Path(stored_path).expanduser().resolve()
            if candidate == self.root or self.root not in candidate.parents:
                return None
            return candidate

        path = await asyncio.to_thread(validated_path)
        if path is None:
            return False

        def unlink() -> bool:
            if not path.is_file():
                return False
            path.unlink()
            return True

        return await asyncio.to_thread(unlink)
