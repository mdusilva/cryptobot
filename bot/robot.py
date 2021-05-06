import cbpro
import numpy as np
import logging
import logging.handlers
import time
import json
from .marketcap import get_market_cap
import model.db as model
import os

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class UserClient(cbpro.WebsocketClient):
        
    def on_open(self):
        self.channels = ['user']
        self.last_prices = {}
        logger.info("Connecting to USER channel")
        self.session = model.connect_to_session()
        self.current_orders = {}

    def on_message(self, msg):
        logger.debug("Received USER message: %s" % msg)
        if 'type' in msg:
            if 'product_id' in msg:
                product = msg.get('product_id')
                order_id = msg.get('order_id')
                side = msg.get('side')
                timestamp = msg.get('time')
                size = msg.get('size')
                funds = msg.get('funds')
                price = msg.get('price')
                r = self.session.query(model.Pairs).filter(model.Pairs.symbol == product).one_or_none()
                pair_id = None
                if r is not None:
                    pair_id = r.id
                if msg['type'] == 'received':
                    status = 'received'
                    if product in self.current_orders:
                        self.current_orders[product] += [order_id]
                    else:
                        self.current_orders[product] = [order_id]
                elif msg['type'] == 'match':
                    status = 'matched'
                    order_id = msg.get('taker_order_id')
                elif msg['type'] == 'done':
                    status = msg.get('reason')
                    if product in self.current_orders:
                        self.current_orders[product].remove(order_id)
                    else:
                        logger.error("Received DONE message for an order (%s) which is not in current list" % order_id)
                else:
                    status = 'other'
                try:
                    self.session.add(
                        model.Transaction(
                            timestamp=timestamp,
                            order_id=order_id,
                            pair_id=pair_id,
                            size=size,
                            funds=funds,
                            price=price,
                            side=side,
                            status=status
                        )
                    )
                    self.session.commit()
                except Exception as e:
                    logger.error("Unable to write transaction to DB: %s" % e, exc_info=True)

    def on_close(self):
        self.session.close()
        logger.error("Lost connection to USER")
        print("-- Goodbye! --")

    def on_error(self, e, data=None):
        self.error = e
        self.stop = True
        logger.error("There was an error with USER subscription: %s" % e)
        print('{} - data: {}'.format(e, data))

class TickerClient(cbpro.WebsocketClient):

    def on_open(self):
        self.url = "wss://ws-feed.pro.coinbase.com/"
        self.channels = ['ticker']
        self.last_prices = {}
        logger.info("Connecting to TICKER channel")
        self.session = model.connect_to_session()
        self.error = None

    def on_message(self, msg):
        #logger.debug("Receives TICKER msg: %s" % msg)
        if 'type' in msg and 'price' in msg and 'product_id' in msg:
            if msg.get('product_id') is not None:
                self.last_prices[msg.get('product_id')] = float(msg.get('price'))

    def on_close(self):
        logger.error("Lost connection to TICKER")
        self.session.close()
        if self.error is not None:
            logger.info("Last connection was stopped in error, attempting reconnection...")
            count = 1
            self.start()
            while count < 100 and not self.ws.connected:
                time.sleep(30)
                count += 1
                self.start()
                logger.debug("Attempt number %s" % count)

        print("-- Goodbye! --")

    def on_error(self, e, data=None):
        self.error = e
        self.stop = True
        logger.error("There was an error with TICKER subscription: %s" % e)
        print('{} - data: {}'.format(e, data))

def get_rest_client(env):
    if env == "production":
        logger.debug("Setting up REST client in production mode...")
        with open("production.json") as json_file:
            client_parameters = json.load(json_file)
    elif env == "test":
        logger.debug("Setting up REST client in test mode...")
        with open("sandbox.json") as json_file:
            client_parameters = json.load(json_file)
    else:
        logger.error("Unknown environment. Client is not set up")
        return
    key = client_parameters.get('api_key')
    b64secret = client_parameters.get('api_secret')
    passphrase = client_parameters.get('passphrase')
    api_url = client_parameters.get('rest_url')
    auth_client = cbpro.AuthenticatedClient(key, b64secret, passphrase, api_url=api_url)
    return auth_client

def get_wss_client(env, products):
    if env == "production":
        logger.debug("Setting up WSS client in production mode...")
        with open("production.json") as json_file:
            client_parameters = json.load(json_file)
    elif env == "test":
        logger.debug("Setting up WSS client in test mode...")
        with open("sandbox.json") as json_file:
            client_parameters = json.load(json_file)
    else:
        logger.error("Unknown environment. Client is not set up")
        return (None, None)
    url = client_parameters.get('wss_url')
    key = client_parameters.get('api_key')
    b64secret = client_parameters.get('api_secret')
    passphrase = client_parameters.get('passphrase')
    ticker_wsClient = TickerClient(products=products)
    user_wsClient = UserClient(url=url, products=products, auth=True, api_key=key, api_secret=b64secret, api_passphrase=passphrase)
    ticker_wsClient.start()
    user_wsClient.start()
    return (ticker_wsClient, user_wsClient)

