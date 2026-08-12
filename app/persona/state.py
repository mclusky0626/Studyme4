from pydantic import BaseModel, Field


class PersonaState(BaseModel):
    conversation_energy: float = Field(default=0.5, ge=0, le=1)
    current_mood: str = "neutral"
    recent_topics: list[str] = []
