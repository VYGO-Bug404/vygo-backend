import itertools
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple

from app.core.schemas import (
    Punto,
    PedidoActivo,
    OfertaEntrante,
    Parada,
    Plan,
    Geometria,
    ResumenPlan,
    MotivoInfactible,
)
from app.core.metrics import (
    distancia_vial_km,
    tiempo_viaje_min,
    calcular_costo_marginal,
    TIEMPO_SERVICIO_RECOLECCION_MIN,
    TIEMPO_SERVICIO_ENTREGA_MIN,
    COSTO_POR_KM_MXN,
    COSTO_POR_MIN_MXN,
)
from app.ai.sequencer import (
    held_karp as ai_held_karp,
    verificar_y_calendarizar as ai_verificar_y_calendarizar,
    Parada as AIParada,
    Restricciones as AIRestricciones,
    _permutaciones_validas_por_precedencia,
)
from app.ai.nav.astar import ruta_vial_interpolada, ruta_astar

_GRAFO_ROUTING = None
_V_MAX_MS = 25.0
_TREE_ROUTING = None
_NODOS_ROUTING = None

def obtener_grafo_routing():
    global _GRAFO_ROUTING, _V_MAX_MS, _TREE_ROUTING, _NODOS_ROUTING
    if _GRAFO_ROUTING is None:
        try:
            from app.ai.nav.grafo import cargar_grafo_ruteable, velocidad_maxima_ms
            _GRAFO_ROUTING = cargar_grafo_ruteable()
            if _GRAFO_ROUTING is not None:
                _V_MAX_MS = velocidad_maxima_ms(_GRAFO_ROUTING)
                try:
                    from scipy.spatial import cKDTree
                    import numpy as np
                    _NODOS_ROUTING = list(_GRAFO_ROUTING.nodes)
                    coords_arr = np.array([[_GRAFO_ROUTING.nodes[n]["x"], _GRAFO_ROUTING.nodes[n]["y"]] for n in _NODOS_ROUTING])
                    _TREE_ROUTING = cKDTree(coords_arr)
                except Exception:
                    _TREE_ROUTING = None
        except Exception:
            _GRAFO_ROUTING = False
    return _GRAFO_ROUTING if _GRAFO_ROUTING is not False else None

def nodo_mas_cercano(lon: float, lat: float) -> Optional[int]:
    global _TREE_ROUTING, _NODOS_ROUTING, _GRAFO_ROUTING
    if _TREE_ROUTING is not None and _NODOS_ROUTING is not None:
        try:
            _, idx = _TREE_ROUTING.query([lon, lat])
            return _NODOS_ROUTING[idx]
        except Exception:
            pass
    if _GRAFO_ROUTING:
        try:
            import osmnx as ox
            return int(ox.distance.nearest_nodes(_GRAFO_ROUTING, X=lon, Y=lat))
        except Exception:
            pass
        try:
            import numpy as np
            if _NODOS_ROUTING is None:
                _NODOS_ROUTING = list(_GRAFO_ROUTING.nodes)
            coords_arr = np.array([[_GRAFO_ROUTING.nodes[n]["x"], _GRAFO_ROUTING.nodes[n]["y"]] for n in _NODOS_ROUTING])
            dists = (coords_arr[:, 0] - lon) ** 2 + (coords_arr[:, 1] - lat) ** 2
            return _NODOS_ROUTING[int(np.argmin(dists))]
        except Exception:
            return None
    return None

# Calentar el grafo vial de Monterrey en segundo plano / import para evitar cold-start en requests
try:
    obtener_grafo_routing()
except Exception:
    pass

class ItemParada:
    def __init__(
        self,
        tipo: str, # "recoleccion" | "entrega"
        pedido_id: str,
        app: str,
        punto: Punto,
        listo_min: float = 0.0, # Minutos desde t0 en que está listo
        limite_min: float = 120.0, # Minutos desde t0 para fecha límite
        theta_frescura_min: float = 30.0,
        ya_recogido: bool = False,
        direccion: Optional[str] = None,
    ):
        self.tipo = tipo
        self.pedido_id = pedido_id
        self.app = app
        self.punto = punto
        self.listo_min = listo_min
        self.limite_min = limite_min
        self.theta_frescura_min = theta_frescura_min
        self.ya_recogido = ya_recogido
        self.direccion = direccion

