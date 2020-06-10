from binance.client import Client
import requests
import os, glob
import json
from datetime import datetime, timedelta
from pandas import DataFrame as df
import re
import binance_keys
import plotly.offline as py
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import time
import multiprocessing
import concurrent.futures
'''For multiprosesing'''
from functools import partial
from contextlib import contextmanager
'''PYTI imports'''
from pyti.smoothed_moving_average import smoothed_moving_average as sma
from pyti.bollinger_bands import *
''' upper_bollinger_band
    middle_bollinger_band
    lower_bollinger_band
    percent_bandwidth'''
from pyti.stochrsi import stochrsi as srsi 



'''
####    NOTES ON WHAT TO DO NEXT    ####

Rewrite 
    1   Solve 'invalid value encountered in double_scalars'
    2   saving json stats
Write
    1   
    2   Write the system that will find the best setting for a strategy (In notes)
Further Ideas
    1   Record time it takes to backtest each interval
'''

client = None
commition = 0.001

@contextmanager
def poolcontext(*args, **kwargs):
    pool = multiprocessing.Pool(*args, **kwargs)
    yield pool
    pool.terminate()

class Binance_Bot():
    @staticmethod
    def connect():
        global client
        client = Client(api_key = binance_keys.Pkey, api_secret = binance_keys.Skey)

    @staticmethod
    def binance_coin_price(coin,interval):
        if interval == '1m':client_interval = Client.KLINE_INTERVAL_1MINUTE
        elif interval == '3m':client_interval = Client.KLINE_INTERVAL_3MINUTE
        elif interval == '5m':client_interval = Client.KLINE_INTERVAL_5MINUTE
        elif interval == '15m':client_interval = Client.KLINE_INTERVAL_15MINUTE
        elif interval == '30m':client_interval = Client.KLINE_INTERVAL_30MINUTE
        elif interval == '1h':client_interval = Client.KLINE_INTERVAL_1HOUR
        elif interval == '2h':client_interval = Client.KLINE_INTERVAL_2HOUR
        elif interval == '4h':client_interval = Client.KLINE_INTERVAL_4HOUR
        elif interval == '6h':client_interval = Client.KLINE_INTERVAL_6HOUR
        elif interval == '8h':client_interval = Client.KLINE_INTERVAL_8HOUR
        elif interval == '12h':client_interval = Client.KLINE_INTERVAL_12HOUR
        elif interval == '1d':client_interval = Client.KLINE_INTERVAL_1DAY
        elif interval == '3d':client_interval = Client.KLINE_INTERVAL_3DAY
        elif interval == '1w':client_interval = Client.KLINE_INTERVAL_1WEEK
        elif interval == '1M':client_interval = Client.KLINE_INTERVAL_1MONTH
        else:
            print("The interval is invalid")
            
        candles = client.get_klines(symbol = coin+'BTC', interval = client_interval)

        candles_data_frame = df(candles)
        candles_data_frame_date = candles_data_frame[0]

        final_date = []
        for time in candles_data_frame_date:
            readable = datetime.fromtimestamp(int(time/1000))
            final_date.append(readable)

        candles_data_frame.pop(0)
        candles_data_frame.pop(11)

        data_frame_final_date = df(final_date)
        data_frame_final_date.columns = ['Date']

        final_data_frame = candles_data_frame.join(data_frame_final_date)
        final_data_frame.set_index('Date', inplace=True)
        final_data_frame.columns = ['open', 'high', 'low', 'close', 'volume', 'close_time', 'asset_volume', 'trade_number', 'taker_buy_base', 'taker_buy_quote']
    
        for col in final_data_frame.columns:
            final_data_frame[col] = final_data_frame[col].astype(float)
    
        return final_data_frame

    @staticmethod
    def json_to_data_frame(path):
        with open(path,'r') as json_file:
            data = json.load(json_file)
        
        data_frame = df(data)
        if data_frame.__len__() == 0:
            print('Json file has no data')
            return None
        else:
            data_frame_date = data_frame[0]

            final_date = []
            for time in data_frame_date:
                readable = datetime.fromtimestamp(int(time/1000))
                final_date.append(readable)
            
            data_frame.pop(0)
            data_frame.pop(11)
            
            data_frame_final_date = df(final_date)
            data_frame_final_date.columns = ['Date']

            final_data_frame = data_frame.join(data_frame_final_date)
            final_data_frame.set_index('Date', inplace=True)
            final_data_frame.columns = ['open', 'high', 'low', 'close', 'volume', 'close_time', 'asset_volume', 'trade_number', 'taker_buy_base', 'taker_buy_quote']
        
            for col in final_data_frame.columns:
                final_data_frame[col] = final_data_frame[col].astype(float)
            
            return final_data_frame

    @staticmethod
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
        perge_list=['USDT', 'UPUSDT', 'DOWNUSDT', 'USDC', 'RUB', 'EUR', 'BUSD', 'NGN', 'TRY', 'ZAR', 'BKRW', 'IDRT']
        coin_list = [x for x in coin_list if x not in perge_list]
        return coin_list

    @staticmethod
    def backtest_resent(func = None, interval = '15m', btc_to_spend = 1, indicator_intr_lst = [], critical_val_lst = []):
        # Performes a backtest with the newly downloaded 500 candles from the binance API
        broken_coins = []
        coin_list = Binance_Bot.get_trading_coins()
        for coin in coin_list:
            try:
                print()
                print(coin)
                data_frame = Binance_Bot.binance_coin_price(coin, interval)
                
                buy_signals, sell_signals = func(data_frame, indicator_intr_lst, critical_val_lst)
                
                stats = Strategy.gen_stats(buy_signals, sell_signals, btc_to_spend)
                if stats == None:
                    print('There were no sell signals')
                
                else: Strategy.print_stats(stats)
                
            except Exception as e:
                broken_coins.append(coin)
                print('Unable to get the data for a coin in a list')
                print(e)
        print('Could not locate historical data for the following coins:', broken_coins)   

    @staticmethod
    def analyse_json(json_file, func = None, interval = '15m', btc_to_spend = 1, minimum_len = 100, limit = 0, save_stats = False, indicator_intr_lst = [], critical_val_lst = []):
        func_name = func.__name__

        #some data_bases might be very short
        limit_used = limit * -1
        
        start_time = time.time() #to time how long it took to process
        execution_start = datetime.now() # to display when the processing started
        data_frame = Binance_Bot.json_to_data_frame('historical_data/' + interval + '/' + json_file)

        if type(data_frame) != type(df([[]])):
            print('',json_file,
                'Backtest with a pair started {}'.format(execution_start.strftime("%H:%M:%S")),
                'Json file is empty',
                sep = '\n')
            # in case json file in empty and json_to_data_frame returns None
            return
        if data_frame.__len__() < minimum_len :
            print('',json_file,
                'Backtest with a pair started {}'.format(execution_start.strftime("%H:%M:%S")),
                f'Skipping as the length of the data < {minimum_len}',
                sep = '\n')
            return
        if data_frame.__len__() < limit:
            print('',json_file,
                'Backtest with a pair started {}'.format(execution_start.strftime("%H:%M:%S")),
                f'Skipping as the length of the data < {limit}',
                sep = '\n')
            return
                
        buy_signals, sell_signals = func(data_frame[limit_used:-1], indicator_intr_lst, critical_val_lst)
        stats = Strategy.gen_stats(buy_signals, sell_signals, btc_to_spend)
        time_taken = round(time.time() - start_time, 1)

        if stats == None:
            print('',json_file,
                'Backtest with a pair started {}'.format(execution_start.strftime("%H:%M:%S")),
                f'No sell signals',
                sep = '\n')
                
        else: 
            print('',json_file,
                'Backtest with a pair started {}'.format(execution_start.strftime("%H:%M:%S")),
                f'Took {time_taken}sec',
                sep = '\n')
            Strategy.print_stats(stats)
            return stats
        

        ''' TO BE REWORKED '''
        if save_stats:
            del Strategy.stats['Interval']
            del Strategy.setting['Interval']

            with open(
                "strategies/" + func_name + "/" + interval + '/' + str(limit) + '_' + json_file
                    ,'w' # set file write mode
            ) as f:
                print('Data is writen to file {}'.format(datetime.now().strftime("%H:%M:%S")))
                f.write(json.dumps({'Stats': Strategy.stats, 'Settings': Strategy.setting}, indent=3))

    @staticmethod
    def backtest_local(func = None, interval = '15m', btc_to_spend = 1, minimum_len = 100, limit = 0, save_stats = False, multi_processing = True, indicator_intr_lst = [], critical_val_lst = []):
        # Backtest of data that is stored lockaly in historical_data and save the results
        func_name = func.__name__
        if os.path.isdir("strategies/" + func_name) != True: os.makedirs("strategies/" + func_name)
        if os.path.isdir("strategies/" + func_name + "/" + interval) != True: os.makedirs("strategies/" + func_name + "/" + interval)

        json_list = os.listdir('historical_data/' + interval)

        if multi_processing:
            with poolcontext(processes=4) as pool:
                result_stats = pool.map(partial(Binance_Bot.analyse_json, func = func, interval = interval, btc_to_spend = btc_to_spend, minimum_len = minimum_len, 
                    limit = limit, save_stats = save_stats, indicator_intr_lst = indicator_intr_lst, critical_val_lst = critical_val_lst), json_list)
        else:
            result_stats = []
            for json_file in json_list:
                stat = Binance_Bot.analyse_json(json_file, func = func, interval = interval, btc_to_spend = btc_to_spend, minimum_len = minimum_len, 
                    limit = limit, save_stats = save_stats, indicator_intr_lst = indicator_intr_lst, critical_val_lst = critical_val_lst)
                result_stats.append(stat)
        
        average_stats = {'%/1w Profit' : [], 'Success Chance' : []}
        for stat in result_stats:
            if type(stat) == type({}):
                if stat['%/1w Profit'] != 0 : average_stats['%/1w Profit'].append(stat['%/1w Profit'])
                if stat['Success Chance'] != 0 : average_stats['Success Chance'].append(stat['Success Chance'])
        ave_prs_per_1w = sum(average_stats['%/1w Profit']) / len(average_stats['%/1w Profit'])
        ave_suc_chan = sum(average_stats['Success Chance']) / len(average_stats['Success Chance'])
        print()
        print(f'Average %/1w Profit: {ave_prs_per_1w*100}, ')
        print(f'Average Success Chance: {ave_suc_chan*100}, ')

