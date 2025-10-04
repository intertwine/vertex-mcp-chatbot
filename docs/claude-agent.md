# Claude Agent SDK + Vertex AI Guide

This guide walks through running the terminal REPL against Anthropic's Claude Agent SDK using Google Cloud Vertex AI as the transport. The runtime inside the SDK handles Model Context Protocol (MCP) tools, prompt templates, and resource access automatically, so most of the heavy lifting happens on Anthropic's side once an agent session is established. When you need Gemini instead, the CLI now offers an opt-in flag that switches back to the legacy Gemini REPL—see [Switching providers](#8-switching-providers) for details.

## 1. Enable Anthropic Claude on Vertex AI

1. Ensure the **Vertex AI API** is enabled for your project.
2. Request access to Anthropic Claude through the [Vertex Model Garden](https://console.cloud.google.com/vertex-ai/publishers/anthropic).
3. Confirm the target region exposes Claude Agent functionality (for example: `us-east5`, `us-central1`, `europe-west4`).

> **Tip:** If your project is not yet approved for Claude Agent SDK on Vertex, you can temporarily disable Vertex integration by setting `CLAUDE_VERTEX_ENABLED=false` and supplying an `ANTHROPIC_API_KEY`. The REPL will then talk directly to the public Anthropic API.

## 2. Authenticate using Application Default Credentials

The CLI relies on Application Default Credentials (ADC) to obtain OAuth access tokens for the Vertex endpoints. Run the following once on your workstation:

```bash
gcloud auth application-default login
```

Alternatively, export `GOOGLE_APPLICATION_CREDENTIALS` to point at a service account JSON key that has the `Vertex AI User` role.

## 3. Configure environment variables

Create a `.env` file (the project ships with `.env.example`) and populate the values that apply to your deployment:

```bash
GOOGLE_CLOUD_PROJECT="my-vertex-project"
GOOGLE_CLOUD_LOCATION="us-east5"
CLAUDE_MODEL="claude-4.5-sonnet"
# Optional overrides
CLAUDE_VERTEX_ENABLED="true"
CLAUDE_VERTEX_PROJECT="my-vertex-project"  # Use a different billing project if needed
CLAUDE_VERTEX_LOCATION="us-east5"         # Override the region the SDK should call
CLAUDE_API_VERSION="2025-02-19"           # Pin the Anthropic API version header
```

If you need to route through a proxy or private service, set `CLAUDE_VERTEX_BASE_URL` to the fully-qualified Anthropic publisher endpoint. Otherwise the helper builds the correct URL automatically:

```
https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/publishers/anthropic
```

## 4. Launch the Claude REPL

Install dependencies and start the chatbot:

```bash
uv sync
uv run main.py
```

You should see output similar to:

```
🚀 Starting Claude Agent REPL...
✅ Ready!
```

If ADC credentials are missing or the Vertex endpoint is unreachable, the CLI will emit a warning and fall back to using the public Anthropic API (when `ANTHROPIC_API_KEY` is set). Set `CLAUDE_VERTEX_ENABLED=false` to opt-out explicitly.

## 5. Managing MCP servers

The Claude Agent SDK automatically registers MCP servers defined in `mcp_config.json`. Place the file at the project root (or pass a custom `MCP_CONFIG` path) and the REPL will:

1. Parse the server list.
2. Spin up any stdio/CLI transports.
3. Register HTTP/SSE transports with the Claude runtime.

Use the `/help` command inside the REPL to discover chat commands. MCP-specific discovery commands are triggered automatically through Claude's reasoning (no bespoke slash commands are required).

## 6. Troubleshooting

| Symptom | Resolution |
| --- | --- |
| `Unable to load MCP configuration` | Ensure `mcp_config.json` exists and is valid JSON. Use `mcp_config.json.example` as a starting template. |
| `Google authentication libraries are unavailable` | Install dependencies via `uv sync` or `pip install -e .` to pull in `google-auth` and friends. |
| `Unable to refresh Google credentials` | Re-run `gcloud auth application-default login`, or export `GOOGLE_APPLICATION_CREDENTIALS` to a service account JSON. |
| Claude responses mention tool failures | Inspect the individual MCP server logs; the Claude Agent SDK streams tool errors directly from the server implementation. |

For deeper debugging enable verbose logging:

```bash
export PYTHONLOGLEVEL=DEBUG
uv run main.py
```

The logging hints emitted by `src/config.py` will reveal whether Vertex credentials were discovered and which endpoint the SDK is targeting.

## 7. Running tests

All automated tests are self-contained and use stub Claude SDK implementations. Run the suite locally with:

```bash
pytest
```

The tests do not hit real Vertex endpoints, so they succeed even without Google Cloud credentials.

## 8. Switching providers

The Claude Agent SDK is limited to Anthropic models at the moment—it cannot host Gemini on Vertex AI. If your workflow requires Gemini features, launch the CLI with:

```bash
uv run main.py --provider gemini [--model gemini-2.0-flash]
```

This command bypasses the Claude Agent SDK and resumes the original Gemini-focused REPL (including MCP integrations managed locally). Omit the `--provider` flag to restore the Claude agent experience.
