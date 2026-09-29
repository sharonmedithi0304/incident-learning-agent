"""Optional polish of the 'why the plan changed' text. Any failure -> original text."""
from .config import Settings


def polish_why(why: str, settings: Settings) -> str:
    if not settings.anthropic_api_key:
        return why
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        msg = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=300,
            messages=[{"role": "user", "content": (
                "Rewrite this incident-response explanation in at most 3 crisp sentences. "
                "Use ONLY the facts given; add nothing new.\n\n" + why)}],
        )
        text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
        return text or why
    except Exception:
        return why
