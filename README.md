# Hackathon Submission: Intelligent Web-Enabled Chat Agent

This repository contains the code for a Microsoft Hackathon entry: a .NET 8.0 conversational AI agent built with the Microsoft Agents SDK, Azure OpenAI (GPT-4o-mini), and a custom web search plugin. It demonstrates how to extend a Bot Framework Agent with external knowledge access and structured event logging for analytics and visualization.

## Key Innovations
- **Hybrid QA & Web Search**: Combines chat-based Q&A with an on-demand Bing Search plugin to fetch live data.
- **Structured NDJSON Logging**: Captures every user message, tool invocation/result, and agent reply as line-delimited JSON events for downstream analysis.
- **Minimalist Extensibility**: Clean separation of agent core, tool plugins, and logging utility makes it straightforward to add new tools or storage backends.

## Architecture Overview
```
┌──────────────┐    Incoming /api/messages    ┌───────────────┐
│ Bot Framework│ ───────────────────────────> │ HackathonAgent│
└──────────────┘                            └───────────────┘
        │                                            │
        │                                    ┌───────┴───────┐
        │ User Text                           │ Chat Completion│
        └───────────────────────┐            └───────┬───────┘
                                ▼                    │
                       ┌────────────────┐             ▼
                       │ OnMessageAsync │ ────► HTTP / AzureOpenAI
                       └────────────────┘             ▲
                                │                    │
               /search command  │            ChatResponse.Text
              invokes plugin    │
                                ▼
                      ┌──────────────────┐
                      │ WebSearchPlugin  │
                      └──────────────────┘
                                │
                          HTTP Bing Search API
                                │
                                ▼
                       JSON search results

  All steps emit events to `ConversationLogger` (conversation.jsonl) as:
    • UserMessage
    • ToolInvocation / ToolResult
    • BotMessage
```

## Component Breakdown

### HackathonAgent (dotnet/HackathonAgent.cs)
- Derives from `AgentApplication`.
- Handles `/search <query>` command: forwards to `WebSearchPlugin` and returns raw JSON.
- Streams plain chat completions via AzureOpenAI client when no search command.
- Emits log events via `ConversationLogger.LogEvent(…)`.

### WebSearchPlugin (dotnet/WebSearchPlugin.cs)
- Lightweight `HttpClient` wrapper over Bing Search REST API.
- Configured via `AIServices:BingSearch` in `appsettings.json` or user secrets.

### ConversationLogger (dotnet/ConversationLogger.cs)
- Static helper writing line-delimited JSON (NDJSON) to `conversation.jsonl` by default.
- Events include UTC timestamp, conversation ID, event type, and payload fields.

## Configuration & Deployment
- **.NET 8.0 SDK** project; config in `appsettings.json` under `AIServices` for BingSearch and AzureOpenAI.
- Override log path: `LOG_FILE_PATH=./mylogs.jsonl` environment variable.
- Compatible with Bot Framework Emulator and Microsoft Teams Test Tool.

## Debugging & Visualization
The submission includes a standalone Conversation Visualizer that parses the NDJSON log (`conversation.jsonl`) and provides two interactive diagnostic views:

- **Knowledge Graph View**: Renders each logged event (user message, tool invocation/result, bot reply) as a node, with edges illustrating conversational flow and contextual relationships.
- **Timeline View**: Displays events in chronological order along a time axis, with filtering options by event type and conversation ID.

Point the visualizer at any `conversation.jsonl` log file to explore conversation trajectories, tool usage patterns, and performance metrics. Live-reload support enables real-time monitoring during local development.

## Future Enhancements
- Enable LLM-driven function calls for tool selection instead of manual `/search` prefixes.
- Format responses with Adaptive Cards for richer UI.
- Persist conversation logs to Azure Blob Storage or Cosmos DB for real-time dashboards.
- Add more plugins (e.g., knowledge base lookup, translation, summarization).

---
_Built with Microsoft Agents SDK & Azure OpenAI during the 2025 hackathon._