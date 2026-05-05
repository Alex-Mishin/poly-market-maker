"""
Standalone export of update_markets.py.

Generated from the current repository sources. It intentionally duplicates the
helper code that update_markets.py imports from data_updater/* so this file can
be copied and run without the original package layout.
"""


# ===== Inlined from data_updater/trading_utils.py: data_updater.trading_utils =====
from py_clob_client.constants import POLYGON
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, BalanceAllowanceParams, AssetType
from py_clob_client.order_builder.constants import BUY

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

import json

from dotenv import load_dotenv
load_dotenv()

import time

import os

MAX_INT = 2**256 - 1

def get_clob_client():
    host = "https://clob.polymarket.com"
    key = os.getenv("PK")
    chain_id = POLYGON
    
    if key is None:
        print("Environment variable 'PK' cannot be found")
        return None


    try:
        client = ClobClient(host, key=key, chain_id=chain_id)
        api_creds = client.create_or_derive_api_creds()
        client.set_api_creds(api_creds)
        return client
    except Exception as ex: 
        print("Error creating clob client")
        print("________________")
        print(ex)
        return None


def approveContracts():
    web3 = Web3(Web3.HTTPProvider("https://polygon-rpc.com"))
    web3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    wallet = web3.eth.account.from_key(os.getenv("PK"))
    
    
    with open('erc20ABI.json', 'r') as file:
        erc20_abi = json.load(file)

    ctf_address = "0x4D97DCd97eC945f40cF65F87097ACe5EA0476045"
    erc1155_set_approval = """[{"inputs": [{ "internalType": "address", "name": "operator", "type": "address" },{ "internalType": "bool", "name": "approved", "type": "bool" }],"name": "setApprovalForAll","outputs": [],"stateMutability": "nonpayable","type": "function"}]"""

    usdc_contract = web3.eth.contract(address="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", abi=erc20_abi)   # usdc.e
    ctf_contract = web3.eth.contract(address=ctf_address, abi=erc1155_set_approval)
    

    for address in ['0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E', '0xC5d563A36AE78145C45a50134d48A1215220f80a', '0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296']:
        usdc_nonce = web3.eth.get_transaction_count( wallet.address )
        raw_usdc_txn = usdc_contract.functions.approve(address, int(MAX_INT, 0)).build_transaction({
            "chainId": 137, 
            "from": wallet.address, 
            "nonce": usdc_nonce
        })
        signed_usdc_txn = web3.eth.account.sign_transaction(raw_usdc_txn, private_key=os.getenv("PK"))
        usdc_tx_receipt = web3.eth.wait_for_transaction_receipt(signed_usdc_txn, 600)


        print(f'USDC Transaction for {address} returned {usdc_tx_receipt}')
        time.sleep(1)

        ctf_nonce = web3.eth.get_transaction_count( wallet.address )
        
        raw_ctf_approval_txn = ctf_contract.functions.setApprovalForAll(address, True).build_transaction({
            "chainId": 137, 
            "from": wallet.address, 
            "nonce": ctf_nonce
        })

        signed_ctf_approval_tx = web3.eth.account.sign_transaction(raw_ctf_approval_txn, private_key=os.getenv("PK"))
        send_ctf_approval_tx = web3.eth.send_raw_transaction(signed_ctf_approval_tx.raw_transaction)
        ctf_approval_tx_receipt = web3.eth.wait_for_transaction_receipt(send_ctf_approval_tx, 600)

        print(f'CTF Transaction for {address} returned {ctf_approval_tx_receipt}')
        time.sleep(1)



    nonce = web3.eth.get_transaction_count( wallet.address )
    raw_txn_2 = usdc_contract.functions.approve("0xC5d563A36AE78145C45a50134d48A1215220f80a", int(MAX_INT, 0)).build_transaction({
        "chainId": 137, 
        "from": wallet.address, 
        "nonce": nonce
    })
    signed_txn_2 = web3.eth.account.sign_transaction(raw_txn_2, private_key=os.getenv("PK"))
    send_txn_2 = web3.eth.send_raw_transaction(signed_txn_2.raw_transaction)


    nonce = web3.eth.get_transaction_count( wallet.address )
    raw_txn_3 = usdc_contract.functions.approve("0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296", int(MAX_INT, 0)).build_transaction({
        "chainId": 137, 
        "from": wallet.address, 
        "nonce": nonce
    })
    signed_txn_3 = web3.eth.account.sign_transaction(raw_txn_3, private_key=os.getenv("PK"))
    send_txn_3 = web3.eth.send_raw_transaction(signed_txn_3.raw_transaction)
    
    
