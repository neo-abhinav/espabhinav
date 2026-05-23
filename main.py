# =========================================================
# ABHINAV AI
# FINAL PRODUCTION BACKEND
# =========================================================

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

import httpx
import json
import os
import uvicorn

# =========================================================
# CONFIG
# =========================================================

OPENROUTER_API_KEY = os.environ["key"]

MODEL = "openrouter/free"

CHAT_FILE = "chat_history.json"

MAX_HISTORY = 20

# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are ABHINAV AI.

Your name is strictly ABHINAV AI.

Never say you are ChatGPT.
Never say you are OpenRouter.
Never mention models or providers.

If asked who you are, say:
"I am ABHINAV AI."

ABHINAV AI was created by Abhinav Kumar.

Important context:

- Abhinav Kumar is a Class 9 student at Oak Grove School.
- This ESP32 AI assistant project is being built for the Science Exhibition on 1st June during Founder Day.
- The audience includes DRM and Moradabad Division officials and visitors.
- The project demonstrates AI, embedded systems, voice interaction, cloud integration, and real-time streaming.

Hardware:
- ESP32
- INMP441 microphone
- MAX98357A amplifier
- SSD1306 OLED display

Behavior:
- concise replies
- conversational
- futuristic personality
- intelligent
- natural speaking
- professional tone
- avoid long paragraphs

VERY IMPORTANT:
- Always respond as if the user will HEAR the response through a speaker.
- Responses must sound natural when spoken aloud.
- Never use LaTeX.
- Never use markdown.
- Never use formatting symbols.
- Never use asterisks.
- Never use hashtags.
- Never use bullet formatting.
- Never use code block formatting.
- Never use bold or italic formatting.
- Never use slash-style math expressions.
- Never use visual formatting styles.
- Output must always be plain readable text only.
- Instead of saying "10 slash 2", say "10 divided by 2".
- Explain formulas naturally in words.
- Speak numbers naturally.
- Prioritize voice clarity over visual formatting.
- Sound futuristic and polished.

