import json

import chainlit as cl

from src.agent import ask_agent_with_payload


@cl.step(name="Run agent", type="tool", show_input=True)
async def run_agent(query: str) -> dict:
    return await cl.make_async(ask_agent_with_payload)(query)


@cl.on_message
async def main(message: cl.Message) -> None:
    result = await run_agent(message.content)
    payload = result.get("frontend_payload")
    elements = (
        [
            cl.Text(
                name="frontend_payload.json",
                content=json.dumps(payload, indent=2),
                display="inline",
                language="json",
            )
        ]
        if payload
        else []
    )

    await cl.Message(
        content=result.get("answer", "No answer returned."),
        elements=elements,
    ).send()