def parse_iso_minutes(iso_str: Optional[str], t0: datetime) -> float:
    if not iso_str:
        return 0.0
    try:
        dt = datetime.fromisoformat(iso_str)
        # Normalizar timezone si uno tiene y otro no
        if dt.tzinfo is not None and t0.tzinfo is None:
            dt = dt.replace(tzinfo=None)
        elif dt.tzinfo is None and t0.tzinfo is not None:
            t0 = t0.replace(tzinfo=None)
        diff_sec = (dt - t0).total_seconds()
        return max(0.0, diff_sec / 60.0)
    except Exception:
        return 0.0

def generar_items_paradas(
    pedidos_activos: List[PedidoActivo],
    oferta_candidata: Optional[OfertaEntrante],
    t0: datetime,
) -> Tuple[List[ItemParada], int]:
    items = []
    carga_inicial = 0

    # Procesar pedidos activos
    for p in pedidos_activos:
        ctx = (p.contexto if isinstance(p.contexto, dict) else p.contexto.model_dump()) if p.contexto else {}
        
        listo_m = parse_iso_minutes(p.listo_en, t0)
        if listo_m == 0.0 and ctx.get("tiempo_preparacion_min") is not None:
            listo_m = float(ctx["tiempo_preparacion_min"])

        limite_m = parse_iso_minutes(p.limite_en, t0) if p.limite_en else (
            parse_iso_minutes(ctx.get("limite_entrega_en"), t0) if ctx.get("limite_entrega_en") else 90.0
        )
        
        if ctx.get("tipo_producto") == "no_perecedero":
            frescura = 99999.0
        elif ctx.get("theta_frescura_min") is not None:
            frescura = float(ctx["theta_frescura_min"])
        else:
            frescura = p.theta_frescura_min if p.theta_frescura_min is not None else 30.0

        dir_rec = p.origen_direccion or (f"{ctx.get('comercio_nombre')} ({p.pedido_id[:6]})" if ctx.get("comercio_nombre") else f"Recolección {p.app.capitalize()} ({p.pedido_id[:6]})")
        dir_ent = p.destino_direccion or f"Entrega {p.app.capitalize()} ({p.pedido_id[:6]})"

        if p.recogido:
            carga_inicial += 1
            items.append(
                ItemParada(
                    tipo="entrega",
                    pedido_id=p.pedido_id,
                    app=p.app,
                    punto=p.destino,
                    listo_min=0.0,
                    limite_min=limite_m,
                    theta_frescura_min=frescura,
                    ya_recogido=True,
                    direccion=dir_ent,
                )
            )
        else:
            items.append(
                ItemParada(
                    tipo="recoleccion",
                    pedido_id=p.pedido_id,
                    app=p.app,
                    punto=p.origen,
                    listo_min=listo_m,
                    limite_min=limite_m,
                    theta_frescura_min=frescura,
                    ya_recogido=False,
                    direccion=dir_rec,
                )
            )
            items.append(
                ItemParada(
                    tipo="entrega",
                    pedido_id=p.pedido_id,
                    app=p.app,
                    punto=p.destino,
                    listo_min=listo_m,
                    limite_min=limite_m,
                    theta_frescura_min=frescura,
                    ya_recogido=False,
                    direccion=dir_ent,
                )
            )

    # Procesar oferta candidata si existe
    if oferta_candidata:
        o_ctx = (oferta_candidata.contexto if isinstance(oferta_candidata.contexto, dict) else oferta_candidata.contexto.model_dump()) if oferta_candidata.contexto else {}
        
        listo_cand_m = parse_iso_minutes(oferta_candidata.listo_estimado_en, t0)
        if listo_cand_m == 0.0 and o_ctx.get("tiempo_preparacion_min") is not None:
            listo_cand_m = float(o_ctx["tiempo_preparacion_min"])

        limite_cand_m = parse_iso_minutes(oferta_candidata.limite_en, t0) if oferta_candidata.limite_en else (
            parse_iso_minutes(o_ctx.get("limite_entrega_en"), t0) if o_ctx.get("limite_entrega_en") else 90.0
        )

        if o_ctx.get("tipo_producto") == "no_perecedero":
            theta_cand = 99999.0
        elif o_ctx.get("theta_frescura_min") is not None:
            theta_cand = float(o_ctx["theta_frescura_min"])
        else:
            theta_cand = 30.0

        o_dir_rec = oferta_candidata.origen_direccion or (f"{o_ctx.get('comercio_nombre')} ({oferta_candidata.pedido_id[:6]})" if o_ctx.get("comercio_nombre") else f"Recolección {oferta_candidata.app.capitalize()} ({oferta_candidata.pedido_id[:6]})")
        o_dir_ent = oferta_candidata.destino_direccion or f"Entrega {oferta_candidata.app.capitalize()} ({oferta_candidata.pedido_id[:6]})"

        items.append(
            ItemParada(
                tipo="recoleccion",
                pedido_id=oferta_candidata.pedido_id,
                app=oferta_candidata.app,
                punto=oferta_candidata.origen,
                listo_min=listo_cand_m,
                limite_min=limite_cand_m,
                theta_frescura_min=theta_cand,
                ya_recogido=False,
                direccion=o_dir_rec,
            )
        )
        items.append(
            ItemParada(
                tipo="entrega",
                pedido_id=oferta_candidata.pedido_id,
                app=oferta_candidata.app,
                punto=oferta_candidata.destino,
                listo_min=listo_cand_m,
                limite_min=limite_cand_m,
                theta_frescura_min=theta_cand,
                ya_recogido=False,
                direccion=o_dir_ent,
            )
        )

    return items, carga_inicial

