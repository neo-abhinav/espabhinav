# =========================================================
# ABHINAV AI
# FULL RENDER-READY BACKEND
# FastAPI + WebSocket + OpenRouter + Chat Memory
# =========================================================

# =========================================================
# INSTALL
# =========================================================
#
# pip install fastapi uvicorn httpx
#
# =========================================================
# RUN LOCAL
# =========================================================
#
# uvicorn main:app --host 0.0.0.0 --port 5000
#
# =========================================================
# RENDER START COMMAND
# =========================================================
#
# uvicorn main:app --host 0.0.0.0 --port $PORT
#
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

MODEL = "openrouter/owl-alpha"

CHAT_FILE = "chat_history.json"

MAX_HISTORY = 20

# =========================================================
# SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
You are ABHINAV AI.

Your name is strictly ABHINAV AI.

Never say you are OWL.
Never say you are ChatGPT.
Never mention OpenRouter.
Never mention your underlying model.

If asked who you are, say:
"I am ABHINAV AI."

ABHINAV AI was created by Abhinav Kumar.

Important context:

- Abhinav Kumar is a Class 9 student at Oak Grove School.
- This ESP32 AI assistant project is being built for the Science Exhibition on 1st June during Founder Day.
- The exhibition audience includes DRM / Moradabad Division officials and visitors.
- The assistant should sound futuristic, intelligent, polished, and impressive.
- The project demonstrates AI, embedded systems, voice interaction, and real-time streaming.

Hardware used:
- ESP32
- INMP441 microphone
- MAX98357A amplifier
- SSD1306 OLED display

Behavior:
- concise replies
- conversational
- natural speaking
- intelligent
- futuristic personality
- avoid markdown
- avoid long paragraphs
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
# CHAT FILE
# =========================================================

if not os.path.exists(CHAT_FILE):

    with open(CHAT_FILE, "w") as f:

        json.dump([], f)

# =========================================================
# CHAT FUNCTIONS
# =========================================================

def load_history():

    try:

        with open(CHAT_FILE, "r") as f:

            return json.load(f)

    except:

        return []

# =========================================================

def save_history(history):

    with open(CHAT_FILE, "w") as f:

        json.dump(history, f, indent=2)

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
# EXTRACT TOKEN
# =========================================================

def extract_token(obj):

    try:

        choices = obj.get("choices", [])

        if not choices:
            return ""

        choice = choices[0]

        # OpenAI style

        if "delta" in choice:

            delta = choice["delta"]

            return delta.get(
                "content",
                ""
            )

        # Message style

        if "message" in choice:

            return choice["message"].get(
                "content",
                ""
            )

        # Text style

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

                # =================================
                # ERROR
                # =================================

                if response.status_code != 200:

                    error_text = await response.aread()

                    error_text = error_text.decode()

                    print(error_text)

                    await send_json(websocket, {

                        "type": "error",

                        "text": error_text
                    })

                    return

                # =================================
                # STREAMING
                # =================================

                await send_json(websocket, {

                    "type": "status",

                    "text": "streaming"
                })

                async for raw_line in response.aiter_lines():

                    if not raw_line:
                        continue

                    line = raw_line.strip()

                    print("RAW:", line)

                    # Ignore comments

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

    print()
    print()
    print("FINAL:")
    print(full_text)

    # =====================================
    # SAVE MEMORY
    # =====================================

    add_message(
        "user",
        user_text
    )

    add_message(
        "assistant",
        full_text
    )

    # =====================================
    # DONE
    # =====================================

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

            # =================================
            # PROMPT
            # =================================

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

            # =================================
            # CLEAR CHAT
            # =================================

            elif msg_type == "clear_chat":

                clear_history()

                await send_json(websocket, {

                    "type": "chat_cleared"
                })

            # =================================
            # PING
            # =================================

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
