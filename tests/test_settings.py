import pytest

from gitissuebot import settings

def test_apikey():
    assert settings.config['APIKEY'] == 'my_magic_secret'