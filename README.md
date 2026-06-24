# Video Game Recommendation Agent

RAG-powered agent for recommending video games from a Qdrant collection of game evidence.

## What it does

- Takes questions like "Recommend a game like Hollow Knight" or "What should I play if I want a relaxing farming game?"
- Retrieves dense and BM25 candidates from Qdrant, fuses them with RRF, and reranks them with a local cross-encoder.
- Answers only from retrieved evidence instead of inventing details.
- Refuses unrelated questions.

## Setup

```bash
uv sync
```

Create a `.env` file with the services you use:

```bash
cp .env.template .env
```

Set the values for your environment. Qdrant connection, collection, embedding,
vector, and payload settings are required and must match the existing collection
schema. `QDRANT_API_KEY` may be empty for local Qdrant. `OPENAI_BASE_URL` is
optional if you use a compatible local or hosted endpoint.
`RETRIEVER_CANDIDATE_K` controls the hybrid candidate pool, `RETRIEVER_K`
controls how many reranked fragments reach the agent, and `RERANK_MODEL_NAME`
selects the FastEmbed cross-encoder.

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

Apply PostgreSQL migrations:

```bash
uv run python -m src.db.migrate
```

Populate Postgres with a Steam app:

```bash
uv run python -m src.data_pipeline.steam_store 1091500 --postgres-dsn "$POSTGRES_DSN"
```

Import one English Eurogamer review by the exact stored game name:

```bash
uv run python -m src.data_pipeline.review_ingest "Hades" --publisher eurogamer --postgres-dsn "$POSTGRES_DSN"
```

The importer finds the review through Eurogamer's yearly sitemaps around the
stored Steam release year, saves the original paragraphs in PostgreSQL, and
upserts overlapping, context-augmented chunks into Qdrant. Each point records
its review ID, publisher, zero-based chunk index, and total chunk count.

Index stored games into Qdrant:

```bash
uv run python -m src.data_pipeline.qdrant_ingest --postgres-dsn "$POSTGRES_DSN"
```

## Test

```bash
uv run pytest
```
