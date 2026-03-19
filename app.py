from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import threading
import time
import os
import sys
import json
import signal

app = Flask(__name__)
CORS(app)

# ===============================
# 🔐 ENVIRONMENT VARIABLES (Render)
# ===============================
API_KEY = os.environ.get("API_KEY", "MAINUL_X_SECURE")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "@MaiNul@ff_tcp_bot##")
USER_PASS = os.environ.get("USER_PASS", "1234")

# ===============================
# 🌍 GLOBAL VARIABLES
# ===============================
bot_processes = {}
console_logs = {}
bot_start_times = {}
server_start_time = time.time()

# ===============================
# 📁 PATH FIX - main.py খুঁজে বের করা
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# সম্ভাব্য লোকেশনগুলো চেক করা
possible_paths = [
    os.path.join(BASE_DIR, "main.py"),
    os.path.join(BASE_DIR, "tcp_bot_ff", "main.py"),
    os.path.join(BASE_DIR, "bot", "main.py"),
    os.path.join(BASE_DIR, "src", "main.py")
]

MAIN_PY_PATH = None
for path in possible_paths:
    if os.path.exists(path):
        MAIN_PY_PATH = path
        break

if not MAIN_PY_PATH:
    MAIN_PY_PATH = os.path.join(BASE_DIR, "main.py")  # ডিফল্ট

# ===============================
# 📁 ACCOUNTS FILE MANAGEMENT
# ===============================
ACCOUNTS_FILE = "accounts.json"

def load_accounts():
    """accounts.json ফাইল থেকে অ্যাকাউন্ট লোড করে"""
    try:
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, 'r') as f:
                return json.load(f)
        else:
            # ফাইল না থাকলে খালি ডিকশনারি তৈরি
            with open(ACCOUNTS_FILE, 'w') as f:
                json.dump({}, f)
            return {}
    except Exception as e:
        print(f"Error loading accounts: {e}")
        return {}

def save_accounts(data):
    """accounts.json ফাইলে অ্যাকাউন্ট সেভ করে"""
    try:
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving accounts: {e}")

# ===============================
# 🔑 API KEY CHECK
# ===============================
def check_key(req):
    """রিকোয়েস্টের API_KEY চেক করে"""
    api_key = req.headers.get('x-api-key')
    if not api_key:
        api_key = req.args.get('api_key')
    return api_key == API_KEY

# ===============================
# 📝 CONSOLE LOGGING
# ===============================
def add_log(uid, text):
    """কনসোলে লগ যোগ করে"""
    timestamp = time.strftime("%H:%M:%S")
    
    if uid not in console_logs:
        console_logs[uid] = []
    
    console_logs[uid].append({
        "timestamp": timestamp,
        "text": str(text)
    })
    
    # সর্বোচ্চ ২০০ লাইন রাখা
    if len(console_logs[uid]) > 200:
        console_logs[uid] = console_logs[uid][-200:]
    
    print(f"[{uid}] [{timestamp}] {text}", flush=True)

# ===============================
# 🤖 BOT START FUNCTION
# ===============================
def start_bot(uid, password):
    """বট চালু করার ফাংশন"""
    
    if uid in bot_processes and bot_processes[uid].poll() is None:
        add_log(uid, "⚠️ Bot already running")
        return
    
    def run():
        try:
            # main.py ফাইল চেক
            if not os.path.exists(MAIN_PY_PATH):
                add_log(uid, f"❌ main.py not found at: {MAIN_PY_PATH}")
                return
            
            cmd = [sys.executable, "-u", MAIN_PY_PATH, uid, password]
            add_log(uid, f"🚀 Starting bot with command: {' '.join(cmd)}")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            bot_processes[uid] = process
            bot_start_times[uid] = time.time()
            add_log(uid, "🟢 Bot started successfully")
            
            # আউটপুট রিড করা
            for line in process.stdout:
                if line and line.strip():
                    add_log(uid, line.strip())
            
            process.wait()
            
        except FileNotFoundError as e:
            add_log(uid, f"❌ File not found: {e}")
        except Exception as e:
            add_log(uid, f"❌ Error: {str(e)}")
        finally:
            bot_processes.pop(uid, None)
            bot_start_times.pop(uid, None)
            add_log(uid, "🔴 Bot stopped")
    
    threading.Thread(target=run, daemon=True).start()

# ===============================
# 🔄 AUTO START ALL ACCOUNTS
# ===============================
def auto_start_all():
    """সব অ্যাকাউন্ট অটো স্টার্ট করে"""
    accounts = load_accounts()
    for uid, password in accounts.items():
        start_bot(uid, password)

