import requests

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }
    r = requests.get("https://tazkarti.com/data/matches-list-json.json", headers=headers, timeout=15)
    matches = r.json()
    print("Total matches:", len(matches))
    for m in matches:
        print(f"ID: {m.get('matchId')} - Status: {m.get('matchStatus')} - {m.get('teamNameAr1')} vs {m.get('teamNameAr2')}")
except Exception as e:
    print("Error:", e)
