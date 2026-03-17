# ===============================
# MAINUL TCP CONTROLLER API
# Developed by MAINUL - X 😈
# ===============================

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess, threading, time, os, sys, signal

app = Flask(__name__)
CORS(app)

API_KEY = "MAINUL_X_SECURE"

# ===============================
# GLOBAL VARIABLES
# ===============================
bot_process = None
bot_status = "STOPPED"
bot_start_time = None
console_lines = []

# 🔥 NEW ACCOUNT SYSTEM
user_uid = None
user_pass = None


# ===============================
# SECURITY
# ===============================
def check_key(req):
    return req.headers.get("x-api-key") == API_KEY


# ===============================
# CONSOLE
# ===============================
def add_console_line(text):
    timestamp = time.strftime("%H:%M:%S")
    console_lines.append({"timestamp": timestamp, "text": text})

    if len(console_lines) > 100:
        console_lines.pop(0)

    print(f"[{timestamp}] {text}")


# ===============================
# BOT RUN
# ===============================
def run_bot():
    global bot_process, bot_status

    if not user_uid or not user_pass:
        add_console_line("❌ No account set")
        return

    try:
        cmd = [sys.executable, "main.py", user_uid, user_pass]

        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        add_console_line(f"🟢 Bot started on UID: {user_uid}")

        while True:
            line = bot_process.stdout.readline()
            if not line:
                break
            if line.strip():
                add_console_line(line.strip())

        bot_process.wait()

    except Exception as e:
        add_console_line(f"❌ Error: {e}")

    finally:
        bot_status = "STOPPED"
        add_console_line("🔴 Bot stopped")


# ===============================
# ROUTES
# ===============================

@app.route("/")
def home():
    return jsonify({"status": "RUNNING"})


@app.route("/api/status")
def status():
    uptime = "0s"
    if bot_start_time and bot_status == "RUNNING":
        uptime = f"{int(time.time() - bot_start_time)}s"

    return jsonify({
        "status": bot_status,
        "uid": user_uid,
        "uptime": uptime
    })


# 🔥 SAVE ACCOUNT
@app.route("/api/set_account", methods=["POST"])
def set_account():
    global user_uid, user_pass

    if not check_key(request):
        return jsonify({"success": False})

    data = request.json

    user_uid = data.get("uid")
    user_pass = data.get("password")

    if not user_uid or not user_pass:
        return jsonify({"success": False, "msg": "Missing data"})

    add_console_line(f"💾 Account saved: {user_uid}")

    return jsonify({"success": True})


# 🚀 START
@app.route("/api/start", methods=["POST"])
def start():
    global bot_status, bot_start_time

    if not check_key(request):
        return jsonify({"success": False})

    if bot_status == "RUNNING":
        return jsonify({"success": False, "msg": "Already running"})

    if not user_uid or not user_pass:
        return jsonify({"success": False, "msg": "No account set"})

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()

    bot_status = "RUNNING"
    bot_start_time = time.time()

    add_console_line("🚀 Bot starting...")

    return jsonify({"success": True})


# 🛑 STOP
@app.route("/api/stop", methods=["POST"])
def stop():
    global bot_process, bot_status

    if not check_key(request):
        return jsonify({"success": False})

    if bot_process:
        try:
            os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
        except:
            pass

    bot_status = "STOPPED"
    add_console_line("🛑 Bot stopped")

    return jsonify({"success": True})


# 🔄 RESTART
@app.route("/api/restart", methods=["POST"])
def restart():
    stop()
    return start()


# 💀 FORCE KILL
@app.route("/api/forcekill", methods=["POST"])
def forcekill():
    global bot_process, bot_status

    if not check_key(request):
        return jsonify({"success": False})

    if bot_process:
        try:
            os.killpg(os.getpgid(bot_process.pid), signal.SIGKILL)
        except:
            pass

    bot_status = "STOPPED"
    add_console_line("💀 Force killed")

    return jsonify({"success": True})


# 📊 CONSOLE
@app.route("/api/console")
def console():
    return jsonify({"console": console_lines})


# 🧹 CLEAR
@app.route("/api/clear", methods=["POST"])
def clear():
    global console_lines
    console_lines = []
    add_console_line("🧹 Console cleared")
    return jsonify({"success": True})


# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, threaded=True)
