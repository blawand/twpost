import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Add src to path so we can import the main entrypoint directly.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "src"))

from main import run


def main():
    load_dotenv(dotenv_path=PROJECT_ROOT / ".env", override=True)

    args = sys.argv[1:]
    if "--dry-run" in args:
        os.environ["ENGAGEMENT_DRY_RUN"] = "true"
        args = [arg for arg in args if arg != "--dry-run"]

    sys.argv = [sys.argv[0], "engage", *args]
    run()


if __name__ == "__main__":
    main()
