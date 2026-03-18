from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess, threading, time, os, sys, json

app = Flask(__name__)
CORS(app)

API_KEY = "MAINUL_X_SECURE"

# ===============================
# GLOBAL
# ===============================
bot_processes = {}
console_logs = {}
server_start_time = time.time()

# ===============================
# PATH FIX
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MAIN_PY_PATH = os.path.join(BASE_DIR, "main.py")
if not os.path.exists(MAIN_PY_PATH):
    MAIN_PY_PATH = os.path.join(BASE_DIR, "tcp_bot_ff", "main.py")

# ===============================
# FILE
# ===============================
ACCOUNTS_FILE = "accounts.json"

# ===============================
# HELPERS
# ===============================
def load_accounts():
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "w") as f:
            f.write("{}")
    with open(ACCOUNTS_FILE) as f:
        return json.load(f)

def save_accounts(data):
    with open(ACCOUNTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def check_key(req):
    return req.headers.get("x-api-key") == API_KEY

def add_log(uid, text):
    timestamp = time.strftime("%H:%M:%S")

    if uid not in console_logs:
        console_logs[uid] = []

    console_logs[uid].append({
        "timestamp": timestamp,
        "text": str(text)
    })

    if len(console_logs[uid]) > 100:
        console_logs[uid] = console_logs[uid][-100:]

    print(f"[{uid}] [{timestamp}] {text}", flush=True)

# ===============================
# BOT START
# ===============================
def start_bot(uid, password):

    if uid in bot_processes and bot_processes[uid].poll() is None:
        add_log(uid, "⚠️ Already running")
        return

    def run():
        try:
            cmd = [sys.executable, "-u", MAIN_PY_PATH, uid, password]

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            bot_processes[uid] = process
            add_log(uid, "🟢 Bot started")

            for line in process.stdout:
                if line.strip():
                    add_log(uid, line.strip())

            process.wait()

        except Exception as e:
            add_log(uid, f"❌ {e}")

        finally:
            bot_processes.pop(uid, None)
            add_log(uid, "🔴 Bot stopped")

    threading.Thread(target=run, daemon=True).start()

# ===============================
# AUTO START
# ===============================
def auto_start_all():
    accounts = load_accounts()
    for uid, password in accounts.items():
        start_bot(uid, password)

# ===============================
# ADD ACCOUNT (FIXED 😈)
# ===============================
@app.route("/api/add_account", methods=["POST"])
def api_add_account():
    if not check_key(request):
        return jsonify({"success": False})

    data = request.json
    uid = data.get("uid")
    password = data.get("password")

    if not uid or not password:
        return jsonify({"success": False, "msg": "Missing UID/PASS"})

    accounts = load_accounts()

    # 🚫 BLOCK DUPLICATE
    if uid in accounts:
        return jsonify({
            "success": False,
            "msg": "UID already added"
        })

    accounts[uid] = password
    save_accounts(accounts)

    start_bot(uid, password)

    return jsonify({"success": True})

# ===============================
# START
# ===============================
@app.route("/api/start", methods=["POST"])
def api_start():
    if not check_key(request):
        return jsonify({"success": False})

    data = request.json
    uid = data.get("uid")
    password = data.get("password")

    start_bot(uid, password)

    return jsonify({"success": True})

# ===============================
# STOP
# ===============================
@app.route("/api/stop", methods=["POST"])
def api_stop():
    if not check_key(request):
        return jsonify({"success": False})

    uid = request.json.get("uid")
    process = bot_processes.get(uid)

    if not process:
        return jsonify({"success": False})

    try:
        process.terminate()
    except:
        pass

    bot_processes.pop(uid, None)
    add_log(uid, "🛑 Stopped")

    return jsonify({"success": True})

# ===============================
# RESTART
# ===============================
@app.route("/api/restart", methods=["POST"])
def api_restart():
    if not check_key(request):
        return jsonify({"success": False})

    uid = request.json.get("uid")

    accounts = load_accounts()
    password = accounts.get(uid)

    if not password:
        return jsonify({"success": False})

    process = bot_processes.get(uid)
    if process:
        try:
            process.terminate()
        except:
            pass

    start_bot(uid, password)

    return jsonify({"success": True})

# ===============================
# FORCE KILL
# ===============================
@app.route("/api/forcekill", methods=["POST"])
def api_forcekill():
    if not check_key(request):
        return jsonify({"success": False})

    uid = request.json.get("uid")
    process = bot_processes.get(uid)

    if not process:
        return jsonify({"success": False})

    try:
        process.kill()
    except:
        pass

    bot_processes.pop(uid, None)
    add_log(uid, "💀 Force killed")

    return jsonify({"success": True})

# ===============================
# STATUS
# ===============================
@app.route("/api/status", methods=["GET"])
def api_status():
    uptime = int(time.time() - server_start_time)

    return jsonify({
        "server_uptime": f"{uptime}s",
        "running_bots": len(bot_processes)
    })

# ===============================
# USER STATUS
# ===============================
@app.route("/api/user_status", methods=["POST"])
def api_user_status():
    uid = request.json.get("uid")

    return jsonify({
        "running": uid in bot_processes
    })

# ===============================
# CONSOLE
# ===============================
@app.route("/api/console", methods=["POST"])
def api_console():
    uid = request.json.get("uid")

    return jsonify({
        "console": console_logs.get(uid, [])
    })

# ===============================
# ACCOUNTS
# ===============================
@app.route("/api/accounts", methods=["GET"])
def api_accounts():
    return jsonify(load_accounts())

# ===============================
# DELETE
# ===============================
@app.route("/api/delete", methods=["POST"])
def api_delete():
    if not check_key(request):
        return jsonify({"success": False})

    uid = request.json.get("uid")

    accounts = load_accounts()
    accounts.pop(uid, None)
    save_accounts(accounts)

    process = bot_processes.get(uid)
    if process:
        try:
            process.terminate()
        except:
            pass

    bot_processes.pop(uid, None)

    return jsonify({"success": True})

# ===============================
# ROOT
# ===============================
@app.route("/")
def home():
    return "MAINUL TCP SERVER RUNNING 😈"

# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    print("🔥 SERVER STARTED", flush=True)
    print("📂 MAIN:", MAIN_PY_PATH, flush=True)

    auto_start_all()

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
