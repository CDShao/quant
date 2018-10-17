# -*- coding: utf-8 -*-


import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandas_datareader as web
import statsmodels.tsa.stattools as ts



def create_pairs_dataframe(datadir, symbols):

    #Creates a pandas DataFrame containing the closing price
    #of a pair of symbols based on CSV files containing a datetime
    #stamp and OHLCV data
    
    # Open the individual CSV files and read into pandas DataFrames
    print ("Importing CSV data...")

    # Fetching Data through Yahoo Finance
    
    sym1 = web.DataReader(symbols[0], data_source='yahoo',start ='2016/1/1',end=time.strftime("%Y/%m/%d"))
    sym2 = web.DataReader(symbols[1], data_source='yahoo',start ='2016/1/1',end=time.strftime("%Y/%m/%d"))

    print ("Constructing dual matrix for %s and %s..." % symbols)

    pairs = pd.DataFrame(index=sym1.index)

    pairs['%s_close' % symbols[0]] = sym1['Adj Close']
    pairs['%s_close' % symbols[1]] = sym2['Adj Close']

    pairs = pairs.dropna()
    
    return pairs


def check_cointegration(pairs, symbols):

    print ("Computing Cointegration...")

    coin_result=ts.coint(pairs['%s_close' % symbols[0]],pairs['%s_close' % symbols[1]])
    #Confidence Level chosen as 0.05 (5%)
    return coin_result[1]


def calculate_spread_zscore(pairs, symbols):

    pairs['returns'] = np.log(pairs['%s_close' % symbols[0]]/pairs['%s_close' %symbols[1]])
    pairs['mean'] = pairs['returns'].rolling(window=30,center=False).mean()
    #30天均值

    pairs = pairs.dropna()
    

    # Create the spread and then a z-score of the spread
    print ("Creating the spread/zscore columns...")
    #pairs['spread'] = pairs['spy_close'] - pairs['hedge_ratio']*pairs['iwm_close']
    
    zcore = (pairs.loc[:,'returns'] - pairs.loc[:,'mean']) /pairs.loc[:,'returns'].rolling(window=30,center=False).std()

    pairs['zscore'] = zcore
    return pairs    
 

def signal_generate(pairs, symbols, 
                                     z_entry_threshold=2.0, 
                                     z_exit_threshold1=0.5,
                                     z_exit_threshold2=3.5):
    """Create the entry/exit signals based on the exceeding of 
    z_enter_threshold for entering a position and falling below
    z_exit_threshold for exiting a position."""

    # Calculate when to be long, short and when to exit
    pairs['longs'] = (pairs['zscore'] <= -z_entry_threshold)*1.0
    pairs['shorts'] = (pairs['zscore'] >= z_entry_threshold)*1.0

    pairs['exits'] = ((np.abs(pairs['zscore']) <= z_exit_threshold1 ) )*1.0

    pairs['long_market'] = 0.0
    pairs['short_market'] = 0.0

    # These variables track whether to be long or short while
    # iterating through the bars
    long_market = 0
    short_market = 0

    for i, b in enumerate(pairs.iterrows()):
        # Calculate longs
        if pairs['longs'][i-1] == 1.0:
            long_market = 1            
        # Calculate shorts
        if pairs['shorts'][i-1] == 1.0:
            short_market = 1
            
            
        if pairs['exits'][i-1] == 1.0 or  ((np.abs(pairs['zscore'][i]-pairs['zscore'][i-1]) > 1) and (np.abs(pairs['zscore'][i]+pairs['zscore'][i-1]) < 1)) :
                                  
            pairs['exits'][i-1]=1
            long_market = 0
            short_market = 0

            
        pairs.ix[i]['long_market'] = long_market
        pairs.ix[i]['short_market'] = short_market

    return pairs    