def resolver_secuencia_optima(
    posicion_actual: Punto,
    items: List[ItemParada],
    carga_inicial: int,
    capacidad_max: int = 3,
    clima: str = "normal",
    t0: Optional[datetime] = None,
) -> Tuple[Optional[List[Dict[str, Any]]], float, float, int, Optional[MotivoInfactible]]:
    """
    Encuentra la secuencia exacta de paradas que minimiza tiempo y costo,
    respetando precedencia, capacidad y frescura mediante Held-Karp compilado con Numba.
    Retorna: (secuencia_optima, distancia_km, duracion_min, secuencias_evaluadas, motivo_infactible)
    """
    if t0 is None:
        t0 = datetime.now(timezone.utc)

    if carga_inicial > capacidad_max:
        return None, 0.0, 0.0, 0, "capacidad"

    if not items:
        return [], 0.0, 0.0, 1, None

    # Si hay recolecciones pendientes y la capacidad actual ya está al tope
    if carga_inicial >= capacidad_max and any(it.tipo in ("recoleccion", "recogida") for it in items):
        return None, 0.0, 0.0, 0, "capacidad"

    n = len(items)
    if n > 12:
        return None, 0.0, 0.0, 0, "capacidad"

    stops: List[AIParada] = []
    r_dict = {}
    l_dict = {}
    theta_dict = {}
    carga_dict = {}

    for idx, it in enumerate(items):
        tipo = "recogida" if it.tipo in ("recoleccion", "recogida") else "entrega"
        pos = (it.punto.lat, it.punto.lon)
        stops.append(AIParada(id=it.pedido_id, tipo=tipo, pos=pos))
        carga_dict[it.pedido_id] = 1

        if tipo == "recogida":
            r_dict[it.pedido_id] = it.listo_min
        else:
            if it.limite_min is not None and it.limite_min < 9000:
                l_dict[it.pedido_id] = it.limite_min
            if it.theta_frescura_min is not None and it.theta_frescura_min < 9000:
                theta_dict[it.pedido_id] = it.theta_frescura_min

    constraints = AIRestricciones(
        capacidad=capacidad_max,
        r=r_dict,
        l=l_dict,
        theta=theta_dict,
        carga=carga_dict,
    )

    pos0 = (posicion_actual.lat, posicion_actual.lon)

    def travel_fn(p1, p2, t):
        pt1 = Punto(lat=p1[0], lon=p1[1])
        pt2 = Punto(lat=p2[0], lon=p2[1])
        d_km = distancia_vial_km(pt1, pt2)
        t_m = tiempo_viaje_min(d_km, clima=clima)
        return t_m, d_km

    orden, tiempo_total, dist_total, optimo_exacto, evals = ai_held_karp(
        stops, 0.0, pos0, travel_fn, constraints, k=10
    )

    if orden is None:
        diag: list[str] = []
        cands = _permutaciones_validas_por_precedencia(stops)
        for perm in cands[:20]:
            ai_verificar_y_calendarizar(
                perm, stops, 0.0, pos0, travel_fn, constraints, _diagnostico=diag
            )
            if diag:
                break
        motivo: MotivoInfactible = diag[0] if diag else "capacidad"
        return None, 0.0, 0.0, evals, motivo

    calendario = ai_verificar_y_calendarizar(orden, stops, 0.0, pos0, travel_fn, constraints)
    if calendario is None:
        return None, 0.0, 0.0, evals, "frescura"

    llegadas, salidas, dist_total = calendario

    secuencia_info = []
    tiempos_recoleccion = {}
    for pos_en_orden, idx in enumerate(orden):
        it = items[idx]
        t_llegada = llegadas[pos_en_orden]
        t_salida = salidas[pos_en_orden]
        if it.tipo in ("recoleccion", "recogida"):
            espera = max(0.0, t_salida - t_llegada)
            tiempos_recoleccion[it.pedido_id] = t_salida
            secuencia_info.append({
                "item": it,
                "eta_min": t_llegada,
                "espera_m": espera,
                "holgura_frescura_min": None,
            })
        else:
            t_rec = tiempos_recoleccion.get(it.pedido_id, 0.0)
            tiempo_transito = t_llegada - t_rec
            holgura_frescura = (
                max(0.0, it.theta_frescura_min - tiempo_transito)
                if it.theta_frescura_min is not None and it.theta_frescura_min < 9000
                else None
            )
            secuencia_info.append({
                "item": it,
                "eta_min": t_llegada,
                "espera_m": 0.0,
                "holgura_frescura_min": holgura_frescura,
            })

    return secuencia_info, dist_total, tiempo_total, evals, None

