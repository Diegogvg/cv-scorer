import os
import re
import time
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

CV = """Estudiante ultimo ciclo Ingenieria Sistemas Universidad Nacional Canete. Datos BI Automatizacion. Ingles basico.
SKILLS: Power BI DAX Power Query Tableau Excel SSAS modelado dimensional dashboards KPIs. SQL Server MySQL JOIN CTE subconsultas. Azure Data Factory Synapse Data Lake Medallion Spark. Power Automate Power Apps n8n RPA. Python Pandas NumPy Scikit-learn Flask. PHP JavaScript HTML CSS. Git Docker Scrum Agile.
EXPERIENCIA: Operador ONPE digitalizacion actas. Practicas TI Municipalidad soporte equipos desarrollo web Flask Python MySQL. Asistente TI Oxicenter. Censista INEI. Atencion cliente logistica.
PROYECTOS: BI Azure 9.4M registros ETL Power BI Synapse Spark. Web Flask Python MySQL. Dashboards Power BI. RPA SUNAT Power Automate. BI ciberseguridad DAX SSAS. ML Random Forest Python Scikit-learn. IoT ESP32."""

PROMPT_SISTEMA = """Eres un reclutador tecnico senior con experiencia en el mercado laboral de Peru y Latinoamerica.

Tu tarea es analizar que tan probable es que este candidato sea seleccionado para una vacante, basandote en una comparacion honesta y detallada entre el CV y los requisitos del puesto.

Considera estos factores reales:
- Nivel de experiencia requerido vs experiencia real del candidato
- Coincidencia de habilidades tecnicas especificas
- Nivel de educacion y si esta en curso o completo
- Idiomas requeridos
- Si es practicante o junior vs senior
- Proyectos relevantes que demuestren las habilidades pedidas

Se honesto y variado en tu evaluacion. No todos los candidatos tienen la misma probabilidad. Un estudiante sin experiencia laboral en un puesto senior deberia tener puntaje bajo. Un estudiante con proyectos relevantes en una practica deberia tener puntaje alto.

Responde UNICAMENTE con un numero entero del 0 al 100 representando la probabilidad de ser seleccionado. Solo el numero, nada mas."""

def extraer_numero(texto):
    if not texto:
        return None
    numeros = re.findall(r'\b(\d{1,3})\b', texto)
    for n in numeros:
        valor = int(n)
        if 0 <= valor <= 100:
            return valor
    return None


def llamar_groq(prompt_usuario, max_reintentos=3):
    time.sleep(2)  # pausa para evitar rate limit
    for intento in range(max_reintentos):
        try:
            respuesta = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": prompt_usuario}
                ],
                max_tokens=15,
                temperature=0.1
            )
            texto = respuesta.choices[0].message.content.strip()
            numero = extraer_numero(texto)
            if numero is not None:
                return numero
            # Si no extrajo numero, reintenta
            time.sleep(1)
        except Exception as e:
            error_str = str(e)
            if "rate_limit" in error_str or "429" in error_str:
                time.sleep(4 * (intento + 1))
            else:
                return None
    return None


@app.route('/puntaje', methods=['POST'])
def puntaje():
    try:
        data = request.get_json(force=True, silent=True) or {}
        titulo = str(data.get('titulo', '')).strip()[:150]
        empresa = str(data.get('empresa', '')).strip()[:80]
        descripcion = str(data.get('descripcion', '')).strip()[:1000]

        prompt = f"VACANTE: {titulo} en {empresa}\nDESCRIPCION: {descripcion}\nCANDIDATO: {CV}\nPuntaje:"

        resultado = llamar_groq(prompt)

        if resultado is None:
            return jsonify({"puntaje": ""}), 200

        return jsonify({"puntaje": str(resultado)}), 200

    except Exception as e:
        return jsonify({"puntaje": "", "error": str(e)[:100]}), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
