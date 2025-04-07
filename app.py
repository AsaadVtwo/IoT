from flask import Flask, request, jsonify
import requests
import datetime
import os

app = Flask(__name__)

# اقرأ التوكن الخاص بك من متغير بيئة (لتبقى آمنًا)
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

        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 100
            }
        }

        response = requests.post(
    "https://api-inference.huggingface.co/models/tiiuae/falcon-7b-instruct",
    headers=headers,
    json=payload
)


        result = response.json()

        if isinstance(result, list):
            report_text = result[0]["generated_text"]
        else:
            report_text = result.get("error", "تعذر توليد التقرير.")

        return jsonify({"report": report_text})

    except Exception as e:
        return jsonify({"error": "حدث خطأ في الخادم", "details": str(e)}), 500
