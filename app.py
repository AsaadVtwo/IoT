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
            logger.error("Missing fields in JSON!")
            return jsonify({"error": "Missing fields in JSON!"}), 400

        # سجل البيانات في ملف CSV
        with open("log.csv", "a") as log_file:
            if os.stat("log.csv").st_size == 0:
                log_file.write("timestamp,temperature,humidity,status\n")
            log_file.write(f"{now},{temp},{hum},{status}\n")

        # إرسال البيانات إلى Google Sheets
        send_data_to_google_sheet(temp, hum, status)

        # بناء الـ prompt لتحليل البيانات عبر OpenAI
        prompt = f"""
        System Reading:
        - Temperature: {temp}°C
        - Humidity: {hum}%
        - Status: {status}
        - Time: {now}

        User Settings:
        - Minimum temperature: {temp_min}°C
        - Maximum temperature: {temp_max}°C

        Please generate a short English AND ARABIC report that:
        1. Analyzes whether the current values are within the user-defined thresholds.
        2. Evaluates whether the system behavior is appropriate.
        3. Checks if the thresholds are reasonable and provides suggestions.
        Do not repeat the input. Write a concise and helpful professional summary in both English and Arabic.
        """

        # استدعاء GPT-3.5 لتحليل البيانات
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are an IoT assistant that analyzes temperature and humidity data."},
                      {"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500  # زيادة عدد التوكنات للسماح بتوليد التقرير باللغتين
        )

        # الحصول على التقرير النهائي
        final_report = response.choices[0].message.content.strip()
        logger.info(f"Generated Report: {final_report}")

        # إرجاع التقرير في صفحة HTML
        html_response = f"""
        <!DOCTYPE html>
        <html lang="ar">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>تقرير الذكاء الاصطناعي</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f9;
                    color: #333;
                    text-align: center;
                    margin: 0;
                    padding: 0;
                }}
                h1 {{
                    color: #0078D4;
                    font-size: 24px;
                    margin-bottom: 20px;
                }}
                pre {{
                    font-size: 16px;
                    background-color: #f0f0f0;
                    padding: 15px;
                    border-radius: 5px;
                    text-align: left;
                    max-width: 80%;
                    margin: auto;
                    white-space: pre-wrap; /* لف النص */
                    word-wrap: break-word; /* كسر الكلمات الطويلة */
                }}
            </style>
        </head>
        <body>
            <h1>تقرير الذكاء الاصطناعي</h1>
            <h2>النسخة الإنجليزية:</h2>
            <pre>{final_report.split("Arabic Report:")[0].strip()}</pre>  <!-- عرض التقرير بالإنجليزية -->
            <h2>النسخة العربية:</h2>
            <pre>{final_report.split("Arabic Report:")[1].strip()}</pre>  <!-- عرض التقرير بالعربية -->
        </body>
        </html>
        """
        return html_response

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500
