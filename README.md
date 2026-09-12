# Vygo Backend — Motor de IA y Optimización de Rutas Multiapp
### HackMTY 2026 · Reto Infosys *"The Courier"*

Backend analítico y copiloto de decisión en tiempo real para repartidores de plataformas de entrega múltiple (Uber Eats, Rappi, DiDi Food) en la Zona Metropolitana de Monterrey, Nuevo León.

El sistema resuelve el **problema dual del meal delivery**: en lugar de optimizar desde la plataforma asignando pedidos a una flota, optimiza desde la perspectiva del trabajador independiente que decide qué ofertas aceptar y cómo acoplarlas a su ruta activa para maximizar su tasa de ganancia horaria ($\rho$, MXN/h) y eliminar kilómetros muertos.

---

## 🚀 Características Principales

1. **Evaluación de Decisión Stateless en Tiempo Real (`POST /decidir`)**:
   - Responde en **$< 10$ ms** en CPU (objetivo de contrato: $< 150$ ms).
   - Sin dependencias de base de datos ni Redis en el camino crítico.
   - Reporta los **tres números de explicabilidad**:
     - `tasa_marginal_mxn_h`: Lo que la oferta paga por hora incremental.
     - `rho_actual_mxn_h`: El ritmo promedio de ganancia del repartidor hoy.
     - `ajuste_aprendido_mxn_h`: Valor posicional aprendido $h^*(S')$ (densidad de zona destino, surge y riesgo).

2. **Ruteador Exacto por Permutaciones Restringidas / Held-Karp (`app/core/router.py`)**:
   - Para $N \le 6$ paradas concurrentes evalúa de forma exacta las permutaciones válidas (e.g. 90 secuencias para 3 pedidos).
   - Garantiza precedencia ($\text{recolección}_i < \text{entrega}_i$), capacidad de mochila ($\le 3$ pedidos) y frescura de producto ($\theta_{\text{frescura}}$).
   - Produce geometría GeoJSON estándar `[lon, lat]` lista para MapLibre / Leaflet.

3. **Políticas de Decisión Jerárquicas (`app/core/policies.py`)**:
   - `B1_simple`: Baseline ingenuo sin acoplamiento multiapp (*"Sin VYGO"*).
   - `B2_umbral`: Regla analítica formal que acepta si $\text{tasa\_marginal} \ge \rho_{\text{actual}}$ (*"VYGO regla"*).
   - `agente_ppo`: Política inteligente con valor posicional hacia zonas de alta demanda (San Pedro, Centro, Tec) y anticipación de eventos surge (*"VYGO agente"*).
   - **Circuit Breaker**: Degradación elegante automática a `B2_umbral` si la política PPO experimenta contingencias.

4. **Simulación Pareada de Turno Completo y Replay (`scripts/generate_replay.py`)**:
   - Simula un turno sincronizado de 6 horas ($21,600$ s) en Monterrey con comercios gastronómicos reales.
   - Evento surge de media jornada a las 3h ($t = 10,800$ s) en el Centro ($1.4\times$).
   - Genera `app/data/replay_12.json` con las 3 pistas sincronizadas para reproducción estática sin internet ni servidor durante el pitch.

5. **Streaming de Turno en Vivo vía SSE (`GET /turno/stream`)**:
   - Server-Sent Events con soporte de parámetro `velocidad` para visualizar y animar el turno acelerado en el mapa del frontend.

---

## 📁 Estructura del Proyecto

```text
vygo-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # Aplicación FastAPI, CORS, middleware de latencia
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py            # /salud, /decidir, /turno/stream, /replay/{id}.json
│   ├── core/
│   │   ├── __init__.py
│   │   ├── schemas.py           # Esquemas Pydantic v2 exactos al Contrato v1.0
│   │   ├── router.py            # Motor Held-Karp / Secuenciador exacto de paradas
│   │   ├── metrics.py           # Distancia vial MTY, costos, tasa marginal, zonas
│   │   ├── policies.py          # B1_simple, B2_umbral y agente PPO con Circuit Breaker
│   │   └── simulator.py         # Motor de simulación en Monterrey (SSE + frames)
│   └── data/
│       └── replay_12.json       # Dataset pareado reproducible para el pitch
├── scripts/
│   ├── generate_replay.py       # Script generador de replay_12.json
│   └── test_api.py              # Script cliente de prueba de la API
├── tests/
│   ├── test_schemas.py          # Validación de contratos y límites geográficos MTY
│   ├── test_router.py           # Verificación de precedencia, capacidad y latencia (<15ms)
│   └── test_decidir.py          # Pruebas integrales de endpoints, SSE y errores 422/404
├── requirements.txt             # Dependencias del proyecto
├── .env.example                 # Variables de entorno de referencia
└── README.md
```

---

## 🛠️ Instalación y Uso

### 1. Requisitos Previos
- Python 3.10 o superior

### 2. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### 3. Ejecución del Servidor
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

La documentación interactiva Swagger estará disponible en:
```text
http://localhost:8000/docs
```

---

## 📡 Endpoints del API

### 1. `GET /salud`
Verifica el estado del servicio y la política predeterminada.
```json
{
  "ok": true,
  "politica": "agente_ppo",
  "version": "1.0",
  "timestamp": "2026-09-12T16:07:44.961800+00:00"
}
```

### 2. `POST /decidir`
Superficie de decisión puntual. Recibe el estado actual del repartidor, pedidos activos y ofertas entrantes.
Devuelve la recomendación (`aceptar` / `rechazar`), justificación numérica y el plan de paradas actualizado.

**Ejemplo de Petición:**
```json
{
  "version": "1.0",
  "repartidor": {
    "id": "8f2c1a40-1234-5678-9abc-def012345678",
    "posicion": { "lat": 25.6714, "lon": -100.3094 },
    "vehiculo": "moto",
    "capacidad": 2,
    "minutos_turno_transcurridos": 182,
    "minutos_turno_restantes": 178,
    "ganancia_turno_mxn": 428.50,
    "km_recorridos": 23.7,
    "rho_actual_mxn_h": 141.30
  },
  "plan_activo": [
    {
      "pedido_id": "a71f0001", "app": "uber", "estado": "asignado",
      "origen": { "lat": 25.6801, "lon": -100.3155 },
      "destino": { "lat": 25.6650, "lon": -100.2980 },
      "listo_en": "2026-09-12T14:09:00-06:00",
      "limite_en": "2026-09-12T14:38:00-06:00",
      "theta_frescura_min": 25, "recogido": false
    }
  ],
  "ofertas": [
    {
      "oferta_id": "c93b0001", "pedido_id": "d15e0001", "app": "rappi",
      "origen": { "lat": 25.6790, "lon": -100.3140 },
      "destino": { "lat": 25.6602, "lon": -100.2905 },
      "precio_mxn": 62.00,
      "listo_estimado_en": "2026-09-12T14:14:00-06:00",
      "limite_en": "2026-09-12T14:45:00-06:00",
      "anillo": 1
    }
  ],
  "contexto": { "clima": "normal", "evento_activo": "surge" }
}
```

**Ejemplo de Respuesta:**
```json
{
  "version": "1.0",
  "generado_en": "2026-09-12T14:03:22+00:00",
  "politica": "agente_ppo",
  "latencia_ms": 1.25,
  "decisiones": [
    {
      "oferta_id": "c93b0001",
      "pedido_id": "d15e0001",
      "app": "rappi",
      "decision": "aceptar",
      "prioridad": 1,
      "confianza": 0.88,
      "economia": {
        "tarifa_mxn": 62.00,
        "delta_tiempo_min": 9.0,
        "delta_distancia_km": 1.2,
        "costo_marginal_mxn": 7.45,
        "ganancia_neta_mxn": 54.55,
        "tasa_marginal_mxn_h": 363.7,
        "rho_actual_mxn_h": 141.3,
        "ajuste_aprendido_mxn_h": 18.0,
        "umbral_superado": true
      },
      "riesgo": {
        "holgura_frescura_min": 19.3,
        "holgura_limite_min": 25.0,
        "prob_entrega_a_tiempo": 0.85,
        "p_gana": 0.65,
        "anillo": 1
      },
      "factible": true,
      "motivo_infactible": null,
      "explicacion_corta": "+$364/h vs tu $141/h",
      "explicacion": "Acepta: paga a $363.7/h contra tu promedio de $141.3/h de hoy, con ajuste posicional de +18.0 MXN/h hacia CENTRO. Agrega sólo 1.2 km y deja 19.3 min de margen de frescura."
    }
  ],
  "plan": {
    "viaje_id": "e45a2789-...",
    "paradas": [ ... ],
    "geometria": {
      "type": "LineString",
      "coordinates": [[-100.3094, 25.6714], [-100.3155, 25.6801], ...]
    },
    "resumen": {
      "paradas_totales": 4,
      "pedidos_a_bordo": 2,
      "distancia_km": 5.8,
      "duracion_min": 22.3,
      "ingreso_mxn": 490.50,
      "costo_mxn": 25.65,
      "tasa_proyectada_mxn_h": 1250.0,
      "optimo_exacto": true,
      "secuencias_evaluadas": 6
    }
  },
  "telemetria": {
    "rho_actual_mxn_h": 141.3,
    "ganancia_turno_mxn": 428.50,
    "pedidos_entregados": 7,
    "puntualidad": 0.94,
    "km_por_pedido": 3.4,
    "factor_agrupamiento": 1.7,
    "utilizacion": 0.72
  },
  "alertas": []
}
```

### 3. `GET /turno/stream`
Flujo Server-Sent Events (SSE) para simular un turno acelerado en el frontend.
- Parámetros: `escenario` (default 12), `politica` (default `agente_ppo`), `velocidad` (default 10.0).

### 4. `GET /replay/{id}.json`
Descarga directa del dataset estático pareado de 3 pistas para reproducción sin red durante el pitch.

---

## 🧪 Pruebas Automatizadas

Para ejecutar la suite completa de pruebas:
```bash
pytest -v
```

Las pruebas cubren:
- **`tests/test_schemas.py`**: Validación de contratos JSON, bounding box geográfico de Monterrey [$25.4, 25.9$] y [$-100.6, -100.1$], y orden GeoJSON `[lon, lat]`.
- **`tests/test_router.py`**: Restricciones de precedencia, capacidad de mochila, holguras de frescura y benchmark de evaluación de 90 secuencias en $< 15$ ms.
- **`tests/test_decidir.py`**: Integración de endpoints `/salud`, `/decidir`, streaming `/turno/stream`, y `/replay/{id}.json`.

---

## 📊 Regeneración del Replay del Pitch

Para regenerar el archivo `app/data/replay_12.json`:
```bash
python scripts/generate_replay.py
```
Resultado del benchmark en simulación sincronizada:
| Política | Etiqueta | Ingreso (MXN) | Km Recorridos | Tasa ($\rho$, MXN/h) | Pedidos Entregados | Puntualidad |
|---|---|---|---|---|---|---|
| `B1_simple` | Sin VYGO | $612.00 | 41.2 km | $102.0/h | 11 | 72% |
| `B2_umbral` | VYGO (regla) | $948.00 | 28.7 km | $158.0/h | 17 | 91% |
| `agente_ppo` | VYGO (agente) | $1,014.00 | 27.1 km | $169.0/h | 18 | 93% |

---

## 🔗 Conexión con el Frontend

El frontend en React desplegado en Vercel (`https://vygo-ten.vercel.app`) se conecta a esta API configurando la variable de entorno:
```env
VITE_AGENT_URL=http://localhost:8000
```
La degradación en cascada del frontend asegura que si el servidor no está disponible, cae automáticamente al archivo `replay_12.json` servido de forma local o estática.
