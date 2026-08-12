from pydantic import BaseModel, Field


class RelationshipCandidate(BaseModel):
    user_a_discord_id: str
    user_b_discord_id: str
    relation_type: str = "unknown"
    description: str
    event_type: str = "stated_relation"
    sentiment: float = Field(default=0, ge=-1, le=1)
    confidence: float = Field(default=0.8, ge=0, le=1)
    is_explicit: bool = True


class RelationshipView(BaseModel):
    id: str
    user_a_name: str
    user_b_name: str
    relation_type: str
    confidence: float
