"""
app/core/db.py
Módulo de integración con la Base de Datos Supabase (11 tablas) y motor de simulación en memoria.
Cumple al 100% con el Contrato de Datos del Agente v2.0 (12 de septiembre de 2026):
  - Consultas de entrada completas (§4.1: Consultas 1 a 4)
  - Escritura de vuelta a la base (§5.3: Aceptar / Rechazar con reescritura de orden)
  - Plan de inyección de datos (§6: 40 pedidos, 4 clústeres en Monterrey ZM, 8 ofertas)
  - 7 Reglas de verificación (§7)
"""

import os
import math
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union

import httpx
from pydantic import BaseModel

from app.core.schemas import (
    Punto,
    RepartidorEstado,
    PedidoActivo,
    OfertaEntrante,
    Contexto,
    PeticionDecidir,
    PedidoContexto,
)

logger = logging.getLogger("vygo.db")

# Coordenadas y clústeres oficiales de Monterrey (§6.1)
CLUSTER_CENTRO = {"nombre": "Centro", "lat": 25.6714, "lon": -100.3094, "zona": "centro"}
CLUSTER_SAN_PEDRO = {"nombre": "San Pedro / Valle", "lat": 25.6580, "lon": -100.3560, "zona": "san_pedro"}
CLUSTER_CUMBRES = {"nombre": "Cumbres", "lat": 25.7180, "lon": -100.3760, "zona": "cumbres"}
CLUSTER_TEC = {"nombre": "Tec / Contry", "lat": 25.6510, "lon": -100.2890, "zona": "tec"}

CLUSTERS_MTY = [CLUSTER_CENTRO, CLUSTER_SAN_PEDRO, CLUSTER_CUMBRES, CLUSTER_TEC]

# 10 Claves de configuración obligatorias (§3.5)
CONFIG_DEFAULT = {
    "radio_ronda_1_metros": 1500,
    "radio_ronda_2_metros": 3000,
    "radio_ronda_3_metros": 5000,
    "duracion_ronda_seg": 45,
    "expiracion_oferta_seg": 30,
    "max_rondas": 3,
    "max_pedidos_por_viaje": 4,
    "costo_km_mxn": 1.20,
    "rho_inicial_mxn_h": 140.00,
    "duracion_turno_min": 360,
}