def market_action( marketId, action, price, size ):
    order_args = OrderArgs(
        price=price,
        size=size,
        side=action,
        token_id=marketId,
    )
    signed_order = get_clob_client().create_order(order_args)
    
    try:
        resp = get_clob_client().post_order(signed_order)
        print(resp)
    except Exception as ex:
        print(ex)
        pass
    
    
def get_position(marketId):
    client = get_clob_client()
    position_res = client.get_balance_allowance(
        BalanceAllowanceParams(
            asset_type=AssetType.CONDITIONAL,
            token_id=marketId
        )
    )
    orderBook = client.get_order_book(marketId)
    price = float(orderBook.bids[-1].price)
    shares = int(position_res['balance']) / 1e6
    return shares * price


# ===== Inlined from data_updater/google_utils.py: data_updater.google_utils =====
from google.oauth2.service_account import Credentials
import gspread
import os
import pandas as pd
import requests
import re


def get_spreadsheet(read_only=False):
    """
    Get the main Google Spreadsheet using credentials and URL from environment variables
    
    Args:
        read_only (bool): If True, uses public CSV export when credentials are missing
    """
    spreadsheet_url = os.getenv("SPREADSHEET_URL")
    if not spreadsheet_url:
        raise ValueError("SPREADSHEET_URL environment variable is not set")
    
    # Check for credentials
    if not os.path.exists('credentials.json'):
        if read_only:
            return ReadOnlySpreadsheet(spreadsheet_url)
        else:
            raise FileNotFoundError("credentials.json not found. Use read_only=True for read-only access.")
    
    # Normal authenticated access
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_file('credentials.json', scopes=scope)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_url(spreadsheet_url)
    return spreadsheet

class ReadOnlySpreadsheet:
    """Read-only wrapper for Google Sheets using public CSV export"""
    
    def __init__(self, spreadsheet_url):
        self.spreadsheet_url = spreadsheet_url
        self.sheet_id = self._extract_sheet_id(spreadsheet_url)
        
    def _extract_sheet_id(self, url):
        """Extract sheet ID from Google Sheets URL"""
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
        if not match:
            raise ValueError("Invalid Google Sheets URL")
        return match.group(1)
    
    def worksheet(self, title):
        """Return a read-only worksheet"""
        return ReadOnlyWorksheet(self.sheet_id, title)

class ReadOnlyWorksheet:
    """Read-only worksheet that fetches data via CSV export"""
    
    def __init__(self, sheet_id, title):
        self.sheet_id = sheet_id
        self.title = title
        
    def get_all_records(self):
        """Get all records from the worksheet as a list of dictionaries"""
        try:
            # Use the public CSV export URL
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={self.title}"
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()
            
            # Read CSV data into DataFrame
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            # Convert to list of dictionaries (same format as gspread)
            return df.to_dict('records')
            
        except Exception as e:
            print(f"Warning: Could not fetch data from sheet '{self.title}': {e}")
            return []
    
    def get_all_values(self):
        """Get all values from the worksheet as a list of lists"""
        try:
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/gviz/tq?tqx=out:csv&sheet={self.title}"
            response = requests.get(csv_url, timeout=30)
            response.raise_for_status()
            
            # Read CSV and return as list of lists
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            # Include headers and convert to list of lists
            headers = [df.columns.tolist()]
            data = df.values.tolist()
            return headers + data
            
        except Exception as e:
            print(f"Warning: Could not fetch data from sheet '{self.title}': {e}")
            return []


# ===== Inlined from data_updater/find_markets.py: data_updater.find_markets =====
import pandas as pd
import numpy as np
import os
import requests
import time
import random
import warnings
warnings.filterwarnings("ignore")


if not os.path.exists('data'):
    os.makedirs('data')

