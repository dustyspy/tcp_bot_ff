# ===========================================
# FILE: app.py - MAINUL TCP CONTROLLER BACKEND
# AUTHOR: MAINUL - X (Md. Mainul Islam)
# CREATED: March 19, 2026
# VERSION: 1.0.0 (FINAL - SECURITY FIXED)
# ===========================================
# CONTACT:
# Telegram: @mdmainulislaminfo
# WhatsApp: +8801308850528
# Email: githubmainul@gmail.com
# GitHub: https://github.com/M41NUL
# ===========================================

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import threading
import time
import os
import sys
import json
import signal
from threading import Lock

app = Flask(__name__)
CORS(app)

# ===============================
# 🔐 ENVIRONMENT VARIABLES (PRODUCTION)
# ===============================
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise Exception("❌ CRITICAL: API_KEY environment variable not set!")

ADMIN_PASS = os.environ.get("ADMIN_PASS")
if not ADMIN_PASS:
    raise Exception("❌ CRITICAL: ADMIN_PASS environment variable not set!")

USER_PASS = os.environ.get("USER_PASS", "1234")

# ===============================
# 🌍 GLOBAL VARIABLES
# ===============================
bot_processes = {}
console_logs = {}
bot_start_times = {}
server_start_time = time.time()
lock = Lock()  # 🔥 NEW: Thread safety lock

# ===============================
# 📁 PATH FIX - main.py খুঁজে বের করা
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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
    MAIN_PY_PATH = os.path.join(BASE_DIR, "main.py")

# ===============================
# 📁 ACCOUNTS FILE MANAGEMENT
# ===============================
ACCOUNTS_FILE = "accounts.json"

def load_accounts():
    try:
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, 'r') as f:
                return json.load(f)
        else:
            with open(ACCOUNTS_FILE, 'w') as f:
                json.dump({}, f)
            return {}
    except Exception as e:
        print(f"Error loading accounts: {e}")
        return {}

