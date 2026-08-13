from monitor_self_attestation import (
    I_HAVE_PUBLISHED_MY_FEDWATCH_MONITOR_SITE,
    URL_TO_MY_FEDWATCH_MONITOR_SITE,
)


def test_monitor_flag_set():
    assert I_HAVE_PUBLISHED_MY_FEDWATCH_MONITOR_SITE


def test_monitor_url_provided():
    assert URL_TO_MY_FEDWATCH_MONITOR_SITE != ""