class Indicator():
    stand_alone = []

    @staticmethod
    def add_srsi(df_or_lst, period):
        if isinstance(df_or_lst, list) == True:
            return srsi(df_or_lst, period)
        else:
            Indicator.stand_alone.append('srsi '+ str(period))
            data_frame['srsi '+ str(period)] = srsi(df_or_lst['close'].tolist(), period)
    
    @staticmethod
    def add_sma(df_or_lst, period):
        if isinstance(df_or_lst, list) == True:
            return sma(df_or_lst, period)
        else:
            data_frame['sma '+ str(period)] = sma(df_or_lst['close'].tolist(), period)
    
    @staticmethod
    def add_boll_up(df_or_lst, period):
        if isinstance(df_or_lst, list) == True:
            return upper_bollinger_band(df_or_lst, period)
        else:
            df_or_lst['boll upper '+ str(period)] = upper_bollinger_band(df_or_lst['close'].tolist(), period)
    
    @staticmethod
    def add_boll_md(df_or_lst, period):
        if isinstance(df_or_lst, list) == True:
            return middle_bollinger_band(df_or_lst, period)
        else:
            df_or_lst['boll middle '+ str(period)] = middle_bollinger_band(df_or_lst['close'].tolist(), period)
    
    @staticmethod
    def add_boll_lw(df_or_lst, period):
        if isinstance(df_or_lst, list) == True:
            return lower_bollinger_band(df_or_lst, period)
        else:
            df_or_lst['boll lower '+ str(period)] = lower_bollinger_band(df_or_lst['close'].tolist(), period)

    @staticmethod
    def add_boll(df_or_lst, period_lw, period_md, period_up):
    # ONLY TO BE USED FOR ADDING TO THE GRAPH
        if isinstance(df_or_lst, list) == True:
            pass
        else:
            df_or_lst['boll lower '+ str(period_lw)] = lower_bollinger_band(df_or_lst['close'].tolist(), period_lw)
            df_or_lst['boll middle '+ str(period_md)] = middle_bollinger_band(df_or_lst['close'].tolist(), period_md)
            df_or_lst['boll upper '+ str(period_up)] = upper_bollinger_band(df_or_lst['close'].tolist(), period_up)

