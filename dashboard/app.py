import sqlalchemy
from . import ws
import model.db as model
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import plotly.express as px
import pandas as pd
import numpy as np
import json
import time
import uuid
import threading

class TickerClient(ws.CBChannelServer, threading.Thread):

    def __init__(self, pairs, **kwargs):
        ws.CBChannelServer.__init__(self, pairs, 'ticker', **kwargs)
        threading.Thread.__init__(self)
        self.daemon = True
        self.last_prices = {}

    def run(self):
        self.connect()

    def on_open(self):
        print("Connecting to TICKER channel")
        self.session = model.connect_to_session()
        self.error = None

    def on_message(self, msg):
        #logger.debug("Receives TICKER msg: %s" % msg)
        if msg is not None:
            msg = json.loads(msg)
            if 'type' in msg and 'price' in msg and 'product_id' in msg:
                if msg.get('product_id') is not None:
                    self.last_prices[msg.get('product_id')] = float(msg.get('price'))

    def on_close(self):
        print("Lost connection to TICKER")
        self.session.close()

    def on_error(self, e):
        self.error = e
        self.stop = True
        print("There was an error with TICKER subscription: %s" % e)
session = model.connect_to_session()
try:
    currency_pairs = session.execute(sqlalchemy.select(model.Pairs.symbol)).scalars().all()

    ticker_wsClient = TickerClient(currency_pairs)
    execution_ids = session.execute(sqlalchemy.select(model.Execution)).scalars().all()
    executions_dict = {e.id: e for e in execution_ids}
    execution_options = [{'label': e.name, 'value': str(e.id)} for e in execution_ids]
    ticker_wsClient.start()
    t0 = time.time()
    while len(ticker_wsClient.last_prices) != len(currency_pairs) and time.time() - t0 < 5 * 60:
        time.sleep(1)
except Exception as e:
    raise

app = dash.Dash(__name__)
server = app.server

def current_positions(positions):
    df = pd.DataFrame.from_dict(positions, orient='index', columns=['Value']).reset_index().rename(columns={'index': 'Asset'})
    fig = px.pie(df, values='Value', names='Asset', hole=0.3, title='Allocation')
    fig.update_layout(
        font_family="Courier New",
        font_color="cyan",
        title_font_family="Times New Roman",
        title_font_color="white",
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        autosize=True,
        margin=dict(t=50, b=50, l=0, r=0),
        height=250,
        legend_x=0.1
    )
    return fig

def portfolio_value(values, current_fig):
    portfolio_data = {dt: sum(v.values()) for dt, v in values.items()}
    df = pd.DataFrame.from_dict(portfolio_data, orient='index', columns=['Value']).reset_index().rename(columns={'index': 'Time'})
    if current_fig is None:
        fig = px.line(
            df, 
            x=df['Time'], 
            y=df['Value'], 
            template='plotly_dark', 
            title='Portfolio value')
        fig.update_layout(
            # font_family="Courier New",
            # font_color="blue",
            title_font_family="Times New Roman",
            title_font_color="white",
            xaxis_title="Time",
            yaxis_title="Value (BTC)",
            paper_bgcolor='rgba(0, 0, 0, 0)',
            plot_bgcolor='rgba(0, 0, 0, 0)',
            autosize=True,
            margin={'b': 15},
            # legend_title_font_color="green"
        )
    else:
        new_x = current_fig.get('data')[0].get('x') + df['Time'].tolist()
        new_y = current_fig.get('data')[0].get('y') + df['Value'].tolist()
        current_fig.update(data=[{'x': new_x[-1000:], 'y': new_y[-1000:]}])
        fig = current_fig
    return fig

@app.callback([
                Output('positions-graph', 'figure'),
                Output('portfolio-value-graph', 'figure'),
                Output('transaction-table', 'data'),
                Output('current-value-text', 'children'),
                Output('price-table', 'data')
                ],
                Input('interval-component', 'n_intervals'),
                Input('execution-id-choice', 'value'),
                State('portfolio-value-graph', 'figure')
            )
