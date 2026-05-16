import requests

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    r = requests.get("https://tazkarti.com/data/matches-list-json.json", headers=headers, timeout=15)
    matches = r.json()
    for match in matches:
        if match.get("matchId") == 2482:
            print(f"Match 2482 Status: {match.get('matchStatus')}")
            break
    else:
        print("Match 2482 not found in current API response.")
except Exception as e:
    print("Error:", e)