class Visualise():
    @staticmethod
    def time_to_intervals(data_frame,time):
        indicator = time[-1]
        time = time[:-1]
        integer = int(time)
        if indicator == 'm':    time = timedelta(minutes = integer)
        elif indicator == 'h':    time = timedelta(hours = integer)
        elif indicator == 'd':    time = timedelta(days = integer)
        elif indicator == 'w':    time = timedelta(days = integer * 7)
        elif indicator == 'M':  
            time = timedelta(days = integer * 28)
            print('The function \"time_to_intervals\" may not work as expected if \"<n>M\" was chosen')
            print('Please use m, h, d, or w instead')
        else:
            raise ValueError('Time is not given in the right format.')
        time_per_candle = data_frame.index[:][-1] - data_frame.index[:][-2]
        if time < time_per_candle:
            raise ValueError('Time passed is smaller than time per interval.')
        elif time % time_per_candle != timedelta(minutes = 0):
            raise ValueError('Number of intervals must turn out to be an integer.')
        num_of_intervals = int(time / time_per_candle)
        return num_of_intervals

    @staticmethod
    def draw_candles(data_frame, buy_signals=[], sell_signals=[]):
        fig = make_subplots(rows=len(Indicator.stand_alone)+1, cols=1, 
                        shared_xaxes=True, 
                        #vertical_spacing=0.19
                        )
        fig.update_layout(title_text="Candles")

        trace_candles = go.Candlestick(
            x = data_frame.index[:],
            open = data_frame['open'],
            close = data_frame['close'],
            high = data_frame['high'],
            low = data_frame['low'],
            name = 'Candlesticks')
        fig.add_trace(trace_candles)
        
        
        if len(buy_signals) != 0:
            buy_signals_data_frame = df(buy_signals)
            buys = go.Scatter(
                    x = buy_signals_data_frame[0],
                    y = buy_signals_data_frame[1],
                    name = "Buy Signals",
                    mode = 'markers',
                    marker=dict(
                            color='Red',
                            size=15,
                            opacity=0.95,
                            line=dict(
                            color='Green',
                            width=1))                        
                    )
            fig.add_trace(buys)
        else:
            print('There were no buy signals')
        
        if len(sell_signals) != 0:
            buy_signals_data_frame = df(sell_signals)
            sells = go.Scatter(
                    x = buy_signals_data_frame[0],
                    y = buy_signals_data_frame[1],
                    name = "Sell Signals",
                    mode = 'markers',
                    marker=dict(
                            color='Green',
                            size=15,
                            opacity=0.95,
                            line=dict(
                            color='Red',
                            width=1)) )
            fig.add_trace(sells)
        else:
            print('There were no sells signals')
        

        for indicator in data_frame.columns:
            if indicator not in ['open', 'high', 'low', 'close', 'volume', 'close_time', 'asset_volume', 'trade_number', 'taker_buy_base', 'taker_buy_quote']:
                if indicator not in Indicator.stand_alone:
                    fig.add_trace(
                        go.Scatter( x = data_frame.index[:],
                                    y = data_frame[indicator],
                                    name = indicator)
                        )
        
        for i in range(0, len(Indicator.stand_alone)):
            if Indicator.stand_alone[i] in data_frame.columns:
                fig.add_trace(
                    go.Scatter(
                        x = data_frame.index[:],
                        y = data_frame[Indicator.stand_alone[i]],
                        name = Indicator.stand_alone[i]
                    ), row = i+2, col = 1
                )
        
        py.plot(fig, filename="data_visualised.html")

