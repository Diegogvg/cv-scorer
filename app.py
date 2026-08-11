import os
import re
import time
import json
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

CV = """
CANDIDATO: Diego Gianfranco Vicente Guerra
ESTADO: Estudiante activo, X ciclo (ultimo), Ingenieria de Sistemas, Universidad Nacional de Canete. Egreso estimado diciembre 2026. Ingles basico.

HABILIDADES TECNICAS:
- Datos y BI: Power BI, Power Query, DAX, SSAS Tabular, Tableau, Excel intermedio, modelado dimensional, dashboards, KPIs
- Bases de datos: SQL Server, MySQL, modelado relacional, JOIN, CTE, subconsultas, procedimientos
- Cloud: Azure Data Factory, Azure Synapse Analytics, Azure Data Lake Gen2, arquitectura Medallion, Apache Spark
- Automatizacion: Power Automate, Power Apps, n8n, RPA
- Programacion: Python (Pandas, NumPy, Scikit-learn, Flask), PHP, JavaScript, HTML, CSS, Bootstrap
- Herramientas: Git, Docker, Scrum, Agile, DevOps

EXPERIENCIA LABORAL (total aprox 1 ano, no es experiencia profesional formal):
- Operador Centro Computo, ONPE (Mar-Jun 2026): digitalizacion actas electorales, control calidad datos
- Practicas preprofesionales TI, Municipalidad Nuevo Imperial (Abr-Jul 2026): soporte tecnico, mantenimiento equipos, desarrollo sistema web SiReC con Flask/Python/MySQL
- Asistente Tecnico TI, Oxicenter (Nov 2025-Feb 2026): mantenimiento equipos, soporte usuarios
- Censista, INEI (Ago-Oct 2025): levantamiento datos campo
- Encargado Counter, Shalom Empresarial (Mar 2024-May 2025): supervision equipo, logistica
- Auxiliar Logistico, Cynara Peru y Consorcio Productores Fruta (2022-2023)

PROYECTOS ACADEMICOS DESTACADOS:
- BI en Azure para 9.4 millones registros financieros: ETL/ELT, arquitectura Medallion, Power BI, Azure Data Factory, Synapse, Apache Spark, Python
- Sistema web SiReC (Flask, Python, MySQL, Bootstrap): desarrollado en practicas reales en municipalidad
- Dashboard Power BI analisis universitario: Power Query, modelado dimensional, KPIs
- RPA automatizacion SUNAT: Power Automate, Excel, flujos RPA
- BI ciberseguridad 100k registros: Power BI, DAX, SSAS Tabular, SQL Server
- Machine Learning precios vivienda: Python, Scikit-learn, Random Forest, Pandas
- Sistema IoT riego: ESP32, Arduino, sensores, aplicacion web
"""

PROMPT_SISTEMA = f"""Eres un reclutador tecnico senior en el mercado laboral peruano.

Tu tarea es evaluar la probabilidad (0 a 100) de que este candidato sea seleccionado para la vacante dada.

CURRICULUM VITAE DEL CANDIDATO:
{CV}

ESCALA DE PUNTAJE:
- 85-100: Practicante / Trainee o rol perfectamente alineado.
- 70-84: Junior (0-2 años) con buena coincidencia técnica.
- 55-69: Falta alguna tecnología o pide más experiencia.
- 0-54: Puesto Senior / Lead o exige Inglés Avanzado.

Responde UNICAMENTE con un JSON valido con este formato exacto:
{{"puntaje": numero_entero_0_a_100}}"""


def llamar_groq(prompt_usuario, max_reintentos=3):
    """Llama a Groq solicitando formato JSON explícito."""
    for intento in range(max_reintentos):
        try:
            respuesta = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": prompt_usuario}
                ],
                max_tokens=30,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            texto = respuesta.choices[0].message.content.strip()
            print(f"📥 Respuesta Groq: '{texto}'")
            
            # Intentar parsear JSON
            data = json.loads(texto)
            puntaje_num = int(data.get("puntaje", 0))
            return max(0, min(100, puntaje_num))

        except Exception as e:
            error_str = str(e)
            print(f"⚠️ Error intento {intento + 1}: {error_str[:120]}")
            if "rate_limit" in error_str or "429" in error_str:
                time.sleep(3 * (intento + 1))
            else:
                return None
    return None


@app.route('/puntaje', methods=['POST'])
def puntaje():
    try:
        data = request.get_json(force=True, silent=True) or {}
        titulo = str(data.get('titulo', '')).strip()[:150]
        empresa = str(data.get('empresa', '')).strip()[:100]
        descripcion = str(data.get('descripcion', '')).strip()

        # Recorte de prueba para consumo mínimo
        descripcion = descripcion[:1000]

        print(f"\n==================== PRUEBA EN GROQ ====================")
        print(f"PUESTO: {titulo}")
        print(f"EMPRESA: {empresa}")
        print(f"DESCRIPCION CARACTERES: {len(descripcion)}")

        if not titulo and not descripcion:
            return jsonify({"puntaje": ""}), 200

        prompt_usuario = f"""
EVALUA ESTA VACANTE:
Puesto: {titulo}
Empresa: {empresa}
Descripción: {descripcion}
"""

        resultado = llamar_groq(prompt_usuario)

        if resultado is None:
            print("❌ No se obtuvo puntaje")
            return jsonify({"puntaje": ""}), 200

        print(f"✅ Puntaje procesado: {resultado}")
        return jsonify({"puntaje": str(resultado)}), 200

    except Exception as e:
        print(f"❌ Error general: {str(e)[:200]}")
        return jsonify({"puntaje": "", "error": str(e)[:100]}), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "provider": "groq", "modelo": "llama-3.3-70b-versatile"})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
