import pymysql.cursors
from datetime import date

from market_edge import MarketEdgeRequestException
from market_edge.marketedge import MarketEdge
from pymysql import IntegrityError

market_edge = MarketEdge("isanketmishra@gmail.com", "An@lyt1cs")


# https://pymysql.readthedocs.io/en/latest/user/examples.html
def insert_into_indicators_table(date, symbol, ud200, ud50, ud21, ud10, score, power, position, reco):
    # Connect to the database
    connection = pymysql.connect(host="localhost",
                                 user="root",
                                 password="Pazzw0rd",
                                 database="marketedge")

    with connection:
        with connection.cursor() as cursor:
            # Create a new record
            sql = "INSERT INTO `indicators` (`date`, `symbol`, `ud200`, `ud50`, `ud21`, `ud10`, `score`, `power`, " \
                  "`position`, `recommendation`) " \
                  f"VALUES ('{date}', '{symbol}', {ud200}, {ud50}, {ud21}, {ud10}, {score}, {power}, " \
                  f"{position}, '{reco}')"

            # print(sql)
            cursor.execute(sql)
        connection.commit()


def fetch_all_from_db():
    # Connect to the database
    connection = pymysql.connect(host="localhost",
                                 user="root",
                                 password="Pazzw0rd",
                                 database="marketedge")

    with connection:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT distinct symbol FROM `indicators`"
            cursor.execute(sql)
            result = cursor.fetchall()
            symbols = [x[0] for x in result]
            print(symbols)
            return symbols


def fetch_records_from_market_edge():
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

    static_list = ['TSLA', 'MSFT', 'TWLO', 'NVDA', 'STLD', 'NFLX', 'IMKTA', 'SWX', 'BOX']

    long_symbols = sorted(set([symbol['sym'] for symbol in all_stocks if symbol['opinion'] == "Long"]
                              + fetch_all_from_db() + static_list))

    for symbol in sorted(long_symbols):
        print(f"Fetching data for: {symbol}")
        try:
            all_data = market_edge.get_data(f"/ssov2/medata/{symbol}")
        except Exception as e:
            print(f"Exception occurred: Skipping {symbol}: {e}")
            continue

        stock_data = all_data['stock'][0]
        ud200 = int(float(stock_data['ud200']))
        ud50 = int(float(stock_data['ud50']))
        ud21 = int(float(stock_data['ud21']))
        ud10 = int(float(stock_data['ud10']))
        score = int(float(stock_data['score']))
        power = int(float(stock_data['pwr']), )
        position = int(float(stock_data['pos']))
        reco = stock_data["sorecommendation"]

        try:
            insert_into_indicators_table(date.today(), symbol, ud200, ud50, ud21, ud10, score, power, position, reco)
        except IntegrityError:
            print(f"{symbol} already processed")
            pass


if __name__ == "__main__":
    fetch_records_from_market_edge()
'''
SELECT * FROM marketedge.indicators;
CREATE TABLE `indicators` (
  `date` date NOT NULL,
  `symbol` varchar(10) NOT NULL,
  `ud200` int DEFAULT NULL,
  `ud50` int DEFAULT NULL,
  `ud21` int DEFAULT NULL,
  `ud10` int DEFAULT NULL,
  `score` int DEFAULT NULL,
  `power` int DEFAULT NULL,
  `position` int DEFAULT NULL,
  `recommendation` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`date`,`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;



SELECT * FROM marketedge.indicators 
where power > 80 and position > 40 and position < 80 
and ud200 > 110 and ud200 > ud50 and ud50 > ud21 and ud21 > ud10
and ud10 > 100
and date = date(current_timestamp())
order by symbol, date;
'''