def get_sel_df(spreadsheet, sheet_name='Selected Markets'):
    try:
        wk2 = spreadsheet.worksheet(sheet_name)
        sel_df = pd.DataFrame(wk2.get_all_records())
        sel_df = sel_df[sel_df['question'] != ""].reset_index(drop=True)
        return sel_df
    except:
        return pd.DataFrame()
    
def get_all_markets(client):
    cursor = ""
    all_markets = []

    while True:
        try:
            markets = client.get_sampling_markets(next_cursor = cursor)
            markets_df = pd.DataFrame(markets['data'])


            cursor = markets['next_cursor']
            


            all_markets.append(markets_df)

            if cursor is None:
                break
        except:
            break

    all_df = pd.concat(all_markets)
    all_df = all_df.reset_index(drop=True)

    return all_df

def get_bid_ask_range(ret, TICK_SIZE):
    bid_from = ret['midpoint'] - ret['max_spread'] / 100
    bid_to = ret['best_ask'] #Although bid to this high up will change bid_from because of changing midpoint, take optimistic approach

    if bid_to == 0:
        bid_to = ret['midpoint']

    if bid_to - TICK_SIZE > ret['midpoint']:
        bid_to = ret['best_bid'] + (TICK_SIZE + 0.1 * TICK_SIZE)

    if bid_from > bid_to:
        bid_from = bid_to - (TICK_SIZE + 0.1 * TICK_SIZE)

    ask_to = ret['midpoint'] + ret['max_spread'] / 100
    ask_from = ret['best_bid']

    if ask_from == 0:
        ask_from = ret['midpoint']

    if ask_from + TICK_SIZE < ret['midpoint']:
        ask_from = ret['best_ask'] - (TICK_SIZE + 0.1 * TICK_SIZE)

    if ask_from > ask_to:
        ask_to = ask_from + (TICK_SIZE + 0.1 * TICK_SIZE)

    bid_from = round(bid_from, 3)
    bid_to = round(bid_to, 3)
    ask_from = round(ask_from, 3)
    ask_to = round(ask_to, 3)

    if bid_from < 0:
        bid_from = 0

    if ask_from < 0:
        ask_from = 0
        
    return bid_from, bid_to, ask_from, ask_to


def generate_numbers(start, end, TICK_SIZE):
    # Calculate the starting point, rounding up to the next hundredth if not an exact multiple of TICK_SIZE
    rounded_start = (int(start * 100) + 1) / 100 if start * 100 % 1 != 0 else start + TICK_SIZE
    
    # Calculate the ending point, rounding down to the nearest hundredth
    rounded_end = int(end * 100) / 100
    
    # Generate numbers from rounded_start to rounded_end, ensuring they fall strictly within the original bounds
    numbers = []
    current = rounded_start
    while current < end:
        numbers.append(current)
        current += TICK_SIZE
        current = round(current, len(str(TICK_SIZE).split('.')[1]))  # Rounding to avoid floating point imprecision

    return numbers

def add_formula_params(curr_df, midpoint, v, daily_reward):
    curr_df['s'] = (curr_df['price'] - midpoint).abs()
    curr_df['S'] = ((v - curr_df['s']) / v) ** 2
    curr_df['100'] = 1/curr_df['price'] * 100

    curr_df['size'] = curr_df['size'] + curr_df['100']

    curr_df['Q'] = curr_df['S'] * curr_df['size']
    curr_df['reward_per_100'] = (curr_df['Q'] / curr_df['Q'].sum()) * daily_reward / 2 / curr_df['size'] * curr_df['100']
    return curr_df

