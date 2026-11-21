from unittest.mock import MagicMock, patch

from app import app


def test_board_shows_values_and_masks_password(monkeypatch):
    monkeypatch.setenv('DB_HOST', 'database.example')
    monkeypatch.setenv('DB_PASSWORD', 'private-password')
    monkeypatch.setenv('VARIABLE_ENV_VISIBLE', 'Visible test value')
    response = app.test_client().get('/')
    page = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'database.example' in page
    assert 'DB_PASSWORD' in page
    assert 'VARIABLE_ENV_VISIBLE' in page
    assert 'Visible test value' in page
    assert 'private-password' not in page


def test_password_reveal_is_local_only(monkeypatch):
    monkeypatch.setenv('ALLOW_SECRET_REVEAL', '1')
    monkeypatch.setenv('DB_PASSWORD', 'private-password')
    client = app.test_client()
    remote_response = client.get('/api/password',
                                 environ_overrides={'REMOTE_ADDR': '203.0.113.2'})
    assert remote_response.status_code == 403
    assert client.get('/api/password').json == {'value': 'private-password'}


def test_database_check_uses_environment(monkeypatch):
    values = {'DB_HOST': 'database', 'DB_PORT': '5433', 'DB_NAME': 'demo',
              'DB_USER': 'user', 'DB_PASSWORD': 'secret'}
    for key, value in values.items():
        monkeypatch.setenv(key, value)
    connection = MagicMock()
    with patch('app.psycopg.connect') as connect:
        connect.return_value.__enter__.return_value = connection
        response = app.test_client().get('/api/check')
    assert response.json['ok'] is True
    connect.assert_called_once_with(host='database', port='5433', dbname='demo',
                                    user='user', password='secret', connect_timeout=3)
    connection.execute.assert_called_once_with('SELECT 1')


def test_database_check_reports_missing_settings(monkeypatch):
    monkeypatch.delenv('DB_HOST', raising=False)
    response = app.test_client().get('/api/check')
    assert response.json['ok'] is False
    assert 'DB_HOST' in response.json['message']


def test_database_check_identifies_starter_password(monkeypatch):
    for key in ('DB_HOST', 'DB_NAME', 'DB_USER'):
        monkeypatch.setenv(key, 'configured')
    monkeypatch.setenv('DB_PASSWORD', 'change-me')
    with patch('app.psycopg.connect') as connect:
        response = app.test_client().get('/api/check')
    assert response.json['ok'] is False
    assert 'starter password' in response.json['message']
    connect.assert_not_called()


def test_health_does_not_require_database():
    assert app.test_client().get('/healthz').json == {'status': 'ok'}


def test_readiness_requires_writable_database(monkeypatch):
    for key in ('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'):
        monkeypatch.setenv(key, 'configured')
    connection = MagicMock()
    with patch('app.psycopg.connect') as connect:
        connect.return_value.__enter__.return_value = connection
        connection.execute.return_value.fetchone.return_value = ('off',)
        assert app.test_client().get('/health').status_code == 200
        connection.execute.return_value.fetchone.return_value = ('on',)
        assert app.test_client().get('/health').status_code == 503
    connection.execute.assert_called_with('SHOW transaction_read_only')


def test_readiness_reports_missing_database_configuration(monkeypatch):
    monkeypatch.delenv('DB_HOST', raising=False)
    assert app.test_client().get('/health').status_code == 503


def test_readiness_reports_database_connection_failure(monkeypatch):
    for key in ('DB_HOST', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'):
        monkeypatch.setenv(key, 'configured')
    with patch('app.psycopg.connect', side_effect=ValueError('invalid port')):
        assert app.test_client().get('/health').status_code == 503
