import os
import re
import json
import time
from flask import Flask, request, jsonify
import anthropic

app = Flask(__name__)

# Inicialización del cliente oficial de Anthropic
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ==============================================================================
# 1. PERFIL DEL CANDIDATO (CONTEXTO BASE CON MARCA DE CACHÉ)
# ==============================================================================
CV_TEXTO = """
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

PROMPT_SISTEMA_BASE = """Eres un reclutador técnico senior en el mercado laboral peruano.
Evalúa la probabilidad (0 a 100) de que el candidato sea seleccionado para la vacante.

ESCALA DE PUNTAJE:
- 85-100: Practicante / Trainee o rol perfectamente alineado con sus tecnologías.
- 70-84: Junior (0-2 años) con buena coincidencia técnica.
- 55-69: Falta alguna tecnología clave o exige mayor experiencia.
- 0-54: Puesto Senior / Lead o requiere Inglés Avanzado obligatorio.

INSTRUCCIÓN DE SALIDA:
Responde ÚNICAMENTE con un JSON válido sin markdown ni formato extra.
Ejemplo exacto de salida esperada:
{"puntaje": 85, "razon": "Estudiante de último ciclo alineado al rol pero falta inglés."}

REGLA DE BREVEDAD: La 'razon' NO debe tener más de 12 palabras."""

# ==============================================================================
# 2. FUNCIÓN DE LIMPIEZA INTELIGENTE DE TEXTO
# ==============================================================================
def limpiar_descripcion(texto_raw):
    """Filtra y elimina el 'texto basura' de la vacante para minimizar consumo de tokens."""
    if not texto_raw:
        return ""
    
    texto = texto_raw
    texto = re.sub(r'http\S+|www\S+', '', texto)
    
    patrones_relleno = [
        r'Estamos comprometidos con la igualdad.*',
        r'Maersk is committed to a diverse.*',
        r'APM Terminals es una unidad de negocios.*',
        r'En APM Terminals, somos un equipo de.*',
        r'¿Te interesa una carrera en.*',
        r'Valoramos la diversidad y prohibimos la discriminación.*'
    ]
    for patron in patrones_relleno:
        texto = re.sub(patron, '', texto, flags=re.IGNORECASE | re.DOTALL)
        
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto[:2200]

# ==============================================================================
# 3. LLAMADA A LA API DE CLAUDE (CON LATENCIA Y TOKENS)
# ==============================================================================
def llamar_claude(prompt_usuario, max_reintentos=3):
    system_prompt = f"{PROMPT_SISTEMA_BASE}\n\nCURRICULUM VITAE DEL CANDIDATO:\n{CV_TEXTO}"

    for intento in range(max_reintentos):
        try:
            # ⏱️ Inicio del cronómetro
            inicio = time.time()

            respuesta = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                temperature=0.1,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt_usuario}
                ]
            )

            # ⏱️ Fin del cronómetro y cálculo de latencia
            fin = time.time()
            latencia_seg = round(fin - inicio, 2)

            # Extraer tokens del objeto usage
            input_tokens = respuesta.usage.input_tokens
            output_tokens = respuesta.usage.output_tokens
            total_tokens = input_tokens + output_tokens

            texto_respuesta = respuesta.content[0].text.strip()
            
            # Limpieza de markdown
            if texto_respuesta.startswith("```"):
                texto_respuesta = re.sub(r"^```[a-zA-Z]*\n?", "", texto_respuesta)
                texto_respuesta = re.sub(r"\n?```$", "", texto_respuesta).strip()

            data = json.loads(texto_respuesta)
            puntaje_val = max(0, min(100, int(data.get("puntaje", 0))))
            razon_val = data.get("razon", "Sin razón especificada").strip()
            
            # IMPRESIÓN COMPLETA EN LOGS DE RAILWAY
            print(f"💡 Resultado: Puntaje={puntaje_val} | Razón='{razon_val}' | Latencia: {latencia_seg}s | Tokens: [In: {input_tokens} | Out: {output_tokens} | Total: {total_tokens}]")
            
            return puntaje_val, razon_val, latencia_seg, input_tokens, output_tokens

        except Exception as e:
            error_str = str(e)
            print(f"⚠️ Error en intento {intento + 1}: {error_str[:120]}")
            if "rate_limit" in error_str or "429" in error_str:
                time.sleep(3 * (intento + 1))
            else:
                return None, None, 0, 0, 0
    return None, None, 0, 0, 0

# ==============================================================================
# 4. ENDPOINT PRINCIPAL (/puntaje)
# ==============================================================================
@app.route('/puntaje', methods=['POST'])
def puntaje():
    try:
        data = request.get_json(force=True, silent=True) or {}
        titulo = str(data.get('titulo', '')).strip()[:150]
        empresa = str(data.get('empresa', '')).strip()[:100]
        descripcion_raw = str(data.get('descripcion', ''))

        descripcion_limpia = limpiar_descripcion(descripcion_raw)

        if not titulo and not descripcion_limpia:
            return jsonify({
                "puntaje": "",
                "razon": "",
                "latencia_seg": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "tokens_total": 0
            }), 200

        prompt_usuario = f"""EVALUA ESTA VACANTE:
Puesto: {titulo}
Empresa: {empresa}
Descripción: {descripcion_limpia}"""

        puntaje_res, razon_res, latencia, tokens_in, tokens_out = llamar_claude(prompt_usuario)

        if puntaje_res is None:
            return jsonify({
                "puntaje": "",
                "razon": "Error al procesar",
                "latencia_seg": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "tokens_total": 0
            }), 200

        # Respuesta JSON con todos los datos clave de telemetría
        return jsonify({
            "puntaje": str(puntaje_res),
            "razon": razon_res,
            "latencia_seg": latencia,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "tokens_total": tokens_in + tokens_out,
            "modelo": "claude-haiku-4-5-20251001"
        }), 200

    except Exception as e:
        return jsonify({"puntaje": "", "razon": "", "error": str(e)[:100]}), 200


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
