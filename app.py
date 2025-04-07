from flask import Flask, request, jsonify
import requests
import os
import datetime

app = Flask(__name__)

# اقرأ التوكن من متغير بيئة
HUGGINGFACE_API_KEY = os.getenv("HF_API_KEY")

@app.route("/")
def home():
    return "✅ Mistral AI server is running."

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.json
        temp = data.get("temperature")
        hum = data.get("humidity")
        status = data.get("status")
        now = datetime.datetime.now().strftime("%H:%M")

        # إعداد الطلب
        prompt = f"""
The smart control device recorded the following:
- Temperature: {temp}°C
- Humidity: {hum}%
- System status: {status}
- Time: {now}

Please generate a short, professional report in English that summarizes the current state and gives suggestions if needed.
Only include the final report, do not repeat the data above.
"""

        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 100,
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
            return jsonify({"report": result[0]["generated_text"]})
        else:
            return jsonify({"error": "Failed to generate report", "details": result}), 500

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
