from src.api.kis_api import fetch_current_price
from src.core.config import config


def test_price():
    print(f"Testing with BASE_URL: {config.BASE_URL}")
    price = fetch_current_price("005930")
    if price:
        print(f"Price: {price}")
    else:
        print("Failed to fetch price. Check logs above.")


if __name__ == "__main__":
    test_price()
