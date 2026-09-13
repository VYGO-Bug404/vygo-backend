# Reporte de Demo y Diagnóstico de Ruteo A*

## 1. Verificación del Recorte y Filtro Anti-Brincos (GPS Simulado)

> [!WARNING]
> **Condición de Prueba de Telemetría GPS**:
> La verificación del recorte progresivo de ruta (`turf.lineSlice`) y de los filtros anti-brincos en el frontend (`mapRouteController.ts`) se ejecutó **exclusivamente en entorno simulado** mediante `MockMap` y suites automatizadas con inyección sintética de coordenadas.
> **El filtro de 3 lecturas consecutivas (para desviaciones > 60 m) y el de 2 lecturas consecutivas (para llegada a parada < 40 m) NO ha sido probado aún con ruido estocástico de GPS urbano real.**
> En cañones urbanos de Monterrey (e.g. edificios altos en San Pedro / Centro, pasos a desnivel o túneles de la Loma Larga y Obispado), el rebote de señal (*multipath*) y la pérdida de fijación satelital podrían inducir falsos positivos de desvío si no se añade filtrado de Kalman o fusión con odometría del vehículo en producción.

---

## 2. Diagnóstico del Tramo Obispado -> Fundidora (Factor de Desvío 1.81x)

### Métricas Observadas
- **Distancia euclidiana (línea recta)**: 6.25 km.
- **Distancia en red vial A***: 11.31 km.
- **Factor de desvío**: **1.81** (esperado urbano típico en Monterrey: 1.2 – 1.4).
- **Velocidad promedio imputada**: 67 km/h (11.3 km en 607.9 s / 10.1 min).

### Hallazgo de la Inspección Visual y Topológica
Se evaluó si el desvío se originaba por el truncamiento del BBOX en su frontera poniente (`lon = -100.360`):
- **Coordenada más occidental alcanzada por A***: `lon = -100.34739` (a más de 1.3 km hacia el interior del BBOX).
- **Conclusión de frontera**: La ruta **no se acerca al borde del grafo**. La hipótesis de truncamiento por límite de BBOX queda **completamente descartada**.

### Explicación Geográfica y Vial
El desvío de 1.81x se explica 100% por la hidrografía y la red de pares viales unidireccionales de Monterrey:
1. **Descenso del Obispado**: Desde el Mirador (Cerro del Obispado), el descenso canaliza por calles locales interiores (Belisario Domínguez / Hidalgo) hacia el distribuidor de **Av. Venustiano Carranza**.
2. **Cruce Sur del Río Santa Catarina**: Venustiano Carranza cruza el río hacia el margen sur para incorporarse a **Av. Ignacio Morones Prieto**, la principal vía rápida unidireccional de poniente a oriente.
3. **Tránsito por Margen Sur**: El repartidor transita por Morones Prieto a alta velocidad (60–70 km/h) aprovechando el flujo libre continuo sin semáforos.
4. **Retorno al Margen Norte (Puente Guadalupe / Juárez)**: Debido a que Parque Fundidora se encuentra en el margen norte del río, el trazado debe cruzar de regreso hacia el norte a través del par vial de **Puente Guadalupe / Av. Benito Juárez**, permitiendo la incorporación a **Av. Constitución** y el acceso hacia el estacionamiento oriente de Fundidora.

El factor 1.81x no es una ineficiencia del algoritmo, sino el costo físico real de salvar la barrera geográfica del Río Santa Catarina a través de vías rápidas unidireccionales.

---

## 3. Velocidades Imputadas y Estimación de Tiempos (ETAs)
- Las velocidades calculadas por OSMnx (`speed_kph` de 60–80 km/h en Morones Prieto y Constitución) asumen flujo libre.
- **Nota operativa**: Mientras no se conecte una API de tráfico en tiempo real (Google Routes / TomTom / HERE) o multiplicadores históricos de congestión $\gamma_{\text{traf}}(t)$, los tiempos de viaje proyectados serán optimistas durante horas pico (08:00–09:30 y 18:00–20:00).

---

## 4. Desacoplamiento Arquitectónico: Navegación vs. Decisión

### 4.1 Navegación en Vivo (A* sobre Red Vial Real)
- **Estado**: **EN VIVO** (resuelto en runtime por el backend).
- **Servicio**: `POST /ruta` (`ai/api/ruta.py` montado en FastAPI).
- **Motor**: A* bidireccional sobre el grafo vial real de OpenStreetMap (Monterrey ZM, 14,690 nodos, heurística haversine / $v_{\max}$ admisible).
- **Desempeño verificado**: **71.3 ms totales** HTTP (**46.5 ms de cómputo en servidor**) para 4 tramos encadenados; 11.6 ms por consulta bajo caché LRU de 5,000 pares.
- **Consumo en Frontend**: El mapa interactivo recibe la geometría GeoJSON en orden `[lon, lat]` y el controlador local `mapRouteController.ts` proyecta la posición GPS del repartidor con `tolerance: 0`, recortando la línea localmente con `@turf/line-slice` **sin saturar la red con peticiones intermedias**.

### 4.2 Decisión (Geometría de Simulación)
- **Estado**: **GEOMETRÍA DE ENTORNO DE SIMULACIÓN**.
- **Servicio**: `POST /decidir` (`app/api/routes.py`).
- **Motor**: Matriz analítica de distancias Manhattan / sintéticas y velocidades de rejilla L0/L1 para la evaluación de inserción (`insertion.py`) y el filtro de factibilidad (`feasibility.py`).
- **Paso Futuro Crítico**: Integrar la matriz de costos y tiempos de la red vial real (OSMnx / L2) a la capa de decisión.
- **Advertencia Metodológica**: Cambiar la matriz de distancias a tiempos de calle reales modifica directamente la función de transición $T(s' \mid s, a)$ que el agente optimizó. **Adoptar la matriz vial en la decisión REQUIERE re-evaluar exhaustivamente los 30 escenarios de prueba (`scenarios/test_30.pkl`) antes de declarar victoria**, ya que las nuevas holguras de frescura y tiempos de viaje alterarán las tasas marginales calculadas.
