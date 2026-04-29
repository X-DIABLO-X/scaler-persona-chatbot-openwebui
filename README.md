# Scaler Persona Chatbot

A persona-based AI chatbot built with **Open WebUI** as the frontend and a custom **OpenAI-compatible Groq proxy** as the backend. The app exposes three selectable personas inside Open WebUI:

- `Anshuman Singh`
- `Abhimanyu Saxena`
- `Kshitij Mishra`

Instead of letting users pick arbitrary models, Open WebUI only sees these three persona-specific models. Switching the selected model changes the system prompt used for the conversation.

## Stack

- Open WebUI for chat UI
- FastAPI persona proxy for persona routing
- Groq `meta-llama/llama-4-scout-17b-16e-instruct` for main responses
- Groq `meta-llama/llama-prompt-guard-2-86m` for prompt-injection screening
- Docker Compose for local setup

## Features

- Persona switcher through the Open WebUI model picker
- Dedicated system prompt for each persona
- Few-shot prompting embedded in each persona prompt
- Internal chain-of-thought instruction with no reasoning leakage
- Prompt-guard pass before the main model call
- User-friendly error handling from the proxy
- Mobile-friendly UI through Open WebUI
- Clean environment-variable based secret management

## Repo Structure

```text
.
|-- docker-compose.yml
|-- .env.example
|-- prompts.md
|-- reflection.md
`-- services/
    `-- persona-proxy/
        |-- Dockerfile
        |-- requirements.txt
        `-- app/
            |-- main.py
            `-- prompts.py
```

## Local Setup

1. Copy `.env.example` to `.env`.
2. Fill in `GROQ_API_KEY` with your real Groq key.
3. Set a long random value for `OPENWEBUI_SECRET_KEY`.
4. Start the app:

```bash
docker compose up --build
```

5. Open [http://localhost:3000](http://localhost:3000)
6. Create the first Open WebUI admin account.
7. In the top model selector, choose one of:
   - `anshuman-singh`
   - `abhimanyu-saxena`
   - `kshitij-mishra`

## How Persona Selection Works

The FastAPI proxy implements the OpenAI-compatible `/v1/models` and `/v1/chat/completions` endpoints. It advertises only three models, each mapped to one persona prompt. Open WebUI therefore treats persona choice as model choice, which keeps the UI simple and assignment-aligned.

## Prompt Guard Flow

Every incoming conversation is first checked with Groq's `meta-llama/llama-prompt-guard-2-86m`.

- If the request looks unsafe or tries to override instructions, the proxy returns a safe refusal.
- If it passes, the proxy prepends the selected persona system prompt and forwards the request to `meta-llama/llama-4-scout-17b-16e-instruct`.

## Deployment

### Recommended: Render

This repo includes a [render.yaml](/D:/HARSHIT/chatbot/render.yaml) Blueprint for a two-service Render deployment:

- `scaler-persona-proxy`: private FastAPI service that talks to Groq
- `scaler-persona-openwebui`: public Open WebUI service with a persistent disk

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/X-DIABLO-X/scaler-persona-chatbot-openwebui)

#### Deploy on Render

1. Open the repo in Render using Blueprint deploy.
2. Let Render create both services from `render.yaml`.
3. Provide `GROQ_API_KEY` when Render prompts for it.
4. Keep the generated values for `PERSONA_PROXY_API_KEY` and `WEBUI_SECRET_KEY`.
5. Wait for both services to finish building.
6. Open the `scaler-persona-openwebui` public URL.
7. Create the first admin account in Open WebUI.

#### Important Render note

Open WebUI needs persistent storage for its SQLite database and uploads. Render persistent disks are only available on paid instances, so the Open WebUI service uses the `starter` plan with a 1 GB disk mounted at `/app/backend/data`.

### Why not Vercel for the full stack?

Vercel does not support deploying Docker images or long-running Open WebUI containers directly, so Render is the correct deployment target for this architecture.

## Environment Variables

See [.env.example](/D:/HARSHIT/chatbot/.env.example) for the full list.

- `GROQ_API_KEY`: Groq API key
- `GROQ_MAIN_MODEL`: Main LLM
- `GROQ_GUARD_MODEL`: Prompt-guard classifier
- `OPENWEBUI_SECRET_KEY`: Open WebUI session secret
- `PERSONA_PROXY_API_KEY`: Internal key Open WebUI uses to talk to the proxy

## Submission Checklist

- Public GitHub repo
- Live deployed URL
- `README.md`
- `prompts.md`
- `reflection.md`
- `.env.example`
- All three personas working
- Error handling in place
- Mobile-responsive frontend

## Screenshots

Add screenshots after local run or deployment:

- Persona selector in Open WebUI
- Chat with Anshuman Singh
- Chat with Abhimanyu Saxena
- Chat with Kshitij Mishra
