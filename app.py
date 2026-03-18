from flask import Flask, request, jsonify, render_template_string
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import os
import time
import re
from collections import defaultdict

app = Flask(__name__)

print("🚀 Loading AMAZON OFFICIAL Customer Support Bot by Nisar Ahmad...")

# Ultra-fast DialoGPT-small
model_name = "microsoft/DialoGPT-small"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.float16, low_cpu_mem_usage=True)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

# 🌟 AMAZON 2026 PRODUCT DATABASE (Real Prices)
AMAZON_PRODUCTS = {
    "iphone": {"name": "iPhone 16 Pro 256GB", "price": "$999", "delivery": "Tomorrow (Prime)"},
    "macbook": {"name": "MacBook Air M3 512GB", "price": "$1,299", "delivery": "2 days"},
    "echo": {"name": "Echo Dot (5th Gen)", "price": "$49.99", "delivery": "Today (Prime)"},
    "fire tv": {"name": "Fire TV Stick 4K Max", "price": "$59.99", "delivery": "Tomorrow"},
    "kindle": {"name": "Kindle Paperwhite Signature", "price": "$189.99", "delivery": "2 days"},
    "laptop": {"name": "ASUS Vivobook 15 (Intel i5)", "price": "$499", "delivery": "3 days"},
    "headphones": {"name": "Sony WH-1000XM5", "price": "$349", "delivery": "Tomorrow"},
    "airpods": {"name": "AirPods Pro 2", "price": "$249", "delivery": "Today"},
    "tv": {"name": "Samsung 55\" QLED 4K", "price": "$799", "delivery": "5 days"}
}

# 💰 AMAZON SUPPORT RESPONSES
AMAZON_RESPONSES = {
    "refund": "✅ Your refund will be processed within **2-5 business days** to your original payment method. Check status at amazon.com/yourorders.",
    "return": "📦 Start your **free return** at **amazon.com/returns**. 30-day return window for most items. Label emailed instantly.",
    "cancel": "❌ You can **cancel unshipped orders** instantly at **amazon.com/yourorders**. Full refund immediately.",
    "order": "📋 Track your order at **amazon.com/yourorders**. Most Prime orders arrive in **1-2 days**.",
    "delivery": "🚚 **Prime**: Same-day/Tomorrow | **Standard**: 2-5 days | **Free shipping** over $35.",
    "prime": "👑 **Amazon Prime**: $14.99/month or $139/year. **Free 30-day trial**. Cancel anytime.",
    "account": "👤 Manage your account at **amazon.com/youraccount**. Update payment, addresses, subscriptions."
}