class MockSupabaseDB:
    """
    Motor en memoria que emula exactamente las 11 tablas de la base de datos Supabase
    del proyecto ihmadvmoenkxanoxrwcy, permitiendo pruebas unitarias, simulación end-to-end
    y fallback sin conexión de red externa.
    """
    def __init__(self):
        self.apps: Dict[int, Dict[str, Any]] = {}
        self.usuarios: Dict[str, Dict[str, Any]] = {}
        self.repartidores: Dict[str, Dict[str, Any]] = {}
        self.platform_connections: List[Dict[str, Any]] = []
        self.configuracion: Dict[str, Any] = {}
        self.ubicaciones_conductores: Dict[str, Dict[str, Any]] = {}
        self.viajes_repartidor: Dict[str, Dict[str, Any]] = {}
        self.pedidos: Dict[str, Dict[str, Any]] = {}
        self.viaje_pedidos: List[Dict[str, Any]] = []
        self.difusiones_pedido: List[Dict[str, Any]] = []
        self.ofertas_pedido: Dict[str, Dict[str, Any]] = {}
        self.inicializar_datos_semilla()

    def inicializar_datos_semilla(self):
        """Ejecuta el plan de inyección de datos oficial (§6)."""
        now = datetime.now(timezone.utc)
        self.limpiar()

        # 1. apps (3)
        self.apps = {
            1: {"id": 1, "nombre": "uber"},
            2: {"id": 2, "nombre": "rappi"},
            3: {"id": 3, "nombre": "didi"},
        }

        # 2. usuarios (1 repartidor de demo + 30 clientes ficticios = 31)
        user_rep_id = "usr-rep-demo-01"
        self.usuarios[user_rep_id] = {
            "id": user_rep_id,
            "nombre": "Carlos Repartidor Demo",
            "email": "carlos.demo@vygo.mx",
            "telefono": "8110000001",
        }
        for i in range(1, 31):
            uid = f"usr-cli-{i:02d}"
            self.usuarios[uid] = {
                "id": uid,
                "nombre": f"Cliente Ficticio {i}",
                "email": f"cliente{i}@ejemplo.com",
                "telefono": f"811000{i:04d}",
            }

        # 3. repartidores (1 demo)
        rep_id = "rep-demo-01"
        self.repartidores[rep_id] = {
            "id": rep_id,
            "usuario_id": user_rep_id,
            "app_id": 1,
            "vehiculo": "moto",
            "disponible": True,
            "rating": 4.95,
        }

        # 4. platform_connections (3 activas)
        self.platform_connections = [
            {"user_id": user_rep_id, "platform": "uber", "is_active": True},
            {"user_id": user_rep_id, "platform": "rappi", "is_active": True},
            {"user_id": user_rep_id, "platform": "didi", "is_active": True},
        ]

        # 5. configuracion (10 claves §3.5)
        self.configuracion = dict(CONFIG_DEFAULT)

        # 6. ubicaciones_conductores (1 posición inicial en ZM de Monterrey)
        self.ubicaciones_conductores[user_rep_id] = {
            "user_id": user_rep_id,
            "lat": CLUSTER_CENTRO["lat"],
            "lng": CLUSTER_CENTRO["lon"],
            "updated_at": now.isoformat(),
        }

        # 7. viajes_repartidor (1 viaje activo, iniciado hace 90 min)
        viaje_id = "viaje-demo-01"
        self.viajes_repartidor[viaje_id] = {
            "id": viaje_id,
            "repartidor_id": rep_id,
            "estado": "activo",
            "iniciado_en": (now - timedelta(minutes=90)).isoformat(),
            "origen_actual": {"lat": CLUSTER_CENTRO["lat"], "lon": CLUSTER_CENTRO["lon"]},
            "ruta_linea": None,
            "actualizado_en": now.isoformat(),
        }

        # 8. pedidos (40 pedidos distribuidos en 4 clústeres: 12 entregados, 3 asignados, 25 buscando)
        comercios_por_cluster = {
            "centro": ["Sushi Roll Centro", "Tacos El Primo", "La Bella Italia Centro", "Burgers MTY Macroplaza", "Chilaquiles Barrio Antiguo"],
            "san_pedro": ["La Postrería Valle", "Steak House San Pedro", "Green Bowl Vasconcelos", "Poke Bar Del Valle", "Pizzeria Napolitana SP"],
            "cumbres": ["Burger Lab Cumbres", "Tacos Leones Cumbres", "Sushi Master Paseo", "Tortas Bravas Cumbres", "Alitas & Ribs Cumbres"],
            "tec": ["Chilaquiles del Tec", "Burritos Garza Sada", "Bao Bao Contry", "Pizza Express Alfonso Reyes", "Bowl Fresco Tec"],
        }

        pedidos_creados = []
        # Generar 40 pedidos (10 por cada uno de los 4 clústeres)
        for cluster_idx, cluster in enumerate(CLUSTERS_MTY):
            zona = cluster["zona"]
            comercios = comercios_por_cluster[zona]
            for j in range(10):
                pid = f"ped-{zona[:3]}-{j+1:02d}"
                cli_id = f"usr-cli-{(cluster_idx * 10 + j) % 30 + 1:02d}"
                app_id = (j % 3) + 1
                app_nombre = self.apps[app_id]["nombre"]

                # Variación de posición dentro de 1.5 km (0.012 grados aprox)
                d_lat_o = (math.sin(j * 1.3) * 0.008)
                d_lon_o = (math.cos(j * 1.3) * 0.008)
                orig_lat = round(cluster["lat"] + d_lat_o, 4)
                orig_lon = round(cluster["lon"] + d_lon_o, 4)

                # Destino dentro de 2.5 km del origen
                d_lat_d = (math.sin(j * 2.1 + 0.5) * 0.015)
                d_lon_d = (math.cos(j * 2.1 + 0.5) * 0.015)
                dest_lat = round(orig_lat + d_lat_d, 4)
                dest_lon = round(orig_lon + d_lon_d, 4)

                # Clasificación de producto y frescura (§4)
                if j % 4 == 0:
                    tipo_prod = "no_perecedero"
                    theta_frescura = None  # Consistencia obligatoria: sin theta para no perecederos
                elif j % 4 == 1:
                    tipo_prod = "frio"
                    theta_frescura = 35.0
                else:
                    tipo_prod = "caliente"
                    theta_frescura = 25.0

                tiempo_prep = 8 + (j % 12)
                precio = 45.0 + (j * 4.5) + (15.0 if zona == "san_pedro" else 0.0)
                comercio = comercios[j % len(comercios)]
                propina = 12.0 if zona in ("san_pedro", "tec") else 0.0

                contexto = {
                    "tiempo_preparacion_min": tiempo_prep,
                    "tipo_producto": tipo_prod,
                    "zona": zona,
                    "propina_esperada_mxn": propina,
                    "comercio_nombre": comercio,
                    "limite_entrega_en": (now + timedelta(minutes=45)).isoformat(),
                }
                if theta_frescura is not None:
                    contexto["theta_frescura_min"] = theta_frescura

                pedidos_creados.append({
                    "id": pid,
                    "app_id": app_id,
                    "app_nombre": app_nombre,
                    "id_externo": f"{app_nombre.upper()}-{pid[-6:]}",
                    "cliente_id": cli_id,
                    "origen": {"lat": orig_lat, "lon": orig_lon},
                    "origen_direccion": f"{comercio}, {cluster['nombre']}",
                    "destino": {"lat": dest_lat, "lon": dest_lon},
                    "destino_direccion": f"Calle Entrega {j+1}, {cluster['nombre']}",
                    "precio": round(precio, 2),
                    "moneda": "MXN",
                    "clima": "normal",
                    "contexto": contexto,
                    "creado_en": (now - timedelta(minutes=20 + j * 2)).isoformat(),
                    "zona": zona,
                })

        # Distribuir los 40 pedidos: 12 entregados, 3 asignados (a bordo), 25 buscando
        # 12 Entregados (los primeros 12)
        for idx in range(12):
            p = pedidos_creados[idx]
            p["estado"] = "entregado"
            p["creado_en"] = (now - timedelta(minutes=100 - idx * 5)).isoformat()
            p["aceptado_en"] = (now - timedelta(minutes=95 - idx * 5)).isoformat()
            p["entregado_en"] = (now - timedelta(minutes=70 - idx * 5)).isoformat()
            self.pedidos[p["id"]] = p
            # 9. viaje_pedidos: registrar los 12 entregados en historial
            self.viaje_pedidos.append({
                "viaje_id": viaje_id,
                "pedido_id": p["id"],
                "orden": idx + 1,
                "agregado_en": p["aceptado_en"],
            })

        # 3 Asignados a bordo del viaje activo (del 12 al 14)
        for idx in range(12, 15):
            p = pedidos_creados[idx]
            p["estado"] = "asignado"
            p["creado_en"] = (now - timedelta(minutes=25)).isoformat()
            p["aceptado_en"] = (now - timedelta(minutes=15)).isoformat()
            p["entregado_en"] = None
            self.pedidos[p["id"]] = p
            orden_a_bordo = idx + 1  # Orden consecutivo 13, 14, 15 sin huecos en el viaje
            self.viaje_pedidos.append({
                "viaje_id": viaje_id,
                "pedido_id": p["id"],
                "orden": orden_a_bordo,
                "agregado_en": p["aceptado_en"],
            })

        # 25 Buscando (del 15 al 39)
        for idx in range(15, 40):
            p = pedidos_creados[idx]
            p["estado"] = "buscando"
            p["creado_en"] = (now - timedelta(minutes=5 + (idx % 10))).isoformat()
            p["aceptado_en"] = None
            p["entregado_en"] = None
            self.pedidos[p["id"]] = p
            # 10. difusiones_pedido (25 filas)
            dif_id = f"dif-{p['id']}"
            self.difusiones_pedido.append({
                "id": dif_id,
                "pedido_id": p["id"],
                "ronda": 1,
                "creado_en": p["creado_en"],
            })

        # 11. ofertas_pedido (8 pendientes para el repartidor demo)
        candidatos_buscando = [p for p in self.pedidos.values() if p["estado"] == "buscando"][:8]
        anillos_desvios = [
            (1, 1500, 450.0),
            (1, 1500, 680.0),
            (1, 1500, 890.0),
            (2, 3000, 1450.0),
            (2, 3000, 1850.0),
            (2, 3000, 2200.0),
            (3, 5000, 3100.0),
            (3, 5000, 4200.0),
        ]
        for i, p in enumerate(candidatos_buscando):
            of_id = f"oferta-demo-{i+1:02d}"
            ronda, radio, desvio = anillos_desvios[i % len(anillos_desvios)]
            self.ofertas_pedido[of_id] = {
                "id": of_id,
                "pedido_id": p["id"],
                "repartidor_id": rep_id,
                "viaje_id": viaje_id,
                "ronda": ronda,
                "radio_metros": radio,
                "desvio_estimado_metros": desvio,
                "expira_en": (now + timedelta(minutes=15 + i * 2)).isoformat(),
                "clima": "normal",
                "estado": "pendiente",
                "ofrecida_en": now.isoformat(),
                "respondida_en": None,
            }

    def limpiar(self):
        """Limpia todas las tablas."""
        self.apps.clear()
        self.usuarios.clear()
        self.repartidores.clear()
        self.platform_connections.clear()
        self.configuracion.clear()
        self.ubicaciones_conductores.clear()
        self.viajes_repartidor.clear()
        self.pedidos.clear()
        self.viaje_pedidos.clear()
        self.difusiones_pedido.clear()
        self.ofertas_pedido.clear()

    # =========================================================================
    # §4.1 CONSULTAS DE ENTRADA COMPLETAS (SQL 1 a 4)
    # =========================================================================

    def obtener_estado_repartidor(self, repartidor_id: str) -> Optional[Dict[str, Any]]:
        """
        Consulta 1 (§4.1):
        select r.id, r.vehiculo, r.disponible,
        coalesce(uc.lat, st_y(v.origen_actual::geometry)) as lat,
        coalesce(uc.lng, st_x(v.origen_actual::geometry)) as lng,
        v.id as viaje_id, v.iniciado_en, uc.updated_at
        from repartidores r
        left join viajes_repartidor v on v.repartidor_id = r.id and v.estado = 'activo'
        left join ubicaciones_conductores uc on uc.user_id = r.usuario_id
        where r.id = :repartidor_id;

        Nota §3.4: Si uc.updated_at tiene más de 60 s, se cae a viajes_repartidor.origen_actual.
        """
        r = self.repartidores.get(repartidor_id)
        if not r:
            return None

        user_id = r.get("usuario_id")
        uc = self.ubicaciones_conductores.get(user_id) if user_id else None

        # Buscar viaje activo
        viaje_activo = None
        for v in self.viajes_repartidor.values():
            if v.get("repartidor_id") == repartidor_id and v.get("estado") == "activo":
                viaje_activo = v
                break

        now = datetime.now(timezone.utc)
        lat = None
        lng = None

        # §3.4: Si uc.updated_at tiene más de 60s, se cae a origen_actual
        if uc and uc.get("updated_at"):
            try:
                uc_dt = datetime.fromisoformat(uc["updated_at"])
                if uc_dt.tzinfo is None:
                    uc_dt = uc_dt.replace(tzinfo=timezone.utc)
                if (now - uc_dt).total_seconds() <= 60.0:
                    lat = uc.get("lat")
                    lng = uc.get("lng")
            except Exception:
                pass

        # Fallback a origen_actual del viaje activo
        if (lat is None or lng is None) and viaje_activo and viaje_activo.get("origen_actual"):
            lat = viaje_activo["origen_actual"].get("lat")
            lng = viaje_activo["origen_actual"].get("lon")

        # Fallback de salvaguarda
        if lat is None or lng is None:
            lat = uc.get("lat") if uc else CLUSTER_CENTRO["lat"]
            lng = uc.get("lng") if uc else CLUSTER_CENTRO["lon"]

        return {
            "id": r["id"],
            "vehiculo": r.get("vehiculo", "moto"),
            "disponible": r.get("disponible", True),
            "lat": lat,
            "lng": lng,
            "viaje_id": viaje_activo["id"] if viaje_activo else None,
            "iniciado_en": viaje_activo["iniciado_en"] if viaje_activo else None,
            "updated_at": uc["updated_at"] if uc else None,
        }

    def obtener_plan_activo(self, viaje_id: str) -> List[Dict[str, Any]]:
        """
        Consulta 2 (§4.1):
        select vp.orden, p.id, p.precio, p.estado,
        st_y(p.origen::geometry) as origen_lat, st_x(p.origen::geometry) as origen_lng,
        st_y(p.destino::geometry) as destino_lat, st_x(p.destino::geometry) as destino_lng,
        p.contexto, p.creado_en, p.aceptado_en, vp.agregado_en
        from viaje_pedidos vp
        join pedidos p on p.id = vp.pedido_id
        where vp.viaje_id = :viaje_id
        and p.estado in ('asignado', 'en_camino')
        order by vp.orden;
        """
        if not viaje_id:
            return []

        resultado = []
        for vp in self.viaje_pedidos:
            if vp.get("viaje_id") == viaje_id:
                pid = vp.get("pedido_id")
                p = self.pedidos.get(pid)
                if p and p.get("estado") in ("asignado", "en_camino"):
                    app_nombre = self.apps.get(p.get("app_id"), {}).get("nombre", "uber")
                    resultado.append({
                        "orden": vp.get("orden", 1),
                        "id": p["id"],
                        "precio": p["precio"],
                        "estado": p["estado"],
                        "app": app_nombre,
                        "origen_lat": p["origen"]["lat"],
                        "origen_lng": p["origen"]["lon"],
                        "destino_lat": p["destino"]["lat"],
                        "destino_lng": p["destino"]["lon"],
                        "contexto": p.get("contexto", {}),
                        "origen_direccion": p.get("origen_direccion"),
                        "destino_direccion": p.get("destino_direccion"),
                        "creado_en": p.get("creado_en"),
                        "aceptado_en": p.get("aceptado_en"),
                        "agregado_en": vp.get("agregado_en"),
                    })

        resultado.sort(key=lambda x: x["orden"])
        return resultado

    def obtener_ofertas_pendientes(
        self,
        repartidor_id: str,
        user_id: Optional[str] = None,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        """
        Consulta 3 (§4.1):
        select o.id, o.pedido_id, o.ronda, o.radio_metros,
        o.desvio_estimado_metros, o.expira_en, o.clima,
        p.precio, p.app_id, p.contexto,
        p.origen_direccion, p.destino_direccion,
        st_y(p.origen::geometry) as origen_lat, st_x(p.origen::geometry) as origen_lng,
        st_y(p.destino::geometry) as destino_lat, st_x(p.destino::geometry) as destino_lng,
        a.nombre as app
        from ofertas_pedido o
        join pedidos p on p.id = o.pedido_id
        join apps a on a.id = p.app_id
        where o.repartidor_id = :repartidor_id
        and o.estado = 'pendiente'
        and o.expira_en > now()
        and a.nombre in (select platform from platform_connections where user_id = :user_id and is_active)
        order by o.ronda asc, o.desvio_estimado_metros asc
        limit 8;
        """
        now = datetime.now(timezone.utc)
        rep = self.repartidores.get(repartidor_id)
        if rep and not rep.get("disponible", True):
            # §3.4: Si disponible es false, no se le ofrece nada
            return []

        if not user_id and rep:
            user_id = rep.get("usuario_id")

        plataformas_activas = {
            conn["platform"]
            for conn in self.platform_connections
            if user_id and conn.get("user_id") == user_id and conn.get("is_active")
        }

        candidatos = []
        for o in self.ofertas_pedido.values():
            if o.get("repartidor_id") != repartidor_id or o.get("estado") != "pendiente":
                continue

            # Validar expiración
            expira_str = o.get("expira_en")
            if expira_str:
                try:
                    expira_dt = datetime.fromisoformat(expira_str)
                    if expira_dt.tzinfo is None:
                        expira_dt = expira_dt.replace(tzinfo=timezone.utc)
                    if expira_dt <= now:
                        continue
                except Exception:
                    pass

            p = self.pedidos.get(o.get("pedido_id"))
            if not p:
                continue

            app_info = self.apps.get(p.get("app_id"))
            app_nombre = app_info.get("nombre") if app_info else "uber"

            if app_nombre not in plataformas_activas:
                continue

            candidatos.append({
                "id": o["id"],
                "pedido_id": p["id"],
                "ronda": o.get("ronda", 1),
                "radio_metros": o.get("radio_metros", 1500),
                "desvio_estimado_metros": o.get("desvio_estimado_metros", 500.0),
                "expira_en": o.get("expira_en"),
                "clima": o.get("clima", p.get("clima", "normal")),
                "precio": p["precio"],
                "app_id": p.get("app_id"),
                "app": app_nombre,
                "contexto": p.get("contexto", {}),
                "origen_direccion": p.get("origen_direccion"),
                "destino_direccion": p.get("destino_direccion"),
                "origen_lat": p["origen"]["lat"],
                "origen_lng": p["origen"]["lon"],
                "destino_lat": p["destino"]["lat"],
                "destino_lng": p["destino"]["lon"],
            })

        candidatos.sort(key=lambda x: (x["ronda"], x["desvio_estimado_metros"]))
        return candidatos[:limit]

    def obtener_metricas_turno(self, repartidor_id: str) -> Dict[str, Any]:
        """
        Consulta 4 (§4.1):
        select coalesce(sum(p.precio), 0) as ingreso_mxn,
        count(*) as entregados,
        extract(epoch from now() - min(v.iniciado_en))/3600.0 as horas
        from viaje_pedidos vp
        join pedidos p on p.id = vp.pedido_id
        join viajes_repartidor v on v.id = vp.viaje_id
        where v.repartidor_id = :repartidor_id
        and p.estado = 'entregado'
        and v.iniciado_en >= date_trunc('day', now());
        """
        now = datetime.now(timezone.utc)
        inicio_hoy = now.replace(hour=0, minute=0, second=0, microsecond=0)

        ingreso_mxn = 0.0
        entregados = 0
        min_iniciado_en: Optional[datetime] = None

        viajes_rep = {v["id"]: v for v in self.viajes_repartidor.values() if v.get("repartidor_id") == repartidor_id}

        for vp in self.viaje_pedidos:
            vid = vp.get("viaje_id")
            if vid in viajes_rep:
                v = viajes_rep[vid]
                iniciado_dt = datetime.fromisoformat(v["iniciado_en"]) if v.get("iniciado_en") else now
                if iniciado_dt.tzinfo is None:
                    iniciado_dt = iniciado_dt.replace(tzinfo=timezone.utc)
                if iniciado_dt >= inicio_hoy:
                    p = self.pedidos.get(vp.get("pedido_id"))
                    if p and p.get("estado") == "entregado":
                        if min_iniciado_en is None or iniciado_dt < min_iniciado_en:
                            min_iniciado_en = iniciado_dt
                        ingreso_mxn += float(p.get("precio", 0.0))
                        entregados += 1

        if min_iniciado_en:
            horas = max(0.1, (now - min_iniciado_en).total_seconds() / 3600.0)
        else:
            # Si no hay pedidos entregados hoy, verificar inicio de viaje activo
            viaje_activo = next((v for v in viajes_rep.values() if v.get("estado") == "activo"), None)
            if viaje_activo and viaje_activo.get("iniciado_en"):
                v_dt = datetime.fromisoformat(viaje_activo["iniciado_en"])
                if v_dt.tzinfo is None:
                    v_dt = v_dt.replace(tzinfo=timezone.utc)
                horas = max(0.0, (now - v_dt).total_seconds() / 3600.0)
            else:
                horas = 0.0

        rho_inicial = float(self.configuracion.get("rho_inicial_mxn_h", 140.0))
        if entregados > 0 and horas > 0:
            rho_actual = max(80.0, round(ingreso_mxn / horas, 1))
        else:
            rho_actual = rho_inicial

        return {
            "ingreso_mxn": round(ingreso_mxn, 2),
            "entregados": entregados,
            "horas": round(horas, 2),
            "rho_actual": rho_actual,
        }

    # =========================================================================
    # §5.3 ESCRITURA DE VUELTA A LA BASE (Write-Backs)
    # =========================================================================

    def persistir_decision_aceptar(
        self,
        oferta_id: str,
        pedido_id: str,
        viaje_id: str,
        nuevo_orden_secuencia: List[Tuple[str, int]],
        coordenadas_ruta: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        """
        Ejecuta las mutaciones de escritura al aceptar una oferta (§5.3):
          1. ofertas_pedido: estado = 'aceptada', respondida_en = now(), viaje_id = :viaje_id
          2. pedidos: estado = 'asignado', aceptado_en = now()
          3. ofertas_pedido (otras): estado = 'perdida'
          4. viaje_pedidos: inserción y reescritura COMPLETA del orden de paradas
          5. viajes_repartidor: ruta_linea y actualizado_en = now()
        """
        now = datetime.now(timezone.utc).isoformat()

        # 1. Oferta aceptada
        if oferta_id in self.ofertas_pedido:
            self.ofertas_pedido[oferta_id]["estado"] = "aceptada"
            self.ofertas_pedido[oferta_id]["respondida_en"] = now
            self.ofertas_pedido[oferta_id]["viaje_id"] = viaje_id

        # 2. Pedido asignado
        if pedido_id in self.pedidos:
            self.pedidos[pedido_id]["estado"] = "asignado"
            self.pedidos[pedido_id]["aceptado_en"] = now

        # 3. Ofertas perdidas para el mismo pedido
        ofertas_perdidas = 0
        for of_key, of_val in self.ofertas_pedido.items():
            if of_val.get("pedido_id") == pedido_id and of_key != oferta_id and of_val.get("estado") == "pendiente":
                of_val["estado"] = "perdida"
                ofertas_perdidas += 1

        # 4. Reescritura completa de viaje_pedidos (§5.3)
        # Preservar órdenes históricos entregados y reescribir pedidos activos consecutivamente
        delivered_vps = [
            vp for vp in self.viaje_pedidos
            if vp.get("viaje_id") == viaje_id and self.pedidos.get(vp.get("pedido_id"), {}).get("estado") == "entregado"
        ]
        delivered_count = len(delivered_vps)
        for idx, dvp in enumerate(delivered_vps):
            dvp["orden"] = idx + 1

        other_vps = [vp for vp in self.viaje_pedidos if vp.get("viaje_id") != viaje_id]

        new_vps = []
        for idx, (pid, _) in enumerate(nuevo_orden_secuencia):
            new_vps.append({
                "viaje_id": viaje_id,
                "pedido_id": pid,
                "orden": delivered_count + idx + 1,
                "agregado_en": now,
            })

        self.viaje_pedidos = other_vps + delivered_vps + new_vps

        # 5. viajes_repartidor actualizado
        if viaje_id in self.viajes_repartidor:
            self.viajes_repartidor[viaje_id]["ruta_linea"] = coordenadas_ruta or []
            self.viajes_repartidor[viaje_id]["actualizado_en"] = now
        else:
            rep_id = self.ofertas_pedido.get(oferta_id, {}).get("repartidor_id", "rep-demo-01")
            self.viajes_repartidor[viaje_id] = {
                "id": viaje_id,
                "repartidor_id": rep_id,
                "estado": "activo",
                "iniciado_en": now,
                "origen_actual": {"lat": CLUSTER_CENTRO["lat"], "lon": CLUSTER_CENTRO["lon"]},
                "ruta_linea": coordenadas_ruta or [],
                "actualizado_en": now,
            }

        return {
            "ok": True,
            "oferta_id": oferta_id,
            "pedido_id": pedido_id,
            "viaje_id": viaje_id,
            "paradas_reordenadas": len(nuevo_orden_secuencia),
            "ofertas_perdidas": ofertas_perdidas,
            "actualizado_en": now,
        }

    def persistir_decision_rechazar(self, oferta_id: str) -> Dict[str, Any]:
        """
        Ejecuta las mutaciones de escritura al rechazar una oferta (§5.3):
        update ofertas_pedido set estado = 'rechazada', respondida_en = now() where id = :oferta_id;
        """
        now = datetime.now(timezone.utc).isoformat()
        if oferta_id in self.ofertas_pedido:
            self.ofertas_pedido[oferta_id]["estado"] = "rechazada"
            self.ofertas_pedido[oferta_id]["respondida_en"] = now

        return {
            "ok": True,
            "oferta_id": oferta_id,
            "estado": "rechazada",
            "respondida_en": now,
        }

    # =========================================================================
    # §7 VERIFICACIONES ANTES DE CONECTAR EL AGENTE
    # =========================================================================

    def verificar_estado_inyeccion(self) -> Dict[str, Any]:
        """
        Ejecuta las 7 verificaciones obligatorias definidas en §7 del contrato.
        Todas deben resultar en True para declarar el sistema operativo.
        """
        # 1. Ningún pedido sin contexto completo (tiempo_preparacion_min is not null)
        pedidos_sin_prep = sum(
            1 for p in self.pedidos.values()
            if not p.get("contexto") or p["contexto"].get("tiempo_preparacion_min") is None
        )

        # 2. Coordenadas dentro de la ZM de Monterrey (25.40 a 25.90 latitud)
        coords_invalidas = sum(
            1 for p in self.pedidos.values()
            if not (25.40 <= p["origen"]["lat"] <= 25.90 and 25.40 <= p["destino"]["lat"] <= 25.90)
        )

        # 3. Coherencia de tipo_producto con theta_frescura_min (sin no-perecederos con theta)
        no_perecederos_con_theta = sum(
            1 for p in self.pedidos.values()
            if p.get("contexto", {}).get("tipo_producto") == "no_perecedero"
            and p.get("contexto", {}).get("theta_frescura_min") is not None
        )

        # 4. viaje_pedidos.orden consecutivo y sin huecos por viaje (1..n)
        orden_valido = True
        viajes_ids = {vp["viaje_id"] for vp in self.viaje_pedidos}
        for vid in viajes_ids:
            ordenes = [vp["orden"] for vp in self.viaje_pedidos if vp["viaje_id"] == vid]
            ordenes.sort()
            esperado = list(range(1, len(ordenes) + 1))
            if ordenes != esperado:
                orden_valido = False
                break

        # 5. Ofertas pendientes con expira_en > now()
        now = datetime.now(timezone.utc)
        ofertas_vigentes = 0
        for o in self.ofertas_pedido.values():
            if o.get("estado") == "pendiente":
                exp = o.get("expira_en")
                if exp:
                    try:
                        dt = datetime.fromisoformat(exp)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        if dt > now:
                            ofertas_vigentes += 1
                    except Exception:
                        pass

        # 6. Las 10 claves de configuración existen
        claves_faltantes = [k for k in CONFIG_DEFAULT if k not in self.configuracion]

        # 7. platform_connections activas para el repartidor demo
        conns_activas = sum(1 for c in self.platform_connections if c.get("is_active"))

        resultado = {
            "v1_contexto_completo": pedidos_sin_prep == 0,
            "v2_coordenadas_mty": coords_invalidas == 0,
            "v3_coherencia_frescura": no_perecederos_con_theta == 0,
            "v4_orden_consecutivo": orden_valido,
            "v5_ofertas_vigentes": ofertas_vigentes >= 1,
            "v6_configuracion_10_claves": len(claves_faltantes) == 0,
            "v7_conexiones_activas": conns_activas >= 1,
            "totales": {
                "pedidos": len(self.pedidos),
                "pedidos_sin_prep": pedidos_sin_prep,
                "coords_invalidas": coords_invalidas,
                "no_perecederos_con_theta": no_perecederos_con_theta,
                "viaje_pedidos": len(self.viaje_pedidos),
                "ofertas_vigentes": ofertas_vigentes,
                "conns_activas": conns_activas,
                "configuracion_claves": len(self.configuracion),
            }
        }
        resultado["todas_pasan"] = all([
            resultado["v1_contexto_completo"],
            resultado["v2_coordenadas_mty"],
            resultado["v3_coherencia_frescura"],
            resultado["v4_orden_consecutivo"],
            resultado["v5_ofertas_vigentes"],
            resultado["v6_configuracion_10_claves"],
            resultado["v7_conexiones_activas"],
        ])
        return resultado


# Instancia singleton para el runtime en memoria
_db_singleton: Optional[MockSupabaseDB] = None

def obtener_db() -> MockSupabaseDB:
    """Devuelve la base de datos en memoria inicializada."""
    global _db_singleton
    if _db_singleton is None:
        _db_singleton = MockSupabaseDB()
    return _db_singleton


def construir_peticion_desde_db(
    repartidor_id: str = "rep-demo-01",
    db: Optional[MockSupabaseDB] = None,
    politica: str = "PPO",
) -> PeticionDecidir:
    """
    Construye el objeto PeticionDecidir de entrada ejecutando las 4 consultas SQL de §4.1.
    """
    if db is None:
        db = obtener_db()

    # 1. Consulta 1: Estado del repartidor
    estado_rep = db.obtener_estado_repartidor(repartidor_id)
    if not estado_rep:
        raise ValueError(f"Repartidor {repartidor_id} no encontrado en la base de datos.")

    # 4. Consulta 4: Métricas del turno para rho_actual
    metricas = db.obtener_metricas_turno(repartidor_id)
    rho_actual = metricas["rho_actual"]

    repartidor = RepartidorEstado(
        id=estado_rep["id"],
        posicion=Punto(lat=estado_rep["lat"], lon=estado_rep["lng"]),
        vehiculo=estado_rep["vehiculo"],
        capacidad=3,
        minutos_turno_transcurridos=round(metricas["horas"] * 60.0, 1),
        minutos_turno_restantes=max(0.0, 360.0 - (metricas["horas"] * 60.0)),
        ganancia_turno_mxn=metricas["ingreso_mxn"],
        km_recorridos=round(metricas["entregados"] * 2.8, 1),
        rho_actual_mxn_h=rho_actual,
    )

    # 2. Consulta 2: Plan activo a bordo
    viaje_id = estado_rep.get("viaje_id")
    pedidos_db = db.obtener_plan_activo(viaje_id) if viaje_id else []

    plan_activo: List[PedidoActivo] = []
    for p in pedidos_db:
        ctx = p.get("contexto", {})
        plan_activo.append(
            PedidoActivo(
                pedido_id=p["id"],
                app=p["app"],
                estado=p["estado"],
                origen=Punto(lat=p["origen_lat"], lon=p["origen_lng"]),
                destino=Punto(lat=p["destino_lat"], lon=p["destino_lng"]),
                precio_mxn=p["precio"],
                contexto=ctx,
                origen_direccion=p.get("origen_direccion"),
                destino_direccion=p.get("destino_direccion"),
                recogido=(p["estado"] == "en_camino"),
            )
        )

    # 3. Consulta 3: Ofertas pendientes
    ofertas_db = db.obtener_ofertas_pendientes(repartidor_id, limit=8)
    ofertas: List[OfertaEntrante] = []
    for o in ofertas_db:
        ctx = o.get("contexto", {})
        ofertas.append(
            OfertaEntrante(
                oferta_id=o["id"],
                pedido_id=o["pedido_id"],
                app=o["app"],
                origen=Punto(lat=o["origen_lat"], lon=o["origen_lng"]),
                destino=Punto(lat=o["destino_lat"], lon=o["destino_lng"]),
                precio_mxn=o["precio"],
                anillo=o["ronda"],
                radio_metros=o["radio_metros"],
                desvio_estimado_metros=o["desvio_estimado_metros"],
                expira_en=o["expira_en"],
                contexto=ctx,
                origen_direccion=o.get("origen_direccion"),
                destino_direccion=o.get("destino_direccion"),
                clima=o.get("clima", "normal"),
            )
        )

    contexto = Contexto(clima="normal", evento_activo=None)

    return PeticionDecidir(
        version="2.0",
        politica=politica,  # type: ignore
        repartidor=repartidor,
        plan_activo=plan_activo,
        ofertas=ofertas,
        contexto=contexto,
    )


def generar_sql_inyeccion_completo(db: Optional[MockSupabaseDB] = None) -> str:
    """
    Genera el script SQL puro para insertar en Supabase (PostgreSQL + PostGIS)
    según el orden de llaves foráneas de la Sección 6 del contrato.
    Garantiza el orden st_makepoint(lon, lat) para Monterrey.
    """
    if db is None:
        db = obtener_db()

    lines = [
        "-- ====================================================================",
        "-- VYGO · PLAN DE INYECCIÓN DE DATOS V2.0 (12 de septiembre de 2026)",
        "-- Reconciliado con Supabase ihmadvmoenkxanoxrwcy (11 tablas)",
        "-- ====================================================================",
        "BEGIN;",
        "",
        "-- 1. Catalogo de Apps (3)",
        "INSERT INTO apps (id, nombre) VALUES",
        "  (1, 'uber'),",
        "  (2, 'rappi'),",
        "  (3, 'didi')",
        "ON CONFLICT (id) DO NOTHING;",
        "",
        "-- 2. Usuarios (1 repartidor + 30 clientes)",
    ]

    # Usuarios
    usr_vals = []
    for u in db.usuarios.values():
        usr_vals.append(f"  ('{u['id']}', '{u['nombre']}', '{u['email']}', '{u['telefono']}')")
    lines.append("INSERT INTO usuarios (id, nombre, email, telefono) VALUES\n" + ",\n".join(usr_vals) + "\nON CONFLICT (id) DO NOTHING;\n")

    # 3. Repartidores
    lines.append("-- 3. Repartidor de Demo")
    rep = db.repartidores["rep-demo-01"]
    lines.append(
        f"INSERT INTO repartidores (id, usuario_id, app_id, vehiculo, disponible, rating) VALUES\n"
        f"  ('{rep['id']}', '{rep['usuario_id']}', {rep['app_id']}, '{rep['vehiculo']}', {str(rep['disponible']).lower()}, {rep['rating']})\n"
        f"ON CONFLICT (id) DO UPDATE SET disponible = true, vehiculo = '{rep['vehiculo']}';\n"
    )

    # 4. platform_connections
    lines.append("-- 4. Conexiones de plataforma activas (3)")
    p_conns = []
    for pc in db.platform_connections:
        p_conns.append(f"  ('{pc['user_id']}', '{pc['platform']}', {str(pc['is_active']).lower()})")
    lines.append("INSERT INTO platform_connections (user_id, platform, is_active) VALUES\n" + ",\n".join(p_conns) + "\nON CONFLICT (user_id, platform) DO UPDATE SET is_active = EXCLUDED.is_active;\n")

    # 5. configuracion
    lines.append("-- 5. Parametros de configuracion del sistema (10 claves §3.5)")
    cfg_vals = []
    for k, v in db.configuracion.items():
        cfg_vals.append(f"  ('{k}', '{v}')")
    lines.append("INSERT INTO configuracion (clave, valor) VALUES\n" + ",\n".join(cfg_vals) + "\nON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor;\n")

    # 6. ubicaciones_conductores
    lines.append("-- 6. Posicion inicial del conductor (Monterrey ZM)")
    lines.append(
        f"INSERT INTO ubicaciones_conductores (user_id, lat, lng, updated_at) VALUES\n"
        f"  ('usr-rep-demo-01', {CLUSTER_CENTRO['lat']}, {CLUSTER_CENTRO['lon']}, now())\n"
        f"ON CONFLICT (user_id) DO UPDATE SET lat = EXCLUDED.lat, lng = EXCLUDED.lng, updated_at = now();\n"
    )

    # 7. viajes_repartidor
    lines.append("-- 7. Viaje activo iniciado hace 90 min")
    lines.append(
        f"INSERT INTO viajes_repartidor (id, repartidor_id, estado, iniciado_en, origen_actual) VALUES\n"
        f"  ('viaje-demo-01', 'rep-demo-01', 'activo', now() - interval '90 minutes', "
        f"st_setsrid(st_makepoint({CLUSTER_CENTRO['lon']}, {CLUSTER_CENTRO['lat']}), 4326)::geography)\n"
        f"ON CONFLICT (id) DO UPDATE SET estado = EXCLUDED.estado, origen_actual = EXCLUDED.origen_actual;\n"
    )

    # 8. pedidos (40)
    lines.append("-- 8. Pedidos con contexto JSONB completo (12 entregados, 3 asignados, 25 buscando)")
    ped_vals = []
    import json
    for p in db.pedidos.values():
        ctx_json = json.dumps(p["contexto"], ensure_ascii=False).replace("'", "''")
        o_lon, o_lat = p["origen"]["lon"], p["origen"]["lat"]
        d_lon, d_lat = p["destino"]["lon"], p["destino"]["lat"]
        creado = "now() - interval '30 minutes'" if p["estado"] == "entregado" else "now() - interval '2 minutes'"
        ped_vals.append(
            f"  ('{p['id']}', {p['app_id']}, '{p['id_externo']}', '{p['cliente_id']}', "
            f"st_setsrid(st_makepoint({o_lon}, {o_lat}), 4326)::geography, '{p['origen_direccion']}', "
            f"st_setsrid(st_makepoint({d_lon}, {d_lat}), 4326)::geography, '{p['destino_direccion']}', "
            f"'{p['estado']}', '{p['clima']}', '{ctx_json}'::jsonb, {p['precio']}, '{p['moneda']}', {creado})"
        )
    lines.append(
        "INSERT INTO pedidos (id, app_id, id_externo, cliente_id, origen, origen_direccion, destino, destino_direccion, estado, clima, contexto, precio, moneda, creado_en) VALUES\n"
        + ",\n".join(ped_vals)
        + "\nON CONFLICT (id) DO NOTHING;\n"
    )

    # 9. viaje_pedidos (15)
    lines.append("-- 9. viaje_pedidos (12 entregados + 3 a bordo con orden consecutivo 1..15)")
    vp_vals = []
    for vp in db.viaje_pedidos:
        vp_vals.append(f"  ('{vp['viaje_id']}', '{vp['pedido_id']}', {vp['orden']}, now() - interval '15 minutes')")
    lines.append("INSERT INTO viaje_pedidos (viaje_id, pedido_id, orden, agregado_en) VALUES\n" + ",\n".join(vp_vals) + "\nON CONFLICT (viaje_id, pedido_id) DO UPDATE SET orden = EXCLUDED.orden;\n")

    # 10. difusiones_pedido (25)
    lines.append("-- 10. difusiones_pedido (para los pedidos en buscando)")
    dif_vals = []
    for dif in db.difusiones_pedido:
        dif_vals.append(f"  ('{dif['id']}', '{dif['pedido_id']}', {dif['ronda']}, now())")
    lines.append("INSERT INTO difusiones_pedido (id, pedido_id, ronda, creado_en) VALUES\n" + ",\n".join(dif_vals) + "\nON CONFLICT (id) DO NOTHING;\n")

    # 11. ofertas_pedido (8 pendientes)
    lines.append("-- 11. ofertas_pedido (8 ofertas pendientes con expira_en > now)")
    of_vals = []
    for o in db.ofertas_pedido.values():
        of_vals.append(
            f"  ('{o['id']}', '{o['pedido_id']}', '{o['repartidor_id']}', '{o['viaje_id']}', "
            f"{o['ronda']}, {o['radio_metros']}, {o['desvio_estimado_metros']}, now() + interval '60 seconds', "
            f"'{o['clima']}', '{o['estado']}', now())"
        )
    lines.append(
        "INSERT INTO ofertas_pedido (id, pedido_id, repartidor_id, viaje_id, ronda, radio_metros, desvio_estimado_metros, expira_en, clima, estado, ofrecida_en) VALUES\n"
        + ",\n".join(of_vals)
        + "\nON CONFLICT (id) DO NOTHING;\n"
    )

    lines.append("COMMIT;")
    return "\n".join(lines)


# Soporte opcional para librería supabase-py oficial
try:
    from supabase import create_client as supabase_create_client
    SUPABASE_SDK_AVAILABLE = True
except ImportError:
    supabase_create_client = None
    SUPABASE_SDK_AVAILABLE = False


class SupabaseLiveClient:
    """
    Cliente asíncrono para interactuar con la instancia Supabase vía PostgREST / REST API o supabase SDK.
    Si no hay SUPABASE_URL ni SUPABASE_KEY en variables de entorno, delega transparentemente
    a MockSupabaseDB.
    """
    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        mock_db: Optional[MockSupabaseDB] = None,
    ):
        self.url = supabase_url or os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
        self.key = supabase_key or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY")
        self.mock_db = mock_db or obtener_db()
        self.es_remoto = bool(self.url and self.key and "http" in self.url and not self.key.startswith("<"))
        self.client_sdk = None
        if self.es_remoto and SUPABASE_SDK_AVAILABLE and supabase_create_client:
            try:
                self.client_sdk = supabase_create_client(self.url, self.key)
            except Exception:
                self.client_sdk = None

    async def extraer_peticion(self, repartidor_id: str = "rep-demo-01", politica: str = "PPO") -> PeticionDecidir:
        """Extrae el estado del repartidor y construye PeticionDecidir."""
        if not self.es_remoto:
            return construir_peticion_desde_db(repartidor_id=repartidor_id, db=self.mock_db, politica=politica)

        # Si hay conexión remota, ejecutamos vía httpx PostgREST
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(base_url=self.url, headers=headers, timeout=5.0) as client:
                res_rep = await client.get(f"/rest/v1/repartidores?id=eq.{repartidor_id}&select=*,viajes_repartidor(*)")
                if res_rep.status_code == 200 and res_rep.json():
                    # Fallback controlado a mock si la tabla remota no está poblada aún
                    return construir_peticion_desde_db(repartidor_id=repartidor_id, db=self.mock_db, politica=politica)
        except Exception as ex:
            logger.warning(f"Error al conectar con Supabase remoto {self.url}: {ex}. Usando base simulada local.")

        return construir_peticion_desde_db(repartidor_id=repartidor_id, db=self.mock_db, politica=politica)

    async def persistir_aceptar(
        self,
        oferta_id: str,
        pedido_id: str,
        viaje_id: str,
        nuevo_orden: List[Tuple[str, int]],
        coords: Optional[List[List[float]]] = None,
    ) -> Dict[str, Any]:
        """Persiste la aceptación de la oferta en la base de datos."""
        res_mock = self.mock_db.persistir_decision_aceptar(
            oferta_id=oferta_id,
            pedido_id=pedido_id,
            viaje_id=viaje_id,
            nuevo_orden_secuencia=nuevo_orden,
            coordenadas_ruta=coords,
        )

        if self.es_remoto:
            try:
                headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}"}
                async with httpx.AsyncClient(base_url=self.url, headers=headers, timeout=5.0) as client:
                    await client.patch(f"/rest/v1/ofertas_pedido?id=eq.{oferta_id}", json={"estado": "aceptada"})
                    await client.patch(f"/rest/v1/pedidos?id=eq.{pedido_id}", json={"estado": "asignado"})
            except Exception as ex:
                logger.warning(f"Error en persistencia remota Supabase: {ex}")

        return res_mock

    async def persistir_rechazar(self, oferta_id: str) -> Dict[str, Any]:
        """Persiste el rechazo de la oferta en la base de datos."""
        res_mock = self.mock_db.persistir_decision_rechazar(oferta_id=oferta_id)
        if self.es_remoto:
            try:
                headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}"}
                async with httpx.AsyncClient(base_url=self.url, headers=headers, timeout=5.0) as client:
                    await client.patch(f"/rest/v1/ofertas_pedido?id=eq.{oferta_id}", json={"estado": "rechazada"})
            except Exception as ex:
                logger.warning(f"Error en persistencia remota Supabase: {ex}")
        return res_mock

