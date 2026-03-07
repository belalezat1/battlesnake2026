import os
from flask import Flask, request, jsonify
from logic import choose_move

app = Flask(__name__)


@app.get("/")
def info():
    return {
        "apiversion": "1",
        "author": "",
        "color": "#FF0000",
        "head": "default",
        "tail": "default",
    }


@app.post("/start")
def start():
    return {}


@app.post("/move")
def move():
    data = request.get_json()
    response = choose_move(data)
    return jsonify(response)


@app.post("/end")
def end():
    return {}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
