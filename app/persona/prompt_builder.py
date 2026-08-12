from __future__ import annotations

from app.conversation.context_builder import ConversationContext
from app.persona.profile import PersonaProfile
from app.persona.state import PersonaState


class PromptBuilder:
    def build_system(
        self,
        *,
        profile: PersonaProfile,
        state: PersonaState,
        context: ConversationContext,
    ) -> str:
        memories = "\n".join(f"- {item}" for item in context.memories) or "- 없음"
        relations = "\n".join(f"- {item}" for item in context.relationships) or "- 없음"
        history = "\n".join(context.recent_messages) or "- 없음"
        prohibited = ", ".join(profile.prohibited_behaviors)
        return f"""너는 Discord의 AI 챗봇 {profile.name}다. AI라는 사실을 숨기지 않는다.
말투: {profile.speaking_style}
현재 대화 에너지: {state.conversation_energy:.2f}; 상태: {state.current_mood}
짧은 메시지에는 짧게 답하고, 매번 질문이나 상대 이름으로 끝내지 마라.
기억은 아래 제공된 항목만 사실로 사용한다. 추론과 사실을 구분하고 확신이 없으면 단정하지 마라.
DM 기억을 서버에 공개하거나 내부 ID, 점수, 근거 ID를 출력하지 마라.
금지: {prohibited}

[관련 기억]
{memories}

[관계]
{relations}

[최근 대화]
{history}"""
