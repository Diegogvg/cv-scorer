import os
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

CV = """
Diego Gianfranco Vicente Guerra. Estudiante IX ciclo Ingenieria de Sistemas Universidad Nacional de Canete.
Experiencia: Operador Centro Computo ONPE 2026, Asistente TI Municipalidad Nuevo Imperial 2026, Asistente Tecnico TI Oxicenter 2025-2026, Censista INEI 2025, Encargado Counter Shalom 2024-2025.
Proyectos: Business Intelligence Azure 9.4 millones registros financieros CFPB arquitectura Medallion ETL Power BI Azure Data Factory Azure Synapse. RPA automatizacion consulta validacion RUC SUNAT Power Automate. Dashboard Power BI analisis incidentes ciberseguridad 100000 registros DAX SSAS. Sistema Reportes Ciudadanos SiReC Flask Python MySQL Bootstrap. Modelo predictivo Machine Learning Python Scikit-learn Random Forest. Sistema IoT riego automatico ESP32 Arduino.
Skills: Power BI DAX Power Query Tableau Excel avanzado SQL Server MySQL Azure Data Factory Azure Synapse Azure Data Lake Python Pandas NumPy Scikit-learn Flask Power Automate Power Apps n8n RPA Git Docker Scrum Agile.
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
