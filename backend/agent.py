import json
import os
from anthropic import Anthropic
from pathlib import Path

# Cargar datos mock
DATA_PATH = Path(__file__).parent.parent / "data" / "mock_data.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    MOCK_DATA = json.load(f)

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """Eres MediCopago, un asistente inteligente de estimación de copagos y cobertura médica para pacientes en Ecuador.

Tu objetivo es guiar al paciente en 3 pasos claros:
1. SÍNTOMA → Identificar qué especialidad médica necesita
2. PÓLIZA → Verificar su cobertura y calcular su copago exacto
3. HOSPITAL → Recomendar el hospital de la red más conveniente

REGLAS IMPORTANTES:
- Sé amable, claro y empático. Habla en español ecuatoriano natural.
- Cuando el paciente describa un síntoma, mapéalo a una de estas especialidades:
  medicina_general, cardiologia, neurologia, ortopedia, gastroenterologia, 
  dermatologia, ginecologia, pediatria, oftalmologia, urologia, endocrinologia, psiquiatria
- SIEMPRE solicita la cédula del paciente para consultar su póliza (si no la ha dado).
- Una vez que tengas la cédula, usa la función get_patient_info para obtener sus datos.
- Con los datos de la póliza y la especialidad, calcula el copago con calculate_copago.
- Presenta los resultados de forma clara: especialidad sugerida, copago estimado, hospitales recomendados.
- Si la especialidad NO está cubierta en su plan, díselo claramente y sugiere alternativas.
- Nunca inventes datos. Si no tienes info, dilo honestamente.
- Al final, ofrece un resumen que el paciente pueda guardar.

Formato de respuesta para el estimado final:
✅ Especialidad sugerida: [especialidad]
💊 Copago estimado: $[monto]
🏥 Hospitales recomendados en tu red: [lista]
📋 Cobertura de tu plan [nombre]: [porcentaje]%

Recuerda: eres una estimación orientativa, no un diagnóstico médico.
"""

TOOLS = [
    {
        "name": "get_patient_info",
        "description": "Obtiene la información del paciente y su póliza a partir de su número de cédula",
        "input_schema": {
            "type": "object",
            "properties": {
                "cedula": {
                    "type": "string",
                    "description": "Número de cédula ecuatoriana del paciente (10 dígitos)"
                }
            },
            "required": ["cedula"]
        }
    },
    {
        "name": "calculate_copago",
        "description": "Calcula el copago para una especialidad médica dado el plan del paciente y devuelve hospitales disponibles en la red",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan": {
                    "type": "string",
                    "description": "Plan del seguro del paciente (Gold, Silver, Basic)"
                },
                "especialidad": {
                    "type": "string",
                    "description": "Especialidad médica requerida"
                }
            },
            "required": ["plan", "especialidad"]
        }
    }
]


def get_patient_info(cedula: str) -> dict:
    """Busca el paciente via Notion (o mock si Notion no está configurado)"""
    from notion_client import get_patient_by_cedula
    return get_patient_by_cedula(cedula)


def calculate_copago(plan: str, especialidad: str) -> dict:
    """Calcula el copago y devuelve hospitales disponibles para la especialidad"""
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
    
    # Filtrar hospitales de la red que atiendan esa especialidad
    hospitales_disponibles = []
    for hospital_nombre in plan_data["hospitales_red"]:
        hospital = MOCK_DATA["hospitales"].get(hospital_nombre, {})
        if especialidad in hospital.get("especialidades", []):
            hospitales_disponibles.append({
                "nombre": hospital_nombre,
                "direccion": hospital.get("direccion", ""),
                "telefono": hospital.get("telefono", ""),
                "costo_base": hospital.get("costo_consulta_base", 0),
                "ciudad": hospital.get("ciudad", "")
            })

    # Ordenar por costo base (más económico primero)
    hospitales_disponibles.sort(key=lambda h: h["costo_base"])

    return {
        "cubierta": True,
        "especialidad": especialidad,
        "plan": plan,
        "copago_usd": copago,
        "cobertura_porcentaje": plan_data["cobertura_porcentaje"],
        "hospitales_disponibles": hospitales_disponibles,
        "hospital_mas_economico": hospitales_disponibles[0] if hospitales_disponibles else None
    }


def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Ejecuta la función correspondiente al tool call del agente"""
    if tool_name == "get_patient_info":
        result = get_patient_info(tool_input["cedula"])
    elif tool_name == "calculate_copago":
        result = calculate_copago(tool_input["plan"], tool_input["especialidad"])
    else:
        result = {"error": f"Tool '{tool_name}' no reconocida"}
    
    return json.dumps(result, ensure_ascii=False)


def chat_with_agent(messages: list) -> dict:
    """
    Envía mensajes al agente y maneja el ciclo de tool_use automáticamente.
    Retorna el texto final de respuesta y los mensajes actualizados.
    """
    current_messages = messages.copy()
    
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=current_messages
        )

        # Si terminó normalmente, extraer texto y retornar
        if response.stop_reason == "end_turn":
            text = " ".join(
                block.text for block in response.content
                if hasattr(block, "text")
            )
            current_messages.append({
                "role": "assistant",
                "content": response.content
            })
            return {"reply": text, "messages": current_messages}

        # Si hay tool_use, procesarlos
        if response.stop_reason == "tool_use":
            current_messages.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = process_tool_call(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            current_messages.append({
                "role": "user",
                "content": tool_results
            })
            # Continúa el loop para que el agente procese los resultados
            continue

        # Si llega aquí por otra razón, romper
        break

    return {"reply": "Lo siento, ocurrió un error inesperado.", "messages": current_messages}