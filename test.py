# app_before.py
from flask import Flask, request, jsonify

app = Flask(__name__)

def check_password(user, pwd):
    # pretend DB lookup
    return user == "alice" and pwd == "correct-horse-battery-staple"

@app.post("/login")
def login():
    user = (request.form.get("user") or "")
    pwd  = (request.form.get("pwd") or "")
    if check_password(user, pwd):
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 401

# Problem: An attacker can POST to /login as fast as possible
# with thousands of credential pairs (password stuffing).
