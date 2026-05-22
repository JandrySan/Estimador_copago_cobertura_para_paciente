# 🏥 MediCopago — Estimador Agéntico de Copago y Cobertura

> Reto 3 del hackIAthon Viamatica 2025  
> Agente conversacional que ayuda al paciente a entender su beneficio antes de atenderse.

## 🎯 ¿Qué hace?

El paciente describe su síntoma. El agente:
1. **Identifica la especialidad médica** necesaria
2. **Consulta la póliza** del paciente (vía Notion o mock)
3. **Calcula el copago exacto** según el plan del seguro
4. **Recomienda el hospital de la red** más conveniente económicamente

## 🏗️ Arquitectura

```
Frontend (HTML/JS)
       ↕ REST
Backend (FastAPI)
       ↕ Anthropic API (Claude)
       ↕ Notion API / Mock JSON
```

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|-----------|-----------|
| Backend | Python + FastAPI |
| IA | Claude claude-sonnet-4-20250514 (Anthropic) |
| Base de datos | Notion API / JSON mock |
| Frontend | HTML + CSS + JS vanilla |
| Deploy | Railway / Render |

## 🚀 Instalación local

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/copago-agent.git
cd copago-agent
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
# Edita .env con tu ANTHROPIC_API_KEY
```

### 4. Correr el servidor
```bash
# Desde la carpeta raíz del proyecto
uvicorn backend.main:app --reload --port 8000

# O desde el directorio backend
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Abrir en el navegador
```
http://localhost:8000
```

## 🌐 Deploy en Railway (recomendado)

1. Conecta tu repositorio en [railway.app](https://railway.app)
2. Configura las variables de entorno en el panel
3. Railway detecta automáticamente el `Procfile`
4. ¡Listo! Tu URL pública estará disponible en minutos

## 📋 Cédulas de prueba (demo)

| Cédula | Nombre | Plan |
|--------|--------|------|
| 1712345678 | Carlos Mendoza | Gold (90% cobertura) |
| 1798765432 | María Herrera | Silver (75% cobertura) |
| 1756789012 | José Ramírez | Basic (60% cobertura) |

## 🔌 Integración con Notion

Para usar Notion en lugar del mock:

1. Crea una base de datos en Notion con las columnas:
   - `cedula` (text), `nombre` (text), `plan` (select), `vigente` (checkbox)
2. Agrega tu `NOTION_API_KEY` y `NOTION_DATABASE_ID` al `.env`
3. El agente consultará Notion automáticamente

## 📡 API Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/` | Frontend web |
| GET | `/health` | Health check |
| POST | `/chat` | Enviar mensaje al agente |
| GET | `/pacientes-demo` | Ver cédulas de prueba |

### Ejemplo de llamada a `/chat`
```json
POST /chat
{
  "message": "Tengo dolor en el pecho",
  "history": []
}
```

## 👥 Equipo

- José Gabriel Álava Barcia
- Jandry Paúl Sánchez Murillo
- Joel Alejandro Barrera Vaca

## 📄 Licencia

MIT