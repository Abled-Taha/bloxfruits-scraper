from flask import Flask
from flask_cors import CORS
import os
from .scraper import get_fruits
from .manager import read_file, write_file, check_file_validity

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "https://bfft.app.abledtaha.online"]}})
debug = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

@app.route("/")
def index():
    return "<p>Hello, World!</p>"

@app.route("/fruits")
def fruits():
    index = 0
    if not debug:
        while index != 3:
            if check_file_validity("storage/fruits.json"):
                return read_file("storage/fruits.json")
            write_file("storage/fruits.json", get_fruits())
            index += 1
    elif debug:
        return get_fruits()
    return {"error": "Failed to fetch data after multiple attempts."}, 500