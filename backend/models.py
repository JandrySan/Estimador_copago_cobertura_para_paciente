from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    history: list = []


class ChatResponse(BaseModel):
    reply: str
    history: list


class Paciente(BaseModel):
    id: str
    nombre: str
    cedula: str
    poliza_id: str
    plan: str
    vigente: bool
    fecha_inicio: str
    fecha_fin: str


class Hospital(BaseModel):
    nombre: str
    ciudad: str
    direccion: str
    telefono: str
    costo_consulta_base: float
    especialidades: list[str]


class ResultadoCopago(BaseModel):
    cubierta: bool
    especialidad: Optional[str] = None
    plan: Optional[str] = None
    copago_usd: Optional[float] = None
    cobertura_porcentaje: Optional[int] = None
    hospitales_disponibles: Optional[list] = None
    hospital_mas_economico: Optional[dict] = None
    mensaje: Optional[str] = None