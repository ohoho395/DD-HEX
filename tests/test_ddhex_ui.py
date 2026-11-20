"""Real Qt controls exercise persisted preferences and rendered recommendations."""
import json
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from lolhex import recommend
from lolhex.config import Settings
from lolhex.engine import Engine
from lolhex.ui import mainwindow, overlay


@pytest.fixture
def window(store, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(QMessageBox, 'information', lambda *a, **k: None)
    settings = Settings()
    engine = Engine(settings, store=store)
    engine.state.update(hero_id='17', hero_source='manual', phase='ingame',
                        offer={'slots': ['1029', '2128', '1373']})
    engine._reevaluate()
    ov = overlay.Overlay(engine)
    ov.timer.stop()
    w = mainwindow.MainWindow(engine, ov)
    w.show()
    w.refresh()
    yield w, engine, app
    w.timer.stop()
    w._update_timer.stop()
    w._notify_timer.stop()
    engine.stop()
    w.hide()
    ov.set_visible(False)
    for widget in (w, ov.panel, ov.badges, ov.champ):
        widget.deleteLater()
    app.processEvents()


def test_smoothing_control_updates_html_offer_and_saved_config(window):
    w, engine, _ = window
    before_html = w.tab_hero.text()
    before_score = engine.state['evaluation']['slots'][0]['score']
    w.set_smoothing.setValue(10000)
    assert w.tab_hero.text() != before_html
    assert engine.state['evaluation']['slots'][0]['score'] < before_score
    assert Settings.load().smoothing_games == 10000
    w.set_reliable.setValue(2500)
    assert Settings.load().reliable_games == 2500
    w.set_winrate.setChecked(False)
    assert Settings.load().show_winrate is False


def test_hidden_winrate_covers_pbe_and_pentakill(window):
    w, _, _ = window
    row = {'index': 0, 'augment_id': '3170', 'verdict': 'best', 'name': '重型',
           'basis': 'pbe', 'pbe_games': 5000, 'pbe_win': .56, 'score': 2.0,
           'games': 40, 'win': .6, 'reasons': ['测试服胜率56.0%']}
    ev = {'hero_id': '17', 'advice': '首选重型', 'slots': [row],
          'pentakill': {'hero': True, 'pbe': True, 'rows': [{'key': 'Q', 'win': .56, 'games': 5000}]}}
    w._render_offer(ev, False)
    assert '%' not in w.offer_cards[0].text() + w.offer_advice.text() + w.offer_cards[0].toolTip()
    assert '5000' in w.offer_cards[0].text()
    layer = overlay.BadgeLayer()
    try:
        snap = {'evaluation': ev, 'offer': {'boxes': [(200, 300, 500, 350)]},
                'settings': {'show_winrate': False}}
        assert '%' not in ' '.join(line for item in layer._badge_layout(snap) for line in item[3])
        snap['settings']['show_winrate'] = True
        assert '56.0%' in ' '.join(line for item in layer._badge_layout(snap) for line in item[3])
    finally:
        layer.close()


def test_manual_update_opens_independent_release_page(monkeypatch):
    calls = []
    monkeypatch.setattr(mainwindow.patch, 'install_root', lambda: None)
    monkeypatch.setattr(mainwindow.webbrowser, 'open', calls.append)
    fake = SimpleNamespace(_worker=None, _update_info={'version': '0.2.0', 'page': 'https://github.com/example/ddhex/releases'})
    mainwindow.MainWindow._start_update(fake)
    assert calls == ['https://github.com/example/ddhex/releases']


def test_source_autostart_runs_from_another_directory(tmp_path, monkeypatch):
    import os
    import subprocess
    import sys
    from lolhex.ui import autostart
    captured = []
    real_list2cmdline = subprocess.list2cmdline
    monkeypatch.setattr(autostart.subprocess, 'list2cmdline', lambda args: captured.append(args) or real_list2cmdline(args))
    autostart._command()
    args = captured[0]
    env = {**os.environ, 'DDHEX_HOME': str(tmp_path / 'home')}
    done = subprocess.run([sys.executable, '-c', args[2], '--demo'], cwd=tmp_path, env=env,
                          capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)['app'] == 'DD HEX'


def test_clear_button_only_removes_own_screenshots_after_confirmation(window, monkeypatch):
    w, engine, _ = window
    photos = engine.home / "screenshots"
    offers = engine.home / "shots"
    photos.mkdir()
    offers.mkdir()
    owned = [photos / "20261119-120000-002-1-选英雄.png",
             photos / "20261119-120001-003-三选一.png", offers / "offer_20261119_120000.jpg"]
    nested = offers / 'other'
    nested.mkdir()
    keep = [photos / "family.png", offers / "offer_manual.jpg", nested / owned[-1].name,
            engine.home / "ddhex.log"]
    for path in owned + keep:
        path.write_bytes(b"data")
    messages = []
    monkeypatch.setattr(QMessageBox, "information", lambda parent, title, text: messages.append(text))
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.No)
    w.clear_shots.click()
    assert all(p.exists() for p in owned)
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.Yes)
    w.clear_shots.click()
    assert messages[-1] == "已删除 3 张截图。"
    assert all(not p.exists() for p in owned)
    assert all(p.read_bytes() == b"data" for p in keep)
    w.clear_shots.click()
    assert messages[-1] == "没有需要清理的截图。"


def test_empty_page_hero_shortcut_loads_the_selected_hero(window):
    from PySide6.QtWidgets import QPushButton
    w, engine, _ = window
    engine.set_hero(None)
    w.refresh()
    choices = w.hero_choices.findChildren(QPushButton)
    assert choices
    choices[0].click()
    w.refresh()
    assert choices[0].text() in w.hero_label.text() and w.hero_choices.isHidden()
