#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sector Performance 
"""

# Import modules
import os
import time
import psycopg2
import pandas as pd
import datetime as dt
from datetime import datetime
from dotenv import load_dotenv
from polygon import RESTClient
from etf_holdings import etf_holdings, index_etf_tickers, etf_tickers
from sqlalchemy import create_engine, Column, String, Float, MetaData, Table, DateTime, func, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import insert

os.chdir('C:\\Users\\Username\\Desktop\\sector_performance')

load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')
POLYGON_API_KEY = os.getenv('POLYGON_API_KEY')

# API key from config
# from config import polygonAPIkey
# Or just assign your API key as a string variable
# polygonAPIkey = 'apiKeyGoesHere'

def rate_of_change(price_data, days, column='close', as_percent=False):
    try: 
        if len(price_data) < days + 1:
            print(f'Not enough data to compute roc for {days} period lookback')
            return None
    except TypeError:
        return None
    
    recent = price_data[column].iloc[-1]
    past = price_data[column].iloc[-1 - days]

    rate_of_change = float((recent - past) / past)
    return rate_of_change * 100 if as_percent else rate_of_change

def get_timeseries(ticker):
    # Daily bars
    try:
        data_request = client.get_aggs(ticker = ticker, 
                                      multiplier = 1,
                                      timespan = 'day',
                                      from_ =  '2023-06-01',
                                      to = '2100-01-01')
    except:
        print(f'Error with {ticker} data request')
        
    # List of polygon agg objects to DataFrame
    price_data = pd.DataFrame(data_request)
    
    # Create Date column
    try: 
        price_data['Date'] = price_data['timestamp'].apply(
            lambda x: pd.to_datetime(x*1000000))
            
        price_data = price_data.set_index('Date')
    except:
        print(f'Data error for {ticker}. Please check ticker availability.')
        return None
    
    return price_data

def merge_symbol_info(index_etf_tickers, etf_tickers, etf_holdings):
    symbol_info = []
    
    # Add index ETFs
    for symbol in index_etf_tickers:
        symbol_info.append({
            'symbol': symbol,
            'symbol_type': 'INDEX',
            'sector': sector_mapping.get(symbol, 'Unknown'),
            'parent_etf': None
        })

    # Add sector ETFs
    for symbol in etf_tickers:
        symbol_info.append({
            'symbol': symbol,
            'symbol_type': 'SECTOR_ETF',
            'sector': sector_mapping.get(symbol, 'Unknown'),
            'parent_etf': None
        })
    
    # Add individual stocks
    for etf_symbol, holdings in etf_holdings.items():
        sector_name = sector_mapping.get(etf_symbol, 'Unknown')
        for stock_symbol in holdings:
            symbol_info.append({
                'symbol': stock_symbol,
                'symbol_type': 'STOCK',
                'sector': sector_name,
                'parent_etf': etf_symbol
            })
     
    return symbol_info

def add_rate_of_change(symbol_info, timeframes = [1, 5 , 20, 60, 252, 504]):
    for symbol_data in symbol_info:
        symbol = symbol_data['symbol']
        
        # Get price data and calculate roc
        print(f'Getting data for {symbol}')
        price_data = get_timeseries(symbol)
        # time.sleep(12.1)
        
        if price_data is not None:
            # Add roc data        
            for lookback in timeframes:
                roc = rate_of_change(price_data, lookback)
                symbol_data.update({f'roc_{lookback}_day': roc})
        
            # Add date of last data point
            symbol_data.update({'data_as_of': price_data.index[-1]})
        else:
            for lookback in timeframes:
                roc = rate_of_change(price_data, lookback)
                symbol_data.update({f'roc_{lookback}_day': None})
        
            # Add date of last data point
            symbol_data.update({'data_as_of': None})
            
    return symbol_info

# Sector mapping
sector_mapping = {
    'SPY': 'Market',
    'XLK': 'Technology',
    'XLU': 'Utilities', 
    'XLRE': 'Real Estate',
    'XLB': 'Materials',
    'XLV': 'Healthcare',
    'XLF': 'Financial',
    'XLI': 'Industrial',
    'XLY': 'Consumer Discretionary',
    'XLP': 'Consumer Staples',
    'XLE': 'Energy'
}

# Performance lookback timeframes
timeframes = [1, 5, 20, 60, 252, 504]

print('Organizing symbol data.')
all_symbol_info = merge_symbol_info(index_etf_tickers, etf_tickers, etf_holdings)

# Create client and authenticate w/ API key // rate limit 5 requests per min
client = RESTClient(POLYGON_API_KEY) # api_key is used

print('Beginning ROC calculations.')
ticker_data = add_rate_of_change(all_symbol_info, timeframes)

print('ROC calculations complete.')

# for data in ticker_data:
#     if data['symbol'] == 'SPY':
#         print(data)
        
# for data in ticker_data:
#     if data['symbol'] == 'BF.b':
#         print(data)
        
# ticker_data[:10]
# ticker_data[-10:]

# DB connection
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for declarative models
Base = declarative_base()

# Define the table model
class StockData(Base):
    __tablename__ = "stock_data"
    
    symbol = Column(String, primary_key=True)
    symbol_type = Column(String, index=True)
    sector = Column(String, index=True)
    parent_etf = Column(String, index=True)
    
    roc_1_day = Column('roc_1_day', Float)
    roc_5_day = Column('roc_5_day', Float)
    roc_20_day = Column('roc_20_day', Float)
    roc_60_day = Column('roc_60_day', Float)
    roc_252_day = Column('roc_252_day', Float)
    roc_504_day = Column('roc_504_day', Float)
    
    data_as_of = Column(DateTime)
    last_update = Column(DateTime)

Base.metadata.create_all(bind=engine)

# Reflect the table from the database
# metadata = MetaData()

# Drop table
# with engine.begin() as conn:
#     stock_data = Table("stock_data", metadata, autoload_with=conn)
#     stock_data.drop(conn)

def upsert_data(data_list):
    session = SessionLocal()   
    try:

        table = StockData.__table__
        
        for item in data_list:
            stmt = insert(table).values(item)
            stmt = stmt.on_conflict_do_update(
                index_elements=['symbol'],
                set_=dict(
                    symbol_type=stmt.excluded.symbol_type,
                    sector=stmt.excluded.sector,
                    parent_etf=stmt.excluded.parent_etf,
                    
                    roc_1_day=stmt.excluded.roc_1_day,
                    roc_5_day=stmt.excluded.roc_5_day,
                    roc_20_day=stmt.excluded.roc_20_day,
                    roc_60_day=stmt.excluded.roc_60_day,
                    roc_252_day=stmt.excluded.roc_252_day,
                    roc_504_day=stmt.excluded.roc_504_day,
                    
                    data_as_of=stmt.excluded.data_as_of,
                    last_update=datetime.now()
                )
            )
            session.execute(stmt)
        
        session.commit()
        print(f"Successfully upserted {len(data_list)} records")
        
    except Exception as e:
        session.rollback()
        print(f"Error during upsert: {e}")
        raise
    finally:
        session.close()

# if __name__ == __main__:
    # upsert_data(ticker_data)

upsert_data(ticker_data)

# Check row count
#with engine.begin() as conn:
#    result = conn.execute(text("SELECT COUNT(*) FROM stock_data"))
#    row_count = result.scalar()
#    print(f"Total rows in stock_data: {row_count}")
    
# Get one row based on ticker value
#ticker = 'AAPL'

#with engine.begin() as conn:
#    result = conn.execute(
#        text("SELECT * FROM stock_data WHERE symbol = :ticker LIMIT 1"),
#        {"ticker": ticker}
#    )
#    row = result.fetchone()

#    if row:
#        print(row)
#    else:
#        print(f"No row found for {ticker}")