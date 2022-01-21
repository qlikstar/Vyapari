# Vyapari
Vyapari means trader (in Sanskrit). This is designed to be highly customizable and configurable stock trading bot that 
runs on Alpaca and Pushover. 

Future PR intend to do the following:
- Persist the trades in a DB (Postgres/SQLite)
- Expose a set of interactive REST API interface
- Integrate Telegram to make it customizable
- GUI to visualize the trades

## Description
This project is highly customizable and is based on the following:
- Alpaca
- Pushover (to send push notifications)

## Architecture
![Vyapari](https://user-images.githubusercontent.com/4952220/134234830-a3ecd063-53ec-4a61-8a9e-72267e6e1794.jpeg)

## How to run
- Rename the `env.yml.sample` to `env.yml`
- Populate the required values for Alpaca and Pushover
- Run `docker-compose up` to bring up Mysql8 instance
- Run the following command `make clean install run`
  
## Setup Webhook for Telegram
- Setup webhook locally: https://github.com/azimjohn/jprq-python-client
- Expose port `8000` locally to receive Telegram requests: `jprq http 8000 -s=<subdomain>`

## Back-testing
- Edit `backtest.py` to suit your needs
- Run the command`$ python3 backtest.py`

## Concepts
To be filled up later

## Credits
- Concepts from Freqtrade (https://www.freqtrade.io/en/stable/)
- https://github.com/SC4RECOIN/simple-crypto-breakout-strategy

## Note
This is for educational purpose only. The author is not liable for any monetary loss during trading

## Issues
- Install TA-Lib on mac: https://stackoverflow.com/questions/41155985/python-ta-lib-install-problems
