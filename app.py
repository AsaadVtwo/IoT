@app.route("/report", methods=["POST"])
def report():
    try:
        data = request.json
        temp = data.get("temperature")
        hum = data.get("humidity")
        status = data.get("status")
        temp_min = data.get("temp_min", 20.0)
        temp_max = data.get("temp_max", 30.0)
        now = datetime.datetime.now().strftime("%H:%M")

        prompt = f"""
The smart environment control system has received the following data:

- Current Temperature: {temp}°C
- Current Humidity: {hum}%
- System Status: {status}
- Time of Reading: {now}

The system is configured by the user with the following thresholds:
- Minimum acceptable temperature: {temp_min}°C
- Maximum acceptable temperature: {temp_max}°C

Please analyze the current state based on these thresholds:
1. Is the current temperature within the acceptable range?
2. Is the humidity acceptable for typical indoor environments?
3. Was the system's action (heating/cooling/off) appropriate?
4. Are the thresholds chosen by the user reasonable?
5. Suggest better thresholds if necessary.

Then generate a short, professional report that answers these points clearly.
Do not repeat the raw data. Just include your analysis and recommendations.
"""

        headers = {
            "Authorization": f"Bearer {HUGGINGFACE_API_KEY}"
        }

        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 150,
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
            generated_text = result[0]["generated_text"]
            final_report = generated_text.split("Just include your analysis and recommendations.")[-1].strip()
            return jsonify({"report": final_report})
        else:
            return jsonify({"error": "Failed to generate report", "details": result}), 500

    except Exception as e:
        return jsonify({"error": "Server error", "details": str(e)}), 500
