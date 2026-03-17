# ===============================
# MAINUL TCP CONTROLLER API
# Developed by MAINUL - X 😈
# ===============================

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import threading
import time
import os
import sys
import signal

app = Flask(__name__)
CORS(app)

# ===============================
# CONFIG 🔐
# ===============================
API_KEY = "MAINUL_X_SECURE"

# ===============================
# GLOBAL VARIABLES
# ===============================
bot_process = None
bot_status = "STOPPED"
bot_start_time = None
console_lines = []
target_uid = None


# ===============================
# SECURITY CHECK
# ===============================
def check_key(req):
    return req.headers.get("x-api-key") == API_KEY


# ===============================
# CONSOLE SYSTEM
# ===============================
def add_console_line(text):
    global console_lines
    timestamp = time.strftime("%H:%M:%S")
    line = {"timestamp": timestamp, "text": text}
    console_lines.append(line)

    if len(console_lines) > 100:
        console_lines = console_lines[-100:]

    print(f"[{timestamp}] {text}")


# ===============================
# BOT RUN FUNCTION (FIXED)
# ===============================
def run_bot():
    global bot_process, bot_status, bot_start_time

    try:
        cmd = [sys.executable, "main.py"]

        if target_uid:
            cmd.append(str(target_uid))

        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        add_console_line("🟢 Bot started")

        # 🔥 NON-BLOCKING OUTPUT READ
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
        bot_start_time = None
        add_console_line("🔴 Bot stopped")


# ===============================
# ROUTES
# ===============================

@app.route("/")
def home():
    return jsonify({
        "name": "MAINUL TCP CONTROLLER",
        "status": "RUNNING"
    })


@app.route("/api/status")
def status():
    uptime = "0s"

    if bot_start_time and bot_status == "RUNNING":
        elapsed = int(time.time() - bot_start_time)
        uptime = f"{elapsed}s"

    return jsonify({
        "status": bot_status,
        "uptime": uptime,
        "uid": target_uid
    })


@app.route("/api/start", methods=["POST"])
def start():
    global bot_status, bot_start_time, target_uid

    if not check_key(request):
        return jsonify({"success": False, "msg": "Unauthorized"})

    if bot_status == "RUNNING":
        return jsonify({"success": False, "msg": "Already running"})

    data = request.json
    if data and "uid" in data:
        target_uid = data["uid"]

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()

    bot_status = "RUNNING"
    bot_start_time = time.time()

    add_console_line("🚀 Bot starting...")

    return jsonify({"success": True})


@app.route("/api/stop", methods=["POST"])
def stop():
    global bot_status, bot_start_time, bot_process

    if not check_key(request):
        return jsonify({"success": False, "msg": "Unauthorized"})

    if bot_process:
        try:
            os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
        except:
            pass

    bot_status = "STOPPED"
    bot_start_time = None

    add_console_line("🔴 Bot stopped")

    return jsonify({"success": True})


@app.route("/api/restart", methods=["POST"])
def restart():
    global bot_process, bot_status, bot_start_time

    if not check_key(request):
        return jsonify({"success": False, "msg": "Unauthorized"})

    if bot_process:
        try:
            os.killpg(os.getpgid(bot_process.pid), signal.SIGTERM)
        except:
            pass

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()

    bot_status = "RUNNING"
    bot_start_time = time.time()

    add_console_line("🔄 Bot restarted")

    return jsonify({"success": True})


@app.route("/api/forcekill", methods=["POST"])
def forcekill():
    global bot_process, bot_status, bot_start_time

    if not check_key(request):
        return jsonify({"success": False, "msg": "Unauthorized"})

    if bot_process:
        try:
            os.killpg(os.getpgid(bot_process.pid), signal.SIGKILL)
        except:
            pass

    bot_status = "STOPPED"
    bot_start_time = None

    add_console_line("💀 Bot force killed")

    return jsonify({"success": True})


@app.route("/api/set_uid", methods=["POST"])
def set_uid():
    global target_uid

    data = request.json

    if data and "uid" in data:
        target_uid = data["uid"]
        add_console_line(f"🎯 UID set: {target_uid}")
        return jsonify({"success": True})

    return jsonify({"success": False})


@app.route("/api/console")
def console():
    return jsonify({"console": console_lines})


@app.route("/api/clear", methods=["POST"])
def clear():
    global console_lines
    console_lines = []
    add_console_line("🧹 Console cleared")
    return jsonify({"success": True})


# ===============================
# RUN SERVER
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
