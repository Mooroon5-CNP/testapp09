# Cross Sprint

A small timed crossword. Enter a name, press **Start game**, and fill the 3 × 3
grid from the across and down clues. The app saves each player's fastest time
in PostgreSQL and shows the top ten.

## Run locally

```sh
pip install -r requirements.txt
export DB_HOST=localhost DB_PORT=5432 DB_NAME=cross_sprint
export DB_USER=postgres DB_PASSWORD=your-password
python app.py
```

Open http://localhost:8080. The app creates the `puzzle_scores` table on first
use. Reusing a player name updates their personal best and game count.

## Run in the cloud

Build and deploy the included Dockerfile. Set `DB_HOST`, `DB_PORT`, `DB_NAME`,
`DB_USER`, and `DB_PASSWORD` as service environment variables. Use the cloud
PostgreSQL service's HA endpoint for `DB_HOST` if you want scores to remain
available through a database failover.

`/healthz` checks the web process and `/readyz` checks database connectivity.