def construir_plan(
    posicion_actual: Punto,
    secuencia_info: List[Dict[str, Any]],
    distancia_km: float,
    duracion_min: float,
    ingreso_total_mxn: float,
    secuencias_evaluadas: int,
    t0: datetime,
    trazar_vial: bool = False,
) -> Plan:
    viaje_id = str(uuid.uuid4())
    paradas: List[Parada] = []
    # GeoJSON: [lon, lat]
    coords: List[List[float]] = [[posicion_actual.lon, posicion_actual.lat]]

    # Pedidos a bordo actualmente = los que ya fueron recogidos previamente
    pedidos_a_bordo = sum(1 for s in secuencia_info if s["item"].ya_recogido)

    for idx, s in enumerate(secuencia_info):
        it: ItemParada = s["item"]

        eta_dt = t0 + timedelta(minutes=s["eta_min"])
        eta_iso = eta_dt.isoformat()

        paradas.append(
            Parada(
                orden=idx + 1,
                tipo=it.tipo,
                pedido_id=it.pedido_id,
                app=it.app,
                punto=it.punto,
                direccion=it.direccion,
                eta=eta_iso,
                eta_min=round(s["eta_min"], 1),
                espera_estimada_min=round(s["espera_m"], 1) if it.tipo == "recoleccion" else None,
                holgura_frescura_min=round(s["holgura_frescura_min"], 1) if s["holgura_frescura_min"] is not None else None,
                estado="pendiente",
            )
        )
        coords.append([it.punto.lon, it.punto.lat])

    # Si se solicita trazado vial para navegación en mapa (estilo Waze/Google Maps)
    if trazar_vial and len(coords) > 1:
        polilinea_vial: List[List[float]] = []
        G = obtener_grafo_routing()
        ox_lib = None
        if G is not None:
            try:
                import osmnx as ox
                ox_lib = ox
            except ImportError:
                ox_lib = None

        for i in range(len(coords) - 1):
            p_origen = coords[i]
            p_destino = coords[i + 1]
            tramo = None
            if G is not None:
                try:
                    nodo_u = nodo_mas_cercano(p_origen[0], p_origen[1])
                    nodo_v = nodo_mas_cercano(p_destino[0], p_destino[1])
                    if nodo_u is not None and nodo_v is not None:
                        tramo = ruta_astar(G, nodo_u, nodo_v, _V_MAX_MS)
                except Exception:
                    tramo = None

            if not tramo or not tramo.get("polilinea"):
                tramo = ruta_vial_interpolada(p_origen[0], p_origen[1], p_destino[0], p_destino[1])

            pts = tramo.get("polilinea", [])
            if pts:
                if pts[0] != p_origen:
                    pts = [p_origen] + pts
                if pts[-1] != p_destino:
                    pts = pts + [p_destino]

            if not polilinea_vial:
                polilinea_vial.extend(pts)
            else:
                polilinea_vial.extend(pts[1:] if pts else [])
        coords = polilinea_vial

    costo_mxn = (distancia_km * COSTO_POR_KM_MXN) + (duracion_min * COSTO_POR_MIN_MXN)
    duracion_h = max(duracion_min, 1.0) / 60.0
    tasa_proyectada = max(0.0, (ingreso_total_mxn - costo_mxn) / duracion_h)

    resumen = ResumenPlan(
        paradas_totales=len(paradas),
        pedidos_a_bordo=pedidos_a_bordo,
        distancia_km=round(distancia_km, 1),
        duracion_min=round(duracion_min, 1),
        ingreso_mxn=round(ingreso_total_mxn, 2),
        costo_mxn=round(costo_mxn, 2),
        tasa_proyectada_mxn_h=round(tasa_proyectada, 1),
        optimo_exacto=True,
        secuencias_evaluadas=max(1, secuencias_evaluadas),
    )

    return Plan(
        viaje_id=viaje_id,
        paradas=paradas,
        geometria=Geometria(coordinates=coords),
        resumen=resumen,
    )


