import pytest
from pydantic import ValidationError

from app.core.schemas import (
    Punto,
    PeticionDecidir,
    RespuestaDecidir,
    RepartidorEstado,
    PedidoActivo,
    OfertaEntrante,
    Plan,
    Geometria,
    ResumenPlan,
    Telemetria,
    Economia,
    Riesgo,
    DecisionOferta,
    Parada,
)

def test_punto_coordenadas_monterrey_validas():
    # Coordenadas válidas en Macroplaza Monterrey
    p = Punto(lat=25.6714, lon=-100.3094)
    assert p.lat == 25.6714
    assert p.lon == -100.3094

def test_punto_coordenadas_invertidas_falla():
    # Coordenadas invertidas (lon en lat y lat en lon) deben disparar error
    with pytest.raises(ValidationError) as exc:
        Punto(lat=-100.3094, lon=25.6714)
    assert "fuera de la Zona Metropolitana de Monterrey" in str(exc.value)

def test_punto_coordenadas_fuera_de_zona_falla():
    # Ciudad de México o Madrid
    with pytest.raises(ValidationError):
        Punto(lat=19.4326, lon=-99.1332)
    with pytest.raises(ValidationError):
        Punto(lat=40.4168, lon=-3.7038)

def test_geometria_orden_geojson_lon_lat():
    # GeoJSON exige [lon, lat]
    coords = [[-100.3094, 25.6714], [-100.3155, 25.6801]]
    geom = Geometria(coordinates=coords)
    assert geom.type == "LineString"
    assert geom.coordinates[0][0] == -100.3094 # Lon primero
    assert geom.coordinates[0][1] == 25.6714  # Lat segundo

def test_peticion_decidir_contrato_valido():
    peticion = PeticionDecidir(
        version="1.0",
        repartidor=RepartidorEstado(
            id="rep-123",
            posicion=Punto(lat=25.67, lon=-100.31),
            capacidad=2,
            minutos_turno_transcurridos=60,
            minutos_turno_restantes=300,
            ganancia_turno_mxn=150.0,
            km_recorridos=12.0,
            rho_actual_mxn_h=150.0,
        ),
        plan_activo=[
            PedidoActivo(
                pedido_id="ped-1",
                app="uber",
                origen=Punto(lat=25.68, lon=-100.32),
                destino=Punto(lat=25.66, lon=-100.29),
            )
        ],
        ofertas=[
            OfertaEntrante(
                oferta_id="of-1",
                pedido_id="ped-2",
                app="rappi",
                origen=Punto(lat=25.679, lon=-100.314),
                destino=Punto(lat=25.661, lon=-100.291),
                precio_mxn=60.0,
            )
        ],
    )
    assert peticion.version == "1.0"
    assert len(peticion.plan_activo) == 1
    assert len(peticion.ofertas) == 1

def test_respuesta_decidir_metricas_explicabilidad():
    resp = RespuestaDecidir(
        version="1.0",
        generado_en="2026-09-12T14:00:00-06:00",
        politica="agente_ppo",
        latencia_ms=12.4,
        decisiones=[
            DecisionOferta(
                oferta_id="of-1",
                pedido_id="ped-2",
                app="rappi",
                decision="aceptar",
                prioridad=1,
                confianza=0.92,
                economia=Economia(
                    tarifa_mxn=62.0,
                    delta_tiempo_min=18.0,
                    delta_distancia_km=3.5,
                    costo_marginal_mxn=10.0,
                    ganancia_neta_mxn=52.0,
                    tasa_marginal_mxn_h=173.3,
                    rho_actual_mxn_h=140.0,
                    ajuste_aprendido_mxn_h=15.0,
                    umbral_superado=True,
                ),
                riesgo=Riesgo(
                    holgura_frescura_min=10.0,
                    holgura_limite_min=15.0,
                    prob_entrega_a_tiempo=0.95,
                    p_gana=0.70,
                    anillo=1,
                ),
                factible=True,
                motivo_infactible=None,
                explicacion_corta="+$173/h vs tu $140/h",
                explicacion="Acepta oferta con ganancia neta superior al umbral.",
            )
        ],
        plan=Plan(
            viaje_id="viaje-01",
            paradas=[],
            geometria=Geometria(coordinates=[[-100.31, 25.67]]),
            resumen=ResumenPlan(
                paradas_totales=2,
                pedidos_a_bordo=1,
                distancia_km=3.5,
                duracion_min=18.0,
                ingreso_mxn=62.0,
                costo_mxn=10.0,
                tasa_proyectada_mxn_h=173.3,
                optimo_exacto=True,
                secuencias_evaluadas=1,
            ),
        ),
        telemetria=Telemetria(
            rho_actual_mxn_h=140.0,
            ganancia_turno_mxn=150.0,
            pedidos_entregados=3,
            puntualidad=0.95,
            km_por_pedido=4.0,
            factor_agrupamiento=1.5,
            utilizacion=0.75,
        ),
        alertas=[],
        evento_activo=None,
    )

    data = resp.model_dump()
    dec = data["decisiones"][0]
    assert "tasa_marginal_mxn_h" in dec["economia"]
    assert "rho_actual_mxn_h" in dec["economia"]
    assert "ajuste_aprendido_mxn_h" in dec["economia"]
    assert dec["decision"] in ["aceptar", "rechazar"]
