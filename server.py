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

# Shopify Webhook Secret (replace with your actual secret)
SHOPIFY_WEBHOOK_SECRET = "a236ce4d313d04271e6b43e65c945f9df0105c71e73695280c2080c709f82e5c"

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///orders.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Order model
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

# Customer model (lightweight storage)
class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shopify_customer_id = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(50), default="Unknown")

    def __init__(self, shopify_customer_id, email, country):
        self.shopify_customer_id = shopify_customer_id
        self.email = email
        self.country = country

# Create tables
with app.app_context():
    db.create_all()

# Webhook verification
def verify_shopify_webhook(data, hmac_header):
    if not hmac_header:
        print("❌ No HMAC header received from Shopify")
        return False

    try:
        print(f"📝 Raw Webhook Data: {data.decode('utf-8')}")

        calculated_hmac = hmac.new(
            SHOPIFY_WEBHOOK_SECRET.encode('utf-8'),
            data,
            hashlib.sha256
        ).digest()

        expected_hmac_base64 = base64.b64encode(calculated_hmac).decode('utf-8').strip()
        received_hmac_base64 = hmac_header.strip()

        print(f"🔍 Expected HMAC: {expected_hmac_base64}")
        print(f"🔍 Received HMAC: {received_hmac_base64}")

        return hmac.compare_digest(expected_hmac_base64, received_hmac_base64)
    except Exception as e:
        print(f"❌ HMAC Verification Error: {str(e)}")
        return False

# Deploy MT5 bot function
def deploy_mt5_bot(api_key, customer_email):
    mt5_api_url = "https://your-mt5-server.com/deploy-bot"  # Replace with real URL
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

# Webhook route
@app.route("/", methods=["POST"])
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_data()
    hmac_header = request.headers.get("X-Shopify-Hmac-SHA256")

    if not verify_shopify_webhook(data, hmac_header):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        json_data = json.loads(data)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid JSON payload"}), 400

    print("🔹 Verified Shopify Webhook Data:")
    print(json.dumps(json_data, indent=4))

    # Handle customer webhooks
    if "email" in json_data and "addresses" in json_data:
        shopify_customer_id = str(json_data.get("id"))
        email = json_data.get("email", "unknown@example.com")
        country = json_data.get("default_address", {}).get("country", "Unknown")

        existing_customer = Customer.query.filter_by(shopify_customer_id=shopify_customer_id).first()
        if existing_customer:
            print(f"👤 Customer already exists: {email}")
        else:
            new_customer = Customer(
                shopify_customer_id=shopify_customer_id,
                email=email,
                country=country
            )
            db.session.add(new_customer)
            db.session.commit()
            print(f"👤 Stored new customer: {email} from {country}")

        return jsonify({"message": "Customer webhook processed"}), 200

    # Handle order webhooks
    elif "id" in json_data and "customer" in json_data:
        shopify_order_id = str(json_data.get("id"))
        customer_email = json_data.get("customer", {}).get("email", "unknown@example.com")

        existing_order = Order.query.filter_by(shopify_order_id=shopify_order_id).first()
        if existing_order:
            return jsonify({"message": "Order already exists"}), 200

        new_order = Order(shopify_order_id=shopify_order_id, customer_email=customer_email)
        db.session.add(new_order)
        db.session.commit()

        print(f"✅ Order {shopify_order_id} stored with API Key: {new_order.api_key}")

        deployment_success = deploy_mt5_bot(new_order.api_key, customer_email)

        if deployment_success:
            new_order.status = "deployed"
            db.session.commit()
            return jsonify({"message": "Bot deployed successfully", "api_key": new_order.api_key}), 200
        else:
            return jsonify({"error": "Bot deployment failed"}), 500

    else:
        print("⚠️ Unrecognized webhook format")
        return jsonify({"message": "Webhook type not recognized"}), 200

# API key retrieval endpoint
@app.route("/get-api-key", methods=["GET"])
def get_api_key():
    customer_email = request.args.get("email")
    if not customer_email:
        return jsonify({"error": "Email parameter is required"}), 400

    order = Order.query.filter_by(customer_email=customer_email).first()
    if not order:
        return jsonify({"error": "No API key found for this email"}), 404

    return jsonify({"api_key": order.api_key, "order_status": order.status}), 200

# Run the server
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
