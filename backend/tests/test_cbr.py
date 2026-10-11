import pytest
from backend.app.providers.cbr import CBRDataError, parse_daily_xml, filter_daily_rates


SAMPLE = b'''<?xml version="1.0" encoding="windows-1251"?>
<ValCurs Date="11.10.2026" name="Foreign Currency Market">
  <Valute ID="R01235"><NumCode>840</NumCode><CharCode>USD</CharCode><Nominal>1</Nominal><Name>US Dollar</Name><Value>81,2345</Value><VunitRate>81,2345</VunitRate></Valute>
  <Valute ID="R01239"><NumCode>978</NumCode><CharCode>EUR</CharCode><Nominal>1</Nominal><Name>Euro</Name><Value>94,7654</Value><VunitRate>94,7654</VunitRate></Valute>
  <Valute ID="R01335"><NumCode>392</NumCode><CharCode>JPY</CharCode><Nominal>100</Nominal><Name>Japanese Yen</Name><Value>54,3200</Value><VunitRate>0,5432</VunitRate></Valute>
</ValCurs>'''


def test_parse_daily_rates_normalizes_xml_comma_decimals_and_nominal():
    parsed = parse_daily_xml(SAMPLE)
    assert parsed["source"] == "Bank of Russia"
    assert parsed["rate_date"] == "2026-10-11"
    rates = {item["base"]: item for item in parsed["items"]}
    assert rates["USD"]["symbol"] == "USD/RUB"
    assert rates["USD"]["rate"] == "81.2345"
    assert rates["EUR"]["rate"] == "94.7654"
    assert rates["JPY"]["official_value"] == "54.3200"
    assert rates["JPY"]["rate"] == "0.5432"
    assert rates["USD"]["rate_type"] == "official_daily_reference"


def test_parse_daily_rates_rejects_bad_xml():
    with pytest.raises(CBRDataError):
        parse_daily_xml("not xml")


def test_parse_daily_rates_rejects_empty_currency_document():
    with pytest.raises(CBRDataError):
        parse_daily_xml('<ValCurs Date="11.10.2026"></ValCurs>')



def test_cbr_filter_defaults_to_all_published_currencies_and_supports_explicit_filter():
    parsed = parse_daily_xml(SAMPLE)
    all_rates = filter_daily_rates(parsed)
    assert {item["base"] for item in all_rates["items"]} == {"USD", "EUR", "JPY"}
    filtered = filter_daily_rates(parsed, ["USD"])
    assert [item["base"] for item in filtered["items"]] == ["USD"]
    assert filtered.get("unsupported_symbols") is None
