import os
from flask import Flask, request, jsonify, send_from_directory
from logic import choose_move, get_last_debug
from personality import SNAKE_COLOR, SNAKE_HEAD, SNAKE_TAIL, SNAKE_AUTHOR

app = Flask(__name__, static_folder="static")


@app.get("/")
def info():
    return {
        "apiversion": "1",
        "author": SNAKE_AUTHOR,
        "color": SNAKE_COLOR,
        "head": SNAKE_HEAD,
        "tail": SNAKE_TAIL,
        "version": "2.0.0",
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


@app.get("/debug")
def debug():
    return send_from_directory("static", "debug.html")


@app.get("/debug/state")
def debug_state():
    return jsonify(get_last_debug())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