def portfolio_returns(pairs, symbols):

    """Creates a portfolio pandas DataFrame which keeps track of
    the account equity and ultimately generates an equity curve.
    This can be used to generate drawdown and risk/reward ratios."""

    # Convenience variables for symbols
    sym1 = symbols[0]
    sym2 = symbols[1]

    pairs['ret_%s' % symbols[0]] = 100*((pairs['%s_close' %sym1]/pairs['%s_close' %sym1].shift(1))-1)
    pairs['ret_%s' % symbols[1]] = 100*((pairs['%s_close' %sym2]/pairs['%s_close' %sym2].shift(1))-1)

    # Construct the portfolio object with positions information
    # Note that minuses to keep track of shorts!

    print("Constructing a portfolio...")
    portfolio = pd.DataFrame(index=pairs.index)

    portfolio['positions'] = pairs['long_market'] - pairs['short_market']

    pairs['positions'] = pairs['long_market'] - pairs['short_market']

    pairs[sym1] = pairs['ret_%s' % symbols[0]] * portfolio['positions']

    pairs[sym2] = -1.0*pairs['ret_%s' % symbols[1]] * portfolio['positions']

    pairs['total'] = pairs[sym1] + pairs[sym2]
    
    portfolio['total'] = pairs[sym1] + pairs[sym2]

    # Construct a percentage returns stream and eliminate all 
    # of the NaN and -inf/+inf cells
    print ("Constructing the equity curve...")

    # portfolio['returns'] = portfolio['total'].pct_change()
    portfolio['returns'] = portfolio['total']/100   ### wyd


    portfolio['returns'].fillna(0.0, inplace=True)
    portfolio['returns'].replace([np.inf, -np.inf], 0.0, inplace=True)
    portfolio['returns'].replace(-1.0, 0.0, inplace=True)

    # Calculate the full equity curve

    # portfolio['cum_sum']=portfolio['total'].cumsum().plot()
    portfolio['cum_sum'] = (1+portfolio['returns']).cumprod()#  wyd
    portfolio['cum_sum'].plot()

    # (100*np.log(pairs['%s_close' % symbols[0]]/ pairs['%s_close' % symbols[0]].shift(1))).cumsum().plot()
    # (100*np.log(pairs['%s_close' % symbols[1]]/ pairs['%s_close' % symbols[1]].shift(1))).cumsum().plot()
    plt.xlabel("DateTime")
    plt.ylabel("Cumulative Returns ")
    plt.grid(True)
    plt.show()


    return portfolio


    
def run():
    datadir='/Users/wangyaodong/study/qaunt_zhang/Statistical-Arbitrage-using-Pairs-Trading-master'
    symbols = ('SBIN.NS', 'ICICIBANK.NS')
    # symbols = ('ACC.NS', 'AMBUJACEM.NS')


    returns = []

    pairs = create_pairs_dataframe(datadir, symbols)

    coint_check = check_cointegration(pairs, symbols)

    if coint_check < 0.47:

        # if pairs == 1:
        #   exit(1)

        print("Pairs are Cointegrated")
        print(coint_check)

        pairs = calculate_spread_zscore(pairs, symbols)
        pairs = signal_generate(pairs, symbols,
                                z_entry_threshold=2.0,
                                z_exit_threshold1=0.5,
                                z_exit_threshold2=3.5)

        portfolio = portfolio_returns(pairs, symbols)


        plt.plot(portfolio['cum_sum'])
        plt.show()
        pairs.to_csv("op.csv")

    else:
        print(coint_check)
        print("Pairs are not CoIntegrated, Exiting...")
        # sys.exit(0)


if __name__ == "__main__":

    datadir = '/Users/wangyaodong/study/qaunt_zhang/Statistical-Arbitrage-using-Pairs-Trading-master'
    symbols = ('601398.SS', '601939.SS')



    pairs = create_pairs_dataframe(datadir, symbols)
    print (pairs.head())

    coint_check = check_cointegration(pairs, symbols)
    print(coint_check)

    pairs = calculate_spread_zscore(pairs, symbols)
    print(pairs.tail())

    pairs = signal_generate(pairs, symbols,
                            z_entry_threshold=2.0,
                            z_exit_threshold1=0.5,
                            z_exit_threshold2=3.5)
    portfolio = portfolio_returns(pairs, symbols)

    #  returns.append(portfolio.ix[-1]['returns'])

    # plt.plot(portfolio['returns'])
    # plt.show()

