#!/usr/bin/env python3
"""
Script generador del replay pareado oficial (app/data/replay_12.json)
Cumple al 100% con el Contrato de Integración v1.0 para la demo del pitch.
"""
import os
import sys
import json
from pathlib import Path

# Agregar raíz del proyecto al path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from app.core.simulator import generar_replay_completo

def main():
    escenario_id = 12
    semilla = 10012
    print(f"Generando replay para escenario {escenario_id} (semilla {semilla})...")
    
    replay = generar_replay_completo(escenario_id=escenario_id, semilla=semilla)
    
    output_path = root_dir / "app" / "data" / f"replay_{escenario_id}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(replay, f, ensure_ascii=False, indent=2)
        
    print(f"Replay generado exitosamente en: {output_path}")
    print(f"Tamaño del archivo: {output_path.stat().st_size / 1024:.1f} KB")
    print("Resumen de pistas generadas:")
    for pista in replay["pistas"]:
        print(f"  - {pista['politica']} ({pista['etiqueta']}): {len(pista['frames'])} frames")
        print(f"    Resumen: {pista['resumen']}")

if __name__ == "__main__":
    main()
