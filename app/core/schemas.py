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

Politica = Literal["agente_ppo", "agente_bc", "B2_umbral", "B1_simple", "PPO", "HIBRIDO", "B1", "B2"]
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

class PedidoContexto(BaseModel):
    """Convenio estricto de JSONB pedidos.contexto según Contrato v2.0 (§4)."""
    tiempo_preparacion_min: int = 12
    tipo_producto: Literal["caliente", "frio", "no_perecedero"] = "caliente"
    theta_frescura_min: Optional[float] = 25.0
    limite_entrega_en: Optional[str] = None
    zona: Optional[str] = "centro"
    propina_esperada_mxn: Optional[float] = 0.0
    comercio_nombre: Optional[str] = None

    @field_validator('theta_frescura_min')
    @classmethod
    def validar_theta_coherencia(cls, v: Optional[float], info) -> Optional[float]:
        # Para no_perecedero, el contrato especifica omitir theta_frescura_min
        tipo = info.data.get("tipo_producto") if hasattr(info, "data") else None
        if tipo == "no_perecedero":
            return None
        return v

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
    contexto: Optional[Union[PedidoContexto, Dict[str, Any]]] = None
    origen_direccion: Optional[str] = None
    destino_direccion: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.contexto:
            ctx = self.contexto if isinstance(self.contexto, dict) else self.contexto.model_dump()
            if ctx.get("tipo_producto") == "no_perecedero":
                self.theta_frescura_min = None
            elif ctx.get("theta_frescura_min") is not None and self.theta_frescura_min == 30.0:
                self.theta_frescura_min = float(ctx["theta_frescura_min"])
            if not self.limite_en and ctx.get("limite_entrega_en"):
                self.limite_en = str(ctx["limite_entrega_en"])

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
    contexto: Optional[Union[PedidoContexto, Dict[str, Any]]] = None
    origen_direccion: Optional[str] = None
    destino_direccion: Optional[str] = None
    clima: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if self.contexto:
            ctx = self.contexto if isinstance(self.contexto, dict) else self.contexto.model_dump()
            if not self.limite_en and ctx.get("limite_entrega_en"):
                self.limite_en = str(ctx["limite_entrega_en"])

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
    # Contrato v1.0
    tarifa_mxn: float
    delta_tiempo_min: float
    delta_distancia_km: float
    costo_marginal_mxn: float
    ganancia_neta_mxn: float
    tasa_marginal_mxn_h: float
    rho_actual_mxn_h: float
    ajuste_aprendido_mxn_h: float
    umbral_superado: bool

    # Contrato v2.0 (src/lib/vygoAgent.ts & §5)
    tarifa: Optional[float] = None
    propina_esperada: Optional[float] = 0.0
    costo_km: Optional[float] = None
    costo_tiempo: Optional[float] = None
    ganancia_neta: Optional[float] = None

    def model_post_init(self, __context: Any) -> None:
        if self.tarifa is None:
            self.tarifa = round(self.tarifa_mxn, 2)
        if self.ganancia_neta is None:
            self.ganancia_neta = round(self.ganancia_neta_mxn, 2)
        if self.costo_km is None:
            self.costo_km = round(self.delta_distancia_km * 2.50, 2)
        if self.costo_tiempo is None:
            self.costo_tiempo = round(self.delta_tiempo_min * 0.50, 2)

class Riesgo(BaseModel):
    # Contrato v1.0
    holgura_frescura_min: float
    holgura_limite_min: float
    prob_entrega_a_tiempo: float
    p_gana: float
    anillo: int = 1

    # Contrato v2.0 (src/lib/vygoAgent.ts & §5)
    prob_retraso: Optional[float] = None
    frescura_restante: Optional[float] = None
    holgura: Optional[float] = None
    desvio_km: Optional[float] = None

    def model_post_init(self, __context: Any) -> None:
        if self.prob_retraso is None:
            self.prob_retraso = round(max(0.0, min(1.0, 1.0 - self.prob_entrega_a_tiempo)), 2)
        if self.frescura_restante is None:
            self.frescura_restante = round(self.holgura_frescura_min, 1)
        if self.holgura is None:
            self.holgura = round(self.holgura_limite_min, 1)

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

    # Contrato v2.0 direct top-level fields (src/lib/vygoAgent.ts & §5)
    aceptar: Optional[bool] = None
    tasa_marginal: Optional[float] = None
    rho_actual: Optional[float] = None
    ajuste_aprendido: Optional[float] = None
    politica: Optional[Literal["B1", "B2", "PPO", "HIBRIDO", "agente_ppo", "B2_umbral", "B1_simple", "agente_bc"]] = None

    def model_post_init(self, __context: Any) -> None:
        if self.aceptar is None:
            self.aceptar = (self.decision == "aceptar")
        if self.tasa_marginal is None:
            self.tasa_marginal = round(self.economia.tasa_marginal_mxn_h, 1)
        if self.rho_actual is None:
            self.rho_actual = round(self.economia.rho_actual_mxn_h, 1)
        if self.ajuste_aprendido is None:
            self.ajuste_aprendido = round(self.economia.ajuste_aprendido_mxn_h, 1)

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

    # Contrato v2.0 fields (src/lib/vygoAgent.ts & §5)
    secuencia: Optional[List[str]] = Field(default_factory=list)
    tiempo_total_min: Optional[float] = None
    distancia_total_km: Optional[float] = None
    eta_ultimo: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.secuencia and self.paradas:
            sec = []
            for p in self.paradas:
                if p.pedido_id not in sec:
                    sec.append(p.pedido_id)
            self.secuencia = sec
        if self.tiempo_total_min is None:
            self.tiempo_total_min = self.resumen.duracion_min
        if self.distancia_total_km is None:
            self.distancia_total_km = self.resumen.distancia_km
        if self.eta_ultimo is None and self.paradas:
            self.eta_ultimo = self.paradas[-1].eta

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
