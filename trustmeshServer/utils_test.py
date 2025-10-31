from utils import *

def test_encode_decode_roundtrip():
    for val in [0, 42, 2**64, 2**200]:
        assert decode_id(encode_id(val)) == val

def test_decode_accepts_str_and_int():
    assert decode_id("123") == 123
    assert decode_id(123) == 123