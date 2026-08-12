from __future__ import annotations

from app.conversation.context_builder import ConversationContext
from app.llm.base import LLMProvider
from app.persona.profile import PersonaProfile
from app.persona.prompt_builder import PromptBuilder
from app.persona.state import PersonaState


class ResponseGenerator:
    def __init__(self, provider: LLMProvider, prompt_builder: PromptBuilder | None = None):
        self.provider = provider
        self.prompt_builder = prompt_builder or PromptBuilder()

    async def generate(
        self,
        *,
        author_name: str,
        content: str,
        context: ConversationContext,
        profile: PersonaProfile,
        state: PersonaState | None = None,
    ) -> str:
        system = self.prompt_builder.build_system(
            profile=profile,
            state=state or PersonaState(),
            context=context,
        )
        return (
            await self.provider.complete(
                system=system,
                user=f"{author_name}: {content}",
            )
        ).strip()
