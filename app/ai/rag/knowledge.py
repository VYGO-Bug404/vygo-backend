"""
app.ai.rag.knowledge
Base de conocimiento estructurada y recuperable para el Copiloto de IA de Vygo.
Cubre dinámicas gastronómicas de Monterrey, tiempos de cocina, zonas de estacionamiento y reglas multi-app.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class DocumentoConocimiento:
    id: str
    categoria: str  # "restaurante", "zona", "plataforma", "estrategia"
    clave: str      # ej. "sushi_roll_centro", "centro", "uber", "multiapp"
    titulo: str
    contenido: str
    tags: List[str]


BASE_CONOCIMIENTO: List[DocumentoConocimiento] = [
    # --- Zonas de Monterrey ---
    DocumentoConocimiento(
        id="zona-centro",
        categoria="zona",
        clave="centro",
        titulo="Dinámica de entrega en Monterrey Centro y Barrio Antiguo",
        contenido=(
            "Centro y Barrio Antiguo tienen alta densidad de pedidos pero calles angostas con sentidos únicos estrictos "
            "(Pino Suárez, Cuauhtémoc, Zaragoza). Estacionamiento difícil para autos; las motos tienen ventaja de 4.5 minutos "
            "por parada si usan aceras peatonales de Macroplaza o cajones de batería en Morelos. Tráfico moderado salvo horas pico."
        ),
        tags=["centro", "barrio antiguo", "macroplaza", "estacionamiento", "sentidos unicos"]
    ),
    DocumentoConocimiento(
        id="zona-san-pedro",
        categoria="zona",
        clave="san_pedro",
        titulo="Dinámica de entrega en San Pedro / Del Valle",
        contenido=(
            "San Pedro Garza García tiene el ticket promedio más alto y propinas superiores ($12-$25 MXN). Corredores Vasconcelos "
            "y Calzada del Valle exigen respetar límites de velocidad. En plazas comerciales (Paseo San Pedro, Arboleda) el acceso "
            "al mostrador demora entre 4 y 6 minutos extra a pie. Muy rentable si se acoplan pedidos del mismo centro comercial."
        ),
        tags=["san pedro", "valle", "vasconcelos", "propina alta", "plazas comerciales"]
    ),
    DocumentoConocimiento(
        id="zona-cumbres",
        categoria="zona",
        clave="cumbres",
        titulo="Dinámica de entrega en Cumbres / Paseo de los Leones",
        contenido=(
            "Cumbres presenta pendientes pronunciadas que incrementan el consumo de combustible en moto en un 18%. Paseo de los "
            "Leones sufre cuellos de botella severos entre 18:00 y 20:30. Solo conviene acoplar pedidos si la recolección y entrega "
            "se mantienen sobre el mismo sector (hacia arriba o hacia abajo del cerro), evitando cruces transversales."
        ),
        tags=["cumbres", "leones", "pendientes", "gasolina", "trafico"]
    ),
    DocumentoConocimiento(
        id="zona-tec",
        categoria="zona",
        clave="tec",
        titulo="Dinámica de entrega en Zona Tec / Contry",
        contenido=(
            "Zona estudiantil con altísima rotación en almuerzos y cenas rápidas sobre Garza Sada y Alfonso Reyes. Clientes suelen "
            "demorar de 2 a 3 minutos en bajar de departamentos/torres. Las entregas en campus Tec tienen puntos de encuentro "
            "fijos (accesos peatonales). Ideal para apilar 2 o 3 órdenes de ticket medio con desvíos menores a 300 metros."
        ),
        tags=["tec", "garza sada", "contry", "estudiantes", "alta rotacion"]
    ),

    # --- Restaurantes Clave ---
    DocumentoConocimiento(
        id="rest-sushi-roll",
        categoria="restaurante",
        clave="sushi_roll",
        titulo="Sushi Roll (Centro / Sucursales)",
        contenido=(
            "Sushi Roll despacha en mostrador exclusivo para repartidores en 7 a 10 minutos. Empaques rectangulares sólidos que caben "
            "perfectamente en la base de la mochila térmica sin aplastar otros paquetes. Temperatura no_perecedera/fresca, lo que "
            "permite mayor margen de tiempo de entrega sin riesgo de enfriamiento."
        ),
        tags=["sushi roll", "sushi", "empaque solido", "rapido", "centro"]
    ),
    DocumentoConocimiento(
        id="rest-tacos-primo",
        categoria="restaurante",
        clave="tacos_el_primo",
        titulo="Tacos El Primo",
        contenido=(
            "Flujo ultrarrápido (4 a 7 min de cocina). Producto caliente que viaja en papel aluminio térmico. Tolerancia de frescura "
            "de 25 minutos. Si el pedido adicional retrasa la llegada más de 8 minutos, la comida puede humedecerse. Conviene acoplar "
            "solo si la siguiente parada es entrega directa."
        ),
        tags=["tacos el primo", "comida caliente", "rapido", "frescura", "centro"]
    ),
    DocumentoConocimiento(
        id="rest-bella-italia",
        categoria="restaurante",
        clave="la_bella_italia",
        titulo="La Bella Italia",
        contenido=(
            "Pizzas y pastas gourmet. Empaque amplio (caja plana de pizza) que requiere espacio horizontal en la mochila. Si ya llevas "
            "2 pedidos voluminosos, aceptar este pedido generará problemas de capacidad física. Tiempo de horno entre 12 y 15 min."
        ),
        tags=["bella italia", "pizza", "pasta", "volumen grande", "capacidad"]
    ),
    DocumentoConocimiento(
        id="rest-postreria-valle",
        categoria="restaurante",
        clave="la_postreria",
        titulo="La Postrería Valle",
        contenido=(
            "Repostería de lujo. Requiere manejo suave en moto para evitar deformaciones del postre. Clientes de San Pedro otorgan "
            "propinas de $15 a $35 pesos si la entrega llega intacta. Empaque pequeño, fácil de transportar junto a otros pedidos."
        ),
        tags=["postreria", "postres", "san pedro", "propina alta", "delicado"]
    ),

    # --- Políticas de Plataformas Multi-App ---
    DocumentoConocimiento(
        id="plat-uber",
        categoria="plataforma",
        clave="uber",
        titulo="Políticas operativas y penalizaciones en Uber Eats",
        contenido=(
            "Uber Eats no penaliza la tasa de aceptación: puedes rechazar pedidos entrantes sin riesgo de suspensión. Sin embargo, "
            "cancelar un pedido una vez recogido en el restaurante genera una alerta roja en la cuenta. Los tiempos estimados de Uber "
            "son holgados (toleran hasta 10 min de desvío sin alerta al cliente)."
        ),
        tags=["uber", "uber eats", "tasa aceptacion", "cancelacion", "tolerancia"]
    ),
    DocumentoConocimiento(
        id="plat-rappi",
        categoria="plataforma",
        clave="rappi",
        titulo="Políticas operativas y geocercas en Rappi",
        contenido=(
            "Rappi monitorea activamente el GPS del repartidor. Si te desvías más de 1.5 km en dirección opuesta a la entrega, la app "
            "envía notificación de '¿Tienes algún problema con tu pedido?'. Es seguro acoplar pedidos si el desvío es menor a 800m y "
            "avanzas en el mismo corredor geográfico."
        ),
        tags=["rappi", "gps", "desvio", "notificacion", "geocerca"]
    ),
    DocumentoConocimiento(
        id="plat-didi",
        categoria="plataforma",
        clave="didi",
        titulo="Estrategia y dinámica en DiDi Food",
        contenido=(
            "DiDi Food ofrece tarifas base competitivas en distancias cortas (menos de 3 km). Ideal como pedido secundario para "
            "'rellenar' una ruta activa de Uber o Rappi, sumando de $35 a $55 MXN adicionales con menos de 5 minutos de desvío total."
        ),
        tags=["didi", "didi food", "cortas distancias", "relleno de ruta", "complementario"]
    ),
    DocumentoConocimiento(
        id="estrat-bundle-vygo",
        categoria="estrategia",
        clave="bundle_vygo",
        titulo="Estrategia óptima de acoplamiento de Vygo",
        contenido=(
            "Vygo maximiza la tasa marginal horaria ($/h). La regla analítica de Bellman recomienda aceptar cuando la ganancia neta "
            "dividida entre el tiempo extra supera tu promedio de turno (rho_actual). Además, el ordenamiento óptimo de paradas con "
            "Held-Karp garantiza que el repartidor recoja todos los pedidos antes de salir a la autopista o vía rápida para entregar en cascada."
        ),
        tags=["estrategia", "vygo", "held karp", "tasa marginal", "acoplamiento"]
    ),
]


def _normalizar_texto(t: str) -> str:
    """Elimina acentos y puntuación para matching semántico tolerante."""
    import re
    import unicodedata
    t = unicodedata.normalize('NFKD', t).encode('ASCII', 'ignore').decode('utf-8')
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return t


def buscar_conocimiento(
    consulta: str = "",
    zona: str = "",
    restaurante: str = "",
    app: str = "",
    top_k: int = 3,
) -> List[DocumentoConocimiento]:
    """
    Recuperador (Retriever) semántico para el RAG.
    Clasifica y puntúa los documentos según coincidencia con la oferta y la consulta del repartidor.
    """
    terminos_clave = set()
    for texto in (consulta, zona, restaurante, app):
        if texto:
            limpio = _normalizar_texto(texto)
            terminos_clave.update(limpio.split())

    puntuaciones: List[tuple[float, DocumentoConocimiento]] = []

    for doc in BASE_CONOCIMIENTO:
        score = 0.0
        doc_norm = _normalizar_texto(f"{doc.clave} {doc.titulo} {doc.contenido} {' '.join(doc.tags)}")

        # Coincidencia directa de clave
        if zona and _normalizar_texto(zona) in _normalizar_texto(doc.clave):
            score += 3.0
        if restaurante and any(p in _normalizar_texto(doc.clave) for p in _normalizar_texto(restaurante).split() if len(p) >= 3):
            score += 4.0
        if app and _normalizar_texto(app) in _normalizar_texto(doc.clave):
            score += 3.0

        # Coincidencia con tags y contenido
        tags_norm = [_normalizar_texto(tag) for tag in doc.tags]
        for termino in terminos_clave:
            if len(termino) < 3:
                continue
            if any(termino in tag for tag in tags_norm):
                score += 2.5
            if termino in doc_norm:
                score += 1.0

        if score > 0:
            puntuaciones.append((score, doc))

    puntuaciones.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in puntuaciones[:top_k]]

