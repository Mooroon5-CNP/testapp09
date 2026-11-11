"""Timed crossword game with a PostgreSQL leaderboard."""
import os
import re

import psycopg
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def database_connection():
    return psycopg.connect(
        host=os.environ['DB_HOST'],
        port=os.environ.get('DB_PORT', '5432'),
        dbname=os.environ['DB_NAME'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASSWORD'],
        connect_timeout=5,
    )


def ensure_scores_table(connection):
    connection.execute(
        'CREATE TABLE IF NOT EXISTS puzzle_scores ('
        'player_name TEXT PRIMARY KEY, '
        'best_time_ms INTEGER NOT NULL CHECK (best_time_ms > 0), '
        'games_played INTEGER NOT NULL DEFAULT 1, '
        'last_played_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP)'
    )


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/healthz')
def health():
    return jsonify(status='ok')


@app.get('/readyz')
def ready():
    try:
        with database_connection() as connection:
            connection.execute('SELECT 1')
        return jsonify(status='ready', database='ok')
    except (KeyError, psycopg.Error):
        return jsonify(status='not_ready', database='unavailable'), 503


@app.get('/api/leaderboard')
def leaderboard():
    try:
        with database_connection() as connection:
            ensure_scores_table(connection)
            rows = connection.execute(
                'SELECT player_name, best_time_ms, games_played '
                'FROM puzzle_scores ORDER BY best_time_ms ASC, last_played_at ASC '
                'LIMIT 10'
            ).fetchall()
        return jsonify(scores=[{'player_name': row[0], 'best_time_ms': row[1],
                                'games_played': row[2]} for row in rows])
    except (KeyError, psycopg.Error):
        return jsonify(error='database_unavailable'), 503


@app.post('/api/scores')
def save_score():
    data = request.get_json(silent=True) or {}
    player_name = str(data.get('player_name', '')).strip()
    if not re.fullmatch(r'[A-Za-z0-9 _-]{1,20}', player_name):
        return jsonify(error='Enter a name using up to 20 letters, numbers, spaces, _ or -.'), 400
    try:
        time_ms = int(data.get('time_ms', 0))
    except (TypeError, ValueError):
        return jsonify(error='Invalid completion time.'), 400
    if not 0 < time_ms <= 3_600_000:
        return jsonify(error='Completion time must be between 1 ms and 1 hour.'), 400

    try:
        with database_connection() as connection:
            ensure_scores_table(connection)
            previous = connection.execute(
                'SELECT best_time_ms FROM puzzle_scores WHERE player_name = %s',
                (player_name,),
            ).fetchone()
            row = connection.execute(
                'INSERT INTO puzzle_scores (player_name, best_time_ms) '
                'VALUES (%s, %s) ON CONFLICT (player_name) DO UPDATE SET '
                'best_time_ms = LEAST(puzzle_scores.best_time_ms, EXCLUDED.best_time_ms), '
                'games_played = puzzle_scores.games_played + 1, '
                'last_played_at = CURRENT_TIMESTAMP '
                'RETURNING player_name, best_time_ms, games_played',
                (player_name, time_ms),
            ).fetchone()
        return jsonify(player_name=row[0], best_time_ms=row[1],
                       games_played=row[2], new_best=previous is None or time_ms < previous[0])
    except (KeyError, psycopg.Error):
        return jsonify(error='database_unavailable'), 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '8080')))