def get_mkt_cap_key():
    logger.debug("Getting marketcap API key...")
    with open("mktcap.json") as json_file:
        parameters = json.load(json_file)
    key = parameters.get('key')
    return key

def get_configuration(session=None):
    close_session = False
    if session is None:
        session = model.connect_to_session()
    configuration_parameters = {}
    with open("configuration.json") as json_file:
        configuration_parameters = json.load(json_file)
    configuration_parameters['base_weight'] = float(configuration_parameters.get('base_weight'))
    universe = configuration_parameters.get('universe')
    base_currency = configuration_parameters.get('base_currency')
    configuration_parameters['portfolio_size'] = int(configuration_parameters.get('portfolio_size', 0))
    product_pairs = {c: c + '-' + base_currency for c in universe}
    configuration_parameters['product_pairs'] = product_pairs
    try:
        r = session.query(model.Execution).filter(model.Execution.name == configuration_parameters['execution_name']).one_or_none()
        if r is None:
            new_execution = model.Execution(parameters=configuration_parameters, name=configuration_parameters['execution_name'])
            session.add(new_execution)
            session.flush()
            execution_id = new_execution.id
            session.commit()
        else:
            execution_id = r.id
    except Exception as e:
        logger.critical("Unable to get configuration: %s" % e, exc_info=True)
        raise
    else:
        configuration_parameters['execution_id'] = execution_id
    if close_session:
        session.close()
    return configuration_parameters

def write_pairs(product_pairs, session=None):
    close_session = False
    if session is None:
        session = model.connect_to_session()
    for p in product_pairs.values():
        try:
            r = session.query(model.Pairs).filter(model.Pairs.symbol == p).one_or_none()
            if r is None:
                session.add(model.Pairs(symbol=p))
        except Exception as e:
            logger.error("Unable to add trading pairs to DB: %s" % e, exc_info=True)
    try:
        session.commit()
    except Exception as e:
        logger.error("Failed to write to DB: %s" % e, exc_info=True)
    if close_session:
        session.close()

def write_amount(timestamp, amount, execution_id, session=None):
    close_session = False
    if session is None:
        session = model.connect_to_session()
    try:
        session.add(model.PortfolioValue(timestamp=timestamp, value=amount, execution_id=execution_id))
    except Exception as e:
        logger.error("Unable to write amount to DB: %s" % e, exc_info=True)
    else:
        session.commit()
    if close_session:
        session.close()

def write_positions(timestamp, positions, execution_id, session=None):
    close_session = False
    if session is None:
        session = model.connect_to_session()
    try:
        session.add_all([model.Positions(timestamp=timestamp, symbol=c, value=v, execution_id=execution_id) for c, v in positions.items()])
    except Exception as e:
        logger.error("Unable to write positions to DB: %s" % e, exc_info=True)
    else:
        session.commit()
    if close_session:
        session.close()

def write_submitted_order(submitted_order, execution_id, session=None):
    close_session = False
    if session is None:
        session = model.connect_to_session()

    r = session.query(model.Pairs).filter(model.Pairs.symbol == submitted_order.get('product_id')).one_or_none()
    pair_id = None
    if r is not None:
        pair_id = r.id
    try:
        session.add(
            model.Transaction(
                timestamp=submitted_order.get('created_at'),
                order_id=submitted_order.get('id'),
                pair_id=pair_id,
                size=submitted_order.get('size'),
                funds=submitted_order.get('funds'),
                price=None,
                side=submitted_order.get('side'),
                status=submitted_order.get('status'),
                execution_id=execution_id
            )
        )
        session.commit()
    except Exception as e:
        logger.error("Unable to write transaction to DB: %s" % e, exc_info=True)
    if close_session:
        session.close()

def initialize_prices(wsClient, universe):
    #Initialize prices
    t0 = time.time()
    logger.debug("Waiting for prices...")
    while len(wsClient.last_prices) != len(universe) and time.time() - t0 < 5 * 60:
        time.sleep(1)
    if len(wsClient.last_prices) == len(universe):
        return True
    else:
        return False

def create_orders(target_positions, current_positions, universe):
    orders = []
    for c in universe:
        delta = target_positions.get(c, np.nan) - current_positions.get(c, np.nan)
        logger.debug("Order delta for %s is %s" % (c, np.round(delta, 5)))
        if not np.isnan(delta):
            orders.append((np.round(delta, 5), c))
    orders.sort()
    return orders

