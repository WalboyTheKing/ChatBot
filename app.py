from flask import Flask, request
import os

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "token_defaut")

@app.route("/")
def home():
    return "Bot en ligne !"

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode = request.args.get("hub.mode")
        token = request.args.get("hub.verify_token")
        challenge = request.args.get("hub.challenge")

        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Token invalide", 403

    elif request.method == "POST":
        data = request.json
        print("Message reçu :", data)
        return "EVENT_RECEIVED", 200

# Utilisation de Waitress pour le serveur
from waitress import serve
if __name__ == "__main__":
    serve(app, host='0.0.0.0', port=5000)  # Utilisation de Waitress
