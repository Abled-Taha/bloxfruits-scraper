from flask import Flask
from .scraper import get_fruits
from .manager import read_file, write_file, check_file_validity

app = Flask(__name__)

@app.route("/")
def index():
    return "<p>Hello, World!</p>"

@app.route("/fruits")
def fruits():
    index = 0
    while index != 3:
        if check_file_validity("storage/fruits.json"):
            return read_file("storage/fruits.json")
        write_file("storage/fruits.json", get_fruits())
        index += 1
    return {"error": "Failed to fetch data after multiple attempts."}, 500