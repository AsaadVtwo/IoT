from flask import Flask, request, jsonify
import openai
import datetime
import os

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")  # مفتاح من متغير بيئة

@app.route("/")
def home():
    return "خادم الذكاء التوليدي يعمل ✅"

@app.route("/report", methods=["POST"])
def report():
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

    من فضلك أنشئ تقريرًا موجزًا باللغة العربية يوضح الحالة الحالية ويوصي بما يجب فعله إن لزم.
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    report_text = response["choices"][0]["message"]["content"]
    return jsonify({"report": report_text})