class Strategy:
    '''Statistics of a list to be able to compare it
    stats = {'Success Chance':0, 'Number of Sells':0, 'Sells Profit':0, 
    'Net Profit':0, 'Persentage Profit':0, 'BTC/1w Profit':0, '%/1w Profit':0 , 'Interval':0, 'Fees Paid': 0, 'Loose Strick': 0} '''
    # The varables that are part of the logic and the logic discribed in words
    setting = {'Interval':0, 'Logic':''}       
    
    @staticmethod
    def gen_stats(buy_signals ,sell_signals ,btc_to_trade):
        try:
            if len(sell_signals) == 0:
                return None
            # returns a dictionaty of stats
            stats = {}
            profitable_sell = 0
            for i in range(0,len(sell_signals)):
                if sell_signals[i][1] > buy_signals[i][1]: profitable_sell += 1
            stats['Success Chance'] = round(profitable_sell / len(sell_signals), 4)
            stats['Number of Sells'] = len(buy_signals)
            stats['Fees Paid'] = 0
            stats['Sells Profit'] = 0
            stats['Loose Strick'] = 0
            for i in range(0,len(sell_signals)):
                stats['Fees Paid'] += (((btc_to_trade / buy_signals[i][1]) * sell_signals[i][1])) * commition
                stats['Fees Paid'] += btc_to_trade * commition
                # Print the how much btc is gained by selling the coins 
                #print((((btc_to_trade / buy_signals[i][1]) * sell_signals[i][1])))
                stats['Sells Profit'] += (((btc_to_trade / buy_signals[i][1]) * sell_signals[i][1]) - btc_to_trade)
            stats['Net Profit'] = stats['Sells Profit'] - stats['Fees Paid'] 
            stats['Interval'] = Strategy.setting['Interval']
            stats['Persentage Profit'] = stats["Net Profit"] / btc_to_trade
            stats['BTC/1w Profit'] = stats['Net Profit'] / ((500 - Strategy.setting['First Candle']) * (int(stats['Interval'].total_seconds()) / 604800))
            stats['%/1w Profit'] = stats['Persentage Profit'] / ((500 - Strategy.setting['First Candle']) * (int(stats['Interval'].total_seconds()) / 604800))

            current_loose_strick = 0
            for i in range(0, len(sell_signals)):
                if sell_signals[i][1] < buy_signals[i][1]: current_loose_strick += 1
                else: 
                    current_loose_strick = 0
                if stats['Loose Strick'] < current_loose_strick: stats['Loose Strick'] = current_loose_strick
            return stats
        except ZeroDivisionError:
            print('Can\'t get stats when there were no sells')

    @staticmethod
    def print_stats(stats):
        red_bg , green_bg , normal_bg = '\u001b[41;1m' , '\u001b[42;1m' , '\u001b[0m'

        if stats['Persentage Profit'] > 0: pp = green_bg
        elif stats['Persentage Profit'] <= 0: pp = red_bg
        else: pp = normal_bg
        if stats['Success Chance'] > 0.5: cc = green_bg
        elif stats['Success Chance'] <= 0.5: cc = red_bg
        else: pp = normal_bg
        
        for key, var in stats.items():
            if key not in  ['Interval']:
                stats[key] = round(var, 8)
        print( pp+' %/1w Profit:{}%'.format(round(stats['%/1w Profit']*100,4)), normal_bg ,end=' ')
        print( cc+' Success Chance:{}%'.format(round(stats['Success Chance']*100,4)), normal_bg ,end=' ')
        print( ' Profit%:{}%'.format(round(stats['Persentage Profit']*100,4)), end=' ')
        print('Num of sells:{}, Interval:{}, BTC/1w Profit:{}'.format(stats['Number of Sells'], stats['Interval'], stats['BTC/1w Profit']))
        print(stats)

    @staticmethod
    def srsi_and_boll(data_frame, indicator_intr_lst = [], critical_val_lst = []):
        # indicator_intr_lst = [ srsi_interval ,  boll_interval ]
        # critical_val_lst   = [ buy_val_srsi ]
        # 14,30,35  15m=   2.092%/1w, 85.14%
        # 14,30,25  15m=   2.53%/1w,  81,85%    limit=700
        # 14,25,25  15m=   1.85%/1w,  77,63%    limit=700
 

        if len(indicator_intr_lst) != 2 or len(critical_val_lst) != 1:
            print('srsi_and_boll needs 2 intervals and 1 critical value')
            raise ValueError('srsi_and_boll needs 2 intervals and 1 critical value')
        srsi_interval = indicator_intr_lst[0]
        boll_interval = indicator_intr_lst[1]
        buy_val_srsi = critical_val_lst[0]

        # set the settings
        Strategy.setting['Srsi Interval'] = srsi_interval
        Strategy.setting['Boll Interval'] = boll_interval
        Strategy.setting['Logic'] = f'Buy if srsi_{srsi_interval} = {buy_val_srsi} and price < boll_lw_{boll_interval}. Sell if price = boll_md_{boll_interval}'
        Strategy.setting['Interval'] = data_frame.index[1] - data_frame.index[0]

        # start the execution 
        lst_lows = data_frame['low'].tolist()
        lst_highs = data_frame['high'].tolist()
        lst_time = data_frame.index[:].tolist()
        isBought = False
        first_candle = srsi_interval if srsi_interval > boll_interval else boll_interval
        Strategy.setting['First Candle'] = first_candle

        buy_signals = []
        sell_signals = []
        for i in range(first_candle, len(lst_lows)):
            if Indicator.add_srsi(lst_lows[:i], srsi_interval)[-1] < buy_val_srsi < Indicator.add_srsi(lst_highs[:i], srsi_interval)[-1] and lst_lows[i] < Indicator.add_boll_lw(lst_lows[:i], boll_interval)[-1] < lst_highs[i] and isBought == False:
                buy_signals.append([lst_time[i], Indicator.add_boll_lw(lst_lows[:i], boll_interval)[-1]])
                isBought = True
            elif lst_lows[i] < Indicator.add_boll_md(lst_lows[:i], boll_interval)[-1] < lst_highs[i] and isBought == True:
                sell_signals.append([lst_time[i],Indicator.add_boll_md(lst_lows[:i], boll_interval)[-1]])
                isBought = False
        return buy_signals, sell_signals
    