def process_single_row(row, client):
    ret = {}
    ret['question'] = row['question']
    ret['neg_risk'] = row['neg_risk']

    ret['answer1'] = row['tokens'][0]['outcome']
    ret['answer2'] = row['tokens'][1]['outcome']

    ret['min_size'] = row['rewards']['min_size']
    ret['max_spread'] = row['rewards']['max_spread']

    token1 = row['tokens'][0]['token_id']
    token2 = row['tokens'][1]['token_id']

    rate = 0
    for rate_info in row['rewards']['rates']:
        if rate_info['asset_address'].lower() == '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'.lower():
            rate = rate_info['rewards_daily_rate']
            break

    ret['rewards_daily_rate'] = rate
    book = client.get_order_book(token1)
    
    bids = pd.DataFrame()
    asks = pd.DataFrame()

    try:
        bids = pd.DataFrame(book.bids).astype(float)
    except:
        pass

    try:
        asks = pd.DataFrame(book.asks).astype(float)
    except:
        pass


    try:
        ret['best_bid'] = bids.iloc[-1]['price']
    except:
        ret['best_bid'] = 0

    try:
        ret['best_ask'] = asks.iloc[-1]['price']
    except:
        ret['best_ask'] = 0

    ret['midpoint'] = (ret['best_bid'] + ret['best_ask']) / 2
    
    TICK_SIZE = row['minimum_tick_size']
    ret['tick_size'] = TICK_SIZE

    bid_from, bid_to, ask_from, ask_to = get_bid_ask_range(ret, TICK_SIZE)
    v = round((ret['max_spread'] / 100), 2)

    bids_df = pd.DataFrame()
    bids_df['price'] = generate_numbers(bid_from, bid_to, TICK_SIZE)

    asks_df = pd.DataFrame()
    asks_df['price'] = generate_numbers(ask_from, ask_to, TICK_SIZE)

    try:
        bids_df = bids_df.merge(bids, on='price', how='left').fillna(0)
    except:
        bids_df = pd.DataFrame()

    try:
        asks_df = asks_df.merge(asks, on='price', how='left').fillna(0)
    except:
        asks_df = pd.DataFrame()

    best_bid_reward = 0
    ret_bid = pd.DataFrame()

    try:
        ret_bid = add_formula_params(bids_df, ret['midpoint'], v, rate)
        best_bid_reward = round(ret_bid['reward_per_100'].max(), 2)
    except:
        pass

    best_ask_reward = 0
    ret_ask = pd.DataFrame()

    try:
        ret_ask = add_formula_params(asks_df, ret['midpoint'], v, rate)
        best_ask_reward = round(ret_ask['reward_per_100'].max(), 2)
    except:
        pass

    ret['bid_reward_per_100'] = best_bid_reward
    ret['ask_reward_per_100'] = best_ask_reward

    ret['sm_reward_per_100'] = round((best_bid_reward + best_ask_reward) / 2, 2)
    ret['gm_reward_per_100'] = round((best_bid_reward * best_ask_reward) ** 0.5, 2)

    ret['end_date_iso'] = row['end_date_iso']
    ret['market_slug'] = row['market_slug']
    ret['token1'] = token1
    ret['token2'] = token2
    ret['condition_id'] = row['condition_id']

    return ret


def get_all_results(all_df, client, max_workers=5):
    all_results = []

    def process_with_progress(args):
        idx, row = args
        try:
            random_delay = random.uniform(0.1, 0.5)
            time.sleep(random_delay)
            return process_single_row(row, client)
        except Exception as e:
            print(f"error fetching market: {e}")
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_with_progress, (idx, row)) for idx, row in all_df.iterrows()]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                all_results.append(result)

            if len(all_results) % (max_workers * 2) == 0:
                print(f'{len(all_results)} of {len(all_df)}')

    return all_results

def get_combined_markets(new_df, new_markets, sel_df):

    if len(sel_df) > 0:
        old_markets = new_df[new_df['question'].isin(sel_df['question'])]
        all_markets = pd.concat([old_markets, new_markets])
    else:
        all_markets = new_markets

    all_markets = all_markets.drop_duplicates('question')

    all_markets = all_markets.sort_values('gm_reward_per_100', ascending=False)
    return all_markets

import concurrent.futures

def calculate_annualized_volatility(df, hours):
    end_time = df['t'].max()
    start_time = end_time - pd.Timedelta(hours=hours)
    window_df = df[df['t'] >= start_time]
    volatility = window_df['log_return'].std()
    annualized_volatility = volatility * np.sqrt(60 * 24 * 252)
    return round(annualized_volatility, 2)

