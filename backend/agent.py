import json
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Inicializar el cliente oficial de DeepSeek
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)
# Cargar datos mock
DATA_PATH = Path(__file__).parent.parent / "data" / "mock_data.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    MOCK_DATA = json.load(f)

SYSTEM_PROMPT = """Eres MediCopago, un asistente inteligente de estimación de copagos y cobertura médica para pacientes en Ecuador.

Tu objetivo es guiar al paciente en 3 pasos claros:
1. SÍNTOMA → Identificar qué especialidad médica necesita
2. PÓLIZA → Verificar su cobertura y calcular su copago exacto
3. HOSPITAL → Recomendar el hospital de la red más conveniente

REGLAS:
- Sé amable y empático. Habla en español ecuatoriano natural.
- Mapea síntomas a estas especialidades: medicina_general, cardiologia, neurologia, ortopedia, gastroenterologia, dermatologia, ginecologia, pediatria, oftalmologia, urologia, endocrinologia, psiquiatria
- SIEMPRE pide la cédula del paciente para consultar su póliza.
- Una vez que tengas la cédula, llama a get_patient_info.
- Con los datos y la especialidad, llama a calculate_copago.
- Si la especialidad NO está cubierta, díselo claramente.
- Nunca inventes datos.

Formato de respuesta final:
✅ Especialidad sugerida: [especialidad]
💊 Copago estimado: $[monto]
🏥 Hospitales recomendados: [lista]
📋 Cobertura de tu plan [nombre]: [porcentaje]%

Nota: esto es una estimación orientativa, no un diagnóstico médico."""


# ── Funciones de negocio ──────────────────────────────────────────────────────
def get_patient_info(cedula: str) -> dict:
    from .notion_client import get_patient_by_cedula
    return get_patient_by_cedula(cedula)


def calculate_copago(plan: str, especialidad: str) -> dict:
    if plan not in MOCK_DATA["planes"]:
        return {"error": "Plan no reconocido"}
    plan_data = MOCK_DATA["planes"][plan]
    if especialidad not in plan_data["especialidades_cubiertas"]:
        return {
            "cubierta": False,
            "mensaje": f"La especialidad '{especialidad}' no está cubierta en el plan {plan}.",
            "especialidades_disponibles": plan_data["especialidades_cubiertas"]
        }
    copago = plan_data["copagos_por_especialidad"].get(especialidad, 0)
    hospitales_disponibles = []
    for h_nombre in plan_data["hospitales_red"]:
        h = MOCK_DATA["hospitales"].get(h_nombre, {})
        if especialidad in h.get("especialidades", []):
            hospitales_disponibles.append({
                "nombre": h_nombre,
                "direccion": h.get("direccion", ""),
                "telefono": h.get("telefono", ""),
                "costo_base": h.get("costo_consulta_base", 0),
                "ciudad": h.get("ciudad", "")
            })
    hospitales_disponibles.sort(key=lambda x: x["costo_base"])
    return {
        "cubierta": True,
        "especialidad": especialidad,
        "plan": plan,
        "copago_usd": copago,
        "cobertura_porcentaje": plan_data["cobertura_porcentaje"],
        "hospitales_disponibles": hospitales_disponibles,
        "hospital_mas_economico": hospitales_disponibles[0] if hospitales_disponibles else None
    }


TOOLS_MAP = {
    "get_patient_info": get_patient_info,
    "calculate_copago": calculate_copago,
}

# Declaración de Herramientas (Tools) en formato OpenAI / DeepSeek
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_patient_info",
            "description": "Obtiene información del paciente y su póliza por cédula",
            "parameters": {
                "type": "object",
                "properties": {
                    "cedula": {"type": "string", "description": "Cédula ecuatoriana de 10 dígitos"}
                },
                "required": ["cedula"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_copago",
            "description": "Calcula el copago para una especialidad según el plan del paciente",
            "parameters": {
                "type": "object",
                "properties": {
                    "plan": {"type": "string", "description": "Gold, Silver o Basic"},
                    "especialidad": {"type": "string", "description": "Especialidad médica"}
                },
                "required": ["plan", "especialidad"]
            }
        }
    }
]


# ── Chat principal con Loop de Function Calling ───────────────────────────────
def chat_with_agent(messages: list) -> dict:
    # Preparar el historial en formato estándar
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    for msg in messages:
        # Evitar meter bloques complejos, solo texto limpio
        if isinstance(msg["content"], str) and msg["content"].strip():
            api_messages.append({"role": msg["role"], "content": msg["content"]})

    max_iter = 5
    for _ in range(max_iter):
        
        # Cambia el modelo viejo por este nuevo:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=api_messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3
        )
        
        response_message = response.choices[0].message
        
        # Guardar la respuesta del modelo en el hilo de la conversación de la API
        # DeepSeek requiere adjuntar el mensaje con tool_calls si decide usarlos
        api_messages.append(response_message)

        # Verificar si el modelo solicitó ejecutar alguna función
        tool_calls = response_message.tool_calls
        if not tool_calls:
            break

        # Procesar cada una de las funciones solicitadas
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            function_to_call = TOOLS_MAP.get(function_name)
            if function_to_call:
                function_response = function_to_call(**function_args)
            else:
                function_response = {"error": f"Tool {function_name} no encontrada"}
            
            # Almacenar el resultado de la función regresándosela a la API
            api_messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(function_response, ensure_ascii=False),
            })

    # El resultado final después del ciclo
    final_reply = api_messages[-1]["content"] if isinstance(api_messages[-1], dict) else api_messages[-1].content

    updated_messages = messages.copy()
    updated_messages.append({"role": "assistant", "content": final_reply})
    
    return {"reply": final_reply, "messages": updated_messages}