# ===============================
# 📋 API: ADD ACCOUNT
# ===============================
@app.route("/api/add_account", methods=["POST"])
def api_add_account():
    if not check_key(request):
        return jsonify({"success": False, "msg": "Invalid API key"})
    
    data = request.json
    uid = data.get("uid")
    password = data.get("password")
    
    if not uid or not password:
        return jsonify({"success": False, "msg": "Missing UID or Password"})
    
    accounts = load_accounts()
    
    if uid in accounts:
        return jsonify({"success": False, "msg": "UID already added"})
    
    accounts[uid] = password
    save_accounts(accounts)
    
    # বট অটো স্টার্ট
    start_bot(uid, password)
    
    return jsonify({"success": True, "msg": "Account added successfully"})

# ===============================
# 📋 API: GET ACCOUNTS
# ===============================
@app.route("/api/accounts", methods=["GET"])
def api_accounts():
    if not check_key(request):
        return jsonify({"success": False, "msg": "Invalid API key"})
    
    return jsonify(load_accounts())

# ===============================
# 🚀 API: START BOT
# ===============================
@app.route("/api/start", methods=["POST"])
def api_start():
    if not check_key(request):
        return jsonify({"success": False, "msg": "Invalid API key"})
    
    data = request.json
    uid = data.get("uid")
    password = data.get("password")
    
    if not uid or not password:
        return jsonify({"success": False, "msg": "Missing UID or Password"})
    
    if uid in bot_processes and bot_processes[uid].poll() is None:
        return jsonify({"success": False, "msg": "Bot already running"})
    
    start_bot(uid, password)
    return jsonify({"success": True, "msg": "Bot starting..."})

# ===============================
# 🛑 API: STOP BOT
# ===============================
@app.route("/api/stop", methods=["POST"])
def api_stop():
    if not check_key(request):
        return jsonify({"success": False, "msg": "Invalid API key"})
    
    uid = request.json.get("uid")
    
    if not uid:
        return jsonify({"success": False, "msg": "Missing UID"})
    
    process = bot_processes.get(uid)
    
    if not process:
        return jsonify({"success": False, "msg": "Bot not running"})
    
    try:
        add_log(uid, "🛑 Stopping bot...")
        process.terminate()
        process.wait(timeout=3)
    except:
        try:
            process.kill()
        except:
            pass
    
    bot_processes.pop(uid, None)
    bot_start_times.pop(uid, None)
    add_log(uid, "✅ Bot stopped")
    
    return jsonify({"success": True})

# ===============================
# 🔄 API: RESTART BOT (FIXED)
# ===============================
@app.route("/api/restart", methods=["POST"])
def api_restart():
    if not check_key(request):
        return jsonify({"success": False, "msg": "Invalid API key"})
    
    uid = request.json.get("uid")
    
    if not uid:
        return jsonify({"success": False, "msg": "Missing UID"})
    
    accounts = load_accounts()
    password = accounts.get(uid)
    
    if not password:
        return jsonify({"success": False, "msg": "No account found"})
    
    process = bot_processes.get(uid)
    add_log(uid, "🔄 Restarting bot...")
    
    if process:
        try:
            process.terminate()
            process.wait(timeout=3)
        except:
            try:
                process.kill()
            except:
                pass
        
        bot_processes.pop(uid, None)
        bot_start_times.pop(uid, None)
    
    start_bot(uid, password)
    
    return jsonify({"success": True, "msg": "Bot restarted"})

# ===============================
# 💀 API: FORCE KILL
# ===============================
@app.route("/api/forcekill", methods=["POST"])
def api_forcekill():
    if not check_key(request):
        return jsonify({"success": False, "msg": "Invalid API key"})
    
    uid = request.json.get("uid")
    
    if not uid:
        return jsonify({"success": False, "msg": "Missing UID"})
    
    process = bot_processes.get(uid)
    
    if not process:
        return jsonify({"success": False, "msg": "Bot not running"})
    
    try:
        add_log(uid, "💀 Force killing bot...")
        process.kill()
    except:
        pass
    
    bot_processes.pop(uid, None)
    bot_start_times.pop(uid, None)
    add_log(uid, "✅ Bot killed")
    
    return jsonify({"success": True})

# ===============================
# 🧹 API: CLEAR CONSOLE
# ===============================
@app.route("/api/clear_console", methods=["POST"])
def api_clear_console():
    if not check_key(request):
        return jsonify({"success": False, "msg": "Invalid API key"})
    
    uid = request.json.get("uid")
    
    if uid:
        console_logs[uid] = []
        return jsonify({"success": True})
    
    return jsonify({"success": False, "msg": "Missing UID"})

