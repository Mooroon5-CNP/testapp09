from unittest.mock import MagicMock, patch

from app import app


def test_health_does_not_require_database():
    assert app.test_client().get('/healthz').json == {'status': 'ok'}


def test_homepage_has_start_button_and_leaderboard():
    response = app.test_client().get('/')
    assert response.status_code == 200
    assert b'id="start"' in response.data
    assert b'id="leaderboard"' in response.data


def test_leaderboard_uses_database_configuration(monkeypatch):
    for key, value in {'DB_HOST': 'database', 'DB_NAME': 'scores',
                       'DB_USER': 'user', 'DB_PASSWORD': 'secret'}.items():
        monkeypatch.setenv(key, value)
    connection = MagicMock()
    connection.execute.return_value.fetchall.return_value = [('Sam', 12000, 3)]
    with patch('app.psycopg.connect') as connect:
        connect.return_value.__enter__.return_value = connection
        response = app.test_client().get('/api/leaderboard')
    assert response.json['scores'][0]['player_name'] == 'Sam'
    assert response.json['scores'][0]['best_time_ms'] == 12000
    connect.assert_called_once_with(host='database', port='5432', dbname='scores',
                                    user='user', password='secret', connect_timeout=5)


def test_score_rejects_invalid_name():
    response = app.test_client().post('/api/scores', json={
        'player_name': '<script>', 'time_ms': 13000,
    })
    assert response.status_code == 400
