from typing import Set

from market_edge.marketedge import MarketEdge

market_edge = MarketEdge("isanketmishra@gmail.com", "An@lyt1cs")


def get_stocks_to_buy():
    best_longs = market_edge.get_data("/ssov2/screens/bestlongs")
    new_highs = market_edge.get_data("/ssov2/screens/newhighs")
    biggest_gainers = market_edge.get_data("/ssov2/screens/biggestgainers")
    biggest_gainer_percent = market_edge.get_data("/ssov2/screens/biggestgainerpercent")
    highest_vol_increase = market_edge.get_data("/ssov2/screens/highestvolincrease")
    upgrades = market_edge.get_data("/ssov2/screens/upgrades")
    pi_growth = market_edge.get_data("/ssov2/screens/pigrowth")
    pi_momentum = market_edge.get_data("/ssov2/screens/pimomentum")
    pi_can_slim = market_edge.get_data("/ssov2/screens/picanslim")
    power_plays = market_edge.get_data("/ssov2/screens/powerplays")

    all_stocks = best_longs + new_highs + biggest_gainers + biggest_gainer_percent + highest_vol_increase + \
                 upgrades + pi_growth + pi_momentum + pi_can_slim + power_plays

    long_symbols = set([symbol['sym'] for symbol in all_stocks if symbol['opinion'] == "Long"])

    result = []
    for symbol in sorted(long_symbols):
        all_data = market_edge.get_data(f"/ssov2/medata/{symbol}")

        stock_data = all_data['stock'][0]

        if float(stock_data['ud']) > 1.0 and \
                (float(stock_data['ud200']) > float(stock_data['ud50']) > float(stock_data['ud21']) > 100) and \
                stock_data['a10'] == stock_data['a21'] == stock_data['a50'] == stock_data['a200'] == "B" and \
                104 < float(stock_data['ud200']) < 125 and 80 < int(stock_data['pwr']) < 100 and \
                40 < int(stock_data['pos']) < 80:

            print(f"===== ***** {symbol} ***** =========")
            print("DEFINITE BUY FOUND")
            print(stock_data["sorecommendation"])
            result.append({"symbol": symbol,
                           "data": {
                               "ud200": float(stock_data['ud200']),
                               "ud50": float(stock_data['ud50']),
                               "ud21": float(stock_data['ud21']),
                               "ud10": float(stock_data['ud10']),
                               "power": int(stock_data['pwr']),
                               "position": int(stock_data['pos'])
                           }})
            print()

    print(f"All best stocks: {result}")


def check_stocks_to_sell(symbols: Set):
    result = []
    for symbol in symbols:
        all_data = market_edge.get_data(f"/ssov2/medata/{symbol}")


        stock_data = all_data['stock'][0]
        if not(stock_data['a10'] == stock_data['a21'] == stock_data['a50'] == stock_data['a200'] == "B"):
            print(f"===== ***** {symbol} ***** =========")
            print(stock_data["sorecommendation"])
            print("DEFINITE SELL FOUND")
            result.append(symbol)
            print()

    print(f"Stocks to be sold: {sorted(set(result))}")


get_stocks_to_buy()

stocks_in_folio = {'ANDE', 'MTDR', 'SSRM', 'AMX', 'GOLD', 'NUGT', 'QUAD', 'CIB', 'GDX', 'COST', 'PDCO', 'NGVC', 'SA',
                   'ORLY', 'VLO', 'RCI', 'URA', 'PAAS', 'JNUG', 'SLCA', 'FUTY', 'SPH', 'IEZ', 'VIVO', 'PAM'}
# check_stocks_to_sell(stocks_in_folio)

folio_stocks1 = {'IEZ', 'JNUG', 'MERC', 'MOS', 'NTR', 'NVGS', 'OIH', 'PANW', 'QUAD', 'RCMT', 'SLCA', 'SXC', 'VIVO', 'VYGR'}
# check_stocks_to_sell(folio_stocks1)

symbols = {'TWLO', 'FLR', 'EUO', 'AG', 'HAL', 'SLB', 'XLE', 'VDE', 'IMKTA', 'OFS', 'SA', 'SWX', 'BOX', 'NUE', 'X', 'AR',
           'NVO', 'IRDM', 'ICLN', 'TAN', 'TSLA', 'VOO', 'XLK'}
# check_stocks_to_sell(symbols)



"""
4/19: ['AMX', 'ANDE', 'CIB', 'COST', 'FUTY', 'GDX', 'GOLD', 'IEZ', 'JNUG', 'MTDR', 'NGVC', 'NUGT', 'ORLY', 'PAAS', 'PAM', 'PDCO', 'QUAD', 'RCI', 'SA', 'SLCA', 'SPH', 'SSRM', 'URA', 'VIVO', 'VLO']
4/20 : ['CHE', 'CPE', 'ENTA', 'EUO', 'EURN', 'IEZ', 'JNUG', 'MERC', 'MOS', 'NTR', 'NUGT', 'NVGS', 'OIH', 'ORA', 'PAAS', 'PAM', 'PANW', 'PWR', 'QUAD', 'RCI', 'RCMT', 'SA', 'SJT', 'SLCA', 'SXC', 'TEO', 'TVTY', 'UNG', 'VIVO', 'VYGR']
"""

[{'symbol': 'CAT', 'data': {'ud200': 115.0, 'ud50': 107.0, 'ud21': 101.0, 'ud10': 101.0, 'power': 85, 'position': 68}},
 {'symbol': 'GLP', 'data': {'ud200': 119.0, 'ud50': 107.0, 'ud21': 103.0, 'ud10': 100.0, 'power': 83, 'position': 55}},
 {'symbol': 'KE', 'data': {'ud200': 121.0, 'ud50': 112.0, 'ud21': 104.0, 'ud10': 102.0, 'power': 85, 'position': 65}}]
