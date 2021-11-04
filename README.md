This repository was created for personal use only and is not being maintained, this is why it does not contain a user guide. It is also not written in a 'coherent' way as it was one of my very first projects. There have been major changes to the Binance API, therefore this repository is no longer usable. This repository only exists as a showcase of my experience.

# BinanceTradingBot
> What it could do:
> - fetch data of any time interval and store it locally
> - write strategies as functions with use of any included indicators
> - backtest and visualise the sell and buy orders with plotly (of any last 30 candles downloaded at run time or stored data)
> - analyse a strategy across multiple parameters and visualise the results (i.e. time interval of the candles, indicator intervals, stop loss...)
> - calculate stats such as commission spent, percentage profit per unit time and others
> - for increased performance each virtual thread of the CPU was used for backtesting a pair (e.g. one thread calculating BTC/USD and the other one LTC/USD and so on)

# Dependencies - all can be downloaded with pip
> - binance
> - requests
> - plotly
> - pandas
> - pyti


# Examples
> Unfortunately since this repository is very outdated I can only present limited amount of examples that I could find on my hard drive
> - check the `Examples of Visualisation` folder for the actual graphs creaded with plotly
> - see `historical_data` folder for the format of fetched data
> ![Data_Visualised_1](/PicturesForREADME/.png?raw=true "Data Visualised 1")
> ![Data_Visualised_2](/PicturesForREADME/.png?raw=true "Data Visualised 2")
> ![Box_Plot_1](/PicturesForREADME/.png?raw=true "Box Plot 1")
> ![Box_Plot_2](/PicturesForREADME/.png?raw=true "Box Plot 2")
