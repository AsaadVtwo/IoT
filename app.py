import os
import json
import datetime
import logging
import requests
import openai
import traceback
from flask import Flask, request, jsonify, render_template_string, redirect

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"
LOG_FILE = "log.csv"
LAST_REPORT_FILE = "/tmp/last_report.txt"
GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbybDA0fCsJG7_OeU4TYaxqDSfFKboKtL0hdcxSWLRahC66zmAmAzAV8SYMr3O5Cu9kx/exec'

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    <html><head><style>
    body {{ font-family: Arial; background: #f4f4f9; text-align: center; }}
    .report-box {{ background: #e8f0fe; padding: 15px; border-radius: 5px; margin: 10px auto; width: 90%; max-width: 600px; text-align: left; }}
    </style></head><body>
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
    '''

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            last_line = f.readlines()[-1]
            parts = last_line.strip().split(",")
            html += f"<h3>🟢 Latest Room Status</h3><div class='report-box'><b>Room:</b> {parts[4]}<br><b>Temp:</b> {parts[1]} degrees<br><b>Humidity:</b> {parts[2]}%<br><b>Status:</b> {parts[3]}</div>"

    html += f"<h3>🧠 AI Summary Report</h3><div class='report-box'>{load_last_report()}</div>"
    html += "</body></html>"
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

        prompt = (
            f"System Reading:\n"
            f"- Temperature: {temp} degrees\n"
            f"- Humidity: {hum}%\n"
            f"- Status: {status}\n"
            f"- Time: {now}\n\n"
            f"User Settings:\n"
            f"- Minimum temperature: {temp_min} degrees\n"
            f"- Maximum temperature: {temp_max} degrees\n\n"
            "Please generate a short English report that:\n"
            "1. Analyzes whether the current values are within the user-defined thresholds.\n"
            "2. Evaluates whether the system behavior is appropriate.\n"
            "3. Checks if the thresholds are reasonable and provides suggestions.\n"
            "Do not repeat the input. Write a concise and helpful professional summary."
        )

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
        save_last_report(final_report)
        return jsonify({"report": final_report})

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500
