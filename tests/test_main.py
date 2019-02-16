from torrt.main import *


def test_basic():
    bootstrap()
    assert TrackerClassesRegistry.get()
    assert NotifierClassesRegistry.get()
    assert RPCClassesRegistry.get()
    walk()
