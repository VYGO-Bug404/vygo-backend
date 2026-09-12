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
        listo_m = parse_iso_minutes(p.listo_en, t0)
        limite_m = parse_iso_minutes(p.limite_en, t0) if p.limite_en else 90.0
        frescura = p.theta_frescura_min if p.theta_frescura_min is not None else 30.0

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
                    direccion=f"Entrega {p.app.capitalize()} ({p.pedido_id[:6]})",
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
                    direccion=f"Recolección {p.app.capitalize()} ({p.pedido_id[:6]})",
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
                    direccion=f"Entrega {p.app.capitalize()} ({p.pedido_id[:6]})",
                )
            )

    # Procesar oferta candidata si existe
    if oferta_candidata:
        listo_cand_m = parse_iso_minutes(oferta_candidata.listo_estimado_en, t0)
        limite_cand_m = parse_iso_minutes(oferta_candidata.limite_en, t0) if oferta_candidata.limite_en else 90.0
        items.append(
            ItemParada(
                tipo="recoleccion",
                pedido_id=oferta_candidata.pedido_id,
                app=oferta_candidata.app,
                punto=oferta_candidata.origen,
                listo_min=listo_cand_m,
                limite_min=limite_cand_m,
                theta_frescura_min=30.0,
                ya_recogido=False,
                direccion=f"Recolección {oferta_candidata.app.capitalize()} ({oferta_candidata.pedido_id[:6]})",
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
                theta_frescura_min=30.0,
                ya_recogido=False,
                direccion=f"Entrega {oferta_candidata.app.capitalize()} ({oferta_candidata.pedido_id[:6]})",
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
    respetando precedencia, capacidad y frescura.
    Retorna: (secuencia_optima, distancia_km, duracion_min, secuencias_evaluadas, motivo_infactible)
    """
    if t0 is None:
        t0 = datetime.now(timezone.utc)

    if carga_inicial > capacidad_max:
        return None, 0.0, 0.0, 0, "capacidad"

    if not items:
        return [], 0.0, 0.0, 1, None

    # Si hay recolecciones pendientes y la capacidad actual ya está al tope
    if carga_inicial >= capacidad_max and any(it.tipo == "recoleccion" for it in items):
        return None, 0.0, 0.0, 0, "capacidad"

    n = len(items)

    # Identificar pares (recolección, entrega) para filtrar precedencia
    pares_precedencia = []
    por_pedido = {}
    for idx, it in enumerate(items):
        por_pedido.setdefault(it.pedido_id, {})[it.tipo] = idx

    for pid, dicc in por_pedido.items():
        if "recoleccion" in dicc and "entrega" in dicc:
            pares_precedencia.append((dicc["recoleccion"], dicc["entrega"]))

    # Precomputar matriz de distancias y tiempos para evitar recalcular trigonometría
    # Índice 0 = posicion_actual, Índices 1..n = items[0..n-1]
    all_pts = [posicion_actual] + [it.punto for it in items]
    dist_matrix = [[distancia_vial_km(all_pts[i], all_pts[j]) for j in range(n + 1)] for i in range(n + 1)]
    time_matrix = [[tiempo_viaje_min(dist_matrix[i][j], clima) for j in range(n + 1)] for i in range(n + 1)]

    mejor_costo = float("inf")
    mejor_secuencia = None
    mejor_distancia = 0.0
    mejor_duracion = 0.0
    secuencias_evaluadas = 0
    fallos = {"capacidad": 0, "frescura": 0, "fecha_limite": 0}

    if n <= 6:
        # Evaluación exacta de permutaciones (para N=6 evalúa exactamente las 90 válidas en precedencia)
        indices = list(range(n))
        for perm in itertools.permutations(indices):
            # 1. Filtro rápido de precedencia
            pos_en_perm = {idx: i for i, idx in enumerate(perm)}
            if any(pos_en_perm[rec] > pos_en_perm[ent] for rec, ent in pares_precedencia):
                continue

            secuencias_evaluadas += 1

            # 2. Filtro de capacidad acumulada
            carga = carga_inicial
            valido_capacidad = True
            for idx in perm:
                it = items[idx]
                if it.tipo == "recoleccion":
                    carga += 1
                    if carga > capacidad_max:
                        valido_capacidad = False
                        fallos["capacidad"] += 1
                        break
                elif it.tipo == "entrega":
                    carga -= 1

            if not valido_capacidad:
                continue

            # 3. Simulación de tiempos y distancias
            tiempo_actual_m = 0.0
            distancia_total = 0.0
            pos_ant_idx = 0
            tiempos_recoleccion = {}
            secuencia_info = []
            valido_restricciones = True

            for idx in perm:
                it = items[idx]
                d_km = dist_matrix[pos_ant_idx][idx + 1]
                t_viaje_m = time_matrix[pos_ant_idx][idx + 1]
                t_llegada_m = tiempo_actual_m + t_viaje_m
                distancia_total += d_km

                if it.tipo == "recoleccion":
                    # Espera en cocina si llegamos antes de que esté listo
                    espera_cocina_m = max(0.0, it.listo_min - t_llegada_m)
                    t_salida_m = t_llegada_m + espera_cocina_m + TIEMPO_SERVICIO_RECOLECCION_MIN
                    tiempos_recoleccion[it.pedido_id] = t_salida_m
                    tiempo_actual_m = t_salida_m

                    secuencia_info.append({
                        "item": it,
                        "eta_min": t_llegada_m,
                        "espera_m": espera_cocina_m,
                        "holgura_frescura_min": None,
                    })
                else:
                    # Entrega
                    t_rec = tiempos_recoleccion.get(it.pedido_id, 0.0)
                    tiempo_en_transito_m = t_llegada_m - t_rec
                    holgura_frescura_m = it.theta_frescura_min - tiempo_en_transito_m
                    holgura_limite_m = it.limite_min - t_llegada_m

                    if holgura_frescura_m < -2.0:
                        valido_restricciones = False
                        fallos["frescura"] += 1
                        break

                    if holgura_limite_m < -5.0:
                        valido_restricciones = False
                        fallos["fecha_limite"] += 1
                        break

                    t_salida_m = t_llegada_m + TIEMPO_SERVICIO_ENTREGA_MIN
                    tiempo_actual_m = t_salida_m

                    secuencia_info.append({
                        "item": it,
                        "eta_min": t_llegada_m,
                        "espera_m": 0.0,
                        "holgura_frescura_min": max(0.0, holgura_frescura_m),
                    })

                pos_ant_idx = idx + 1

            if not valido_restricciones:
                continue

            costo = (distancia_total * COSTO_POR_KM_MXN) + (tiempo_actual_m * COSTO_POR_MIN_MXN)
            if costo < mejor_costo:
                mejor_costo = costo
                mejor_secuencia = secuencia_info
                mejor_distancia = distancia_total
                mejor_duracion = tiempo_actual_m
    else:
        # Algoritmo Branch-and-Bound DFS para N > 6: poda ramas que violan capacidad,
        # precedencia o cuya cota inferior de costo excede el mejor costo conocido.
        prec_map = {ent: rec for rec, ent in pares_precedencia}
        visited = [False] * n

        def dfs(step, current_carga, pos_idx, cur_dist, cur_time, tiempos_rec, cur_sec):
            nonlocal mejor_costo, mejor_secuencia, mejor_distancia, mejor_duracion, secuencias_evaluadas
            if step == n:
                secuencias_evaluadas += 1
                costo = (cur_dist * COSTO_POR_KM_MXN) + (cur_time * COSTO_POR_MIN_MXN)
                if costo < mejor_costo:
                    mejor_costo = costo
                    mejor_secuencia = list(cur_sec)
                    mejor_distancia = cur_dist
                    mejor_duracion = cur_time
                return

            for i in range(n):
                if not visited[i]:
                    it = items[i]
                    if it.tipo == "recoleccion" and current_carga >= capacidad_max:
                        continue
                    if i in prec_map and not visited[prec_map[i]]:
                        continue

                    d_km = dist_matrix[pos_idx][i + 1]
                    t_viaje_m = time_matrix[pos_idx][i + 1]
                    t_llegada_m = cur_time + t_viaje_m
                    new_dist = cur_dist + d_km

                    # Poda por cota inferior de costo
                    if (new_dist * COSTO_POR_KM_MXN) + (t_llegada_m * COSTO_POR_MIN_MXN) >= mejor_costo:
                        continue

                    if it.tipo == "recoleccion":
                        espera_m = max(0.0, it.listo_min - t_llegada_m)
                        t_salida_m = t_llegada_m + espera_m + TIEMPO_SERVICIO_RECOLECCION_MIN
                        tiempos_rec[it.pedido_id] = t_salida_m
                        step_info = {
                            "item": it,
                            "eta_min": t_llegada_m,
                            "espera_m": espera_m,
                            "holgura_frescura_min": None,
                        }
                        visited[i] = True
                        cur_sec.append(step_info)
                        dfs(step + 1, current_carga + 1, i + 1, new_dist, t_salida_m, tiempos_rec, cur_sec)
                        cur_sec.pop()
                        visited[i] = False
                    else:
                        t_rec = tiempos_rec.get(it.pedido_id, 0.0)
                        tiempo_transito_m = t_llegada_m - t_rec
                        holgura_frescura_m = it.theta_frescura_min - tiempo_transito_m
                        holgura_limite_m = it.limite_min - t_llegada_m

                        if holgura_frescura_m < -2.0 or holgura_limite_m < -5.0:
                            continue

                        t_salida_m = t_llegada_m + TIEMPO_SERVICIO_ENTREGA_MIN
                        step_info = {
                            "item": it,
                            "eta_min": t_llegada_m,
                            "espera_m": 0.0,
                            "holgura_frescura_min": max(0.0, holgura_frescura_m),
                        }
                        visited[i] = True
                        cur_sec.append(step_info)
                        dfs(step + 1, current_carga - 1, i + 1, new_dist, t_salida_m, tiempos_rec, cur_sec)
                        cur_sec.pop()
                        visited[i] = False

        dfs(0, carga_inicial, 0, 0.0, 0.0, {}, [])

    motivo = None
    if mejor_secuencia is None:
        if fallos["frescura"] > 0:
            motivo = "frescura"
        elif fallos["capacidad"] > 0:
            motivo = "capacidad"
        elif fallos["fecha_limite"] > 0:
            motivo = "fecha_limite"
        else:
            motivo = "capacidad"

    return mejor_secuencia, mejor_distancia, mejor_duracion, secuencias_evaluadas, motivo

def construir_plan(
    posicion_actual: Punto,
    secuencia_info: List[Dict[str, Any]],
    distancia_km: float,
    duracion_min: float,
    ingreso_total_mxn: float,
    secuencias_evaluadas: int,
    t0: datetime,
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
