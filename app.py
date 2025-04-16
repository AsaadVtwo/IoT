
import os
import json
import datetime
import logging
from flask import Flask, request, jsonify, render_template_string, redirect
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"
GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbybDA0fCsJG7_OeU4TYaxqDSfFKboKtL0hdcxSWLRahC66zmAmAzAV8SYMr3O5Cu9kx/exec'
LOG_FILE = "log.csv"

LAST_REPORT_FILE = "last_report.txt"

def save_last_report(text):
    with open(LAST_REPORT_FILE, "w") as f:
        f.write(text)

def load_last_report():
    if os.path.exists(LAST_REPORT_FILE):
        with open(LAST_REPORT_FILE, "r") as f:
            return f.read()
    return "No AI report available yet."


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f)


@app.route("/", methods=["GET"])
def index():
    settings = load_settings()
    default_min = settings.get("room1", {}).get("temp_min", 20.0)
    default_max = settings.get("room1", {}).get("temp_max", 30.0)
    html = f'''
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f9;
                color: #333;
                margin: 0;
                padding: 20px;
                text-align: center;
            }}
            h2, h3 {{
                color: #0078D4;
            }}
            form {{
                background-color: #fff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                display: inline-block;
                margin-bottom: 30px;
            }}
            input, select {{
                font-size: 16px;
                padding: 10px;
                width: 250px;
                border: 1px solid #ddd;
                border-radius: 4px;
                margin-bottom: 15px;
            }}
            button {{
                background-color: #0078D4;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
            }}
            button:hover {{
                background-color: #005fa3;
            }}
            .report-box {{
                background-color: #e8f0fe;
                padding: 15px;
                border-radius: 5px;
                margin: 10px auto;
                width: 90%;
                max-width: 600px;
                text-align: left;
            }}
        </style>
    </head>
    <body>
    <h2>🌡️ Room Temperature Control</h2>
    <form action="/save_settings" method="POST">
        <label>Select Room:</label><br>
        <select name="device">
            <option value="room1">Room 1</option>
            <option value="room2">Room 2</option>
        </select><br><br>
        <label>Temp Min:</label><br>
        <input type="number" name="temp_min" step="0.1" value="{default_min}"><br><br>
        <label>Temp Max:</label><br>
        <input type="number" name="temp_max" step="0.1" value="{default_max}"><br><br>
        <button type="submit">💾 Save Settings</button>
    </form>

    <h3>🟢 Latest Room Status</h3>
    '''

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            last_line = f.readlines()[-1]
            parts = last_line.strip().split(",")
            html += f"<div class='report-box'><b>Room:</b> {parts[4]}<br><b>Temp:</b> {parts[1]}°C<br><b>Humidity:</b> {parts[2]}%<br><b>Status:</b> {parts[3]}</div>"

    html += "<h3>🧠 Last AI Reports</h3><ul>"
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            rows = f.readlines()[-10:]
            for r in reversed(rows):
                html += f"<li>{r}</li>"
    html += "</ul></body></html>"
    return html
@app.route("/save_settings", methods=["POST"])
def save_settings_route():
    device = request.form.get("device")
    temp_min = request.form.get("temp_min")
    temp_max = request.form.get("temp_max")
    settings = load_settings()
    settings[device] = {"temp_min": float(temp_min), "temp_max": float(temp_max)}
    save_settings(settings)
    return redirect("/")

@app.route("/settings")
def get_device_settings():
    device = request.args.get("device")
    settings = load_settings()
    if device in settings:
        return jsonify(settings[device])
    else:
        return jsonify({"error": "Device not found"}), 404

# OLD /report removed
def report():
    try:
        data = request.json
        temp = data.get("temperature")
        hum = data.get("humidity")
        status = data.get("status")
        temp_min = data.get("temp_min")
        temp_max = data.get("temp_max")
        device = data.get("device")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if None in [temp, hum, status, temp_min, temp_max, device]:
            return jsonify({"error": "Missing fields"}), 400

        with open(LOG_FILE, "a") as f:
            if os.stat(LOG_FILE).st_size == 0:
                f.write("timestamp,temperature,humidity,status,device\n")
            f.write(f"{now},{temp},{hum},{status},{device}\n")

        send_data_to_google_sheet(temp, hum, status)

        
        if float(temp) > float(temp_max):
            send_telegram_alert(f"🚨 {device} - High Temp {temp}°C! Cooling ON.")
        elif float(temp) < float(temp_min):
            send_telegram_alert(f"❄️ {device} - Low Temp {temp}°C! Heating ON.")

        report_text = f"Room: {device}\nTemp: {temp}°C\nHumidity: {hum}%\nStatus: {status}\nAI Suggestions:\n- Check thresholds\n- System running properly."
        return jsonify({"report": report_text})

    except Exception as e:
        logger.error(f"Error in report: {e}")
        return jsonify({"error": str(e)}), 500

def send_data_to_google_sheet(temp, hum, status):
    payload = {'temperature': temp, 'humidity': hum, 'status': status}
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, headers={'Content-Type': 'application/json'})
        logger.info(f"Google Sheet Response: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending to sheet: {e}")

@app.route("/chart")
def chart():
    labels, temps, hums = [], [], []
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()[1:][-50:]
            for line in lines:
                parts = line.strip().split(",")
                labels.append(parts[0][-8:])
                temps.append(float(parts[1]))
                hums.append(float(parts[2]))
    html = f'''
    <html>
    <head>
        <title>Chart</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
    <h3>📊 Last 50 Readings</h3>
    <canvas id="chart" width="900" height="400"></canvas>
    <script>
    new Chart(document.getElementById('chart'), {{
        type: 'line',
        data: {{
            labels: {labels},
            datasets: [
                {{
                    label: 'Temp (°C)',
                    data: {temps},
                    borderColor: 'red',
                    fill: false
                }},
                {{
                    label: 'Humidity (%)',
                    data: {hums},
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
    '''
    return html

if __name__ == "__main__":
    app.run(debug=True)


# Removed duplicate chart endpoint


import openai
import traceback
openai.api_key = os.getenv("OPENAI_API_KEY")



@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.json
        temp = data.get("temperature")
        hum = data.get("humidity")
        status = data.get("status")
        temp_min = data.get("temp_min")
        temp_max = data.get("temp_max")
        device = data.get("device")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if None in [temp, hum, status, temp_min, temp_max, device]:
            return jsonify({"error": "Missing fields"}), 400

        with open(LOG_FILE, "a") as f:
            if os.stat(LOG_FILE).st_size == 0:
                f.write("timestamp,temperature,humidity,status,device\n")
            f.write(f"{now},{temp},{hum},{status},{device}\n")

        send_data_to_google_sheet(temp, hum, status)

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
        """.strip()

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an IoT assistant that analyzes temperature and humidity data."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )

        final_report = response["choices"][0]["message"]["content"].strip()
        save_last_report(final_report)
        logger.info(f"Generated Report: {final_report}")
        return jsonify({"report": final_report})

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500
