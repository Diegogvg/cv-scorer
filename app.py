import os
import re
import json
import time
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

# Inicialización del cliente de Groq utilizando la variable de entorno
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ==============================================================================
# 1. PERFIL DEL CANDIDATO (CONTEXTO BASE)
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

# ==============================================================================
# 2. PROMPT DE SISTEMA CON REGLAS Y EVALUACIÓN
# ==============================================================================
PROMPT_SISTEMA = f"""Eres un reclutador tecnico senior en el mercado laboral peruano.

Tu tarea es evaluar la probabilidad (0 a 100) de que el candidato sea seleccionado para la vacante.

CURRICULUM VITAE DEL CANDIDATO:
{CV_TEXTO}

ESCALA DE PUNTAJE:
- 85-100: Practicante / Trainee o rol perfectamente alineado con sus tecnologías.
- 70-84: Junior (0-2 años) con buena coincidencia técnica.
- 55-69: Falta alguna tecnología clave o exige mayor experiencia.
- 0-54: Puesto Senior / Lead o requiere Inglés Avanzado obligatorio.

INSTRUCCIÓN DE SALIDA:
Responde UNICAMENTE con un objeto JSON valido con esta estructura exacta:
{{
  "puntaje": numero_entero_0_a_100,
  "razon": "Explicacion breve de 1 sola frase con el motivo del puntaje"
}}
"""

# ==============================================================================
# 3. FUNCIÓN DE LIMPIEZA INTELIGENTE DE TEXTO (REDUCCIÓN DE TOKENS)
# ==============================================================================
def limpiar_descripcion(texto_raw):
    """
    Filtra y elimina el 'texto basura' de la vacante (legales, beneficios genéricos, URLs)
    para comprimir el tamaño del prompt y maximizar el ahorro de tokens.
    """
    if not texto_raw:
        return ""
    
    texto = texto_raw
    
    # 1. Eliminar enlaces y URLs
    texto = re.sub(r'http\S+|www\S+', '', texto)
    
    # 2. Eliminar secciones legales y de relleno comunes en LinkedIn
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
        
    # 3. Normalizar espacios en blanco y saltos de línea repetidos
    texto = re.sub(r'\s+', ' ', texto).strip()
    
    # 4. Limitar a 2,200 caracteres (Suficiente para cubrir Requisitos y Funciones clave)
    return texto[:2200]

# ==============================================================================
# 4. LLAMADA A LA API DE GROQ Y EXTRACCIÓN DE METADATA
# ==============================================================================
def llamar_groq(prompt_usuario, max_reintentos=3):
    """Ejecuta la llamada a Groq solicitando JSON estricto y muestra métricas de consumo."""
    for intento in range(max_reintentos):
        try:
            respuesta = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": PROMPT_SISTEMA},
                    {"role": "user", "content": prompt_usuario}
                ],
                max_tokens=80,
                temperature=0.1,
                response_format={"type": "json_object"}  # Garantiza respuesta en formato JSON
            )
            
            # Captura de métricas de uso de tokens
            usage = respuesta.usage
            print(f"📊 CONSUMO DE TOKENS (Groq):")
            print(f"   • Tokens de Entrada (Prompt): {usage.prompt_tokens}")
            print(f"   • Tokens de Salida (Respuesta): {usage.completion_tokens}")
            print(f"   • Total Tokens: {usage.total_tokens}")

            texto_respuesta = respuesta.choices[0].message.content.strip()
            print(f"📥 Respuesta JSON cruda: {texto_respuesta}")
            
            # Parsear el objeto JSON de la respuesta
            data = json.loads(texto_respuesta)
            puntaje_val = int(data.get("puntaje", 0))
            razon_val = data.get("razon", "Sin razón especificada")
            
            print(f"💡 Razón del Reclutador IA: '{razon_val}'")
            return max(0, min(100, puntaje_val))

        except Exception as e:
            error_str = str(e)
            print(f"⚠️ Error en intento {intento + 1}: {error_str[:120]}")
            if "rate_limit" in error_str or "429" in error_str:
                time.sleep(3 * (intento + 1))
            else:
                return None
    return None

# ==============================================================================
# 5. ENDPOINT PRINCIPAL (/puntaje)
# ==============================================================================
@app.route('/puntaje', methods=['POST'])
def puntaje():
    try:
        data = request.get_json(force=True, silent=True) or {}
        titulo = str(data.get('titulo', '')).strip()[:150]
        empresa = str(data.get('empresa', '')).strip()[:100]
        descripcion_raw = str(data.get('descripcion', ''))

        # Aplicar la estrategia de limpieza inteligente
        descripcion_limpia = limpiar_descripcion(descripcion_raw)

        print(f"\n==================== PRUEBA EN GROQ CON LIMPIEZA ====================")
        print(f"PUESTO: {titulo} | EMPRESA: {empresa}")
        print(f"📏 Caracteres Originales: {len(descripcion_raw)}  ──>  Limpios: {len(descripcion_limpia)}")

        if not titulo and not descripcion_limpia:
            return jsonify({"puntaje": ""}), 200

        prompt_usuario = f"""
EVALUA ESTA VACANTE:
Puesto: {titulo}
Empresa: {empresa}
Descripción Filtrada:
{descripcion_limpia}
"""

        # Pausa preventiva anti-rate limit
        time.sleep(2)

        resultado = llamar_groq(prompt_usuario)

        if resultado is None:
            print("❌ No se pudo procesar el puntaje")
            return jsonify({"puntaje": ""}), 200

        print(f"✅ PUNTAJE FINAL: {resultado}")
        return jsonify({"puntaje": str(resultado)}), 200

    except Exception as e:
        print(f"❌ Error general en endpoint: {str(e)[:200]}")
        return jsonify({"puntaje": "", "error": str(e)[:100]}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "provider": "groq", "modelo": "llama-3.3-70b-versatile"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
