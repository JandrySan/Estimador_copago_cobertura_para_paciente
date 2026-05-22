from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path
import os

load_dotenv()

try:
    from .agent import chat_with_agent
except ImportError:
    # Soporta correr desde backend/ con uvicorn main:app
    from agent import chat_with_agent

app = FastAPI(
    title="MediCopago - Estimador de Copago",
    description="Agente IA para estimación de copagos y cobertura médica en Ecuador",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servir el frontend estático
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ── Modelos ──────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list = []   # Lista de {role, content} previos


class ChatResponse(BaseModel):
    reply: str
    history: list


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    index_path = frontend_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "MediCopago API está corriendo 🏥", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "MediCopago"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    # Construir historial de mensajes para Claude
    messages = request.history.copy()
    messages.append({"role": "user", "content": request.message})

    try:
        result = chat_with_agent(messages)

        # Serializar content (puede tener objetos Anthropic) a dicts simples
        clean_history = []
        for msg in result["messages"]:
            role = msg["role"]
            content = msg["content"]

            if isinstance(content, str):
                clean_history.append({"role": role, "content": content})
            elif isinstance(content, list):
                serialized = []
                for block in content:
                    if hasattr(block, "__dict__"):
                        serialized.append(block.__dict__)
                    elif isinstance(block, dict):
                        serialized.append(block)
                clean_history.append({"role": role, "content": serialized})

        return ChatResponse(reply=result["reply"], history=clean_history)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error del agente: {str(e)}")


@app.get("/pacientes-demo")
async def pacientes_demo():
    """Endpoint de ayuda para ver cédulas de prueba disponibles"""
    return {
        "cedulas_demo": [
            {"cedula": "1712345678", "nombre": "Carlos Mendoza", "plan": "Gold"},
            {"cedula": "1798765432", "nombre": "María Herrera", "plan": "Silver"},
            {"cedula": "1756789012", "nombre": "José Ramírez", "plan": "Basic"},
        ],
        "nota": "Usa estas cédulas para probar el agente"
    }