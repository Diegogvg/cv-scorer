import os
import re
import time
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

PROMPT_SISTEMA = """Eres un reclutador tecnico senior con amplia experiencia en el mercado laboral peruano y latinoamericano.

Tu tarea es evaluar que tan probable es que este candidato sea SELECCIONADO en un proceso de seleccion real para la vacante dada.

PROCESO DE EVALUACION (razona internamente estos puntos):

1. NIVEL DEL PUESTO vs PERFIL DEL CANDIDATO:
   - El candidato es estudiante universitario en su ultimo ciclo con practicas y proyectos academicos
   - Si la vacante pide practicante/trainee/intern: alta compatibilidad base
   - Si pide junior (0-2 anos): compatibilidad media-alta si las skills encajan
   - Si pide 2-4 anos de experiencia profesional: compatibilidad baja-media
   - Si pide 4+ anos, senior, lead, o gerente: compatibilidad muy baja

2. COINCIDENCIA TECNICA:
   - Identifica las tecnologias y herramientas que PIDE la vacante
   - Compara con las que TIENE el candidato
   - Una alta coincidencia sube el puntaje, baja coincidencia lo baja

3. IDIOMAS:
   - Si la vacante exige ingles intermedio-avanzado: resta puntos significativos (el candidato tiene ingles basico)
   - Si no menciona ingles o es opcional: no penalizar

4. PROYECTOS RELEVANTES:
   - Si el candidato tiene proyectos academicos que demuestran las skills pedidas: suma puntos
   - Los proyectos con datos reales (9.4M registros, 100k registros) son un diferenciador importante

5. SECTOR/INDUSTRIA:
   - El candidato no tiene experiencia en sectores especificos (banca, retail, consumo masivo)
   - Si la vacante exige experiencia en sector especifico: resta puntos

ESCALA DE PUNTAJE:
- 85-100: Candidato muy competitivo, cumple casi todos los requisitos, alta probabilidad de pasar a entrevista
- 70-84: Buen candidato, cumple los requisitos principales, probabilidad media-alta
- 55-69: Candidato parcialmente apto, cumple algunos requisitos pero faltan cosas importantes
- 35-54: Candidato debil para esta vacante, faltan requisitos clave
- 0-34: Candidato no apto, hay una brecha significativa con los requisitos

IMPORTANTE: Se honesto y diferenciador. No todos los candidatos merecen 75-80. Un practicante en puesto de practicante puede ser 90. Un estudiante en puesto senior debe ser 20-30. Usa todo el rango del 0 al 100.

Responde UNICAMENTE con el numero entero final. Solo el numero, sin explicaciones."""


def extraer_numero(texto):
    """Extrae el primer numero valido entre 0 y 100."""
    if not texto:
        return None
    # Busca numeros de 1-3 digitos
    numeros = re.findall(r'\b(\d{1,3})\b', texto.strip())
    for n in numeros:
        valor = int(n)
        if 0 <= valor <= 100:
            return valor
    return None


def llamar_groq(prompt_usuario, max_reintentos=4):
    """Llama a Groq con reintentos ante rate limit."""
    for intento in range(max_reintentos):
        try:
            respuesta = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": prompt_usuario}
                ],
                max_tokens=20,
                temperature=0.4
            )
            texto = respuesta.choices[0].message.content.strip()
            print(f"Groq respondio: '{texto}'")
            numero = extraer_numero(texto)
            if numero is not None:
                return numero
            # Si no extrajo numero, reintenta
            print(f"No se pudo extraer numero de: '{texto}', reintentando...")
            time.sleep(2)
        except Exception as e:
            error_str = str(e)
            print(f"Error en intento {intento + 1}: {error_str[:100]}")
            if "rate_limit" in error_str or "429" in error_str:
                espera = 5 * (intento + 1)
                print(f"Rate limit, esperando {espera}s...")
                time.sleep(espera)
            else:
                return None
    return None


@app.route('/puntaje', methods=['POST'])
def puntaje():
    try:
        data = request.get_json(force=True, silent=True) or {}
        titulo = str(data.get('titulo', '')).strip()[:200]
        empresa = str(data.get('empresa', '')).strip()[:100]
        descripcion = str(data.get('descripcion', '')).strip()

        # Tomar hasta 1500 chars de la descripcion
        descripcion = descripcion[:1500]

        print(f"TITULO: {titulo}")
        print(f"EMPRESA: {empresa}")
        print(f"DESCRIPCION ({len(descripcion)} chars): {descripcion[:80]}")

        if not titulo and not descripcion:
            return jsonify({"puntaje": ""}), 200

        prompt_usuario = f"""Evalua esta vacante para el candidato descrito en el sistema.

VACANTE: {titulo}
EMPRESA: {empresa}

DESCRIPCION COMPLETA:
{descripcion}

Basandote en el CV del candidato y los requisitos de esta vacante, indica la probabilidad de ser seleccionado (0-100):"""

        # Pausa entre llamadas para evitar rate limit
        time.sleep(3)

        resultado = llamar_groq(prompt_usuario)

        if resultado is None:
            print("No se pudo obtener puntaje, devolviendo vacio")
            return jsonify({"puntaje": ""}), 200

        print(f"Puntaje final: {resultado}")
        return jsonify({"puntaje": str(resultado)}), 200

    except Exception as e:
        print(f"Error general: {str(e)[:200]}")
        return jsonify({"puntaje": "", "error": str(e)[:100]}), 200


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "modelo": "llama-3.3-70b-versatile"})


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
