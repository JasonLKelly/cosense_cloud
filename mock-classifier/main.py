"""Mock AutoML classifier endpoint for testing.

Returns random classifications in Vertex AI prediction format.
Deploy to Cloud Run and use the URL in Flink SQL.
"""

import random
from flask import Flask, request, jsonify

app = Flask(__name__)

CATEGORIES = ["NORMAL", "HUMAN_FACTOR", "EQUIPMENT", "ENVIRONMENTAL"]


@app.route("/v1/projects/<project>/locations/<location>/endpoints/<endpoint>:predict", methods=["POST"])
def predict(project, location, endpoint):
    """Mock Vertex AI prediction endpoint."""
    data = request.get_json()
    instances = data.get("instances", [])

    predictions = []
    for instance in instances:
        # Simple heuristic based on input values (mimics what AutoML would learn)
        decision_count = instance.get("decision_count", 0)
        stop_count = instance.get("stop_count", 0)
        slow_count = instance.get("slow_count", 0)
        sensor_disagreement = instance.get("sensor_disagreement_count", 0)

        # Apply the same logic as the training data patterns
        if sensor_disagreement >= 3:
            category = "EQUIPMENT"
            confidence = 0.75 + random.uniform(0, 0.2)
        elif stop_count >= 4 and decision_count >= 15:
            category = "HUMAN_FACTOR"
            confidence = 0.70 + random.uniform(0, 0.25)
        elif slow_count >= 10 and slow_count > stop_count * 3:
            category = "ENVIRONMENTAL"
            confidence = 0.72 + random.uniform(0, 0.2)
        elif decision_count <= 14 and stop_count <= 2:
            category = "NORMAL"
            confidence = 0.85 + random.uniform(0, 0.12)
        else:
            # Random fallback with slight bias toward NORMAL
            category = random.choices(
                CATEGORIES,
                weights=[0.4, 0.25, 0.15, 0.2]
            )[0]
            confidence = 0.55 + random.uniform(0, 0.3)

        predictions.append({
            "category": category,
            "confidence": round(confidence, 3)
        })

    return jsonify({"predictions": predictions})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"})


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
