from verkit.promoter import _increment_semver

def test_increment_semver():
    assert _increment_semver("0.1.0", "patch") == "0.1.1"
    assert _increment_semver("0.1.0", "minor") == "0.2.0"
    assert _increment_semver("0.1.0", "major") == "1.0.0"
    assert _increment_semver("1.2.3-rc1", "patch") == "1.2.4-rc1"