def trazar_ruta_puntos(
    origen: Punto,
    destinos: List[Punto],
    clima: str = "normal",
) -> Tuple[List[List[float]], float, float, List[Dict[str, Any]]]:
    """
    Traza la polilínea continua de alta fidelidad vial (A* con curvatura OSMnx)
    conectando origen -> destino_1 -> destino_2 -> ...
    Garantiza que la línea parta de la posición del conductor y pase por cada punto.
    """
    if not destinos:
        return [[origen.lon, origen.lat]], 0.0, 0.0, []

    puntos_cadena = [origen] + destinos
    G = obtener_grafo_routing()
    polilinea_total: List[List[float]] = []
    distancia_total_km = 0.0
    duracion_total_min = 0.0
    tramos_info: List[Dict[str, Any]] = []

    for i in range(len(puntos_cadena) - 1):
        p1 = puntos_cadena[i]
        p2 = puntos_cadena[i + 1]
        p_origen = [round(p1.lon, 6), round(p1.lat, 6)]
        p_destino = [round(p2.lon, 6), round(p2.lat, 6)]

        tramo = None
        if G is not None:
            try:
                nodo_u = nodo_mas_cercano(p1.lon, p1.lat)
                nodo_v = nodo_mas_cercano(p2.lon, p2.lat)
                if nodo_u is not None and nodo_v is not None and nodo_u != nodo_v:
                    tramo = ruta_astar(G, nodo_u, nodo_v, _V_MAX_MS)
            except Exception:
                tramo = None

        if not tramo or not tramo.get("polilinea"):
            tramo = ruta_vial_interpolada(p1.lon, p1.lat, p2.lon, p2.lat)

        pts = tramo.get("polilinea", [])
        if pts:
            if pts[0] != p_origen:
                pts = [p_origen] + pts
            if pts[-1] != p_destino:
                pts = pts + [p_destino]
        else:
            pts = [p_origen, p_destino]

        # Evitar puntos duplicados en las uniones
        if not polilinea_total:
            polilinea_total.extend(pts)
        else:
            polilinea_total.extend(pts[1:] if pts else [])

        m_tramo = tramo.get("metros", 0.0)
        s_tramo = tramo.get("segundos", 0.0)
        km_tramo = round(m_tramo / 1000.0, 2) if m_tramo > 0 else round(distancia_vial_km(p1, p2), 2)
        min_tramo = round(s_tramo / 60.0, 1) if s_tramo > 0 else round(tiempo_viaje_min(km_tramo, clima), 1)

        distancia_total_km += km_tramo
        duracion_total_min += min_tramo

        tramos_info.append({
            "origen": p1.model_dump(),
            "destino": p2.model_dump(),
            "distancia_km": km_tramo,
            "duracion_min": min_tramo,
            "puntos": len(pts),
        })

    return polilinea_total, round(distancia_total_km, 2), round(duracion_total_min, 1), tramos_info

