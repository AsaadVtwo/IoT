import os
import openai
import requests
import datetime
from flask import Flask, request, jsonify

# إنشاء تطبيق Flask
app = Flask(__name__)

# مفتاح OpenAI API من المتغير البيئي
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
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if None in [temp, hum, status, temp_min, temp_max]:
            return jsonify({"error": "Missing fields in JSON!"}), 400

        # تخزين البيانات في CSV (اختياري)
        with open("log.csv", "a") as log_file:
            if os.stat("log.csv").st_size == 0:
                log_file.write("timestamp,temperature,humidity,status\n")
            log_file.write(f"{now},{temp},{hum},{status}\n")

        # بناء الـ Prompt
        user_prompt = f"""
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

        # استدعاء OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an IoT assistant that analyzes temperature and humidity data."},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=300
        )

        final_report = response.choices[0].message.content.strip()
        return jsonify({"report": final_report})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500