# MAIN CODE STARTS HERE
# MUltiprosessing backtest




Binance_Bot.backtest_local(func = Strategy.srsi_and_boll, limit = 700, indicator_intr_lst = [14,25], critical_val_lst = [25])


#Binance_Bot.connect()
#data_frame = Binance_Bot.binance_coin_price('ETH', '15m')
#Indicator.add_boll(data_frame,30,30,30)
#Indicator.add_srsi(data_frame, 14)
#Visualise.draw_candles(data_frame)

#Binance_Bot.backtest_resent(Strategy.srsi_and_boll, indicator_intr_lst=[14,30], critical_val_lst= [35])

#data_frame = Binance_Bot.json_to_data_frame('historical_data/3d/Binance_ARK_3d_1501545600000-1590969600000.json')


























'''
interval_list = ['1m','3m']
indicator_intr_lsts = [[30,40]]
critical_val_lsts = [[5,15]]

lst_lst= [[interval,indicator,value] for interval in interval_list for indicator in indicator_intr_lsts for value in critical_val_lsts ]
print(lst_lst)

for interval in interval_list[::-1]: # interval
        for indicator_intr_lst in indicator_intr_lsts:
            for indicator in indicator_intr_lst: # indicator
                for critical_val_lst in critical_val_lsts:
                    for critical_value in critical_val_lst: #critical value
                        print(interval, indicator, critical_value)
'''
'''
for interval in interval_list: #interval
    #how many indicators and crit_values the function expects
    num_of_indicators = len(indicator_intr_lsts)
    num_of_crit_values = len(critical_val_lsts)

    for  in indicator_intr_lsts:
        for idicator in indicator_intr_lst:
            pass
''' 
            
            







