"""Config Bingo: inspect local configuration and check PostgreSQL connectivity."""

import ipaddress
import os

import psycopg
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv(override=False)

app = Flask(__name__)

VARIABLES = (
    'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'PORT',
    'VARIABLE_ENV_VISIBLE',
)


def config_cards():
    cards = []
    for name in VARIABLES:
        value = os.environ.get(name, '')
        cards.append({
            'name': name,
            'value': '••••••••' if name == 'DB_PASSWORD' and value else value,
            'set': bool(value.strip()),
            'secret': name == 'DB_PASSWORD',
        })
    return cards


def local_reveal_allowed():
    try:
        client_is_local = ipaddress.ip_address(request.remote_addr).is_loopback
    except (TypeError, ValueError):
        client_is_local = False
    return os.environ.get('ALLOW_SECRET_REVEAL') == '1' and client_is_local


@app.get('/')
def index():
    cards = config_cards()
    return render_template('index.html', cards=cards,
                           reveal_allowed=local_reveal_allowed(),
                           all_set=all(card['set'] for card in cards))


@app.get('/api/password')
def reveal_password():
    if not local_reveal_allowed():
        return jsonify(error='Password reveal is only available for local development.'), 403
    return jsonify(value=os.environ.get('DB_PASSWORD', ''))


@app.get('/api/check')
def check_database():
    required = ('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD')
    missing = [name for name in required if not os.environ.get(name, '').strip()]
    if missing:
        return jsonify(ok=False, message='Set ' + ', '.join(missing) + ' to test PostgreSQL.')
    if os.environ['DB_PASSWORD'] == 'change-me':
        return jsonify(
            ok=False,
            message='The .env has a starter password. Enter your PostgreSQL credentials '
                    'and restart the app.',
        )

    try:
        with psycopg.connect(
            host=os.environ['DB_HOST'],
            port=os.environ.get('DB_PORT', '5432'),
            dbname=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD'],
            connect_timeout=3,
        ) as connection:
            connection.execute('SELECT 1').fetchone()
    except (psycopg.Error, ValueError) as exc:
        # Database errors can contain credentials or connection strings.
        app.logger.info('PostgreSQL check failed: %s', type(exc).__name__)
        return jsonify(ok=False, message='Could not connect to PostgreSQL. Check the values and server.')

    return jsonify(ok=True, message='PostgreSQL connection successful!')


@app.get('/healthz')
def health():
    return jsonify(status='ok')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '8080')))