chat_sessions = defaultdict(lambda: None)
response_cache = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🤖 Amazon Customer Support</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 1000px; margin: auto; padding: 20px; background: linear-gradient(135deg, #ff9900 0%, #ff7b00 50%, #e67e22 100%); min-height: 100vh; }
        .header { text-align: center; margin-bottom: 30px; color: white; }
        .header h1 { font-size: 3em; margin-bottom: 10px; text-shadow: 0 4px 15px rgba(0,0,0,0.3); }
        .logo { font-size: 4em; display: block; margin-bottom: 10px; }
        .bio { background: rgba(255,255,255,0.95); color: #111; padding: 20px 30px; border-radius: 20px; margin-bottom: 25px; box-shadow: 0 15px 35px rgba(0,0,0,0.2); text-align: center; }
        .bio strong { color: #ff9900; font-size: 1.3em; }
        #chatbox { background: white; border-radius: 25px; height: 550px; overflow-y: auto; padding: 25px; margin-bottom: 20px; box-shadow: 0 25px 50px rgba(0,0,0,0.25); border: 3px solid #ff9900; }
        .message { margin: 18px 0; padding: 18px 25px; border-radius: 25px; max-width: 85%; word-wrap: break-word; animation: slideIn 0.4s ease; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        .user { background: linear-gradient(135deg, #232f3e, #1a2530); color: white; margin-left: auto; text-align: right; }
        .bot { background: linear-gradient(135deg, #ff9900, #ff7b00); color: white; margin-right: auto; font-weight: 500; }
        .input-group { display: flex; gap: 15px; backdrop-filter: blur(15px); padding: 25px; background: rgba(255,255,255,0.95); border-radius: 30px; box-shadow: 0 20px 40px rgba(0,0,0,0.15); }
        #message { flex: 1; padding: 20px 30px; border: 3px solid #e5e7eb; border-radius: 30px; font-size: 17px; outline: none; background: white; transition: all 0.3s; }
        #message:focus { border-color: #ff9900; box-shadow: 0 0 25px rgba(255,153,0,0.3); }
        button { padding: 20px 40px; background: linear-gradient(135deg, #232f3e, #1a2530); color: white; border: none; border-radius: 30px; font-size: 17px; font-weight: 600; cursor: pointer; transition: all 0.3s; }
        button:hover { transform: translateY(-4px); box-shadow: 0 20px 40px rgba(35,47,62,0.4); }
        .status { text-align: center; color: white; font-size: 1em; margin: 15px 0; font-weight: 500; text-shadow: 0 2px 10px rgba(0,0,0,0.3); }
        .footer { text-align: center; margin-top: 30px; color: rgba(255,255,255,0.95); font-size: 1em; padding: 20px; background: rgba(0,0,0,0.2); border-radius: 20px; }
        @keyframes slideIn { from { opacity: 0; transform: translateY(25px); } to { opacity: 1; transform: translateY(0); } }
        a { color: #3b82f6; text-decoration: none; font-weight: 600; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">🛒</div>
        <h1>Amazon Customer Support</h1>
        <p>Official AI Assistant | Orders • Returns • Pricing • Prime</p>
        <div class="bio">
            <strong>👨‍💻 Developed by Nisar Ahmad</strong><br>
            <em>AI Developer | CUI Sahiwal, Pakistan | Custom Chatbot Specialist<br>
            <a href="https://github.com/nisar_ai" target="_blank">github.com/nisarai</a> | Fiverr: nisar_ahmad_1</em>
        </div>
    </div>
    <div id="chatbox">
        <div class="message bot">Hello! I'm your <strong>Amazon Customer Support Assistant</strong>. I can help with orders, returns, pricing, Prime, and more! 🛒<br><br>How can I assist you today?</div>
    </div>
    <div class="input-group">
        <input type="text" id="message" placeholder="Ask about iPhone price, refunds, delivery..." onkeypress="if(event.key==='Enter') sendMessage()">
        <button onclick="sendMessage()">Send 🚀</button>
    </div>
    <div class="status">⚡ Ultra-fast responses | Optimized for Amazon support</div>
    <div class="footer">
        🚀 Built by <strong>Nisar Ahmad</strong> | CUI Sahiwal Campus | <a href="https://github.com/nisarai" target="_blank">github.com/nisarai</a>
    </div>

    <script>
        async function sendMessage() {
            const msg = document.getElementById('message').value.trim();
            if (!msg) return;
            
            addMessage(msg, 'user');
            document.getElementById('message').value = '';
            
            const typingMsg = addMessage('🤖 Amazon Support is typing...', 'bot');
            
            try {
                const start = performance.now();
                const res = await fetch('/chat', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({message: msg})
                });
                const data = await res.json();
                const end = performance.now();
                
                typingMsg.remove();
                addMessage(data.reply || 'Sorry, I could not process that.', 'bot');
            } catch(e) {
                typingMsg.remove();
                addMessage('Connection error. Please try again.', 'bot');
            }
        }
        
        function addMessage(text, className) {
            const chatbox = document.getElementById('chatbox');
            const div = document.createElement('div');
            div.className = `message ${className}`;
            div.innerHTML = text;
            chatbox.appendChild(div);
            chatbox.scrollTop = chatbox.scrollHeight;
            return div;
        }
    </script>
</body>
</html>
"""

def get_amazon_response(message):
    """Amazon-specific instant responses"""
    message_lower = message.lower()
    
    # 💰 PRODUCT PRICING
    for product, info in AMAZON_PRODUCTS.items():
        if product in message_lower:
            return f"🛒 **{info['name']}** on Amazon:\n💰 **Price**: {info['price']}\n🚚 **Delivery**: {info['delivery']}\n\nAdd to cart at amazon.com/{product.replace(' ', '-')}"
    
    # 📋 SUPPORT QUERIES
    for keyword, response in AMAZON_RESPONSES.items():
        if keyword in message_lower:
            return response
    
    # Quick responses
    if any(word in message_lower for word in ["hello", "hi", "hey"]):
        return "Hello! Welcome to Amazon Customer Support. How can I help you today? 🛒"
    
    if "thank" in message_lower:
        return "You're welcome! Is there anything else I can help you with? 😊"
    
    return None

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/chat", methods=['POST'])
def chat():
    start_time = time.time()
    
    try:
        data = request.json
        message = data.get('message', '').strip()
        if not message:
            return jsonify({'reply': 'Please send a message.'})

        session_id = data.get('session_id', 'default')
        chat_history_ids = chat_sessions[session_id]

        # ⚡ INSTANT AMAZON RESPONSES (0.01 sec)
        amazon_reply = get_amazon_response(message)
        if amazon_reply:
            end_time = time.time()
            print(f"🛒 AMAZON INSTANT: {end_time-start_time:.2f}s")
            return jsonify({'reply': amazon_reply})

        # ⚡ ULTRA-FAST DIALOGPT
        with torch.no_grad():
            new_user_input_ids = tokenizer.encode(message + tokenizer.eos_token, return_tensors='pt')
            
            if chat_history_ids is not None:
                bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids], dim=-1)
            else:
                bot_input_ids = new_user_input_ids

            chat_history_ids = model.generate(
                bot_input_ids,
                max_new_tokens=40,
                temperature=0.7,
                top_p=0.9,
                top_k=40,
                pad_token_id=tokenizer.eos_token_id,
                do_sample=True,
                repetition_penalty=1.1,
                use_cache=True
            )

        chat_sessions[session_id] = chat_history_ids
        response = tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
        
        end_time = time.time()
        print(f"⚡ DIALOGPT: {end_time-start_time:.2f}s | '{response.strip()}'")
        
        return jsonify({'reply': response.strip()})

    except Exception as e:
        end_time = time.time()
        print(f"❌ ERROR: {end_time-start_time:.2f}s - {e}")
        return jsonify({'reply': 'Sorry, our Amazon support team is experiencing technical difficulties. Please try again or visit amazon.com/contact-us.'}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print("🚀 AMAZON BOT + NISARAI BRANDING STARTED on port", port)
    app.run(host="0.0.0.0", port=port, debug=False)
