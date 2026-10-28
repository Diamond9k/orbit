import urllib.request
import time

def read_token():
    with open('host/token.txt', 'r') as file:
        return file.read().strip()

def heartbeat():
    token = read_token()
    url = f"http://localhost:8000/api/hosts/heartbeat?token={token}"
    try:
        urllib.request.urlopen(url)
        print("online")
    except urllib.error.URLError as e:
        print(f"Error: {e.reason}")

if __name__ == "__main__":
    while True:
        heartbeat()
        time.sleep(60)
