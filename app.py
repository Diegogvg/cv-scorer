import os
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

CV = CV = """
Diego Gianfranco Vicente Guerra. Estudiante X ciclo Ingenieria de Sistemas Universidad Nacional de Canete. Orientado a Datos, BI y Automatizacion.

PERFIL TECNICO: Power BI, Power Query, Tableau, Excel, DAX, SSAS Tabular, modelado dimensional, dashboards, KPIs. SQL Server, MySQL, modelado relacional, SELECT, JOIN, GROUP BY, subconsultas, CTE. Microsoft Azure, Azure Data Factory, Azure Data Lake Gen2, Azure Synapse Analytics, arquitectura Medallion, Apache Spark. Power Automate, Power Apps, n8n, RPA. Python (Pandas, NumPy, Scikit-learn, Flask), PHP, JavaScript, HTML, CSS, Bootstrap. Git, Docker, Scrum, Agile, DevOps.

EXPERIENCIA: Operador Centro Computo ONPE Mar-Jun 2026, digitalizacion actas electorales control calidad. Asistente Oficina Tecnologica Municipalidad Nuevo Imperial Abr-Jul 2026, soporte TI mantenimiento equipos desarrollo sistema SiReC Flask Python MySQL. Asistente Tecnico TI Oxicenter Nov 2025-Feb 2026, mantenimiento equipos soporte usuarios. Censista INEI Ago-Oct 2025, levantamiento datos Censos 2025. Encargado Counter Shalom Mar 2024-May 2025, supervision equipo logistica. Auxiliar Logistico Cynara Peru y Consorcio Productores Fruta 2022-2023.

PROYECTOS: BI Azure 9.4 millones reclamos financieros CFPB arquitectura Medallion ETL Power BI Azure Data Factory Azure Synapse Apache Spark Python 2026. Sistema SiReC reportes ciudadanos Municipalidad Nuevo Imperial Python Flask MySQL Bootstrap 2026. Dashboard analisis admision Power BI Power Query SQL modelado dimensional 2026. RPA automatizacion consulta validacion RUC SUNAT Power Automate Excel 2026. BI analisis 100000 incidentes ciberseguridad Power BI SSAS DAX SQL Server 2026. Sistema gestion documental Mesa Partes PHP MySQL JavaScript Docker GitHub 2024. Modelo predictivo Machine Learning precios vivienda Random Forest Python Scikit-learn Pandas 2025. Sistema IoT riego automatico ESP32 Arduino sensores humedad 2025.

EDUCACION: Ingenieria de Sistemas Universidad Nacional de Canete 2022-2026 estimado.

CERTIFICACIONES: SQL Server UNI-OTI, Excel Fundacion Romero, Fundamentos Analisis Datos Cisco, Ciberseguridad Cisco, Redes Cisco, ONPE Coordinador Centro Poblado.
"""

@app.route('/puntaje', methods=['POST'])
def puntaje():
    data = request.json
    titulo = data.get('titulo', '')
    descripcion = data.get('descripcion', '')[:800]
    
    prompt = f"""Eres reclutador senior en Peru. Analiza que tan compatible es este candidato con la vacante.
Responde SOLO con un numero entero del 1 al 100. Sin texto adicional, solo el numero.

VACANTE: {titulo}
DESCRIPCION: {descripcion}

CV CANDIDATO: {CV}"""
    
    respuesta = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=5,
        temperature=0.1
    )
    
    puntaje_valor = respuesta.choices[0].message.content.strip()
    return jsonify({"puntaje": puntaje_valor})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
