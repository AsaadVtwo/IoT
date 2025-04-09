from flask import Flask, request, jsonify
import requests
import os
import datetime

app = Flask(__name__)

# مفتاح Hugging Face API من متغير بيئة
HUGGINGFACE_API_KEY = os.getenv("HF_API_KEY")

@app.route("/")
def home():
    return "✅ Mistral AI server with logging and chart is running."

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.json
        temp = data.get("temperature")
        hum = data.get("humidity")
        status = data.get("status")
        temp_min = data.get("temp_min", 20.0)
        temp_max = data.get("temp_max", 30.0)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 📝 تخزين البيانات في log.csv
        with open("log.csv", "a") as log_file:
            if os.stat("log.csv").st_size == 0:
                log_file.write("timestamp,temperature,humidity,status\n")
            log_file.write(f"{now},{temp},{hum},{status}\n")

        # 🎯 إعداد Prompt للذكاء التوليدي
        prompt = f"""
The smart environment control system has received the following data:

- Current Temperature: {temp}°C
- Current Humidity: {hum}%
- System Status: {status}
- Time of Reading: {now[-8:]}

The system is configured by the user with the following thresholds:
- Minimum acceptable temperature: {temp_min}°C
- Maximum acceptable temperature: {temp_max}°C

Please analyze the current state based on these thresholds:
1. Is the current temperature within the acceptable range?
2. Is the humidity acceptable for typical indoor environments?
3. Was the system's action (heating/cooling/off) appropriate?
4. Are the thresholds chosen by the user reasonable?
5. Suggest better thresholds if necessary.

Then generate a short, professional report that answers these points clearly.
Do not repeat the raw data. Just include your analysis and recommendations.
"""

        headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 150,
                "temperature": 0.7,
                "do_sample": True
            }
        }

        response = requests.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.1",
            headers=headers,
            json=payload
        )
        result = response.json()

        if isinstance(result, list) and "generated_text" in result[0]:
            generated_text = result[0]["generated_text"]
            final_report = generated_text.split("Just include your analysis and recommendations.")[-1].strip()
            return jsonify({"report": final_report})
        else:
            return jsonify({"error": "Failed to generate report", "details": result}), 500

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500


@app.route("/chart")
def chart():
    labels = []
    temperatures = []
    humidities = []

    if os.path.exists("log.csv"):
        with open("log.csv", "r") as f:
            lines = f.readlines()[1:]  # تخطي السطر الأول (رؤوس الأعمدة)
            for line in lines[-50:]:  # عرض آخر 50 قراءة فقط
                parts = line.strip().split(",")
                labels.append(parts[0][-8:])  # عرض التوقيت hh:mm:ss
                temperatures.append(float(parts[1]))
                humidities.append(float(parts[2]))

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Temperature & Humidity Chart</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h2>📈 Temperature and Humidity (Last 50 records)</h2>
        <canvas id="myChart" width="900" height="400"></canvas>
        <script>
            const labels = {labels};
            const tempData = {temperatures};
            const humData = {humidities};

            const ctx = document.getElementById('myChart').getContext('2d');
            const myChart = new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: labels,
                    datasets: [
                        {{
                            label: 'Temperature (°C)',
                            data: tempData,
                            borderColor: 'red',
                            fill: false
                        }},
                        {{
                            label: 'Humidity (%)',
                            data: humData,
                            borderColor: 'blue',
                            fill: false
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        y: {{
                            beginAtZero: true
                        }}
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    app.run(debug=True)
