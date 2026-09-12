from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

# Constantes de delimitación de la Zona Metropolitana de Monterrey
MTY_MIN_LAT = 25.40
MTY_MAX_LAT = 25.90
MTY_MIN_LON = -100.60
MTY_MAX_LON = -100.10

class Punto(BaseModel):
    lat: float
    lon: float

    @field_validator('lat')
    @classmethod
    def validar_latitud(cls, v: float) -> float:
        if not (MTY_MIN_LAT <= v <= MTY_MAX_LAT):
            raise ValueError(
                f'Latitud {v} fuera de la Zona Metropolitana de Monterrey [{MTY_MIN_LAT}, {MTY_MAX_LAT}]. '
                'Verifique el orden lat/lon.'
            )
        return v

    @field_validator('lon')
    @classmethod
    def validar_longitud(cls, v: float) -> float:
        if not (MTY_MIN_LON <= v <= MTY_MAX_LON):
            raise ValueError(
                f'Longitud {v} fuera de la Zona Metropolitana de Monterrey [{MTY_MIN_LON}, {MTY_MAX_LON}]. '
                'Verifique el orden lat/lon.'
            )
        return v

Politica = Literal["agente_ppo", "agente_bc", "B2_umbral", "B1_simple"]
Decision = Literal["aceptar", "rechazar"]
TipoParada = Literal["recoleccion", "entrega"]
EstadoParada = Literal["pendiente", "en_curso", "completada"]
MotivoInfactible = Literal[
    "capacidad",
    "frescura",
    "fecha_limite",
    "expirada",
    "incompatible_plataforma",
    "fuera_de_turno"
]
NivelAlerta = Literal["info", "aviso", "critico"]
CodigoAlerta = Literal[
    "frescura_critica",
    "riesgo_retraso",
    "evento_surge",
    "cierre_vial",
    "fin_turno_cercano"
]
TipoEvento = Literal["surge", "cierre_vial"]
Vehiculo = Literal["moto", "bici", "auto"]
AppNombre = Literal["uber", "didi", "rappi"]

class RepartidorEstado(BaseModel):
    id: str
    posicion: Punto
    vehiculo: str = "moto"
    capacidad: int = 3
    minutos_turno_transcurridos: float = 0.0
    minutos_turno_restantes: float = 360.0
    ganancia_turno_mxn: float = 0.0
    km_recorridos: float = 0.0
    rho_actual_mxn_h: float = 140.0

class PedidoActivo(BaseModel):
    pedido_id: str
    app: str
    estado: str = "asignado"
    origen: Punto
    destino: Punto
    precio_mxn: Optional[float] = None
    listo_en: Optional[str] = None
    limite_en: Optional[str] = None
    theta_frescura_min: Optional[float] = 30.0
    recogido: bool = False

class OfertaEntrante(BaseModel):
    oferta_id: str
    pedido_id: str
    app: str
    origen: Punto
    destino: Punto
    precio_mxn: float
    listo_estimado_en: Optional[str] = None
    limite_en: Optional[str] = None
    expira_en: Optional[str] = None
    anillo: Optional[int] = 1
    radio_metros: Optional[float] = None
    desvio_estimado_metros: Optional[float] = None

class Contexto(BaseModel):
    clima: Optional[str] = "normal"
    evento_activo: Optional[str] = None

class PeticionDecidir(BaseModel):
    version: str = "1.0"
    politica: Optional[Politica] = None
    repartidor: RepartidorEstado
    plan_activo: List[PedidoActivo] = Field(default_factory=list)
    ofertas: List[OfertaEntrante] = Field(default_factory=list)
    contexto: Optional[Contexto] = None

class Economia(BaseModel):
    tarifa_mxn: float
    delta_tiempo_min: float
    delta_distancia_km: float
    costo_marginal_mxn: float
    ganancia_neta_mxn: float
    tasa_marginal_mxn_h: float
    rho_actual_mxn_h: float
    ajuste_aprendido_mxn_h: float
    umbral_superado: bool

class Riesgo(BaseModel):
    holgura_frescura_min: float
    holgura_limite_min: float
    prob_entrega_a_tiempo: float
    p_gana: float
    anillo: int = 1

class DecisionOferta(BaseModel):
    oferta_id: str
    pedido_id: str
    app: str
    decision: Decision
    prioridad: int = 1
    confianza: float = 0.90
    economia: Economia
    riesgo: Riesgo
    factible: bool = True
    motivo_infactible: Optional[MotivoInfactible] = None
    explicacion_corta: str
    explicacion: str

class Parada(BaseModel):
    orden: int
    tipo: TipoParada
    pedido_id: str
    app: str
    punto: Punto
    direccion: Optional[str] = None
    eta: str
    eta_min: float
    espera_estimada_min: Optional[float] = None
    holgura_frescura_min: Optional[float] = None
    estado: EstadoParada = "pendiente"

class Geometria(BaseModel):
    type: Literal["LineString"] = "LineString"
    coordinates: List[List[float]] # GeoJSON: [lon, lat]

class ResumenPlan(BaseModel):
    paradas_totales: int
    pedidos_a_bordo: int
    distancia_km: float
    duracion_min: float
    ingreso_mxn: float
    costo_mxn: float
    tasa_proyectada_mxn_h: float
    optimo_exacto: bool = True
    secuencias_evaluadas: int = 1

class Plan(BaseModel):
    viaje_id: str
    paradas: List[Parada]
    geometria: Geometria
    resumen: ResumenPlan

class Telemetria(BaseModel):
    rho_actual_mxn_h: float
    ganancia_turno_mxn: float
    pedidos_entregados: int
    puntualidad: float
    km_por_pedido: float
    factor_agrupamiento: float
    utilizacion: float

class Alerta(BaseModel):
    nivel: NivelAlerta
    codigo: CodigoAlerta
    pedido_id: Optional[str] = None
    mensaje: str

class EventoActivo(BaseModel):
    tipo: TipoEvento
    zona: str
    multiplicador_tarifa: Optional[float] = 1.0
    inicia_en: str
    termina_en: str

class RespuestaDecidir(BaseModel):
    version: str = "1.0"
    generado_en: str
    politica: Politica
    latencia_ms: float
    decisiones: List[DecisionOferta]
    plan: Plan
    telemetria: Telemetria
    alertas: List[Alerta] = Field(default_factory=list)
    evento_activo: Optional[EventoActivo] = None

class EscenarioReplay(BaseModel):
    id: int
    semilla: int
    duracion_seg: int
    bbox: Dict[str, float]
    comercios: List[Dict[str, Any]]
    evento: Optional[Dict[str, Any]] = None

class PistaReplay(BaseModel):
    politica: Politica
    etiqueta: str
    frames: List[Dict[str, Any]]
    resumen: Dict[str, Any]

class ReplayData(BaseModel):
    version: str = "1.0"
    escenario: EscenarioReplay
    pistas: List[PistaReplay]
