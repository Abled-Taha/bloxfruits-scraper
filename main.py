import os
import dotenv, subprocess

dotenv.load_dotenv()
debug = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

if __name__ == "__main__":
    if debug:
        from src.flask import app
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        subprocess.call(["waitress-serve", f"--listen=0.0.0.0:5000", "src.flask:app"])
  