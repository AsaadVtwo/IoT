from flask import Flask, request, jsonify
import requests
import datetime
import os

app = Flask(__name__)

HUGGINGFACE_API_KEY = os.getenv("HF_API_KEY")

@app.route("/")
def home():
    return "✅ خادم Falcon يعمل بنجاح"

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
اكتب فقط التقرير بدون إعادة كتابة البيانات السابقة.
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
            "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct",
            headers=headers,
            json=payload
        )

        result = response.json()

        if isinstance(result, list) and "generated_text" in result[0]:
            report_text = result[0]["generated_text"]
        else:
            report_text = result.get("error", "تعذر توليد التقرير.")

        return jsonify({"report": report_text})

    except Exception as e:
        return jsonify({"error": "حدث خطأ في الخادم", "details": str(e)}), 500
