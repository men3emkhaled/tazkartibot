import re

EGYPTIAN_LEAGUE_TEAMS = [
    "الأهلي", "الزمالك", "الإسماعيلي", "المصري",
    "الاتحاد", "غزل المحلة", "بلدية المحلة",
    "Al Ahly", "Zamalek", "ISMAILY", "Ismaily", "Al Masry",
    "Alithad", "Ittihad", "Ghazl Elmahala", "Baladiyat"
]

def clean_team_name(name):
    if not name: return ""
    name = re.sub(r'^(نادي|النادي|نادى|النادى)\s+', '', name)
    name = name.replace(" الرياضي", "").replace(" رياضي", "").replace(" للرياضة", "")
    name = name.replace(" الرياضى", "").replace(" رياضى", "") # Let's see if this matters
    name = re.sub(r'\s+(SC|FC|Club)$', '', name, flags=re.IGNORECASE)
    return name.strip()

def is_popular_team(team_name):
    if not team_name: return False
    cleaned = clean_team_name(team_name).lower()
    if "بنك" in cleaned or "bank" in cleaned:
        return False
    for p in EGYPTIAN_LEAGUE_TEAMS:
        if p.lower() in cleaned:
            return True
    return False

print("Ismaily:", is_popular_team("نادي الاسماعيلى الرياضى"))
print("Ghazl El Mahalla:", is_popular_team("نادي غزل المحلة"))
print("Al Ittihad:", is_popular_team("نادي الاتحاد السكندري"))