# ===============================
# 📊 API: SERVER STATUS
# ===============================
@app.route("/api/status", methods=["GET"])
def api_status():
    uptime = int(time.time() - server_start_time)
    
    return jsonify({
        "server_uptime": f"{uptime}s",
        "running_bots": len(bot_processes),
        "status": "online"
    })

# ===============================
# 👤 API: USER STATUS
# ===============================
@app.route("/api/user_status", methods=["POST"])
def api_user_status():
    if not check_key(request):   # 🔥 ADD THIS
        return jsonify({"success": False, "msg": "Invalid API key"})

    uid = request.json.get("uid")

    return jsonify({
        "running": uid in bot_processes,
        "start_time": bot_start_times.get(uid)
    })

# ===============================
# 📟 API: GET CONSOLE LOGS
# ===============================
@app.route("/api/console", methods=["POST"])
def api_console():
    if not check_key(request):   # 🔥 ADD THIS
        return jsonify({"success": False, "msg": "Invalid API key"})

    uid = request.json.get("uid")

    return jsonify({
        "console": console_logs.get(uid, [])
    })

# ===============================
# 🔐 API: USER LOGIN
# ===============================
@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    
    # ইউজার চেক
    if username == "mainul" and password == USER_PASS:
        return jsonify({
            "success": True,
            "role": "user",
            "msg": "Login successful"
        })
    
    return jsonify({
        "success": False,
        "msg": "Invalid credentials"
    })

# ===============================
# 👑 API: ADMIN LOGIN
# ===============================
@app.route("/api/admin_login", methods=["POST"])
def api_admin_login():
    data = request.json
    password = data.get("password")
    
    if password == ADMIN_PASS:
        return jsonify({
            "success": True,
            "msg": "Admin access granted"
        })
    
    return jsonify({
        "success": False,
        "msg": "Wrong admin password"
    })

# ===============================
# 🏠 HOME PAGE
# ===============================
@app.route("/")
def home():
    uptime = int(time.time() - server_start_time)
    bots = len(bot_processes)
    
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    seconds = uptime % 60
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>MAINUL TCP SERVER</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            background: #0a0a0a;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            text-align: center;
            padding: 50px 20px;
            margin: 0;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .box {{
            border: 2px solid #00ff00;
            padding: 40px;
            border-radius: 20px;
            background: rgba(0, 255, 0, 0.05);
            box-shadow: 0 0 30px rgba(0, 255, 0, 0.2);
            max-width: 600px;
            width: 100%;
        }}
        h1 {{
            color: #00ff00;
            font-size: 32px;
            margin-bottom: 30px;
            text-shadow: 0 0 10px #00ff00;
        }}
        .status {{
            font-size: 20px;
            margin: 20px 0;
            padding: 15px;
            border: 1px solid #00ff00;
            border-radius: 10px;
            background: rgba(0, 255, 0, 0.1);
        }}
        .value {{
            font-size: 24px;
            font-weight: bold;
            color: #00ff00;
        }}
        .footer {{
            margin-top: 30px;
            color: #008800;
            font-size: 14px;
        }}
        .badge {{
            display: inline-block;
            padding: 5px 10px;
            background: #00ff00;
            color: black;
            border-radius: 5px;
            font-weight: bold;
            margin: 5px;
        }}
        .contact-section {{
            margin: 30px 0;
            padding: 20px;
            border: 1px solid #00ff00;
            border-radius: 10px;
            background: rgba(0, 255, 0, 0.05);
        }}
        .contact-title {{
            color: #00ff00;
            font-size: 18px;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}
        .contact-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .contact-item {{
            padding: 10px;
            border: 1px solid #00ff00;
            border-radius: 8px;
            transition: all 0.3s ease;
        }}
        .contact-item:hover {{
            background: rgba(0, 255, 0, 0.1);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 255, 0, 0.2);
        }}
        .contact-icon {{
            font-size: 24px;
            margin-bottom: 5px;
        }}
        .contact-label {{
            color: #008800;
            font-size: 12px;
            text-transform: uppercase;
        }}
        .contact-value {{
            color: #00ff00;
            font-size: 14px;
            word-break: break-word;
        }}
        .contact-value a {{
            color: #00ff00;
            text-decoration: none;
            transition: color 0.3s;
        }}
        .contact-value a:hover {{
            color: white;
            text-decoration: underline;
        }}
        .separator {{
            margin: 20px 0;
            border: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, #00ff00, transparent);
        }}
    </style>
    <!-- Font Awesome for icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
