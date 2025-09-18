from flask import Flask
from flask_cors import CORS
import os
from .fruits_scraper import get_fruits
from .stock_scraper import get_stock_all
from .manager import read_file, write_file, check_file_validity, write_fruits_info_file

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
            if check_file_validity("storage/fruits.json", 7200):
                return read_file("storage/fruits.json")
            write_file("storage/fruits.json", get_fruits())
            index += 1
    elif debug:
        return get_fruits()
    return {"error": "Failed to fetch data after multiple attempts."}, 500

@app.route("/stock")
def stock():
    index = 0
    if not debug:
        while index != 3:
            if check_file_validity("storage/stock.json", 600):
                return read_file("storage/stock.json")
            write_file("storage/stock.json", get_stock_all())
            index += 1
    elif debug:
        return get_stock_all()
    return {"error": "Failed to fetch data after multiple attempts."}, 500

@app.route("/info")
def info():
    index = 0
    while index != 3:
        if check_file_validity("storage/info.json", 86400):
            return read_file("storage/info.json")
        write_fruits_info_file()
        index += 1
    return {"error": "Failed to fetch data after multiple attempts."}, 500