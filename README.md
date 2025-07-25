# Expel Vertex AI Chatbot

An interactive command-line chatbot powered by Google's Gemini LLM via Vertex AI. This application provides a rich terminal interface for conversing with Gemini models, complete with markdown rendering, conversation history, and various utility commands.

## Features

- 🤖 **Interactive Chat Interface**: Clean, intuitive terminal UI with rich formatting
- 📝 **Markdown Support**: Responses are rendered with proper markdown formatting
- 💾 **Persistent History**: Conversation history saved between sessions
- 🎨 **Rich Terminal UI**: Colorful, well-formatted output using Rich library
- 🔧 **Multiple Models**: Support for different Gemini models (flash, pro)
- 📋 **Command System**: Built-in commands for managing your chat session

## Prerequisites

- Python 3.9 or higher
- [uv](https://docs.astral.sh/uv/) package manager installed
- Access to Google Cloud Vertex AI with Gemini models
- Google Cloud CLI (`gcloud`) installed and authenticated

## Installation

1. Clone this repository:
```bash
cd /Users/bryanyoung/experiments/gemini-local
```

2. Install dependencies with uv (creates virtual environment automatically):
```bash
uv sync
```

3. Authenticate with Google Cloud (Application Default Credentials):
```bash
gcloud auth application-default login
```

4. (Optional) Set up environment variables:
```bash
cp .env.example .env
```

You can optionally edit `.env` to override default project settings:
```bash
# GOOGLE_CLOUD_PROJECT='your-project-id'
# GOOGLE_CLOUD_LOCATION='us-central1'
```

## Usage

### Basic Usage

Start the chatbot with the default model (gemini-2.5-flash):
```bash
uv run main.py
```

### Using Different Models

Start with a different model:
```bash
uv run main.py --model gemini-2.5-pro
```

### Available Commands

While chatting, you can use these commands:

- `/help` - Show available commands and tips
- `/clear` - Clear the chat history and start fresh
- `/history` - Display the full conversation history
- `/model` - Show which Gemini model you're using
- `/prune` - Clear local command history (with confirmation)
- `/quit` or `/exit` - Exit the chatbot

### Example Session

```
🚀 Initializing Gemini Chatbot...
✅ Vertex AI initialized successfully
✅ Model 'gemini-2.5-flash' ready
✅ Chatbot ready!
Type '/help' for commands or '/quit' to exit

You> What is machine learning?

╭─ Gemini ─────────────────────────────────────────────╮
│                                                      │
│  Machine learning (ML) is a type of artificial       │
│  intelligence (AI) that allows software              │
│  applications to become more accurate in             │
│  predicting outcomes without being explicitly        │
│  programmed to do so...                              │
│                                                      │
╰──────────────────────────────────────────────────────╯

You> /model
Current model: gemini-2.5-flash

You> /quit

👋 Goodbye!
```

## Project Structure

```
gemini-local/
├── main.py              # Entry point
├── pyproject.toml       # Python project configuration and dependencies
├── .env.example        # Example environment file
├── .gitignore          # Git ignore rules
├── README.md           # This file
└── src/
    ├── __init__.py     # Package init
    ├── config.py       # Configuration management
    ├── gemini_client.py # Gemini/Vertex AI client wrapper
    └── chatbot.py      # Interactive chatbot implementation
```

## Configuration

The application uses the following configuration (can be modified in `src/config.py`):

- **Project ID**: `expel-engineering-prod`
- **Location**: `us-central1`
- **Default Model**: `gemini-2.5-flash`
- **Max History Length**: 10 conversation turns

## Troubleshooting

### "Failed to initialize Google Gen AI client"

Make sure you've:
1. Authenticated with Google Cloud: `gcloud auth application-default login`
2. Your account has access to the specified Google Cloud project
3. Vertex AI API is enabled in your project
4. Your account has the necessary permissions (Vertex AI User role)

### "Authentication Error"

Check that:
1. You've run `gcloud auth application-default login` successfully
2. The project ID in the config matches your GCP project
3. Gemini models are available in your specified region
4. Your Google Cloud account has billing enabled

### Connection Issues

Ensure:
1. You have an active internet connection
2. No firewall/proxy blocking access to Google Cloud
3. Your service account is active and not expired

## Development

To extend or modify the chatbot:

1. The `GeminiClient` class in `src/gemini_client.py` handles all Vertex AI interactions
2. The `GeminiChatbot` class in `src/chatbot.py` manages the UI and user interaction
3. Add new commands by extending the `process_command` method
4. Modify model parameters in the `Config` class

## Security Notes

- Never commit your `.env` file or service account credentials
- The `.gitignore` file is configured to exclude sensitive files
- Store your service account JSON securely
- Consider using Google Cloud Secret Manager for production deployments

## License

This project is for internal Expel use. Please follow company guidelines for code usage and distribution.