If current or recent information is required,
use web search automatically.
""".strip()

# =========================================================
# APP
# =========================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# CHAT STORAGE
# =========================================================

if not os.path.exists(CHAT_FILE):

    with open(CHAT_FILE, "w") as f:

        json.dump([], f)

# =========================================================
# LOAD CHAT
# =========================================================

def load_history():

    try:

        with open(CHAT_FILE, "r") as f:

            return json.load(f)

    except:

        return []

# =========================================================
# SAVE CHAT
# =========================================================

def save_history(history):

    with open(CHAT_FILE, "w") as f:

        json.dump(history, f, indent=2)

# =========================================================
# ADD MESSAGE
# =========================================================

def add_message(role, content):

    history = load_history()

    history.append({

        "role": role,

        "content": content
    })

    history = history[-MAX_HISTORY:]

    save_history(history)

# =========================================================
# CLEAR CHAT
# =========================================================

def clear_history():

    with open(CHAT_FILE, "w") as f:

        json.dump([], f)

# =========================================================
# ROOT
# =========================================================

@app.get("/")
async def root():

    return {

        "status": "running",

        "assistant": "ABHINAV AI",

        "model": MODEL
    }

# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
async def health():

    return {

        "ok": True
    }

# =========================================================
# HISTORY
# =========================================================

@app.get("/history")
async def history():

    return load_history()

# =========================================================
# CLEAR
# =========================================================

@app.get("/clear")
async def clear():

    clear_history()

    return {

        "status": "chat cleared"
    }

# =========================================================
# SEND JSON
# =========================================================

async def send_json(websocket, data):

    await websocket.send_text(
        json.dumps(data)
    )

# =========================================================
# BUILD MESSAGES
# =========================================================

def build_messages(user_text):

    history = load_history()

    messages = [

        {
            "role": "system",

            "content": SYSTEM_PROMPT
        }
    ]

    messages.extend(history)

    messages.append({

        "role": "user",

        "content": user_text
    })

    return messages

# =========================================================
# CHECK WEB SEARCH
# =========================================================

def needs_web_search(text):

    text = text.lower()

    keywords = [

        "latest",
        "today",
        "current",
        "news",
        "recent",
        "live",
        "weather",
        "score",
        "ipl",
        "cricket",
        "headline",
        "technology update",
        "trending"
    ]

    return any(
        word in text
        for word in keywords
    )

# =========================================================
# CLEAN RESPONSE
# =========================================================

def clean_response(text):

    replacements = {

        "**": "",
        "__": "",
        "###": "",
        "##": "",
        "#": "",
        "*": "",
        "`": ""
    }

    for old, new in replacements.items():

        text = text.replace(old, new)

    return text.strip()

# =========================================================
# EXTRACT TOKEN
# =========================================================

def extract_token(obj):

    try:

        choices = obj.get("choices", [])

        if not choices:
            return ""

        choice = choices[0]

        # DELTA FORMAT

        if "delta" in choice:

            delta = choice["delta"]

            return delta.get(
                "content",
                ""
            )

        # MESSAGE FORMAT

        if "message" in choice:

            return choice["message"].get(
                "content",
                ""
            )

        # TEXT FORMAT

        if "text" in choice:

            return choice["text"]

    except:

        pass

    return ""

# =========================================================
# AI STREAM
# =========================================================

async def stream_ai_response(
    user_text,
    websocket
):

    headers = {

        "Authorization":
        f"Bearer {OPENROUTER_API_KEY}",

        "Content-Type":
        "application/json",

        "HTTP-Referer":
        "https://espabhinav.onrender.com",

        "X-Title":
        "ABHINAV AI"
    }

    payload = {

        "model": MODEL,

        "messages": build_messages(
            user_text
        ),

        "stream": True
    }

    # =====================================================
    # WEB SEARCH
    # =====================================================

    if needs_web_search(user_text):

        payload["tools"] = [

            {
                "type": "openrouter:web_search"
            }
        ]

        print("WEB SEARCH ENABLED")

    print()
    print("================================")
    print("USER:", user_text)
    print("================================")
    print()

    full_text = ""

    async with httpx.AsyncClient(
        timeout=120
    ) as client:

        try:

            async with client.stream(

                "POST",

                "https://openrouter.ai/api/v1/chat/completions",

                headers=headers,

                json=payload

            ) as response:

                print(
                    "STATUS:",
                    response.status_code
                )

                # ERROR

                if response.status_code != 200:

                    error_text = await response.aread()

                    error_text = error_text.decode()

                    print(error_text)

                    await send_json(websocket, {

                        "type": "error",

                        "text": error_text
                    })

                    return

                # STREAMING

                await send_json(websocket, {

                    "type": "status",

                    "text": "streaming"
                })

                async for raw_line in response.aiter_lines():

                    if not raw_line:
                        continue

                    line = raw_line.strip()

                    # Ignore keepalive

                    if line.startswith(":"):
                        continue

                    if not line.startswith("data:"):
                        continue

                    data = line[5:].strip()

                    if data == "[DONE]":
                        break

                    try:

                        obj = json.loads(data)

                    except:

                        continue

                    token = extract_token(obj)

                    if token:

                        print(
                            token,
                            end="",
                            flush=True
                        )

                        full_text += token

                        await send_json(websocket, {

                            "type": "stream",

                            "token": token
                        })

        except Exception as e:

            print("STREAM ERROR:", e)

            await send_json(websocket, {

                "type": "error",

                "text": str(e)
            })

            return

    # =====================================================
    # CLEAN FINAL RESPONSE
    # =====================================================

    full_text = clean_response(full_text)

    print()
    print()
    print("FINAL:")
    print(full_text)

    # =====================================================
    # SAVE MEMORY
    # =====================================================

    add_message(
        "user",
        user_text
    )

    add_message(
        "assistant",
        full_text
    )

    # =====================================================
    # DONE
    # =====================================================

    await send_json(websocket, {

        "type": "done",

        "text": full_text
    })

# =========================================================
# WEBSOCKET
# =========================================================

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket
):

    await websocket.accept()

    print()
    print("================================")
    print("ESP32 CONNECTED")
    print("================================")
    print()

    await send_json(websocket, {

        "type": "ready",

        "assistant": "ABHINAV AI",

        "model": MODEL
    })

    try:

        while True:

            data = await websocket.receive_text()

            print()
            print("RECEIVED:")
            print(data)

            try:

                obj = json.loads(data)

            except:

                continue

            msg_type = obj.get("type")

            # =================================================
            # PROMPT
            # =================================================

            if msg_type == "prompt":

                user_text = obj.get(
                    "text",
                    ""
                )

                await send_json(websocket, {

                    "type": "status",

                    "text": "thinking"
                })

                await stream_ai_response(
                    user_text,
                    websocket
                )

            # =================================================
            # CLEAR CHAT
            # =================================================

            elif msg_type == "clear_chat":

                clear_history()

                await send_json(websocket, {

                    "type": "chat_cleared"
                })

                print("CHAT CLEARED")

            # =================================================
            # PING
            # =================================================

            elif msg_type == "ping":

                await send_json(websocket, {

                    "type": "pong"
                })

    except Exception as e:

        print()
        print("DISCONNECTED")
        print(e)

# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    uvicorn.run(

        "main:app",

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                5000
            )
        )
    )
