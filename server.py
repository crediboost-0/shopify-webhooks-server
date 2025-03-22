from flask import Flask, request, jsonify

app = Flask(__name__)

# Catch-all webhook (for debugging)
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("🔹 Received Webhook:", data)
    return jsonify({"message": "Webhook received!"}), 200

# Order Created Webhook
@app.route("/orders-created", methods=["POST"])
def orders_created():
    data = request.json
    print("🛒 Order Created:", data)
    return jsonify({"message": "Order webhook received"}), 200

# Subscription Created Webhook
@app.route("/subscription-created", methods=["POST"])
def subscription_created():
    data = request.json
    print("📅 Subscription Created:", data)
    return jsonify({"message": "Subscription created webhook received"}), 200

# Subscription Updated Webhook
@app.route("/subscription-updated", methods=["POST"])
def subscription_updated():
    data = request.json
    print("✏️ Subscription Updated:", data)
    return jsonify({"message": "Subscription updated webhook received"}), 200

# Subscription Cancelled Webhook
@app.route("/subscription-cancelled", methods=["POST"])
def subscription_cancelled():
    data = request.json
    print("❌ Subscription Cancelled:", data)
    return jsonify({"message": "Subscription cancelled webhook received"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
