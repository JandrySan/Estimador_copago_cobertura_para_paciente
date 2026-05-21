import os
import json
from pathlib import Path

# Intenta importar el SDK de Notion; si no está, usa mock
try:
    from notion_client import Client
    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False

NOTION_API_KEY = os.getenv("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# Datos mock como fallback
DATA_PATH = Path(__file__).parent.parent / "data" / "mock_data.json"
with open(DATA_PATH, "r", encoding="utf-8") as f:
    MOCK_DATA = json.load(f)


def _usar_notion() -> bool:
    """Devuelve True solo si Notion está configurado y disponible"""
    return NOTION_AVAILABLE and bool(NOTION_API_KEY) and bool(NOTION_DATABASE_ID)


def get_patient_by_cedula(cedula: str) -> dict:
    """
    Busca un paciente por cédula.
    Primero intenta Notion; si no está configurado, usa el mock.
    """
    if _usar_notion():
        return _get_from_notion(cedula)
    return _get_from_mock(cedula)


def _get_from_notion(cedula: str) -> dict:
    """Consulta la base de datos de Notion"""
    try:
        notion = Client(auth=NOTION_API_KEY)
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "cedula",
                "rich_text": {"equals": cedula}
            }
        )

        if not response["results"]:
            return {"encontrado": False, "mensaje": "No se encontró ningún paciente con esa cédula."}

        page = response["results"][0]
        props = page["properties"]

        def get_text(prop):
            try:
                return props[prop]["rich_text"][0]["plain_text"]
            except (KeyError, IndexError):
                return ""

        def get_select(prop):
            try:
                return props[prop]["select"]["name"]
            except (KeyError, TypeError):
                return ""

        def get_checkbox(prop):
            try:
                return props[prop]["checkbox"]
            except KeyError:
                return False

        plan = get_select("plan")
        plan_info = MOCK_DATA["planes"].get(plan, {})

        return {
            "encontrado": True,
            "nombre": get_text("nombre"),
            "plan": plan,
            "poliza_id": get_text("poliza_id"),
            "vigente": get_checkbox("vigente"),
            "cobertura_porcentaje": plan_info.get("cobertura_porcentaje", 0),
            "deducible_anual": plan_info.get("deducible_anual", 0),
            "tope_anual": plan_info.get("tope_anual", 0),
            "especialidades_cubiertas": plan_info.get("especialidades_cubiertas", []),
            "hospitales_red": plan_info.get("hospitales_red", []),
            "fuente": "notion"
        }

    except Exception as e:
        # Si Notion falla, cae al mock
        print(f"[notion_client] Error consultando Notion: {e}. Usando mock.")
        return _get_from_mock(cedula)


def _get_from_mock(cedula: str) -> dict:
    """Busca el paciente en los datos mock locales"""
    for paciente in MOCK_DATA["pacientes"]:
        if paciente["cedula"] == cedula:
            plan_info = MOCK_DATA["planes"][paciente["plan"]]
            return {
                "encontrado": True,
                "nombre": paciente["nombre"],
                "plan": paciente["plan"],
                "poliza_id": paciente["poliza_id"],
                "vigente": paciente["vigente"],
                "cobertura_porcentaje": plan_info["cobertura_porcentaje"],
                "deducible_anual": plan_info["deducible_anual"],
                "tope_anual": plan_info["tope_anual"],
                "especialidades_cubiertas": plan_info["especialidades_cubiertas"],
                "hospitales_red": plan_info["hospitales_red"],
                "fuente": "mock"
            }
    return {"encontrado": False, "mensaje": "No se encontró ningún paciente con esa cédula."}