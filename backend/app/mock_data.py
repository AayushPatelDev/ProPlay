"""Offline fallback: a realistic-looking EPL dataset with fictional players.

Used when no API key is configured, when the free plan blocks requests, or for
fast local development. Club names are real; every player is invented.
"""
import numpy as np
import pandas as pd

from .features import FULL_SEASON_MINUTES, PLAYER_COLUMNS

CLUBS = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton", "Chelsea",
    "Crystal Palace", "Everton", "Fulham", "Ipswich", "Leicester", "Liverpool",
    "Manchester City", "Manchester United", "Newcastle", "Nottingham Forest",
    "Southampton", "Tottenham", "West Ham", "Wolves",
]
FIRST_NAMES = [
    "Alex", "Ben", "Callum", "Dani", "Eli", "Felipe", "Gabriel", "Harvey", "Isaac", "Jonas",
    "Kai", "Luca", "Marcus", "Nico", "Oscar", "Pedro", "Rafael", "Sami", "Theo", "Umar",
    "Victor", "Will", "Xavi", "Yann", "Zane", "Jamal", "Mateo", "Noah", "Kofi", "Emil",
    "Ruben", "Leon", "Joao", "Tomas", "Ibrahim", "Declan", "Ollie", "Enzo", "Moussa", "Ryo",
]
LAST_NAMES = [
    "Ashford", "Barros", "Carver", "Diallo", "Eriksen", "Fontaine", "Garrido", "Hartley",
    "Ivanov", "Jensen", "Kamara", "Lindqvist", "Mendes", "Nwosu", "Okafor", "Pereira",
    "Quinn", "Rossi", "Sandoval", "Traore", "Ueda", "Valverde", "Whitmore", "Yilmaz",
    "Zielinski", "Adeyemi", "Blackwood", "Castillo", "Delaney", "Esposito", "Falk", "Grealey",
    "Holm", "Iwobi-Lane", "Juric", "Kowalski", "Laporte-Reid", "Moreau", "Novak", "Osei",
    "Pryce", "Rahman", "Sterling-Hope", "Tanaka", "Underwood", "Vidal", "Weston", "Abara",
    "Brennan", "Coutinho-Silva", "Dubois", "Eze-Morgan", "Fofana", "Gomez", "Hayes", "Idowu",
]
NATIONALITIES = [
    "England", "England", "England", "France", "Spain", "Brazil", "Portugal", "Netherlands",
    "Germany", "Belgium", "Nigeria", "Ghana", "Senegal", "Argentina", "Scotland", "Wales",
    "Ireland", "Norway", "Denmark", "Japan", "Colombia", "Ivory Coast", "Sweden", "Croatia",
]
POSITION_PROBS = {"Goalkeeper": 0.10, "Defender": 0.34, "Midfielder": 0.33, "Attacker": 0.23}
GOALS_PER90 = {"Goalkeeper": 0.0, "Defender": 0.045, "Midfielder": 0.13, "Attacker": 0.40}
ASSISTS_PER90 = {"Goalkeeper": 0.004, "Defender": 0.055, "Midfielder": 0.13, "Attacker": 0.15}


def generate_mock_dataset(n_players: int = 720, seasons=(2021, 2022, 2023, 2024), seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    used_names: set[str] = set()
    positions, probs = list(POSITION_PROBS), list(POSITION_PROBS.values())
    rows = []

    for player_id in range(100_001, 100_001 + n_players):
        while True:
            first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
            if f"{first} {last}" not in used_names:
                used_names.add(f"{first} {last}")
                break
        position = str(rng.choice(positions, p=probs))
        talent = rng.beta(2.2, 2.6)
        nationality = str(rng.choice(NATIONALITIES))
        club = str(rng.choice(CLUBS))
        start = int(rng.integers(0, len(seasons)))
        span = int(rng.integers(1, len(seasons) - start + 1))
        age0 = int(rng.integers(17, 33))

        for offset, season in enumerate(seasons[start:start + span]):
            age = age0 + offset
            if offset and rng.random() < 0.12:
                club = str(rng.choice(CLUBS))
            form = float(np.clip(talent + rng.normal(0, 0.08) - 0.003 * (age - 26) ** 2, 0.02, 1.0))
            availability = rng.beta(2.0, 1.2)
            minutes = int(np.clip(FULL_SEASON_MINUTES * form ** 0.6 * availability + rng.normal(0, 150), 0, FULL_SEASON_MINUTES))
            nineties = minutes / 90
            rows.append({
                "player_id": player_id,
                "name": f"{first} {last}",
                "firstname": first,
                "lastname": last,
                "nationality": nationality,
                "photo": "",
                "team": club,
                "season": season,
                "position": position,
                "age": age,
                "appearances": int(min(38, round(nineties * 1.12 + rng.integers(0, 4)))) if minutes else 0,
                "minutes": minutes,
                "goals": int(rng.poisson(GOALS_PER90[position] * nineties * (0.4 + 1.4 * form))),
                "assists": int(rng.poisson(ASSISTS_PER90[position] * nineties * (0.4 + 1.3 * form))),
            })

    return pd.DataFrame(rows, columns=PLAYER_COLUMNS)
