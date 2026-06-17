# Video Game Recommendation Agent

RAG-powered agent for recommending video games from a Qdrant collection of game evidence.

## What it does

- Takes questions like "Recommend a game like Hollow Knight" or "What should I play if I want a relaxing farming game?"
- Retrieves relevant game evidence from Qdrant.
- Answers only from retrieved evidence instead of inventing details.
- Refuses unrelated questions.

## Setup

```bash
uv sync
```

Create a `.env` file with the services you use:

```bash
OPENAI_API_KEY=...
AGENT_MODEL=gpt-4o-mini
QDRANT_URL=...
QDRANT_API_KEY=...
QDRANT_COLLECTION_NAME=video_game_recommendations
```

`OPENAI_BASE_URL` is optional if you use a compatible local or hosted endpoint.

## Run

```bash
uv run python -m src.main "Recommend a game like Cyberpunk 2077"
```

Or start the small interactive loop:

```bash
uv run python main.py
```

## Test

```bash
uv run pytest
```
