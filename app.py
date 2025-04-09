import os
import datetime
import logging
from flask import Flask, request, jsonify
from openai import OpenAI
import requests
import traceback

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# إعداد السجل لعرض الرسائل في الـ logs
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# URL الخاص بـ Google Apps Script
GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbzNQfywoqMbCeUpJ8F2vZnnuBIDQrS8oT8WqS7Vb7usv0TSwO0flM0y71OlI3W2VNm4/exec'

@app.route("/")
def home():
    return "✅ AI IoT Report Server is running with OpenAI."


@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.json
        temp = data.get("temperature")
        hum = data.get("humidity")
        status = data.get("status")
        temp_min = data.get("temp_min")
        temp_max = data.get("temp_max")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if None in [temp, hum, status, temp_min, temp_max]:
            logger.error("Missing fields in JSON!")
            return jsonify({"error": "Missing fields in JSON!"}), 400

        # سجل البيانات في ملف CSV
        with open("log.csv", "a") as log_file:
            if os.stat("log.csv").st_size == 0:
                log_file.write("timestamp,temperature,humidity,status\n")
            log_file.write(f"{now},{temp},{hum},{status}\n")

        # إرسال البيانات إلى Google Sheets
        send_data_to_google_sheet(temp, hum, status)

        # بناء الـ prompt لتحليل البيانات عبر OpenAI
        prompt = f"""
        System Reading:
        - Temperature: {temp}°C
        - Humidity: {hum}%
        - Status: {status}
        - Time: {now}

        User Settings:
        - Minimum temperature: {temp_min}°C
        - Maximum temperature: {temp_max}°C

        Please generate a short English report that:
        1. Analyzes whether the current values are within the user-defined thresholds.
        2. Evaluates whether the system behavior is appropriate.
        3. Checks if the thresholds are reasonable and provides suggestions.
        Do not repeat the input. Write a concise and helpful professional summary.
        """

        # استدعاء GPT-3.5 لتحليل البيانات
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an IoT assistant that analyzes temperature and humidity data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )

        final_report = response.choices[0].message.content.strip()
        logger.info(f"Generated Report: {final_report}")
        return jsonify({"report": final_report})

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


def send_data_to_google_sheet(temp, hum, status):
    """إرسال البيانات إلى Google Sheets عبر Google Apps Script"""
    payload = {
        'temperature': temp,
        'humidity': hum,
        'status': status
    }
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, headers=headers)
        if response.status_code == 200:
            logger.info("Data successfully sent to Google Sheets.")
        else:
            logger.error(f"Failed to send data to Google Sheets. Status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending data to Google Sheets: {str(e)}")


@app.route("/chart")
def chart():
    labels = []
    temperatures = []
    humidities = []

    if os.path.exists("log.csv"):
        with open("log.csv", "r") as f:
            lines = f.readlines()[1:]  # تخطي العنوان
            for line in lines[-50:]:  # آخر 50 قراءة فقط
                parts = line.strip().split(",")
                labels.append(parts[0][-8:])  # hh:mm:ss
                temperatures.append(float(parts[1]))
                humidities.append(float(parts[2]))

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>📊 Temperature & Humidity Chart</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <h2>📈 Last 50 Readings</h2>
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
