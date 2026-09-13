"""
app.ai.rag.copiloto
Motor RAG y Copiloto de IA de Vygo para el repartidor.
Combina la optimización matemática HÍBRIDA con conocimiento del mundo real de Monterrey.
Soporta LLMs (Google Gemini / OpenAI) con fallback contextual semántico inmediato.
"""

from __future__ import annotations
import os
import time
import logging
from typing import Optional, Dict, Any, List

from .knowledge import buscar_conocimiento, DocumentoConocimiento

logger = logging.getLogger("vygo.rag.copiloto")


class CopilotoVygo:
    """Copiloto inteligente que traduce métricas de optimización en consejos tácticos para el repartidor."""

    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def explicar_decision(
        self,
        oferta_id: str,
        decision: str,  # "aceptar" | "rechazar"
        tasa_marginal: float,
        rho_actual: float,
        delta_km: float,
        delta_min: float,
        ganancia_neta: float,
        holgura_frescura_min: Optional[float] = None,
        restaurante: str = "Restaurante",
        zona: str = "centro",
        app: str = "uber",
    ) -> Dict[str, Any]:
        """
        Genera la explicación aumentada con RAG para una decisión de oferta.
        """
        inicio = time.perf_counter()
        
        # 1. Recuperar contexto semántico relevante (Retrieval)
        docs = buscar_conocimiento(
            consulta=f"entrega en {restaurante} {zona} {app}",
            zona=zona,
            restaurante=restaurante,
            app=app,
            top_k=2,
        )
        contexto_textos = [f"[{d.titulo}]: {d.contenido}" for d in docs]
        contexto_unificado = "\n".join(contexto_textos)

        # 2. Si hay LLM disponible (Gemini), intentar generación generativa
        explicacion_llm = None
        if self.gemini_key:
            try:
                explicacion_llm = self._generar_con_gemini(
                    decision=decision,
                    tasa_marginal=tasa_marginal,
                    rho_actual=rho_actual,
                    delta_km=delta_km,
                    delta_min=delta_min,
                    ganancia_neta=ganancia_neta,
                    restaurante=restaurante,
                    zona=zona,
                    app=app,
                    contexto_doc=contexto_unificado,
                )
            except Exception as e:
                logger.warning(f"Error llamando a Gemini LLM: {e}. Usando generador semántico.")

        # 3. Fallback semántico inteligente (Determinista, seguro y sin latencia)
        if not explicacion_llm:
            explicacion_llm = self._generador_semantico(
                decision=decision,
                tasa_marginal=tasa_marginal,
                rho_actual=rho_actual,
                delta_km=delta_km,
                delta_min=delta_min,
                ganancia_neta=ganancia_neta,
                holgura_frescura_min=holgura_frescura_min,
                restaurante=restaurante,
                zona=zona,
                app=app,
                docs=docs,
            )

        duracion_ms = round((time.perf_counter() - inicio) * 1000.0, 2)

        return {
            "oferta_id": oferta_id,
            "decision": decision,
            "frase_corta": (
                f"+${round(tasa_marginal):.0f}/h vs tu ${round(rho_actual):.0f}/h"
                if decision == "aceptar"
                else f"${round(tasa_marginal):.0f}/h < tu ${round(rho_actual):.0f}/h"
            ),
            "explicacion_copiloto": explicacion_llm,
            "contexto_recuperado": [
                {"id": d.id, "titulo": d.titulo, "categoria": d.categoria} for d in docs
            ],
            "metricas": {
                "tasa_marginal_mxn_h": round(tasa_marginal, 1),
                "rho_actual_mxn_h": round(rho_actual, 1),
                "delta_km": round(delta_km, 2),
                "delta_min": round(delta_min, 1),
                "ganancia_neta_mxn": round(ganancia_neta, 2),
            },
            "latencia_ms": duracion_ms,
            "origen_rag": "gemini_llm" if (self.gemini_key and explicacion_llm) else "semantico_local",
        }

    def _generador_semantico(
        self,
        decision: str,
        tasa_marginal: float,
        rho_actual: float,
        delta_km: float,
        delta_min: float,
        ganancia_neta: float,
        holgura_frescura_min: Optional[float],
        restaurante: str,
        zona: str,
        app: str,
        docs: List[DocumentoConocimiento],
    ) -> str:
        """Generador heurístico en lenguaje natural con modismos de Monterrey y datos precisos."""
        app_nombre = app.capitalize()
        extra_info = ""
        for d in docs:
            if d.categoria == "restaurante":
                extra_info = f" En {restaurante} el empaque es confiable."
            elif d.categoria == "zona" and zona.lower() in ("centro", "barrio_antiguo"):
                extra_info = " El acceso en moto por el Centro no te costará tiempo extra."
            elif d.categoria == "zona" and zona.lower() == "san_pedro":
                extra_info = " En San Pedro la propina estimada es favorable."

        if decision == "aceptar":
            holgura_txt = f" Mantienes {round(holgura_frescura_min):.0f} min de margen de frescura." if holgura_frescura_min else ""
            return (
                f"Tómala: esta orden de {app_nombre} rinde a ${round(tasa_marginal):.0f}/h, superando con creces tu promedio de ${round(rho_actual):.0f}/h. "
                f"Solo te agrega {delta_km:.1f} km y {round(delta_min):.0f} min de ruta.{extra_info}{holgura_txt} ¡Subes tu ganancia neta en ${ganancia_neta:.0f} MXN!"
            )
        else:
            return (
                f"Déjala pasar: este pedido solo te daría ${round(tasa_marginal):.0f}/h, castigando tu promedio actual de ${round(rho_actual):.0f}/h. "
                f"No compensa los {delta_km:.1f} km de desvío y {round(delta_min):.0f} min perdidos. Mantén tu ruta activa actual."
            )

    def _generar_con_gemini(
        self,
        decision: str,
        tasa_marginal: float,
        rho_actual: float,
        delta_km: float,
        delta_min: float,
        ganancia_neta: float,
        restaurante: str,
        zona: str,
        app: str,
        contexto_doc: str,
    ) -> Optional[str]:
        """Llama a la API de Gemini para generar una respuesta en lenguaje natural."""
        import urllib.request
        import json

        prompt = (
            f"Eres el copiloto de IA de Vygo, un asistente en tiempo real para repartidores de comida en Monterrey. "
            f"Tu tono es profesional, motivador, directo y práctico (estilo regio amigable, sin rodeos, máx 3 frases). "
            f"Decisión tomada por el algoritmo matemático: {decision.upper()}. "
            f"Métricas: Tasa marginal ${tasa_marginal:.0f}/h (promedio actual del conductor: ${rho_actual:.0f}/h). "
            f"Desvío: {delta_km:.1f} km, tiempo extra: {delta_min:.0f} min, ganancia neta: ${ganancia_neta:.0f} MXN. "
            f"Restaurante: {restaurante}, Zona: {zona}, App: {app}. "
            f"Contexto recuperado de la ciudad:\n{contexto_doc}\n\n"
            f"Explícale al conductor en 2 o 3 frases contundentes por qué debe {decision} esta orden."
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_key}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.3, "maxOutputTokens": 150},
        }

        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    def responder_chat(self, pregunta: str, contexto_conductor: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Asistente conversacional RAG para dudas en ruta."""
        inicio = time.perf_counter()
        docs = buscar_conocimiento(consulta=pregunta, top_k=3)
        contexto_textos = [f"- {d.titulo}: {d.contenido}" for d in docs]

        # Respuesta estructurada informada por la base de conocimiento
        respuesta = (
            f"Hola, como copiloto de Vygo te comento: sobre '{pregunta}', "
            f"nuestra base de conocimiento indica que:\n"
            + "\n".join(contexto_textos)
        )

        return {
            "pregunta": pregunta,
            "respuesta": respuesta,
            "fuentes": [{"id": d.id, "titulo": d.titulo} for d in docs],
            "latencia_ms": round((time.perf_counter() - inicio) * 1000.0, 2),
        }


# Instancia singleton del copiloto
_copiloto_instancia: Optional[CopilotoVygo] = None

def obtener_copiloto() -> CopilotoVygo:
    global _copiloto_instancia
    if _copiloto_instancia is None:
        _copiloto_instancia = CopilotoVygo()
    return _copiloto_instancia
