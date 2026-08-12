from pydantic import BaseModel, Field


class PersonaProfile(BaseModel):
    name: str
    version: str = "v1"
    speaking_style: str
    humor: float = Field(default=0.5, ge=0, le=1)
    kindness: float = Field(default=0.7, ge=0, le=1)
    curiosity: float = Field(default=0.5, ge=0, le=1)
    initiative: float = Field(default=0.2, ge=0, le=1)
    prohibited_behaviors: list[str] = [
        "AI라는 정체성 숨기기",
        "감정적 의존 유도",
        "확인되지 않은 개인 정보 단정",
    ]
