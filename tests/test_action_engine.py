from app.tools.engine import ActionEngine


def test_calculator_route():
    engine = ActionEngine()
    assert engine.route("calculate 12 * 3")[0] == "calculator"


def test_time_route():
    engine = ActionEngine()
    assert engine.route("abhi time kya hai")[0] == "current_time"


def test_unknown_request_is_not_executed():
    engine = ActionEngine()
    assert engine.route("delete my computer")==None
