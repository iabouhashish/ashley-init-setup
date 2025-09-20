# MCP Agent API (Azure OpenAI + Qdrant + Firestore + SSE)

FastAPI endpoints for a production-ready, agentic chat backend:

- **Azure OpenAI** (chat + embeddings)
- **Qdrant** vector DB
- **Firestore** conversation memory (with emulator support)
- **SSE** token streaming
- Docker & Docker Compose

---

## Environment Variables (What each one does)

| Key | Why it matters | Example |
|---|---|---|
| `API_KEY` | Static API key the client must send via `X-API-Key` header to call secured endpoints. | `super-secret-key` |
| `CORS_ORIGINS` | Comma-separated allowed origins for browsers/mobile webviews. Use `*` for dev. | `https://app.example.com` or `*` |

### Azure OpenAI (chat/completions)
| Key | Why it matters | Example |
|---|---|---|
| `AZURE_OPENAI_KEY` | Your Azure OpenAI API key. Required for both chat and embeddings. | `xxxxxxxx...` |
| `AZURE_OPENAI_ENDPOINT` | Base endpoint for your Azure OpenAI resource. | `https://my-aoai.openai.azure.com` |
| `AZURE_API_VERSION` | API version used by the SDK. Must match your resource’s supported versions. | `2024-02-15-preview` |
| `AZURE_DEPLOYMENT_NAME` | **Deployment name** of your chat model (not the family). | `gpt-4o-dev` |

### Azure OpenAI (embeddings)
| Key | Why it matters | Example |
|---|---|---|
| `AZURE_EMBEDDING_DEPLOYMENT` | Deployment name for your embedding model. | `text-embedding-3-large` |

> **Important:** Your Qdrant collection’s vector size must match the chosen embedding model:  
> - `text-embedding-3-large` → **3072**  
> - `text-embedding-3-small` → **1536**  
> Update `EMBEDDING_DIM` accordingly.

### Qdrant (vector DB)
| Key | Why it matters | Example |
|---|---|---|
| `QDRANT_HOST` | Hostname of Qdrant. In Docker Compose, it’s the service name. | `qdrant` (inside compose) or `127.0.0.1` (local) |
| `QDRANT_PORT` | Qdrant gRPC/HTTP port. | `6333` |
| `QDRANT_COLLECTION` | Collection name used for RAG data. Auto-created if missing. | `memory` |
| `QDRANT_DISTANCE` | Similarity metric (`COSINE` or `DOT`). | `COSINE` |
| `EMBEDDING_DIM` | **Must match** your embedding model’s output dimension. | `3072` for `text-embedding-3-large` |

### Firestore (conversation memory)
| Key | Why it matters | Example |
|---|---|---|
| `GCP_PROJECT_ID` | Project id for Firestore. Also used for the emulator. | `my-gcp-project` |

> **Emulator:** If `FIRESTORE_EMULATOR_HOST` is set (Compose does this), the app uses the emulator and **does not** need real GCP creds.  
> **Production:** Unset emulator vars and provide application default creds (`GOOGLE_APPLICATION_CREDENTIALS`) or run on GCP.

---

## Quickstart (local, no Compose)

```bash
# 1) Create env
cp .env.example .env
# Fill in AZURE_* and set EMBEDDING_DIM properly (e.g., 3072 for text-embedding-3-large)

# 2) Run Qdrant in Docker
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant

# 3) (Optional) Firestore emulator in another terminal
# If you prefer this to Compose:
gcloud beta emulators firestore start --host-port=127.0.0.1:8081
export FIRESTORE_EMULATOR_HOST=127.0.0.1:8081

# 4) Run the API
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
