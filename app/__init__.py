import os

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    from .main import app  # noqa: E402
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
