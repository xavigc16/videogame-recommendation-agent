import chainlit as cl

from src.agent import ask_agent_with_payload


@cl.step(name="Run agent", type="tool", show_input=True)
async def run_agent(query: str) -> dict:
    return await cl.make_async(ask_agent_with_payload)(query)


@cl.on_message
async def main(message: cl.Message) -> None:
    result = await run_agent(message.content)
    payload = result.get("frontend_payload")
    card = _game_card_markdown(payload) if payload else ""
    content = result.get("answer", "No answer returned.")
    if card:
        content = f"{content}\n\n{card}"

    await cl.Message(
        content=content,
        elements=_game_card_elements(payload) if payload else [],
    ).send()


def _game_card_markdown(payload: dict) -> str:
    name = payload.get("name") or "Unknown game"
    description = payload.get("short_description") or "No short description available."
    lines = [f"### {name}", description]

    genres = _join_values(payload.get("genres"))
    if genres:
        lines.append(f"**Genres:** {genres}")

    tags = _join_values(payload.get("tags"))
    if tags:
        lines.append(f"**Tags:** {tags}")

    platforms = _join_values(payload.get("platforms"), title=True)
    if platforms:
        lines.append(f"**Platforms:** {platforms}")

    facts = []
    if payload.get("price"):
        facts.append(f"Price: {payload['price']}")
    if payload.get("metacritic_score") is not None:
        facts.append(f"Metacritic: {payload['metacritic_score']}")
    if payload.get("release_date"):
        facts.append(f"Released: {payload['release_date']}")
    if facts:
        lines.append(f"**At a glance:** {' · '.join(facts)}")

    if payload.get("source_url"):
        lines.append(f"[Store page]({payload['source_url']})")

    return "\n\n".join(lines)


def _game_card_elements(payload: dict) -> list:
    if not payload.get("header_image"):
        return []
    return [
        cl.Image(
            name=f"{payload.get('name') or 'Game'} cover",
            url=payload["header_image"],
            display="inline",
            size="large",
        )
    ]


def _join_values(values: list[str] | None, *, title: bool = False) -> str:
    if not values:
        return ""
    if title:
        values = [value.title() for value in values]
    return ", ".join(values)