def add_volatility(row):
    res = requests.get(f'https://clob.polymarket.com/prices-history?interval=1m&market={row["token1"]}&fidelity=10')
    price_df = pd.DataFrame(res.json()['history'])
    price_df['t'] = pd.to_datetime(price_df['t'], unit='s')
    price_df['p'] = price_df['p'].round(2)

    price_df.to_csv(f'data/{row["token1"]}.csv', index=False)
    
    price_df['log_return'] = np.log(price_df['p'] / price_df['p'].shift(1))

    row_dict = row.copy()

    stats = {
        '1_hour': calculate_annualized_volatility(price_df, 1),
        '3_hour': calculate_annualized_volatility(price_df, 3),
        '6_hour': calculate_annualized_volatility(price_df, 6),
        '12_hour': calculate_annualized_volatility(price_df, 12),
        '24_hour': calculate_annualized_volatility(price_df, 24),
        '7_day': calculate_annualized_volatility(price_df, 24 * 7),
        '14_day': calculate_annualized_volatility(price_df, 24 * 14),
        '30_day': calculate_annualized_volatility(price_df, 24 * 30),
        'volatility_price': price_df['p'].iloc[-1]
    }

    new_dict = {**row_dict, **stats}
    return new_dict

def add_volatility_to_df(df, max_workers=2):
    
    results = []
    df = df.reset_index(drop=True)

    def process_volatility_with_progress(args):
        idx, row = args
        try:
            ret = add_volatility(row.to_dict())
            return ret
        except:
            print("Error fetching volatility")
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(process_volatility_with_progress, (idx, row)) for idx, row in df.iterrows()]
        
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            if result is not None:
                results.append(result)
                
            if len(results) % (max_workers * 2) == 0:
                print(f'{len(results)} of {len(df)}')
            
    return pd.DataFrame(results)

    
def get_markets(all_results, sel_df, maker_reward=1):
    new_df = pd.DataFrame(all_results)
    new_df['spread'] = abs(new_df['best_ask'] - new_df['best_bid'])
    new_df = new_df.sort_values('rewards_daily_rate', ascending=False)
    new_df[' '] = ''

    new_df = new_df[['question', 'answer1', 'answer2', 'neg_risk', 'spread', 'best_bid', 'best_ask', 'rewards_daily_rate', 'bid_reward_per_100', 'ask_reward_per_100', 'gm_reward_per_100', 'sm_reward_per_100', 'min_size', 'max_spread', 'tick_size', 'market_slug', 'token1', 'token2', 'condition_id']]
    new_df = new_df.replace([np.inf, -np.inf], 0)
    all_data = new_df.copy()
    s_df = new_df.copy()
    

    making_markets = s_df[~new_df['question'].isin(sel_df['question'])]
    making_markets = making_markets.sort_values('gm_reward_per_100', ascending=False)
    making_markets = making_markets[making_markets['gm_reward_per_100'] >= maker_reward]
    all_markets = get_combined_markets(new_df, making_markets, sel_df)    

    return all_data, all_markets


# ===== Inlined from update_markets.py: update_markets entry point =====
import time
import pandas as pd
from gspread_dataframe import set_with_dataframe
import traceback

# Thresholds
MAX_VOLATILITY = 40

# Initialize global variables
spreadsheet = get_spreadsheet()
client = get_clob_client()

wk_all = spreadsheet.worksheet("All Markets")
wk_vol = spreadsheet.worksheet("Volatility Markets")

sel_df = get_sel_df(spreadsheet, "Selected Markets")

def update_sheet(data, worksheet):
    all_values = worksheet.get_all_values()
    existing_num_rows = len(all_values)
    existing_num_cols = len(all_values[0]) if all_values else 0

    num_rows, num_cols = data.shape
    max_rows = max(num_rows, existing_num_rows)
    max_cols = max(num_cols, existing_num_cols)

    # Create a DataFrame with the maximum size and fill it with empty strings
    padded_data = pd.DataFrame('', index=range(max_rows), columns=range(max_cols))

    # Update the padded DataFrame with the original data and its columns
    padded_data.iloc[:num_rows, :num_cols] = data.values
    padded_data.columns = list(data.columns) + [''] * (max_cols - num_cols)

    # Update the sheet with the padded DataFrame, including column headers
    set_with_dataframe(worksheet, padded_data, include_index=False, include_column_header=True, resize=True)

