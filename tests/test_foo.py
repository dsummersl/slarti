from slarti.foo import bar


def test_bar():
    assert bar() == "foobar"
