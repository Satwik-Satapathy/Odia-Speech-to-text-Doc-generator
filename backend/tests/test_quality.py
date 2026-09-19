from backend.app.quality import character_error_rate, normalize_text, word_error_rate


def test_odia_unicode_normalization():
    assert normalize_text("ଓଡ଼ିଆ  ଭାଷା") == "ଓଡ଼ିଆ ଭାଷା"


def test_identical_transcript_has_zero_error():
    text = "ଏହା ଏକ ଓଡ଼ିଆ ବାକ୍ୟ।"
    assert word_error_rate(text, text) == 0
    assert character_error_rate(text, text) == 0


def test_different_transcript_has_error():
    assert word_error_rate("ଆଜି ଭଲ ଦିନ", "ଆଜି ଦିନ") > 0