def sort_df(df):
    # Calculate the mean and standard deviation for each column
    mean_gm = df['gm_reward_per_100'].mean()
    std_gm = df['gm_reward_per_100'].std()
    
    mean_volatility = df['volatility_sum'].mean()
    std_volatility = df['volatility_sum'].std()
    
    # Standardize the columns
    df['std_gm_reward_per_100'] = (df['gm_reward_per_100'] - mean_gm) / std_gm
    df['std_volatility_sum'] = (df['volatility_sum'] - mean_volatility) / std_volatility
    
    # Define a custom scoring function for best_bid and best_ask
    def proximity_score(value):
        if 0.1 <= value <= 0.25:
            return (0.25 - value) / 0.15
        elif 0.75 <= value <= 0.9:
            return (value - 0.75) / 0.15
        else:
            return 0
    
    df['bid_score'] = df['best_bid'].apply(proximity_score)
    df['ask_score'] = df['best_ask'].apply(proximity_score)
    
    # Create a composite score (higher is better for rewards, lower is better for volatility, with proximity scores)
    df['composite_score'] = (
        df['std_gm_reward_per_100'] - 
        df['std_volatility_sum'] + 
        df['bid_score'] + 
        df['ask_score']
    )
    
    # Sort by the composite score in descending order
    sorted_df = df.sort_values(by='composite_score', ascending=False)
    
    # Drop the intermediate columns used for calculation
    sorted_df = sorted_df.drop(columns=['std_gm_reward_per_100', 'std_volatility_sum', 'bid_score', 'ask_score', 'composite_score'])
    
    return sorted_df

def fetch_and_process_data():
    global spreadsheet, client, wk_all, wk_vol, sel_df
    
    spreadsheet = get_spreadsheet()
    client = get_clob_client()

    wk_all = spreadsheet.worksheet("All Markets")
    wk_vol = spreadsheet.worksheet("Volatility Markets")
    wk_full = spreadsheet.worksheet("Full Markets")

    sel_df = get_sel_df(spreadsheet, "Selected Markets")


    all_df = get_all_markets(client)
    print("Got all Markets")
    all_results = get_all_results(all_df, client)
    print("Got all Results")
    m_data, all_markets = get_markets(all_results, sel_df, maker_reward=0.75)
    print("Got all orderbook")

    print(f'{pd.to_datetime("now")}: Fetched all markets data of length {len(all_markets)}.')
    new_df = add_volatility_to_df(all_markets)
    new_df['volatility_sum'] =  new_df['24_hour'] + new_df['7_day'] + new_df['14_day']
    
    new_df = new_df.sort_values('volatility_sum', ascending=True)
    new_df['volatilty/reward'] = ((new_df['gm_reward_per_100'] / new_df['volatility_sum']).round(2)).astype(str)

    new_df = new_df[['question', 'answer1', 'answer2', 'spread', 'rewards_daily_rate', 'gm_reward_per_100', 'sm_reward_per_100', 'bid_reward_per_100', 'ask_reward_per_100',  'volatility_sum', 'volatilty/reward', 'min_size', '1_hour', '3_hour', '6_hour', '12_hour', '24_hour', '7_day', '30_day',  
                     'best_bid', 'best_ask', 'volatility_price', 'max_spread', 'tick_size',  
                     'neg_risk',  'market_slug', 'token1', 'token2', 'condition_id']]

    
    volatility_df = new_df.copy()
    volatility_df = volatility_df[new_df['volatility_sum'] < MAX_VOLATILITY]
    # volatility_df = sort_df(volatility_df)
    volatility_df = volatility_df.sort_values('gm_reward_per_100', ascending=False)
   
    new_df = new_df.sort_values('gm_reward_per_100', ascending=False)
    

    print(f'{pd.to_datetime("now")}: Fetched select market of length {len(new_df)}.')

    if len(new_df) > 50:
        update_sheet(new_df, wk_all)
        update_sheet(volatility_df, wk_vol)
        update_sheet(m_data, wk_full)
    else:
        print(f'{pd.to_datetime("now")}: Not updating sheet because of length {len(new_df)}.')

if __name__ == "__main__":
    while True:
        try:
            fetch_and_process_data()
            time.sleep(60 * 60)  # Sleep for an hour
        except Exception as e:
            traceback.print_exc()
            print(str(e))
