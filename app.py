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

# Prompt de sistema (instrucciones fijas del reclutador)
PROMPT_SISTEMA_BASE = """Eres un reclutador tecnico senior en el mercado laboral peruano.

Tu tarea es evaluar la probabilidad (0 a 100) de que el candidato sea seleccionado para la vacante.

ESCALA DE PUNTAJE:
- 85-100: Practicante / Trainee o rol perfectamente alineado con sus tecnologías.
- 70-84: Junior (0-2 años) con buena coincidencia técnica.
- 55-69: Falta alguna tecnología clave o exige mayor experiencia.
- 0-54: Puesto Senior / Lead o requiere Inglés Avanzado obligatorio.

INSTRUCCIÓN DE SALIDA:
Responde UNICAMENTE con un objeto JSON valido con esta estructura exacta:
{
  "puntaje": numero_entero_0_a_100,
  "razon": "Explicacion breve de 1 sola frase con el motivo del puntaje"
}"""

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
# 3. LLAMADA A LA API DE CLAUDE CON PROMPT CACHING
# ==============================================================================
def llamar_claude(prompt_usuario, max_reintentos=3):
    """Llama a Claude 3.5 Haiku marcando el CV con caché efímera."""
    
    # Estructura del System Prompt dividida para aplicar Prompt Caching únicamente al CV
    system_blocks = [
        {
            "type": "text",
            "text": PROMPT_SISTEMA_BASE
        },
        {
            "type": "text",
            "text": f"\nCURRICULUM VITAE DEL CANDIDATO:\n{CV_TEXTO}",
            "cache_control": {"type": "ephemeral"}  # <--- AQUÍ SE ACTIVA EL 90% DE DESCUENTO
        }
    ]

    for intento in range(max_reintentos):
        try:
            respuesta = client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=100,
                temperature=0.1,
                system=system_blocks,
                messages=[
                    {"role": "user", "content": prompt_usuario}
                ]
            )
            
            # Auditoría detallada de Tokens y Caché de Anthropic
            usage = respuesta.usage
            input_tokens = usage.input_tokens
            cache_creation = getattr(usage, 'cache_creation_input_tokens', 0)
            cache_read = getattr(usage, 'cache_read_input_tokens', 0)
            
            print(f"📊 CONSUMO DE TOKENS (Claude 3.5 Haiku):")
            print(f"   • Tokens de Entrada Nuevos: {input_tokens}")
            print(f"   • Tokens Escritos en Caché (1ª vez): {cache_creation}")
            print(f"   • Tokens Leídos de Caché (90% Descuento): {cache_read}")
            print(f"   • Tokens de Salida: {usage.output_tokens}")

            texto_respuesta = respuesta.content[0].text.strip()
            print(f"📥 Respuesta JSON cruda: {texto_respuesta}")
            
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

        print(f"\n==================== PRUEBA EN CLAUDE CON CACHÉ ====================")
        print(f"PUESTO: {titulo} | EMPRESA: {empresa}")
        print(f"📏 Caracteres Originales: {len(descripcion_raw)}  ──>  Limpios: {len(descripcion_limpia)}")

        if not titulo and not descripcion_limpia:
            return jsonify({"puntaje": ""}), 200

        prompt_usuario = f"""EVALUA ESTA VACANTE:
Puesto: {titulo}
Empresa: {empresa}
Descripción Filtrada:
{descripcion_limpia}"""

        resultado = llamar_claude(prompt_usuario)

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
    return jsonify({"status": "ok", "provider": "anthropic", "modelo": "claude-3-5-haiku-20241022"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
