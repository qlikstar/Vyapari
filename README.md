# Vyapari
Vyapari means trader (in Sanskrit). This is designed to be highly customizable and configurable stock trading bot that 
runs on Alpaca and Pushover. 

This software is designed to do the following:
- Persist the trades in a DB (MySQL)
- Expose a set of interactive REST API interface
- Integrate Telegram to send out push notifications
- GUI to visualize the trades ( http://<IP_ADDRESS>:8000/ui/index )

## Description
This project is highly customizable and is based on the following:
- Alpaca
- Telegram (to send push notifications)

## Architecture
![Vyapari](https://user-images.githubusercontent.com/4952220/134234830-a3ecd063-53ec-4a61-8a9e-72267e6e1794.jpeg)

## Run the service locally for development
- Rename the `env.yml.sample` to `env.yml`
- Populate the required values for Alpaca and Telegram and FMP credentials
- Run `docker-compose -f docker-compose-mysql.yml up -d` to bring up Mysql8 instance
- Run the following command `make run`

## Run the service on a remote instance
- Rename the `env.yml.sample` to `env.yml`
- Populate the required values for Alpaca, Telegram and FMP credentials
- Run `docker-compose up` and you should see the server running
- Use `docker-compose up --build` in case you modify any `.py` files
  
## Setup Virtualenv and install dependencies
- Create a new virtual env `virtualenv venv`
- Activate the virtualenv `source venv/bin/activate`
- Now install the required dependencies: `pip install -r requirements.txt`
- Finally, run the app either using `python app.py` or `uvicorn app:app`

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

