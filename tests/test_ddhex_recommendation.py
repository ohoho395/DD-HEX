"""Fork features: persistent preferences and live/offline recommendation flow."""
import json

from lolhex.config import Settings
from lolhex import recommend


def test_preferences_survive_restart(tmp_path):
    path = tmp_path / 'config.json'
    s = Settings(show_winrate=False, smoothing_games=850, reliable_games=2500)
    assert s.save(path)
    loaded = Settings.load(path)
    assert (loaded.show_winrate, loaded.smoothing_games, loaded.reliable_games) == (False, 850, 2500)


def test_invalid_preferences_fall_back_and_clamp(tmp_path):
    path = tmp_path / 'config.json'
    path.write_text(json.dumps({'show_winrate': 'false', 'smoothing_games': -1,
                                'reliable_games': 10**50, 'check_data_updates': 'false'}))
    s = Settings.load(path)
    assert s.show_winrate is True
    assert s.smoothing_games == 0 and s.reliable_games == 100000
    assert s.check_data_updates is False
    path.write_text(json.dumps({'smoothing_games': float('nan'), 'reliable_games': True}))
    s = Settings.load(path)
    assert s.smoothing_games == 300 and s.reliable_games == 1000


def test_reliable_threshold_changes_candidate_pool(store):
    _, augments = store.dataset.table(None)
    base = store.win_data('17')['sample_win']
    augments['17']['1029'] = {'games': 2000, 'wins': 1040, 'win_rate': base + .01}
    augments['17']['2128'] = {'games': 500, 'wins': 350, 'win_rate': .7}
    conservative = recommend.evaluate(store, '17', ['1029', '2128', None], reliable_games=1000)
    permissive = recommend.evaluate(store, '17', ['1029', '2128', None], reliable_games=250)
    assert conservative['best_index'] == 0 and permissive['best_index'] == 1
    assert conservative['slots'][1]['sample_warning']
    assert not permissive['slots'][1].get('sample_warning')
    assert conservative['slots'][1]['win'] == permissive['slots'][1]['win'] == .7


def test_smoothing_change_invalidates_engine_panel(store, tmp_path, monkeypatch):
    from lolhex.engine import Engine
    monkeypatch.setenv('DDHEX_HOME', str(tmp_path))
    engine = Engine(Settings(), store=store)
    first = engine.hero_panel('17')
    engine.settings.smoothing_games = 10000
    second = engine.hero_panel('17')
    assert first is not second
    a = next(x for x in first['augments'] if x['id'] == '1029')
    b = next(x for x in second['augments'] if x['id'] == '1029')
    assert b['delta'] < a['delta']


def test_cli_demo_offline(no_network, tmp_path, monkeypatch, capsys):
    from lolhex.__main__ import main
    monkeypatch.setenv('DDHEX_HOME', str(tmp_path))
    monkeypatch.setattr('lolhex.__main__._setup_logging', lambda debug: None)
    assert main(['--demo', '--hero', '提莫']) == 0
    out = json.loads(capsys.readouterr().out)
    assert out['app'] == 'DD HEX' and out['evaluation']['slots']
    assert out['evaluation']['best_index'] is not None
    assert out['data']['dataset_revision']


def test_cli_demo_rejects_unknown_hero(no_network, tmp_path, monkeypatch, capsys):
    from lolhex.__main__ import main
    monkeypatch.setenv('DDHEX_HOME', str(tmp_path))
    monkeypatch.setattr('lolhex.__main__._setup_logging', lambda debug: None)
    assert main(['--demo', '--hero', '不存在的英雄']) == 2
    assert '找不到英雄' in capsys.readouterr().out
