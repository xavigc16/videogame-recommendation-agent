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
POSTGRES_DSN=postgresql://postgres:postgres@localhost:5432/videogames
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

Run the Chainlit visualizer:

```bash
DEBUG=false uv run chainlit run chainlit_app.py --host 0.0.0.0 --port 8000
```

Populate Postgres with a Steam app:

```bash
uv run python -m src.data_pipeline.steam_store 1091500 --postgres-dsn "$POSTGRES_DSN"
```

Index stored games into Qdrant:

```bash
uv run python -m src.data_pipeline.qdrant_ingest --postgres-dsn "$POSTGRES_DSN"
```

## Test

```bash
uv run pytest
```