</head>
<body>
    <div class="box">
        <h1>🚀 MAINUL TCP SERVER</h1>
        
        <div class="status">
            <div>🤖 STATUS: <span class="value">ONLINE</span></div>
            <div style="margin-top: 15px;">⏱ UPTIME: <span class="value">{hours:02d}h {minutes:02d}m {seconds:02d}s</span></div>
            <div style="margin-top: 15px;">📊 RUNNING BOTS: <span class="value">{bots}</span></div>
        </div>

        
        <div class="contact-section">
            <div class="contact-title">
                <i class="fas fa-address-card"></i> CONTACT DEVELOPER
            </div>
            
            <div class="contact-grid">
                <!-- টেলিগ্রাম -->
                <div class="contact-item">
                    <div class="contact-icon">
                        <i class="fab fa-telegram"></i>
                    </div>
                    <div class="contact-label">Telegram</div>
                    <div class="contact-value">
                        <a href="https://t.me/mdmainulislaminfo" target="_blank">@mdmainulislaminfo</a>
                    </div>
                </div>

                <!-- হোয়াটসঅ্যাপ -->
                <div class="contact-item">
                    <div class="contact-icon">
                        <i class="fab fa-whatsapp"></i>
                    </div>
                    <div class="contact-label">WhatsApp</div>
                    <div class="contact-value">
                        <a href="https://wa.me/8801308850528" target="_blank">+8801308850528</a>
                    </div>
                </div>

                <!-- ইমেইল -->
                <div class="contact-item">
                    <div class="contact-icon">
                        <i class="fas fa-envelope"></i>
                    </div>
                    <div class="contact-label">Email</div>
                    <div class="contact-value">
                        <a href="mailto:githubmainul@gmail.com">githubmainul@gmail.com</a>
                    </div>
                </div>

                <!-- গিটহাব -->
                <div class="contact-item">
                    <div class="contact-icon">
                        <i class="fab fa-github"></i>
                    </div>
                    <div class="contact-label">GitHub</div>
                    <div class="contact-value">
                        <a href="https://github.com/M41NUL" target="_blank">M41NUL</a>
                    </div>
                </div>
            </div>

            <!-- কুইক কন্টাক্ট বাটন -->
            <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
                <a href="https://t.me/mdmainulislaminfo" target="_blank" style="text-decoration: none;">
                    <span class="badge" style="background: #0088cc; color: white;">
                        <i class="fab fa-telegram"></i> Telegram
                    </span>
                </a>
                <a href="https://wa.me/8801308850528" target="_blank" style="text-decoration: none;">
                    <span class="badge" style="background: #25D366; color: white;">
                        <i class="fab fa-whatsapp"></i> WhatsApp
                    </span>
                </a>
                <a href="mailto:githubmainul@gmail.com" style="text-decoration: none;">
                    <span class="badge" style="background: #EA4335; color: white;">
                        <i class="fas fa-envelope"></i> Email
                    </span>
                </a>
                <a href="https://github.com/M41NUL" target="_blank" style="text-decoration: none;">
                    <span class="badge" style="background: #333; color: white;">
                        <i class="fab fa-github"></i> GitHub
                    </span>
                </a>
            </div>
        </div>

        <div>
            <span class="badge">🔥 MAINUL - X</span>
            <span class="badge">⚡ TCP CONTROLLER</span>
            <span class="badge">💀 v1.0.0</span>
        </div>

        <hr class="separator">

        <div class="footer">
            <p>© 2026 MAINUL - X. All Rights Reserved.</p>
            <p style="font-size: 12px;">⚡ POWERED BY MAINUL - X ⚡</p>
            <p style="font-size: 11px; margin-top: 10px;">
                <i class="fas fa-clock"></i> Server Time: {time.strftime("%Y-%m-%d %H:%M:%S")}
            </p>
        </div>
    </div>
</body>
</html>
"""

# ===============================
# 🚀 RUN SERVER
# ===============================
if __name__ == "__main__":
    print("=" * 50)
    print("🔥 MAINUL TCP SERVER STARTING...")
    print(f"📂 Main bot path: {MAIN_PY_PATH}")
    print(f"🔑 API Key: {API_KEY[:5]}...{API_KEY[-5:] if len(API_KEY) > 10 else ''}")
    print(f"🤖 Auto-starting accounts...")
    print("=" * 50)
    
    
    auto_start_all()
    
   
    port = int(os.environ.get("PORT", 5000))
    
    print(f"✅ Server running on port {port}")
    print(f"🌐 http://localhost:{port}")
    print("=" * 50)
    
    app.run(host="0.0.0.0", port=port, debug=False)
