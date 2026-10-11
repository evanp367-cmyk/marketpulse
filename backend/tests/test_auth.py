import hashlib,hmac,time
from urllib.parse import urlencode
from backend.app.core.auth import validate_telegram_init_data

def test_telegram_init_data_validation():
    token="123:fake-token-for-test";data={"auth_date":str(int(time.time())),"user":'{"id":42,"first_name":"Test"}'}
    check="\n".join(f"{k}={v}" for k,v in sorted(data.items()));secret=hmac.new(b"WebAppData",token.encode(),hashlib.sha256).digest();data['hash']=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
    result=validate_telegram_init_data(urlencode(data),token,60);assert result['id']==42
def test_bad_signature_rejected():
    try:validate_telegram_init_data("auth_date=1&user=%7B%7D&hash=nope","token",100)
    except ValueError:pass
    else:assert False,"invalid signature should be rejected"


def test_duplicate_telegram_fields_are_rejected():
    with __import__('pytest').raises(ValueError):
        validate_telegram_init_data('auth_date=1&auth_date=2&user=%7B%22id%22%3A42%7D&hash=nope', 'token', 100)

def test_expired_telegram_init_data_is_rejected():
    import pytest
    token = "123:fake-token-for-test"
    data = {"auth_date": str(int(time.time()) - 120), "user": '{"id":42}'}
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    with pytest.raises(ValueError):
        validate_telegram_init_data(urlencode(data), token, 60)


def test_telegram_init_data_rejects_non_positive_or_non_integer_user_id():
    import pytest
    token = "123:fake-token-for-test"
    for user_json in ('{"id":0}', '{"id":-42}', '{"id":"42"}', '{"id":true}'):
        data = {"auth_date": str(int(time.time())), "user": user_json}
        check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
        data["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
        with pytest.raises(ValueError):
            validate_telegram_init_data(urlencode(data), token, 60)
