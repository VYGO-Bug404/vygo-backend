# Reporte de Demo y Diagnóstico de Ruteo A*

## Observaciones de Diagnóstico (Compuerta B)

### 1. Factor de Desvío en Tramo Obispado -> Fundidora (1.81x)
- **Métrica observada**: Distancia en línea recta: 6.2 km vs. Distancia en red vial A*: 11.3 km (factor de desvío = 1.81).
- **Contexto urbano típico**: En Monterrey el factor de desvío habitual es 1.2 - 1.4.
- **Hipótesis técnica**: El mirador del Obispado se ubica a ~1.3 km del borde oeste del BBOX actual del grafo (`-100.360`). Al truncarse el grafo en ese límite occidental, A* se ve forzado a rodear por calles interiores para incorporarse a vías troncales en dirección este hacia Fundidora.
- **Acción**: Verificar visualmente la geometría del tramo en el mapa interactivo del frontend (Parte C). Si se confirma que la ruta realiza una vuelta pronunciada cerca del límite del BBOX, la solución será ampliar el BBOX hacia el poniente, preservando intacto el algoritmo A*.

### 2. Velocidades Imputadas y Estimación de Tiempos (ETAs)
- **Métrica observada**: El tramo Obispado -> Fundidora promedia 67 km/h (11.3 km en 607.9 s).
- **Causa**: Proviene de las velocidades asignadas por categoría de vía en OSMnx (`speed_kph` de vías rápidas como Constitución / Morones Prieto).
- **Nota operativa**: Los ETAs representan condiciones de flujo libre y serán optimistas en arterias principales hasta que se incorpore modulación por tráfico en tiempo real.