def save_accounts(data):
    try:
        with open(ACCOUNTS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving accounts: {e}")

# ===============================
# 🔑 API KEY CHECK
# ===============================
def check_key(req):
    api_key = req.headers.get('x-api-key')
    if not api_key:
        api_key = req.args.get('api_key')
    return api_key == API_KEY

# ===============================
# 👑 ADMIN CHECK (FIX 1)
# ===============================
def check_admin(req):
    if not check_key(req):
        return False
    
    data = req.json or {}
    admin_pass = data.get("admin_pass")
    
    return admin_pass == ADMIN_PASS

# ===============================
# 📝 CONSOLE LOGGING
# ===============================
def add_log(uid, text):
    timestamp = time.strftime("%H:%M:%S")
    
    if uid not in console_logs:
        console_logs[uid] = []
    
    console_logs[uid].append({
        "timestamp": timestamp,
        "text": str(text)
    })
    
    if len(console_logs[uid]) > 200:
        console_logs[uid] = console_logs[uid][-200:]
    
    print(f"[{uid}] [{timestamp}] {text}", flush=True)

# ===============================
# 🤖 BOT START FUNCTION (FIX 3 - THREAD SAFE)
# ===============================
def start_bot(uid, password):
    with lock:
        if uid in bot_processes and bot_processes[uid].poll() is None:
            add_log(uid, "⚠️ Bot already running")
            return
    
    def run():
        try:
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
            
            with lock:
                bot_processes[uid] = process
                bot_start_times[uid] = time.time()
            add_log(uid, "🟢 Bot started successfully")
            
            for line in process.stdout:
                if line and line.strip():
                    add_log(uid, line.strip())
            
            process.wait()
            
        except FileNotFoundError as e:
            add_log(uid, f"❌ File not found: {e}")
        except Exception as e:
            add_log(uid, f"❌ Error: {str(e)}")
        finally:
            with lock:
                bot_processes.pop(uid, None)
                bot_start_times.pop(uid, None)
            add_log(uid, "🔴 Bot stopped")
    
    threading.Thread(target=run, daemon=True).start()

# ===============================
# 🔄 AUTO START ALL ACCOUNTS
# ===============================
def auto_start_all():
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
    
    with lock:
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
    
    with lock:
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
    
    with lock:
        bot_processes.pop(uid, None)
        bot_start_times.pop(uid, None)
    add_log(uid, "✅ Bot stopped")
    
    return jsonify({"success": True})

# ===============================
# 🔄 API: RESTART BOT
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
    
    with lock:
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
        
        with lock:
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
    
    with lock:
        process = bot_processes.get(uid)
    
    if not process:
        return jsonify({"success": False, "msg": "Bot not running"})
    
    try:
        add_log(uid, "💀 Force killing bot...")
        process.kill()
    except:
        pass
    
    with lock:
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
    if not check_key(request):
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
    if not check_key(request):
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
# 👑 ADMIN API: ALL USERS (FIX 1 APPLIED)
# ===============================
@app.route("/api/admin/users", methods=["GET"])
def api_admin_users():
    if not check_admin(request):
        return jsonify({"success": False, "msg": "Admin authentication failed"})
    
    accounts = load_accounts()
    return jsonify(accounts)

# ===============================
# 👑 ADMIN API: DELETE USER (FIX 1 APPLIED)
# ===============================
@app.route("/api/admin/delete_user", methods=["POST"])
def api_admin_delete_user():
    if not check_admin(request):
        return jsonify({"success": False, "msg": "Admin authentication failed"})
    
    data = request.json
    uid = data.get("uid")
    
    accounts = load_accounts()
    
    if uid in accounts:
        del accounts[uid]
        save_accounts(accounts)
        
        with lock:
            if uid in bot_processes:
                try:
                    bot_processes[uid].kill()
                except:
                    pass
                bot_processes.pop(uid, None)
                bot_start_times.pop(uid, None)
        
        add_log("ADMIN", f"🗑️ Deleted user: {uid}")
        return jsonify({"success": True, "msg": "User deleted"})
    
    return jsonify({"success": False, "msg": "User not found"})

# ===============================
# 👑 ADMIN API: STOP ALL BOTS (FIX 1 APPLIED)
# ===============================
@app.route("/api/admin/stop_all", methods=["POST"])
def api_admin_stop_all():
    if not check_admin(request):
        return jsonify({"success": False, "msg": "Admin authentication failed"})
    
    count = 0
    with lock:
        for uid, process in list(bot_processes.items()):
            try:
                process.terminate()
                count += 1
                add_log(uid, "🛑 Stopped by admin")
            except:
                pass
        
        bot_processes.clear()
        bot_start_times.clear()
    
    add_log("ADMIN", f"🛑 Stopped {count} bots")
    return jsonify({"success": True, "msg": f"Stopped {count} bots"})

# ===============================
# 👑 ADMIN API: CLEAR ALL CONSOLES (FIX 1 APPLIED)
# ===============================
@app.route("/api/admin/clear_all", methods=["POST"])
def api_admin_clear_all():
    if not check_admin(request):
        return jsonify({"success": False, "msg": "Admin authentication failed"})
    
    console_logs.clear()
    add_log("ADMIN", "🧹 Cleared all consoles")
    
    return jsonify({"success": True, "msg": "All consoles cleared"})

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
                <div class="contact-item">
                    <div class="contact-icon"><i class="fab fa-telegram"></i></div>
                    <div class="contact-label">Telegram</div>
                    <div class="contact-value">
                        <a href="https://t.me/mdmainulislaminfo" target="_blank">@mdmainulislaminfo</a>
                    </div>
                </div>
                <div class="contact-item">
                    <div class="contact-icon"><i class="fab fa-whatsapp"></i></div>
                    <div class="contact-label">WhatsApp</div>
                    <div class="contact-value">
                        <a href="https://wa.me/8801308850528" target="_blank">+8801308850528</a>
                    </div>
                </div>
                <div class="contact-item">
                    <div class="contact-icon"><i class="fas fa-envelope"></i></div>
                    <div class="contact-label">Email</div>
                    <div class="contact-value">
                        <a href="mailto:githubmainul@gmail.com">githubmainul@gmail.com</a>
                    </div>
                </div>
                <div class="contact-item">
                    <div class="contact-icon"><i class="fab fa-github"></i></div>
                    <div class="contact-label">GitHub</div>
                    <div class="contact-value">
                        <a href="https://github.com/M41NUL" target="_blank">M41NUL</a>
                    </div>
                </div>
            </div>

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
            <span class="badge">💀 v2.1.0</span>
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
    print("=" * 60)
    print("🔥 MAINUL TCP SERVER STARTING...")
    print("👤 Developer: MAINUL - X (Md. Mainul Islam)")
    print("📱 Contact: @mdmainulislaminfo")
    print("=" * 60)
    print(f"🤖 Auto-starting accounts...")
    print("=" * 60)
    
    auto_start_all()
    
    port = int(os.environ.get("PORT", 5000))
    
    print(f"✅ Server running on port {port}")
    print(f"🌐 http://localhost:{port}")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=port, debug=False)
