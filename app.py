
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
    html = '''
    <h2>🌡️ Temperature Configuration</h2>
    <form action="/save_settings" method="POST">
        <label>Select Room:</label>
        <select name="device">
            <option value="room1">Room 1</option>
            <option value="room2">Room 2</option>
        </select><br><br>
        <label>Temp Min:</label>
        <input type="number" name="temp_min" step="0.1"><br><br>
        <label>Temp Max:</label>
        <input type="number" name="temp_max" step="0.1"><br><br>
        <button type="submit">💾 Save Settings</button>
    </form>
    <hr>
    <h3>📄 Last AI Reports:</h3>
    <ul>
    '''
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            rows = f.readlines()[-10:]
            for r in reversed(rows):
                html += f"<li>{r}</li>"
    html += "</ul>"
    return render_template_string(html)

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
    <!DOCTYPE html>
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


def send_telegram_alert(message):
    token = "7957608560:AAFi-qgB52eGSkPAn1KnhmT4iYFcETim1Lc"
    chat_id = "1172667635"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")



@app.route("/stats")
def stats():
    import pandas as pd
    if not os.path.exists(LOG_FILE):
        return "No data yet."

    df = pd.read_csv(LOG_FILE)
    room_data = {}
    for room in df['device'].unique():
        sub = df[df['device'] == room]
        stats = {
            "max_temp": sub["temperature"].max(),
            "min_temp": sub["temperature"].min(),
            "avg_temp": round(sub["temperature"].mean(), 2),
            "avg_hum": round(sub["humidity"].mean(), 2),
            "cooling_count": (sub["status"] == "cooling").sum(),
            "heating_count": (sub["status"] == "heating").sum()
        }
        room_data[room] = stats

    html = "<h2>📊 System Statistics</h2>"
    for room, s in room_data.items():
        html += f"<h3>Room: {room}</h3><ul>"
        html += f"<li>🌡️ Max Temp: {s['max_temp']}°C</li>"
        html += f"<li>❄️ Min Temp: {s['min_temp']}°C</li>"
        html += f"<li>📈 Avg Temp: {s['avg_temp']}°C</li>"
        html += f"<li>💧 Avg Humidity: {s['avg_hum']}%</li>"
        html += f"<li>🔁 Cooling Count: {s['cooling_count']}</li>"
        html += f"<li>🔥 Heating Count: {s['heating_count']}</li></ul><hr>"
    return html
