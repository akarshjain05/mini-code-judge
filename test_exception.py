import sys
import traceback
from fastapi.testclient import TestClient
from app.main import app

def run():
    try:
        client = TestClient(app)
        client.get("/problems")
    except Exception as e:
        traceback.print_exc()

if __name__ == "__main__":
    run()
