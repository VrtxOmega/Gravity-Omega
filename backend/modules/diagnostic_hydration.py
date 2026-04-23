import os
import psycopg2
from web3 import Web3
from decimal import Decimal
import logging
from pathlib import Path

# Load credentials from .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# CONFIG
RPC_URL = "https://mainnet.base.org" 
DB_PARAMS = (
    f"dbname={os.environ.get('LIQUIDATION_DB_NAME', 'liquidation_engine')} "
    f"user={os.environ.get('LIQUIDATION_DB_USER', 'sovereign')} "
    f"password={os.environ.get('LIQUIDATION_DB_PASSWORD', '')} "
    f"host={os.environ.get('LIQUIDATION_DB_HOST', 'localhost')}"
)
AAVE_POOL = "0xA238Dd80C259a72E81d7e4674A947812f444952c"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DIAGNOSTIC")

def run():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    curr = w3.eth.block_number
    logger.info(f"Current Block: {curr}")
    
    # 1. Find a candidate
    # 1. Find a candidate
    # 1. Find a candidate
    logger.info("Scanning recent 2000 blocks for ANY logs...")
    
    # Check Aave
    logs_aave = w3.eth.get_logs({
        "fromBlock": hex(curr - 2000),
        "toBlock": "latest",
        "address": Web3.to_checksum_address(AAVE_POOL)
    })
    
    target_log = None
    protocol = "AaveV3"
    
    if logs_aave:
        logger.info(f"Found {len(logs_aave)} Aave logs.")
        for l in logs_aave:
            if len(l['topics']) > 2:
                target_log = l
                break
    
    if not target_log:
        # Check Morpho
        MORPHO = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
        logs_morpho = w3.eth.get_logs({
            "fromBlock": hex(curr - 2000),
            "toBlock": "latest",
            "address": Web3.to_checksum_address(MORPHO)
        })
        if logs_morpho:
            logger.info(f"Found {len(logs_morpho)} Morpho logs.")
            for l in logs_morpho:
                if len(l['topics']) > 3:
                    target_log = l
                    protocol = "Morpho"
                    break

    if not target_log:
        logger.error("No logs found for Aave or Morpho in recent blocks.")
        return

    if protocol == "AaveV3":
        user = Web3.to_checksum_address("0x" + target_log['topics'][2].hex()[-40:])
    else:
        user = Web3.to_checksum_address("0x" + target_log['topics'][3].hex()[-40:])
        
    logger.info(f"Targeting User: {user} ({protocol})")
    logger.info(f"Targeting User: {user} ({protocol})")
    
    # 2. Hydrate
    def failsafe_call(func, *args, **kwargs):
        retries = 0
        while retries < 8:
            try:
                return func(*args, **kwargs).call()
            except Exception as e:
                if "429" in str(e) or "Too Many Requests" in str(e):
                    import time
                    sleep_time = (1.5 ** retries) + 1
                    logger.warning(f"RPC 429 Rate Limit. Backoff {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    retries += 1
                else:
                    raise e
        raise Exception("Max RPC retries exceeded")

    try:
        if protocol == "AaveV3":
            abi = [{"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getUserAccountData","outputs":[{"internalType":"uint256","name":"totalCollateralBase","type":"uint256"},{"internalType":"uint256","name":"totalDebtBase","type":"uint256"},{"internalType":"uint256","name":"availableBorrowsBase","type":"uint256"},{"internalType":"uint256","name":"currentLiquidationThreshold","type":"uint256"},{"internalType":"uint256","name":"ltv","type":"uint256"},{"internalType":"uint256","name":"healthFactor","type":"uint256"}],"stateMutability":"view","type":"function"}]
            pool = w3.eth.contract(address=Web3.to_checksum_address(AAVE_POOL), abi=abi)
            data = failsafe_call(pool.functions.getUserAccountData, user)
            logger.info(f"Aave Data: {data}")
            
            debt_usd = Decimal(data[1]) / Decimal(10**8)
            collat_usd = Decimal(data[0]) / Decimal(10**8)
            hf = float(data[5]) / 1e18
            market_id = "global"

        else: # Morpho
            market_id = target_log['topics'][1].hex()
            abi = [{"inputs":[{"internalType":"bytes32","name":"id","type":"bytes32"},{"internalType":"address","name":"user","type":"address"}],"name":"position","outputs":[{"internalType":"uint256","name":"supplyShares","type":"uint256"},{"internalType":"uint256","name":"borrowShares","type":"uint256"},{"internalType":"uint128","name":"collateral","type":"uint128"},{"internalType":"uint128","name":"borrowAmount","type":"uint128"}],"stateMutability":"view","type":"function"}]
            morpho_addr = "0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb"
            morpho = w3.eth.contract(address=Web3.to_checksum_address(morpho_addr), abi=abi)
            
            mid_bytes = Web3.to_bytes(hexstr=market_id)
            logger.info(f"Morpho Call: Market={market_id}, User={user}")
            data = failsafe_call(morpho.functions.position, mid_bytes, user)
            logger.info(f"Morpho Data: {data}")
            
            # Morpho data: supplyShares(0), borrowShares(1), collateral(2), borrowAmount(3)
            borrow_shares = data[1]
            collateral = data[2]
            debt_usd = Decimal(borrow_shares) / Decimal(10**18) if borrow_shares > 0 else Decimal(0)
            collat_usd = Decimal(collateral) / Decimal(10**18)
            hf = 1.1 if borrow_shares > 0 else 100.0

        logger.info(f"Parsed: Debt=${debt_usd}, Collat=${collat_usd}, HF={hf}")
        
        if debt_usd > 0 or collat_usd > 0:
            logger.info("Condition met: Active User.")
            # 3. DB Upsert
            conn = psycopg2.connect(DB_PARAMS)
            conn.autocommit = True
            with conn.cursor() as cur:
                addr_low = str(user).lower()
                market_low = str(market_id).lower()
                logger.info(f"Upserting: {addr_low} / {market_low}")
                
                cur.execute("""
                    INSERT INTO borrower_state (address, market_id, protocol, hf_current, hf_prev, hf_delta, debt_usd, collateral_usd, last_update_block)
                    VALUES (%s, %s, %s, %s, %s, 0.0, %s, %s, 0)
                    ON CONFLICT (address, market_id) DO UPDATE SET
                        hf_current = EXCLUDED.hf_current, debt_usd = EXCLUDED.debt_usd, collateral_usd = EXCLUDED.collateral_usd, updated_at = NOW()
                    RETURNING address;
                """, (addr_low, market_low, protocol, hf, hf, debt_usd, collat_usd))
                res = cur.fetchone()
                logger.info(f"DB Result: {res}")
            conn.close()
        else:
            logger.warning("User has no debt/collat (Ghost event?)")
            
    except Exception as e:
        logger.error(f"Hydration Failed: {e}")

if __name__ == "__main__":
    run()
