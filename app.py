# ===============================
# MAINUL TCP CONTROLLER API
# Developed by MAINUL - X 😈
# ===============================

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess, threading, time, os, sys

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
    global console_lines

    timestamp = time.strftime("%H:%M:%S")

    console_lines.append({
        "timestamp": timestamp,
        "text": str(text)
    })

    if len(console_lines) > 100:
        console_lines = console_lines[-100:]

    print(f"[{timestamp}] {text}")


# ===============================
# BOT RUN (🔥 FIXED)
# ===============================
def run_bot():
    global bot_process, bot_status

    if not user_uid or not user_pass:
        add_console_line("❌ No account set")
        bot_status = "STOPPED"
        return

    try:
        cmd = [sys.executable, "main.py", user_uid, user_pass]

        bot_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        if bot_process is None:
            add_console_line("❌ Failed to start bot")
            bot_status = "STOPPED"
            return

        add_console_line(f"🟢 Bot started on UID: {user_uid}")

        # 🔥 LIVE OUTPUT READ
        while True:
            line = bot_process.stdout.readline()

            if not line and bot_process.poll() is not None:
                break

            if line:
                clean = line.replace("\x1b[H", "").replace("\x1b[2J", "").replace("\x1b[3J", "")
                clean = clean.strip()

                if clean:
                    add_console_line(clean)

        if bot_process:
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
    return jsonify({
        "name": "MAINUL TCP CONTROLLER",
        "status": "RUNNING"
    })


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


# ===============================
# SAVE ACCOUNT
# ===============================
@app.route("/api/set_account", methods=["POST"])
def set_account():
    global user_uid, user_pass

    if not check_key(request):
        return jsonify({"success": False, "msg": "Unauthorized"})

    data = request.json or {}

    user_uid = data.get("uid")
    user_pass = data.get("password")

    if not user_uid or not user_pass:
        return jsonify({"success": False, "msg": "Missing UID or Password"})

    try:
        with open("MAINUL9X.txt", "w") as f:
            f.write(f"uid={user_uid},password={user_pass}")
    except:
        pass

    add_console_line(f"💾 Account saved: {user_uid}")

    return jsonify({"success": True})


# ===============================
# START (🔥 SAFE)
# ===============================
@app.route("/api/start", methods=["POST"])
def start():
    global bot_status, bot_start_time, bot_process

    if not check_key(request):
        return jsonify({"success": False, "msg": "Unauthorized"})

    if bot_status == "RUNNING":
        return jsonify({"success": False, "msg": "Already running"})

    if bot_process is not None:
        return jsonify({"success": False, "msg": "Process already exists"})

    if not user_uid or not user_pass:
        return jsonify({"success": False, "msg": "No account set"})

    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()

    bot_status = "RUNNING"
    bot_start_time = time.time()

    add_console_line("🚀 Bot starting...")

    return jsonify({"success": True})


# ===============================
# STOP (🔥 SAFE)
# ===============================
@app.route("/api/stop", methods=["POST"])
def stop():
    global bot_process, bot_status

    if not check_key(request):
        return jsonify({"success": False, "msg": "Unauthorized"})

    try:
        if bot_process is not None:
            bot_process.terminate()
            bot_process = None
    except:
        pass

    bot_status = "STOPPED"
    add_console_line("🛑 Bot stopped")

    return jsonify({"success": True})


# ===============================
# RESTART
# ===============================
@app.route("/api/restart", methods=["POST"])
def restart():
    stop()
    time.sleep(1)
    return start()


# ===============================
# FORCE KILL
# ===============================
@app.route("/api/forcekill", methods=["POST"])
def forcekill():
    global bot_process, bot_status

    if not check_key(request):
        return jsonify({"success": False, "msg": "Unauthorized"})

    try:
        if bot_process is not None:
            bot_process.kill()
            bot_process = None
    except:
        pass

    bot_status = "STOPPED"
    add_console_line("💀 Bot force killed")

    return jsonify({"success": True})


# ===============================
# CONSOLE
# ===============================
@app.route("/api/console")
def console():
    return jsonify({"console": console_lines})


# ===============================
# CLEAR
# ===============================
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
    app.run(host="0.0.0.0", port=port, threaded=True)
