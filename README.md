# Config Bingo

A small Flask app for checking the PostgreSQL settings the app actually uses. The
board shows `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `PORT`,
and `VARIABLE_ENV_VISIBLE`.
Fill the board and click **Test PostgreSQL** to check a live connection. The app
does not create tables or change data.

## Run locally

The repository includes an ignored `.env` file. Set its `DB_*` values for your
PostgreSQL server and use `VARIABLE_ENV_VISIBLE` for any text you want to see on
the board, then run:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:8080. Restart the app after editing `.env`. Existing process
environment variables take priority over `.env` values.

The password is masked on the board. A reveal button is available only when
`ALLOW_SECRET_REVEAL=1` and the request comes from the local machine. Never enable
that setting in a deployed environment. `.env` is excluded from Git and Docker.

## Deploy

The template uses PostgreSQL. Configure `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`,
and `DB_PASSWORD` as deployment environment variables. `PORT` defaults to 8080.
`/healthz` checks the web process; `/api/check` tests PostgreSQL connectivity.
