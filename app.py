# ===============================
# MAINUL TCP CONTROLLER API (MULTI USER 😈)
# ===============================

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess, threading, time, os, sys

app = Flask(__name__)
CORS(app)

API_KEY = "MAINUL_X_SECURE"

# ===============================
# GLOBAL
# ===============================
bot_processes = {}   # 🔥 multi user bot
console_logs = {}    # 🔥 per user console
users = {}           # 🔥 simple login system

server_start_time = time.time()

# main.py এর সঠিক পাথ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PY_PATH = os.path.join(BASE_DIR, "main.py")

# ===============================
# SECURITY
# ===============================
def check_key(req):
    return req.headers.get("x-api-key") == API_KEY

# ===============================
# CONSOLE
# ===============================
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
# REGISTER
# ===============================
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if username in users:
        return jsonify({"success": False, "msg": "User exists"})
    users[username] = password
    return jsonify({"success": True})

# ===============================
# LOGIN
# ===============================
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    if users.get(username) == password:
        return jsonify({"success": True})
    return jsonify({"success": False})

# ===============================
# START BOT (PER USER)
# ===============================
@app.route("/api/start", methods=["POST"])
def start():
    if not check_key(request):
        return jsonify({"success": False})
    data = request.json
    uid = data.get("uid")
    password = data.get("password")

    if uid in bot_processes:
        return jsonify({"success": False, "msg": "Already running"})

    def run():
        try:
            cmd = [sys.executable, "-u", MAIN_PY_PATH, uid, password]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            bot_processes[uid] = process
            add_log(uid, "🟢 Bot started")
            for line in process.stdout:
                clean = line.strip()
                if clean:
                    add_log(uid, clean)
            process.wait()
        except Exception as e:
            add_log(uid, f"❌ {e}")
        finally:
            bot_processes.pop(uid, None)
            add_log(uid, "🔴 Bot stopped")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"success": True})

# ===============================
# STOP (ONLY ONE USER)
# ===============================
@app.route("/api/stop", methods=["POST"])
def stop():
    if not check_key(request):
        return jsonify({"success": False})
    data = request.json
    uid = data.get("uid")
    process = bot_processes.get(uid)
    if not process:
        return jsonify({"success": False})
    process.terminate()
    bot_processes.pop(uid, None)
    add_log(uid, "🛑 Stopped")
    return jsonify({"success": True})

# ===============================
# STATUS
# ===============================
@app.route("/api/status")
def status():
    uptime = int(time.time() - server_start_time)
    return jsonify({
        "server_uptime": f"{uptime}s",
        "running_bots": len(bot_processes)
    })

# ===============================
# USER STATUS
# ===============================
@app.route("/api/user_status", methods=["POST"])
def user_status():
    data = request.json
    uid = data.get("uid")
    return jsonify({
        "running": uid in bot_processes
    })

# ===============================
# CONSOLE (PER USER)
# ===============================
@app.route("/api/console", methods=["POST"])
def console():
    data = request.json
    uid = data.get("uid")
    return jsonify({
        "console": console_logs.get(uid, [])
    })

# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("🔥 MULTI USER SERVER STARTED", flush=True)
    app.run(host="0.0.0.0", port=port)
