from __future__ import annotations

from datetime import datetime, timezone

from app.core.prompts import SYSTEM_PROMPT


class MorningBrief:
    """Build a concise, fresh morning briefing using the LLM web-grounding path."""

    TOPICS = (
        "AI and automation: OpenAI, Google Gemini, Anthropic, new models, agents and major launches",
        "Technology: Microsoft, Apple, Google, Meta, NVIDIA, cybersecurity and important product updates",
        "India and world: major events, government/economy/business developments with real impact",
        "Markets and business: major market-moving developments, startups and important economic news",
    )

    def __init__(self, llm):
        self.llm = llm

    async def generate(self) -> str:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        topic_block = "\n".join(f"{i + 1}. {topic}" for i, topic in enumerate(self.TOPICS))
        system = (
            SYSTEM_PROMPT
            + "\n\nMORNING BRIEF MODE: Create a factual, concise morning briefing for Boss. "
            "Use live web grounding. Prefer developments from the last 24 hours; if an item is older, "
            "include it only when it is still important today. Never invent a headline, date, number, "
            "company statement, or source. Separate confirmed facts from analysis. Reply in natural Roman Hinglish."
        )
        prompt = (
            f"Prepare today's Morning Brief for {today}. Cover these areas:\n{topic_block}\n\n"
            "Return exactly 5 most important stories. For each: headline, 1-2 line summary, why it matters, "
            "and a short source/domain mention. End with 'MIRA Take:' containing 3 concise practical observations."
        )
        return await self.llm.generate(system, [], prompt, web_search=True)
