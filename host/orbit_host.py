import urllib.request
import urllib.parse
import urllib.error
import time

def send_heartbeat(token, url="http://localhost:8000/api/hosts/heartbeat"):
    data = urllib.parse.urlencode({"token": token}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                print("online")
                return True
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(e)
        return False

def main():
    with open("host/token.txt", "r") as file:
        token = file.read().strip()
    while True:
        send_heartbeat(token)
        time.sleep(60)

if __name__ == "__main__":
    main()
