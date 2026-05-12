#!/usr/bin/env python3
"""Script temporaire pour visualiser les commentaires dans la DB NewsFeed.

Usage:
    python3 view_comments.py           # Affiche tous les commentaires
    python3 view_comments.py --seed    # Ajoute des données de test d'abord
    python3 view_comments.py --table feedbacks   # Seulement les feedbacks
    python3 view_comments.py --table comments    # Seulement les news_comments
"""

import argparse
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "newsfeed.db"

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
GRAY   = "\033[90m"
RED    = "\033[31m"


def header(text: str) -> None:
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def ensure_tables(con: sqlite3.Connection) -> None:
    con.executescript("""
        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source_url TEXT NOT NULL UNIQUE,
            source_name TEXT NOT NULL,
            category TEXT NOT NULL,
            published_at TEXT NOT NULL,
            description TEXT,
            final_score REAL DEFAULT 0.0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS news_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_item_id INTEGER NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_item_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            comment TEXT,
            created_at TEXT
        );
    """)
    con.commit()


def show_news_comments(con: sqlite3.Connection) -> None:
    header("NOTES PERSONNELLES  (news_comments)")
    rows = con.execute("""
        SELECT nc.id, nc.body, nc.created_at, ni.title
        FROM news_comments nc
        JOIN news_items ni ON nc.news_item_id = ni.id
        ORDER BY nc.created_at DESC
    """).fetchall()

    if not rows:
        print(f"  {GRAY}(aucune note){RESET}")
        return

    for row_id, body, created_at, title in rows:
        ts = (created_at or "?")[:16]
        print(f"\n  {BOLD}#{row_id}{RESET}  {GRAY}{ts}{RESET}")
        print(f"  {YELLOW}Article :{RESET} {title[:80]}")
        print(f"  {GREEN}Note    :{RESET} {body}")

    print(f"\n  {GRAY}Total : {len(rows)} note(s){RESET}")


def show_feedbacks(con: sqlite3.Connection) -> None:
    header("FEEDBACKS UTILISATEUR  (feedbacks avec commentaire)")

    rows = con.execute("""
        SELECT f.id, f.action, f.comment, f.created_at, ni.title
        FROM feedbacks f
        JOIN news_items ni ON f.news_item_id = ni.id
        WHERE f.comment IS NOT NULL AND f.comment != ''
        ORDER BY f.created_at DESC
    """).fetchall()

    if not rows:
        print(f"  {GRAY}(aucun feedback avec commentaire){RESET}")
        total = con.execute("SELECT COUNT(*) FROM feedbacks").fetchone()[0]
        if total:
            print(f"  {GRAY}(il y a {total} feedback(s) sans texte — like/dislike/skip){RESET}")
        return

    action_color = {"like": GREEN, "dislike": RED, "skip": GRAY}
    for row_id, action, comment, created_at, title in rows:
        ts = (created_at or "?")[:16]
        color = action_color.get(action, RESET)
        print(f"\n  {BOLD}#{row_id}{RESET}  {GRAY}{ts}{RESET}  {color}[{action}]{RESET}")
        print(f"  {YELLOW}Article     :{RESET} {title[:80]}")
        print(f"  {GREEN}Commentaire :{RESET} {comment}")

    print(f"\n  {GRAY}Total : {len(rows)} feedback(s) avec texte{RESET}")


def seed_test_data(con: sqlite3.Connection) -> None:
    print(f"{YELLOW}Insertion de données de test...{RESET}")
    now = "2026-05-11 10:00:00"

    articles = [
        ("La NASA annonce une mission vers Europe, lune de Jupiter",
         "https://example.com/nasa-1", "NASA Blog", "spatial", now),
        ("Nouveau modèle Claude 4 dépasse GPT-5 sur tous les benchmarks",
         "https://example.com/tech-2", "TechCrunch", "tech_ai", now),
        ("Montréal : festival de jazz annulé à cause de la météo",
         "https://example.com/mtl-3", "La Presse", "evenements_mtl", now),
    ]
    con.executemany(
        "INSERT OR IGNORE INTO news_items (title, source_url, source_name, category, published_at, created_at)"
        " VALUES (?,?,?,?,?,?)",
        [(*a, now) for a in articles],
    )
    con.commit()

    ids = [
        con.execute("SELECT id FROM news_items WHERE source_url=?", (a[1],)).fetchone()[0]
        for a in articles
    ]

    con.executemany(
        "INSERT INTO news_comments (news_item_id, body, created_at) VALUES (?,?,?)",
        [
            (ids[0], "À suivre de près, mission fascinante!", now),
            (ids[1], "Faut tester ça dès que possible.", now),
        ],
    )
    con.executemany(
        "INSERT INTO feedbacks (news_item_id, action, comment, created_at) VALUES (?,?,?,?)",
        [
            (ids[0], "like",    "Super article, très bien écrit.", now),
            (ids[1], "like",    None, now),
            (ids[2], "dislike", "Pas vraiment intéressant pour moi.", now),
        ],
    )
    con.commit()
    print(f"{GREEN}✓ Données insérées (3 articles, 2 notes, 3 feedbacks){RESET}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualiser les commentaires NewsFeed")
    parser.add_argument("--seed",  action="store_true", help="Insérer des données de test")
    parser.add_argument("--table", choices=["comments", "feedbacks", "all"], default="all")
    args = parser.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    ensure_tables(con)

    try:
        if args.seed:
            seed_test_data(con)

        if args.table in ("comments", "all"):
            show_news_comments(con)

        if args.table in ("feedbacks", "all"):
            show_feedbacks(con)

        print()
    finally:
        con.close()


if __name__ == "__main__":
    main()
