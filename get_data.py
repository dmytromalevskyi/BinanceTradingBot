# requires dateparser package
import dateparser
import pytz
from datetime import datetime
import json
import requests
from binance.client import Client
import time
import os

def date_to_milliseconds(date_str):
    """Convert UTC date to milliseconds
    If using offset strings add "UTC" to date string e.g. "now UTC", "11 hours ago UTC"
    See dateparse docs for formats http://dateparser.readthedocs.io/en/latest/
    :param date_str: date in readable format, i.e. "January 01, 2018", "11 hours ago UTC", "now UTC"
    :type date_str: str
    """
    # get epoch value in UTC
    epoch = datetime.utcfromtimestamp(0).replace(tzinfo=pytz.utc)
    # parse our date string
    d = dateparser.parse(date_str)
    # if the date is not timezone aware apply UTC timezone
    if d.tzinfo is None or d.tzinfo.utcoffset(d) is None:
        d = d.replace(tzinfo=pytz.utc)

    # return the difference in time
    return int((d - epoch).total_seconds() * 1000.0)

def interval_to_milliseconds(interval):
    """Convert a Binance interval string to milliseconds
    :param interval: Binance interval string 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w
    :type interval: str
    :return:
         None if unit not one of m, h, d or w
         None if string not in correct format
         int value of interval in milliseconds
    """
    ms = None
    seconds_per_unit = {
        "m": 60,
        "h": 60 * 60,
        "d": 24 * 60 * 60,
        "w": 7 * 24 * 60 * 60
    }

    unit = interval[-1]
    if unit in seconds_per_unit:
        try:
            ms = int(interval[:-1]) * seconds_per_unit[unit] * 1000
        except ValueError:
            print('interval_to_milliseconds function was given wrong ibject type')
            pass
    return ms

def get_historical_klines(symbol, interval, start_str, end_str=None):
    """Get Historical Klines from Binance
    See dateparse docs for valid start and end string formats http://dateparser.readthedocs.io/en/latest/
    If using offset strings for dates add "UTC" to date string e.g. "now UTC", "11 hours ago UTC"
    :param symbol: Name of symbol that will be traided against BTC
    :type symbol: str
    :param interval: Biannce Kline interval
    :type interval: str
    :param start_str: Start date string in UTC format
    :type start_str: str
    :param end_str: optional - end date string in UTC format
    :type end_str: str
    :return: list of OHLCV values
    """
    # make it into a pair
    symbol = symbol+'BTC'

    # create the Binance client, no need for api key
    client = Client("", "")

    # init our list
    output_data = []

    # setup the max limit
    limit = 500

    # convert interval to useful value in seconds
    timeframe = interval_to_milliseconds(interval)

    # convert our date strings to milliseconds
    start_ts = date_to_milliseconds(start_str)

    # if an end time was passed convert it
    end_ts = None
    if end_str:
        end_ts = date_to_milliseconds(end_str)

    idx = 0
    # it can be difficult to know when a symbol was listed on Binance so allow start time to be before list date
    symbol_existed = False
    while True:
        # fetch the klines from start_ts up to max 500 entries or the end_ts if set
        temp_data = client.get_klines(
            symbol=symbol,
            interval=interval,
            #limit=limit,
            startTime=start_ts,
            endTime=end_ts
        )

        # handle the case where our start date is before the symbol pair listed on Binance
        if not symbol_existed and len(temp_data):
            symbol_existed = True

        if symbol_existed:
            # append this loops data to our output data
            output_data += temp_data
            try:    
                # update our start timestamp using the last value in the array and add the interval timeframe
                start_ts = temp_data[len(temp_data) - 1][0] + timeframe
            except Exception as e:
                print(e)
                print('That random error accured again')
                print('The coin might be new')
        else:
            # it wasn't listed yet, increment our start date
            start_ts += timeframe

        idx += 1
        # check if we received less than the required limit and exit the loop
        if len(temp_data) < limit:
            # exit the while loop
            break

        # sleep after every 3rd call to be kind to the API
        if idx % 3 == 0:
            time.sleep(1)

    return output_data


'''
symbol = "ETH"
start = "1 Dec, 2017"
end = "1 Jan, 2018"
interval = Client.KLINE_INTERVAL_30MINUTE
klines = get_historical_klines(symbol, interval, start, end)
# open a file with filename including symbol, interval and start and end converted to milliseconds
with open(
    "historical_data/Binance_{}_{}_{}-{}.json".format(
        symbol, 
        interval, 
        date_to_milliseconds(start),
        date_to_milliseconds(end)
    ),
    'w' # set file write mode
) as f:
    f.write(json.dumps(klines))
'''



