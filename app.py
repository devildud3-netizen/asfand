from flask import Flask, render_template, request, jsonify
import os, json, datetime, difflib
from netmiko import ConnectHandler

app = Flask(__name__)

DATA_DIR = "data"
ROLLBACK_DIR = os.path.join(DATA_DIR, "rollback")
JOB_FILE = os.path.join(DATA_DIR, "jobs.json")

DEVICE_TYPES = ["cisco_ios", "cisco_nxos", "cisco_asa", "cisco_ftd"]

os.makedirs(ROLLBACK_DIR, exist_ok=True)

# ---------- Helpers ----------

def connect_device(ip, auth):
    for dtype in DEVICE_TYPES:
        try:
            conn = ConnectHandler(
                device_type=dtype,
                host=ip,
                username=auth["user"],
                password=auth["pwd"],
                secret=auth["secret"],
                fast_cli=False
            )
            conn.enable()
            return conn, dtype
        except Exception:
            pass
    raise Exception("Device detection failed")

def record_job(device_count):
    jobs = json.load(open(JOB_FILE)) if os.path.exists(JOB_FILE) else []
    jobs.append({
        "date": datetime.date.today().isoformat(),
        "time": datetime.datetime.now().strftime("%H:%M:%S"),
        "devices": device_count
    })
    json.dump(jobs, open(JOB_FILE, "w"), indent=2)

# ---------- Routes ----------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/connect", methods=["POST"])
def connect():
    data = request.json
    results = {}
    for ip in data["ips"]:
        try:
            conn, _ = connect_device(ip, data["auth"])
            conn.disconnect()
            results[ip] = True
        except:
            results[ip] = False
    return jsonify(results)

@app.route("/run", methods=["POST"])
def run_cmds():
    data = request.json
    output = []
    diffs = []

    record_job(len(data["ips"]))

    for ip in data["ips"]:
        try:
            conn, _ = connect_device(ip, data["auth"])
            before = conn.send_command("show running-config")

            rb_path = os.path.join(ROLLBACK_DIR, f"{ip}.cfg")
            open(rb_path, "w").write(before)

            if data["exec"]:
                for c in data["cmds"]:
                    out = conn.send_command(c)
                    output.append(f"[{ip}] $ {c}\n{out}")

            if data["config"] and not data["dry"]:
                out = conn.send_config_set(data["cmds"])
                output.append(f"[{ip}] CONFIG:\n{out}")

            after = conn.send_command("show running-config")

            diff = difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile="BEFORE",
                tofile="AFTER",
                lineterm=""
            )
            diffs.extend(list(diff))

            conn.disconnect()
            output.append(f"[{ip}] ✅ SUCCESS")

        except Exception as e:
            output.append(f"[{ip}] ❌ FAILED: {e}")

    return jsonify({"output": output, "diff": diffs})

@app.route("/jobs")
def jobs():
    jobs = json.load(open(JOB_FILE)) if os.path.exists(JOB_FILE) else []
    return jsonify(jobs)

@app.route("/rollback", methods=["POST"])
def rollback():
    data = request.json
    output = []

    for ip in data["ips"]:
        try:
            cfg = open(os.path.join(ROLLBACK_DIR, f"{ip}.cfg")).read().splitlines()
            conn, _ = connect_device(ip, data["auth"])
            conn.send_config_set(cfg)
            conn.disconnect()
            output.append(f"[{ip}] 🔄 Rolled back")
        except Exception as e:
            output.append(f"[{ip}] ❌ Rollback failed: {e}")

    return jsonify(output)

if __name__ == "__main__":
    app.run(debug=True)