def update_positions(n, execution_id, current_portfolio_fig):
    session = model.connect_to_session()
    # execution_id = session.execute(sqlalchemy.select(model.Execution)).scalar().id
    execution_id = uuid.UUID(execution_id)
    subq = sqlalchemy.select(sqlalchemy.func.max(model.Positions.timestamp)).subquery()
    positions_query = sqlalchemy.select(model.Positions).join(subq, model.Positions.timestamp == subq).filter(model.Positions.execution_id == execution_id)
    result = session.execute(positions_query).scalars().all()
    # result = session.execute(sqlalchemy.select(model.Positions.value, model.Positions.timestamp, model.Positions.symbol).filter(model.Positions.execution_id == execution_id)).all()
    transactions_query = sqlalchemy.select(model.Transaction).filter(sqlalchemy.and_(model.Transaction.execution_id == execution_id, model.Transaction.status == 'pending'))
    last_transactions_pending = session.execute(transactions_query.order_by(model.Transaction.timestamp.desc()).limit(10)).scalars().all()
    pending_ids = {x.order_id: x for x in last_transactions_pending}
    last_transactions = session.execute(sqlalchemy.select(model.Transaction).filter(model.Transaction.order_id.in_(pending_ids.keys())).order_by(model.Transaction.timestamp.desc())).scalars().all()
    filled_ids= {x.order_id: x for x in last_transactions if x.status == 'filled'}
    matched_ids = {x.order_id: x for x in last_transactions if x.status == 'matched'}
    orders_records = [
        {'Timestamp': matched_ids.get(k, v).timestamp, 
        'Pair': filled_ids.get(k, v).pair.symbol, 
        'Size': matched_ids.get(k, v).size, 
        'Funds': v.funds, 
        'Price': matched_ids.get(k, v).price, 
        'Side': filled_ids.get(k, v).side, 
        'Status': filled_ids.get(k, v).status} for k, v in pending_ids.items()]
    prices_records = [
        {
        'Pair': n,
        'Price': v
        } for n, v in ticker_wsClient.last_prices.items()]
    session.close()
    result_dic = {r.symbol: r.value for r in result}
    current_prices = {n.split('-', 1)[0]: v for n, v in ticker_wsClient.last_prices.items()}
    result_dic = {n: v * current_prices.get(n) if current_prices.get(n) is not None else v for n, v in result_dic.items()}
    fig_positions = current_positions(result_dic)
    fig_portfolio_value = portfolio_value({pd.Timestamp(1).now(): result_dic}, current_portfolio_fig)
    current_value_text = "%s BTC" % sum(result_dic.values())
    return fig_positions, fig_portfolio_value, orders_records, current_value_text, prices_records

#Layout
app.layout = html.Div([
    html.Div(className='row', children=[
        html.Div(className='four columns div-user-controls', children=[
            html.H1('Cryptobot dashboard'),
            html.H4(id='current-value-text'),
            html.P('Current execution'),
            html.Div(
                className='div-for-dropdown',
                children= [
                        dcc.Dropdown(
                                        id='execution-id-choice',
                                        options=execution_options,
                                        value=execution_options[-1]['value'],
                                        clearable=False
                                    )
                ],
                style={'color': '#1E1E1E'}
            ),
            dcc.Graph(id='positions-graph'),
            html.H4('Current prices'),
            dash_table.DataTable(
                    id='price-table',
                    columns=[{'id': c, 'name': c} for c in ['Pair', 'Price']],
                    page_size=15,
                    style_as_list_view=True,
                    style_header={'backgroundColor': 'rgb(30, 30, 30)'},
                    style_cell={
                                'backgroundColor': 'rgb(50, 50, 50)',
                                'color': 'white'
                                },
                    sort_action='native',
            ),
        ]),
        html.Div(className='eight columns div-for-charts bg-grey', children=[
            dcc.Graph(id='portfolio-value-graph'),
            html.Div(
                style={'width': '85%'},
                children=[
                        html.H4('Recent transactions'),
                        dash_table.DataTable(
                            id='transaction-table',
                            columns=[{'id': c, 'name': c} for c in ['Timestamp', 'Pair', 'Size', 'Funds', 'Price', 'Side', 'Status']],
                            page_size=10,
                            style_as_list_view=True,
                            style_header={'backgroundColor': 'rgb(30, 30, 30)'},
                            style_cell={
                                        'backgroundColor': 'rgb(50, 50, 50)',
                                        'color': 'white'
                                        },
            ),
                ]
            ),
            dcc.Interval(
                            id='interval-component',
                            n_intervals=0,
                            interval=5000
                        ),
            ])
        ])
    ])

def start():
    app.run_server(debug=True)

if __name__ == "__main__":
    start()