def get_trading_coins():
    # Returns a list of trading coins against BTC
    url = "https://api.binance.com/api/v3/exchangeInfo"
    try:
        responce = requests.get(url)
        data = json.loads(responce.text)
    except Exception as Exp:
        print('Unable to connect to', url)
        print(Exp)

    pair_list = []
    for dictionary in data['symbols']:
        if dictionary['status']:
            if dictionary['status'] == 'TRADING':
                pair_list.append(dictionary['symbol'])
    coin_list= []
    for pair in pair_list:
        if 'BTC' in pair:
            coin_list.append(pair.replace('BTC',''))              
    perge_list=['USDT', 'UPUSDT', 'DOWNUSDT', 'USDC', 'RUB', 'EUR', 'BUSD', 'NGN', 'TRY', 'ZAR', 'BKRW', 'IDRT', 'BRD']
    coin_list = [x for x in coin_list if x not in perge_list]
    return coin_list

def get_historical_data(interval, start, end):
    # Downloads klines (and saves as jason) for a particular interval for a list of coins obtained by get_trading_coins 
    '''     Values for interval
    Client.KLINE_INTERVAL_1MINUTE
    Client.KLINE_INTERVAL_3MINUTE 
    Client.KLINE_INTERVAL_5MINUTE 
    Client.KLINE_INTERVAL_15MINUTE 
    Client.KLINE_INTERVAL_30MINUTE 
    Client.KLINE_INTERVAL_1HOUR 
    Client.KLINE_INTERVAL_2HOUR 
    Client.KLINE_INTERVAL_4HOUR 
    Client.KLINE_INTERVAL_6HOUR 
    Client.KLINE_INTERVAL_8HOUR
    Client.KLINE_INTERVAL_12HOUR 
    Client.KLINE_INTERVAL_1DAY 
    Client.KLINE_INTERVAL_3DAY 
    Client.KLINE_INTERVAL_1WEEK
    Client.KLINE_INTERVAL_1MONTH - does NOT work. get_historical_klines would have to be rewriten
    '''
    coins = get_trading_coins()
    i = 1
    for symbol in coins:
        now = datetime.now()
        print()
        print('Starting to fetch data for {}/BTC, {}, {}/{}'.format(symbol, now.strftime("%H:%M:%S"), i, len(coins)))
        i += 1
        if os.path.exists("historical_data/{}/Binance_{}_{}_{}-{}.json".format(
                interval,
                symbol, 
                interval, 
                date_to_milliseconds(start),
                date_to_milliseconds(end)
            )):
            print('Skeping, file already exists')
            continue
        klines = get_historical_klines(symbol, interval, start, end)
        print('Data downloaded')
        with open(
            "historical_data/{}/Binance_{}_{}_{}-{}.json".format(
                interval,
                symbol, 
                interval, 
                date_to_milliseconds(start),
                date_to_milliseconds(end)
            ),
            'w' # set file write mode
        ) as f:
            # for some reason when fetching data for some intervals it puts everything in a list, it has to be removes for compatobility
            print('Data is writen to file')
            f.write(json.dumps(klines))

        



# TESTING STARTS HERE
# Binance exists since July 2017


for time_frame in [
    Client.KLINE_INTERVAL_1MINUTE,
    #Client.KLINE_INTERVAL_3MINUTE, SOME
    #Client.KLINE_INTERVAL_5MINUTE, DONE
    #Client.KLINE_INTERVAL_15MINUTE, DONE
    #Client.KLINE_INTERVAL_30MINUTE, DONE
    #Client.KLINE_INTERVAL_1HOUR, DONE
    #Client.KLINE_INTERVAL_2HOUR, DONE
    #Client.KLINE_INTERVAL_4HOUR, DONE
    #Client.KLINE_INTERVAL_6HOUR, DONE
    #Client.KLINE_INTERVAL_8HOUR, DONE
    #Client.KLINE_INTERVAL_12HOUR, DONE
    #Client.KLINE_INTERVAL_1DAY, DONE
    #Client.KLINE_INTERVAL_3DAY, DONE
    #Client.KLINE_INTERVAL_1WEEK DONE
]:
    get_historical_data(time_frame,'1 Aug, 2017', '1 Jun, 2020')