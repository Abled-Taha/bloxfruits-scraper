import os
import dotenv

dotenv.load_dotenv()
debug = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

if __name__ == "__main__":
  from src.flask import app
  app.run(debug=debug)
  