''' WRITING A FUNCTION HERE
def backtest_optomise(func = None, btc_to_spend = 1, limit = 0, save_stats = Fasle, 
    interval_list = ['1m','3m','5m','15m','30m','1h','2h','4h','6h','8h','12h','1d','3d','1w'],
    indicator_intr_lsts=[[],[],[]], critical_val_lsts = [[],[],[]]):
    for interval in interval_list[::-1]: # interval
        for indicator_intr_lst in critical_val_lsts:
            for indicator in indicator_intr_lst: # indicator
                for critical_val_lst in critical_val_lsts:
                    for critical_value in critical_val_lst: #critical value

                        Binance_Bot.backtest_local(func=func, indicator_intr_lst=[30,20], critical_val_lst= [35],limit= 100,  interval='1d' )

        
        with concurrent.futures.ProcessPoolExecutor() as executer:
            secs = [1,2,3,4,5]
            processes = [executer.submit(func, sec) for sec in secs]
'''


'''
data_frame = Binance_Bot.binance_coin_price('LTC', '15m')

Indicator.add_srsi(data_frame, 30)
Indicator.add_boll(data_frame, 20,20,20)

Strategy.srsi_and_boll(data_frame, 30, 20)

Visualise.draw_candles(data_frame)

Strategy.gen_stats(1)
Strategy.print_stats()
'''

#data_frame = Binance_Bot.json_to_data_frame("historical_data/1m/Binance_ETH_1m_1501545600000-1591456884049.json")

#Binance_Bot.backtest_local(func = Strategy.srsi_and_boll, fun_arg_1 = 30, fun_arg_2 = 20,interval = '15m', limit = 1000)
'''
data_frame = Binance_Bot.json_to_data_frame("historical_data/1w/Binance_BNB_1w_1501545600000-1591467650243.json")
Indicator.add_srsi(data_frame, 30)
Indicator.add_boll(data_frame, 20,20,20)
Strategy.srsi_and_boll(data_frame, 30,20)
Strategy.gen_stats(data_frame)
Strategy.print_stats()
Visualise.draw_candles(data_frame)
'''