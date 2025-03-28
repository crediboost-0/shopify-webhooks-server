import hmac
import hashlib
import base64
import json
import uuid
import requests
import os
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

# Initialize Flask app
app = Flask(__name__)

# Shopify Webhook Secret (Replace with your actual secret)
SHOPIFY_WEBHOOK_SECRET = "a236ce4d313d04271e6b43e65c945f9df0105c71e73695280c2080c709f82e5c"

# Database Configuration (Replace with your actual database)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///orders.db"  # Change to PostgreSQL/MySQL if needed
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Order Model
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shopify_order_id = db.Column(db.String(50), unique=True, nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    api_key = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(50), default="pending")

    def __init__(self, shopify_order_id, customer_email):
        self.shopify_order_id = shopify_order_id
        self.customer_email = customer_email
        self.api_key = str(uuid.uuid4())  # Generate unique API key

# Create tables
with app.app_context():
    db.create_all()

# Shopify Webhook Verification
def verify_shopify_webhook(data, hmac_header):
    """Verify Shopify webhook signature"""
    if not hmac_header:
        print("❌ No HMAC header received from Shopify")
        return False

    # Generate HMAC using the shared secret
    calculated_hmac = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
        data,
        hashlib.sha256
    ).digest()

    # Base64 encode it to match Shopify's header format and strip whitespace
    expected_hmac_base64 = base64.b64encode(calculated_hmac).decode('utf-8').strip()
    received_hmac_base64 = hmac_header.strip()

    # Log for debugging
    print(f"🔍 Expected HMAC: {expected_hmac_base64}")
    print(f"🔍 Received HMAC: {received_hmac_base64}")

    return hmac.compare_digest(expected_hmac_base64, received_hmac_base64)

# Function to Deploy MT5 Bot
def deploy_mt5_bot(api_key, customer_email):
    """Trigger MT5 Bot Deployment"""
    mt5_api_url = "https://your-mt5-server.com/deploy-bot"  # Replace with actual MT5 API endpoint
    payload = {
        "api_key": api_key,
        "email": customer_email
    }

    try:
        response = requests.post(mt5_api_url, json=payload)
        if response.status_code == 200:
            print(f"🚀 MT5 Bot Deployed for {customer_email}")
            return True
        else:
            print(f"⚠️ Deployment failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Deployment Error: {str(e)}")
        return False

# Webhook Route
@app.route("/", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_data()  # Get raw request data
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")

    if not verify_shopify_webhook(data, hmac_header):
        return jsonify({"error": "Unauthorized"}), 401

    json_data = json.loads(data)
    print("🔹 Verified Shopify Webhook Data:", json.dumps(json_data, indent=4))

    # Extract Order Data
    shopify_order_id = str(json_data.get("id"))
    customer_email = json_data.get("email", "unknown@example.com")  # Fallback email

    # Check if order already exists
    existing_order = Order.query.filter_by(shopify_order_id=shopify_order_id).first()
    if existing_order:
        return jsonify({"message": "Order already exists"}), 200

    # Create new order entry
    new_order = Order(shopify_order_id=shopify_order_id, customer_email=customer_email)
    db.session.add(new_order)
    db.session.commit()

    print(f"✅ Order {shopify_order_id} stored with API Key: {new_order.api_key}")

    # Deploy MT5 Bot
    deployment_success = deploy_mt5_bot(new_order.api_key, customer_email)

    if deployment_success:
        new_order.status = "deployed"
        db.session.commit()
        return jsonify({"message": "Bot deployed successfully", "api_key": new_order.api_key}), 200
    else:
        return jsonify({"error": "Bot deployment failed"}), 500

# Endpoint to Retrieve API Key
@app.route("/get-api-key", methods=["GET"])
def get_api_key():
    customer_email = request.args.get("email")
    if not customer_email:
        return jsonify({"error": "Email parameter is required"}), 400

    order = Order.query.filter_by(customer_email=customer_email).first()
    if not order:
        return jsonify({"error": "No API key found for this email"}), 404

    return jsonify({"api_key": order.api_key, "order_status": order.status}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Default to 10000, but Render will set PORT dynamically
    app.run(host="0.0.0.0", port=port)
