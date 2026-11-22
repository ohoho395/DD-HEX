"""The observer owns and releases its capture handle on the capturing thread."""

import threading

import numpy as np
import pytest

from lolhex.config import Settings
from lolhex.engine import Engine
from lolhex.vision import capture, window


@pytest.fixture
def observer(store, tmp_path, monkeypatch):
    engine = Engine(Settings(), home=tmp_path, store=store)
    state = {"game": False, "client": True, "foreground": True, "rect": window.Rect(0, 0, 80, 60)}
    instances = []

    class Capture:
        def __init__(self):
            self.owner = threading.get_ident()
            self.closed_by = []
            self.grabs = 0

        def grab(self, rect):
            assert threading.get_ident() == self.owner
            self.grabs += 1
            return np.zeros((rect["height"], rect["width"], 4), np.uint8)

        def close(self):
            self.closed_by.append(threading.get_ident())

    def current_capture():
        instance = getattr(capture._local, "mss", None)
        if instance is None:
            instance = Capture()
            capture._local.mss = instance
            instances.append(instance)
        return instance

    monkeypatch.setattr(capture, "_mss", current_capture)
    monkeypatch.setattr(window, "find_game_window", lambda: 2 if state["game"] else 0)
    monkeypatch.setattr(window, "find_client_window", lambda: 1 if state["client"] else 0)
    monkeypatch.setattr(window, "is_foreground", lambda hwnd: state["foreground"])
    monkeypatch.setattr(window, "client_rect", lambda hwnd: state["rect"])
    monkeypatch.setattr(window, "drawn_rects", lambda: [])
    yield engine, state, instances
    engine.stop()
    capture.release()


@pytest.mark.parametrize("transition,interval", [("background", 1.0), ("game", 2.0), ("closed", 3.0)])
def test_leaving_foreground_capture_releases_handle(observer, transition, interval):
    engine, state, instances = observer
    assert engine._observe_once() == 1.0
    instance = instances[0]
    assert not instance.closed_by
    if transition == "background":
        state["foreground"] = False
    elif transition == "game":
        state["game"] = True
    else:
        state["client"] = False
    assert engine._observe_once() == interval
    assert instance.closed_by == [instance.owner]
    assert getattr(capture._local, "mss", None) is None


def test_foreground_capture_reuses_handle_and_recreates_after_pause(observer):
    engine, state, instances = observer
    engine._observe_once()
    engine._observe_once()
    assert len(instances) == 1 and instances[0].grabs == 2
    assert not instances[0].closed_by
    state["foreground"] = False
    engine._observe_once()
    state["foreground"] = True
    engine._observe_once()
    assert len(instances) == 2
    assert instances[0].closed_by == [instances[0].owner]
    assert not instances[1].closed_by


def test_missing_client_geometry_releases_previous_capture(observer):
    engine, state, instances = observer
    engine._observe_once()
    state["rect"] = None
    engine._observe_once()
    assert instances[0].closed_by == [instances[0].owner]


def test_observer_stop_releases_handle_on_capturing_thread(observer, monkeypatch):
    engine, _, instances = observer
    observe = engine._observe_once
    main_thread = threading.get_ident()

    def capture_then_stop():
        interval = observe()
        engine.stop()
        return interval

    monkeypatch.setattr(engine, "_observe_once", capture_then_stop)
    thread = threading.Thread(target=engine._observer_loop)
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive()
    assert len(instances) == 1 and instances[0].owner != main_thread
    assert instances[0].closed_by == [instances[0].owner]


def test_stop_does_not_close_a_capture_from_the_calling_thread(observer, monkeypatch):
    engine, _, instances = observer
    scan = engine._champ_select_scan
    captured, resume = threading.Event(), threading.Event()

    def in_flight_scan(hwnd):
        scan(hwnd)
        captured.set()
        assert resume.wait(timeout=2)

    monkeypatch.setattr(engine, "_champ_select_scan", in_flight_scan)
    thread = threading.Thread(target=engine._observer_loop)
    thread.start()
    try:
        assert captured.wait(timeout=2)
        engine.stop()
        assert thread.is_alive()
        assert not instances[0].closed_by
    finally:
        resume.set()
        thread.join(timeout=2)
    assert not thread.is_alive()
    assert instances[0].closed_by == [instances[0].owner]


def test_unexpected_observer_exit_releases_capture(observer, monkeypatch):
    engine, _, instances = observer
    observe = engine._observe_once

    class ObserverExit(BaseException):
        pass

    def capture_then_exit():
        observe()
        raise ObserverExit()

    monkeypatch.setattr(engine, "_observe_once", capture_then_exit)
    with pytest.raises(ObserverExit):
        engine._observer_loop()
    assert instances[0].closed_by == [instances[0].owner]


def test_observer_error_releases_before_recovery_and_final_stop(observer, monkeypatch):
    engine, _, instances = observer
    observe = engine._observe_once
    cycles = 0

    def capture_then_fail_or_stop():
        nonlocal cycles
        cycles += 1
        if cycles == 2:
            # Cleanup must precede the retry, not just happen when the thread exits.
            assert instances[0].closed_by == [instances[0].owner]
        interval = observe()
        if cycles == 1:
            raise RuntimeError("synthetic observer failure")
        engine.stop()
        return interval

    monkeypatch.setattr(engine, "_observe_once", capture_then_fail_or_stop)
    # Keep the retry deterministic without a multi-second test sleep.
    monkeypatch.setattr(engine._stop, "wait", lambda timeout=None: engine._stop.is_set())
    thread = threading.Thread(target=engine._observer_loop)
    thread.start()
    thread.join(timeout=2)
    assert not thread.is_alive() and cycles == 2
    assert len(instances) == 2
    assert all(instance.closed_by == [instance.owner] for instance in instances)
