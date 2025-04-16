import os
import json
import datetime
import logging
import requests
import openai
import traceback
from flask import Flask, request, jsonify, render_template, redirect

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

def send_data_to_google_sheet(temp, hum, status):
    payload = {'temperature': temp, 'humidity': hum, 'status': status}
    try:
        response = requests.post(GOOGLE_SCRIPT_URL, json=payload, headers={'Content-Type': 'application/json'})
        logger.info(f"Google Sheet Response: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending to sheet: {e}")

@app.route("/", methods=["GET"])
def index():
    return render_template("templates_room_tabs.html")

@app.route("/status")
def get_status():
    device = request.args.get("device")
    try:
        if not os.path.exists(LOG_FILE):
            return jsonify({"error": "Log file does not exist"})
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()[1:]
            last = next(line for line in reversed(lines) if device in line)
            parts = last.strip().split(",")
            return jsonify({
                "timestamp": parts[0],
                "temperature": float(parts[1]),
                "humidity": float(parts[2]),
                "status": parts[3],
                "report": load_last_report()
            })
    except Exception as e:
        return jsonify({"error": "No data for this device", "details": str(e)}), 404

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

        prompt = (
            f"System Reading:\n"
            f"- Temperature: {temp}°C\n"
            f"- Humidity: {hum}%\n"
            f"- Status: {status}\n"
            f"- Time: {now}\n\n"
            f"User Settings:\n"
            f"- Minimum temperature: {temp_min}°C\n"
            f"- Maximum temperature: {temp_max}°C\n\n"
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

@app.route("/generate_from_logs", methods=["POST"])
def generate_from_logs():
    device = request.args.get("device")
    try:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()[1:]
            last = next((line for line in reversed(lines) if device in line), None)
            if not last:
                return jsonify({"error": "No logs for this device"}), 404
            parts = last.strip().split(",")
            temp = float(parts[1])
            hum = float(parts[2])
            status = parts[3]

        settings = load_settings()
        temp_min = settings.get(device, {}).get("temp_min", 20)
        temp_max = settings.get(device, {}).get("temp_max", 30)

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        prompt = (
            f"System Reading:\n"
            f"- Temperature: {temp}°C\n"
            f"- Humidity: {hum}%\n"
            f"- Status: {status}\n"
            f"- Time: {now}\n\n"
            f"User Settings:\n"
            f"- Minimum temperature: {temp_min}°C\n"
            f"- Maximum temperature: {temp_max}°C\n\n"
            "Please generate a short English report that:\n"
            "1. Analyzes whether the current values are within the user-defined thresholds.\n"
            "2. Evaluates whether the system behavior is appropriate.\n"
            "3. Checks if the thresholds are reasonable and provides suggestions.\n"
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

        return jsonify({
            "temperature": temp,
            "humidity": hum,
            "status": status,
            "report": final_report
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
