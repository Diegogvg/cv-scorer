import os
import re
import time
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# CV compacto — solo lo esencial para puntuar (menos tokens = evita rate limit)
CV = """Estudiante ultimo ciclo (X) Ingenieria de Sistemas, Universidad Nacional de Canete. Perfil orientado a Datos, BI y Automatizacion. Ingles basico.
SKILLS: Power BI, Power Query, DAX, Tableau, Excel, SSAS Tabular, modelado dimensional, dashboards, KPIs. SQL Server, MySQL, JOIN, CTE, subconsultas. Azure Data Factory, Azure Synapse, Azure Data Lake, arquitectura Medallion, Apache Spark. Power Automate, Power Apps, n8n, RPA. Python (Pandas, NumPy, Scikit-learn, Flask), PHP, JavaScript, HTML, CSS. Git, Docker, Scrum, Agile.
EXPERIENCIA (practicas y tecnica, ~1 ano): Operador Centro Computo ONPE. Practicas soporte TI Municipalidad (desarrollo sistema web Flask). Asistente TI Oxicenter. Censista INEI. Atencion cliente y logistica.
PROYECTOS: BI Azure 9.4M registros financieros (ETL, Power BI, Synapse, Spark). Sistema web Flask/Python/MySQL. Dashboards Power BI. RPA SUNAT Power Automate. BI ciberseguridad 100k registros (DAX, SSAS). Machine Learning Random Forest (Python, Scikit-learn). IoT ESP32.
EDUCACION: Ingenieria Sistemas 2022-2026. Certificaciones SQL Server, Excel, Cisco."""

PROMPT_SISTEMA = """Eres un reclutador tecnico senior en Peru. Evaluas compatibilidad candidato-vacante con un puntaje 0-100.

Criterio ESTRICTO (no todos merecen 80):
NIVEL:
- Practicas/trainee + candidato estudiante ultimo ciclo: 70-95
- Junior 0-2 anos que encaja: 60-85
- Pide 2-3 anos: 40-60
- Pide 4+ anos o senior/gerente: 10-35

TECNICO:
- Suma si herramientas de la vacante (Power BI, SQL, Python, Azure, RPA) estan en el CV
- Resta si piden clave que NO tiene (Databricks, PyTorch, TensorFlow, ingles avanzado)

IDIOMA:
- Exige ingles avanzado y candidato tiene basico: resta 15-25

Responde UNICAMENTE con el numero entero final. Solo el numero."""


def extraer_numero(texto):
    numeros = re.findall(r'\d+', texto)
    for n in numeros:
        valor = int(n)
        if 0 <= valor <= 100:
            return valor
    return 50


def llamar_groq_con_reintentos(prompt_usuario, max_reintentos=4):
    for intento in range(max_reintentos):
        try:
            respuesta = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": prompt_usuario}
                ],
                max_tokens=8,
                temperature=0.3
            )
            return respuesta.choices[0].message.content.strip()
        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str or "429" in error_str:
                time.sleep(3 * (intento + 1))
                continue
            else:
                raise e
    return None


@app.route('/puntaje', methods=['POST'])
def puntaje():
    try:
        data = request.get_json(force=True, silent=True) or {}
        titulo = str(data.get('titulo', '')).strip()[:200]
        empresa = str(data.get('empresa', '')).strip()[:100]
        descripcion = str(data.get('descripcion', '')).strip()[:1200]

        if not titulo and not descripcion:
            return jsonify({"puntaje": "0", "motivo": "sin datos"}), 200

        prompt_usuario = f"""VACANTE: {titulo}
EMPRESA: {empresa}
DESCRIPCION: {descripcion}

CANDIDATO: {CV}

Puntaje de compatibilidad (0-100):"""

        resultado = llamar_groq_con_reintentos(prompt_usuario)

        if resultado is None:
            return jsonify({"puntaje": "", "motivo": "rate_limit"}), 200

        puntaje_num = extraer_numero(resultado)
        return jsonify({"puntaje": str(puntaje_num)}), 200

    except Exception as e:
        return jsonify({"puntaje": "", "error": str(e)[:200]}), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
