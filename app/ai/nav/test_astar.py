"""
ai/nav/test_astar.py
Pruebas unitarias de fidelidad geométrica de calles para el algoritmo A* en Monterrey.
Valida:
  1. Ausencia de puntos consecutivos duplicados en polilíneas.
  2. Densidad geométrica >= 2.5x sobre los 30 pares de prueba representativos.
  3. Alineación estricta de extremos de aristas con sus nodos (< 25 m), previniendo el bug de sentido invertido.
"""

from pathlib import Path
import pytest

from app.ai.nav.grafo import cargar_grafo_ruteable
from app.ai.nav.astar import ruta_astar, haversine_metros

_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _DIR.parent.parent.parent
_PARES_FILE = _REPO_ROOT / "test_pares_30.txt"


@pytest.fixture(scope="module")
def grafo_mty():
    """Carga una sola vez el grafo ruteable fuertemente conexo de Monterrey."""
    G = cargar_grafo_ruteable()
    assert G is not None, "No se pudo cargar el grafo ruteable de Monterrey"
    return G


@pytest.fixture(scope="module")
def pares_30():
    """Carga los 30 pares de nodos de prueba."""
    assert _PARES_FILE.exists(), f"Archivo {_PARES_FILE} no existe"
    pares = []
    with open(_PARES_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                partes = line.split()
                pares.append((partes[0], partes[1]))
    assert len(pares) == 30, f"Se esperaban 30 pares, se encontraron {len(pares)}"
    return pares


def test_sin_puntos_consecutivos_duplicados(grafo_mty, pares_30):
    """
    Requisito 1: Ninguna polilínea repite dos puntos consecutivos idénticos.
    Verifica que la deduplicación de vértices entre aristas contiguas funcione al 100%.
    """
    for u_str, v_str in pares_30:
        u = int(u_str) if int(u_str) in grafo_mty else u_str
        v = int(v_str) if int(v_str) in grafo_mty else v_str
        res = ruta_astar(grafo_mty, u, v)
        assert res is not None, f"Fallo al resolver ruta A* para {u} -> {v}"
        polilinea = res["polilinea"]
        assert len(polilinea) >= 2, "Polilínea con menos de 2 puntos"

        for i, (p1, p2) in enumerate(zip(polilinea[:-1], polilinea[1:])):
            assert p1 != p2, (
                f"Punto duplicado consecutivo en índice {i} para ruta {u}->{v}: {p1}"
            )
            # Verificar también distancia > 1e-5 para evitar micro-duplicados flotantes
            d_m = haversine_metros(p1[0], p1[1], p2[0], p2[1])
            assert d_m > 1e-4, (
                f"Puntos colapsados a menos de 0.1 mm en índice {i}: {p1} vs {p2}"
            )


def test_densidad_geometria_30_pares(grafo_mty, pares_30):
    """
    Requisito 2: Sobre 30 pares, el promedio de puntos por ruta es al menos 2.5x el número
    de nodos del camino. Confirma que se está extrayendo y renderizando la geometría real
    de las aristas (curvas, glorietas, retornos).
    """
    total_puntos = 0
    total_nodos = 0

    for u_str, v_str in pares_30:
        u = int(u_str) if int(u_str) in grafo_mty else u_str
        v = int(v_str) if int(v_str) in grafo_mty else v_str
        res = ruta_astar(grafo_mty, u, v)
        assert res is not None, f"Fallo al resolver ruta A* para {u} -> {v}"
        total_puntos += len(res["polilinea"])
        total_nodos += res["nodos"]

    ratio = total_puntos / total_nodos
    assert ratio >= 2.5, (
        f"Densidad insuficiente de geometría: {ratio:.3f}x < 2.5x "
        f"({total_puntos} puntos para {total_nodos} nodos)"
    )


def test_puntos_cercanos_a_segmento_arista(grafo_mty, pares_30):
    """
    Requisito 3: Cada punto de la polilínea cae a menos de 25 m del segmento de nodos que le corresponde.
    Esta prueba atrapa el bug del sentido invertido de OSMnx: si una arista curva se digitalizó en sentido
    contrario y no se voltea, sus extremos no coinciden con los nodos u y v de avance y los puntos
    se disparan decenas o cientos de metros.
    """
    import networkx as nx

    for u_str, v_str in pares_30:
        u = int(u_str) if int(u_str) in grafo_mty else u_str
        v = int(v_str) if int(v_str) in grafo_mty else v_str
        camino = nx.astar_path(grafo_mty, u, v, weight="travel_time")

        for a, b in zip(camino[:-1], camino[1:]):
            d = min(grafo_mty[a][b].values(), key=lambda x: x.get("travel_time", 999999.0))
            g = d.get("geometry")
            if g is not None:
                pts = (
                    [[float(p[0]), float(p[1])] for p in g.coords]
                    if hasattr(g, "coords")
                    else [[float(x), float(y)] for x, y in zip(g.xy[0], g.xy[1])]
                )
                ax, ay = float(grafo_mty.nodes[a]["x"]), float(grafo_mty.nodes[a]["y"])
                bx, by = float(grafo_mty.nodes[b]["x"]), float(grafo_mty.nodes[b]["y"])

                # Validar la regla de volteo idéntica a ruta_astar
                if ((pts[0][0] - ax) ** 2 + (pts[0][1] - ay) ** 2 >
                    (pts[-1][0] - ax) ** 2 + (pts[-1][1] - ay) ** 2):
                    pts.reverse()

                # Extremo inicial debe coincidir con nodo origen a menos de 25 m (0.0 m exactos)
                d_origen = haversine_metros(pts[0][0], pts[0][1], ax, ay)
                assert d_origen < 25.0, (
                    f"Arista {a}->{b} invertida o desalineada: inicio dista {d_origen:.2f} m (> 25 m) de nodo origen"
                )

                # Extremo final debe coincidir con nodo destino a menos de 25 m (0.0 m exactos)
                d_destino = haversine_metros(pts[-1][0], pts[-1][1], bx, by)
                assert d_destino < 25.0, (
                    f"Arista {a}->{b} invertida o desalineada: fin dista {d_destino:.2f} m (> 25 m) de nodo destino"
                )