def get_target_weights(universe, market_caps, base_weight, portfolio_size):
    current_caps = [(market_caps.get(c).get('rank'), c) for c in universe if c in market_caps]
    current_caps.sort()
    current_selection = [v[-1] for v in current_caps[:portfolio_size]]
    target_weights = {c: (1 - base_weight) / portfolio_size if c in current_selection else 0 for c in universe}
    return target_weights

def run(env):
    session = model.connect_to_session()
    auth_client = get_rest_client(env)
    mkt_cap_key = get_mkt_cap_key()
    configuration_parameters = get_configuration(session=session)
    timestep = int(configuration_parameters['timestep'])
    universe = configuration_parameters.get('universe')
    base_currency = configuration_parameters.get('base_currency')
    base_weight = configuration_parameters['base_weight']
    product_pairs = configuration_parameters['product_pairs']
    execution_id = configuration_parameters['execution_id']
    portfolio_size = configuration_parameters['portfolio_size']
    write_pairs(product_pairs, session=session)
    ticker_wsClient, user_wsClient = get_wss_client(env, list(product_pairs.values()))
    has_prices = initialize_prices(ticker_wsClient, configuration_parameters['universe'])
    if has_prices and ticker_wsClient is not None and user_wsClient is not None and auth_client is not None:
        orders_submitted = {}
        while True:
            orders = {}
            try:
                market_caps = get_market_cap(mkt_cap_key)
                target_weights = get_target_weights(universe, market_caps, base_weight, portfolio_size)
                accounts = auth_client.get_accounts()
                current_orders = {c: sum([f for i, f in v.items() if i in user_wsClient.current_orders.get(c, [])]) for c, v in orders_submitted.items()}
                logger.debug("Current orders = %s" % current_orders)
                logger.debug("Current prices = %s" % ticker_wsClient.last_prices)
                current_positions = {acc.get('currency'): float(acc.get('balance')) for acc in accounts if acc.get('currency') in universe + [base_currency]}
                # write_positions(auth_client.get_time().get('iso'), current_positions, execution_id, session=session)
                current_positions = {c: ticker_wsClient.last_prices.get(product_pairs.get(c), np.nan) * v if c != base_currency else v for c, v in current_positions.items()}
                logger.debug("Current positions = %s" % current_positions)
                amount = sum(current_positions.values())
                logger.debug("Total amount=%s" % amount)
                write_amount(auth_client.get_time().get('iso'), amount, execution_id, session=session)
                current_weights = {}
                if not np.isnan(amount) and amount != 0:
                    current_weights = {c: v / amount for c, v in current_positions.items() if c in universe}
                logger.debug("Current weights = %s" % current_weights)
                logger.debug("Target weights = %s" % target_weights)
                target_positions = {c: amount * target_weights.get(c, np.nan) for c in universe}
                logger.debug("Target positions = %s" % target_positions)
                # orders = {c: target_positions.get(c, np.nan) - current_positions.get(c, np.nan) for c in universe}
                if len(market_caps) < 1:
                    logger.debug("No market caps received so weights are unreliable. Keeping current weights")
                    orders = []
                else:
                    orders = create_orders(target_positions, current_positions, universe)
                logger.debug("Current orders = %s" % orders)
            except Exception as e:
                logger.error("Error computing orders: %s" % e, exc_info=True)
                break
            try:
                for v, c in orders:
                    if not np.isnan(v) and v != 0:
                        trading_pair = product_pairs.get(c)
                        side = 'buy' if v > 0 else 'sell'
                        funds = abs(v)
                        logger.debug("Placing %s order of %s %s for %s" % (side, funds, base_currency, trading_pair))
                        r = auth_client.place_market_order(product_id=trading_pair, 
                               side=side, 
                               funds=funds)
                        if 'status' in r and r['status'] == 'pending' and 'id' in r and 'product_id' in r:
                            if r['product_id'] in orders_submitted:
                                orders_submitted[r['product_id']].update({r['id']: r['funds']})
                            else:
                                orders_submitted[r['product_id']] = {r['id']: r['funds']}
                            write_submitted_order(r, execution_id, session=session)
                            logger.debug("Submitted orders for %s are now: %s" % (r['product_id'], orders_submitted[r['product_id']]))
                        logger.debug("Response is: %s" % r)
                current_positions = {acc.get('currency'): float(acc.get('balance')) for acc in accounts if acc.get('currency') in universe + [base_currency]}
                write_positions(auth_client.get_time().get('iso'), current_positions, execution_id, session=session)
            except Exception as e:
                logger.error("Error sending orders: %s" % e, exc_info=True)
            time.sleep(timestep)
        ticker_wsClient.close()
        user_wsClient.close()
    session.close()

    if __name__ == "__main__":
        pass
