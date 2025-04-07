from flask import Flask, request, jsonify
import requests
import datetime
import os

app = Flask(__name__)

HUGGINGFACE_API_KEY = os.getenv("HF_API_KEY")

@app.route("/")
def home():
    return "✅ خادم Hugging Face يعمل بشكل جيد"

@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.json
        temp = data.get("temperature")
        hum = data.get("humidity")
        status = data.get("status")
        now = datetime.datetime.now().strftime("%H:%M")

        prompt = f"""
تم تسجيل القيم التالية بواسطة جهاز تحكم ذكي:
- درجة الحرارة: {temp} درجة مئوية
- الرطوبة: {hum}٪
- حالة النظام: {status}
- الوقت: {now}

من فضلك أنشئ تقريرًا موجزًا باللغة العربية يوضح الحالة ويوصي بما يجب فعله إن لزم.
"""
        prompt += "\n\nاكتب فقط تقريرًا مختصرًا باللغة العربية يوضح حالة النظام ويوصي بما يجب فعله. لا تكرر البيانات أعلاه."

        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 80,
                "temperature": 0.7,
                "do_sample": True
            }
        }

        response = requests.post(
            "https://api-inference.huggingface.co/models/deepseek-ai/deepseek-coder-6.7b-instruct",
            headers=headers,
            json=payload
        )

        result = response.json()

        if isinstance(result, list) and "generated_text" in result[0]:
            report_text = result[0]["generated_text"].replace(prompt.strip(), "").strip()
        else:
            report_text = result.get("error", "تعذر توليد التقرير.")

        return jsonify({"report": report_text})

    except Exception as e:
        return jsonify({"error": "حدث خطأ في الخادم", "details": str(e)}), 500
