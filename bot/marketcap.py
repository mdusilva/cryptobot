from requests import Request, Session
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects
import json
import logging

logger = logging.getLogger(__name__)

def get_market_cap(api_key='87d2b2ac-718c-45c3-9d47-865344d973b5'):
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    parameters = {
    'start':'1',
    'limit':'100',
    'convert':'EUR'
    }
    headers = {
    'Accepts': 'application/json',
    'X-CMC_PRO_API_KEY': api_key,
    }

    session = Session()
    session.headers.update(headers)
    market_cap_info = {}
    try:
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
        for c in data.get('data', {}):
            print(c.get('id'), c.get('name'), c.get('symbol'), c.get('cmc_rank'), c.keys())
            if c.get('symbol') is not None:
                market_cap_info[c.get('symbol')] = {'rank': c.get('cmc_rank'), 'supply': c.get('circulating_supply')}
        #   print(data.get('data'))
    except (ConnectionError, Timeout, TooManyRedirects) as e:
        market_cap_info = {}
    return market_cap_info
if __name__ == "__main__":
    print (get_market_cap())