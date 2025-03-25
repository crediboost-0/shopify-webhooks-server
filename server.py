import hmac
import hashlib
import base64
import json
from flask import Flask, request, jsonify

# Initialize Flask app
app = Flask(__name__)

# Replace this with your actual Shopify webhook secret
SHOPIFY_WEBHOOK_SECRET = "a236ce4d313d04271e6b43e65c945f9df0105c71e73695280c2080c709f82e5c"

def verify_shopify_webhook(data, hmac_header):
    """Verify Shopify webhook signature"""
    calculated_hmac = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
        data,
        hashlib.sha256
    ).digest()
    calculated_hmac_base64 = base64.b64encode(calculated_hmac).decode('utf-8')
    return hmac.compare_digest(calculated_hmac_base64, hmac_header)

@app.route("/", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_data()  # Get raw request data
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")
    
    if not hmac_header or not verify_shopify_webhook(data, hmac_header):
        return jsonify({"error": "Unauthorized"}), 401
    
    json_data = json.loads(data)
    print("🔹 Verified Shopify Webhook Data:", json.dumps(json_data, indent=4))
    
    # Process the webhook data (e.g., trigger bot deployment, update database, etc.)
    
    return jsonify({"message": "Webhook received and verified!"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
