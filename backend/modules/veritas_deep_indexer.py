#!/usr/bin/env python3
"""
VERITAS_DEEP_INDEXER V3.3 - Production Whale Vacuum
High-velocity borrower scan with USD valuation and optimized hydration.
"""

import os
import psycopg2
from pathlib import Path
from web3 import Web3
import time
import logging
from decimal import Decimal

# Load credentials from .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

# TARGETS: AAVE V3 & MORPHO BLUE (Base L2)
RPC_URL = "https://mainnet.base.org" 
DB_PARAMS = (
    f"dbname={os.environ.get('LIQUIDATION_DB_NAME', 'liquidation_engine')} "
    f"user={os.environ.get('LIQUIDATION_DB_USER', 'sovereign')} "
    f"password={os.environ.get('LIQUIDATION_DB_PASSWORD', '')} "
    f"host={os.environ.get('LIQUIDATION_DB_HOST', 'localhost')}"
)
w3 = Web3(Web3.HTTPProvider(RPC_URL))

PROTOCOLS = {
    "AAVE_V3": Web3.to_checksum_address("0xA238Dd80C259a72E81d7e4674A947812f444952c"),
    "MORPHO": Web3.to_checksum_address("0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb")
}

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [DEEP_INDEXER] %(message)s',
    handlers=[
        logging.FileHandler('deep_indexer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DEEP_INDEXER")

class DeepIndexer:
    def __init__(self):
        self.w3 = w3
        self.conn = None
        self.aave_pool = self._load_aave_pool()
        self.morpho_contract = self._load_morpho()
        
    def _load_aave_pool(self):
        abi = [{"inputs":[{"internalType":"address","name":"user","type":"address"}],"name":"getUserAccountData","outputs":[{"internalType":"uint256","name":"totalCollateralBase","type":"uint256"},{"internalType":"uint256","name":"totalDebtBase","type":"uint256"},{"internalType":"uint256","name":"availableBorrowsBase","type":"uint256"},{"internalType":"uint256","name":"currentLiquidationThreshold","type":"uint256"},{"internalType":"uint256","name":"ltv","type":"uint256"},{"internalType":"uint256","name":"healthFactor","type":"uint256"}],"stateMutability":"view","type":"function"}]
        return self.w3.eth.contract(address=PROTOCOLS["AAVE_V3"], abi=abi)

    def _load_morpho(self):
        abi = [{"inputs":[{"internalType":"bytes32","name":"id","type":"bytes32"},{"internalType":"address","name":"user","type":"address"}],"name":"position","outputs":[{"internalType":"uint256","name":"supplyShares","type":"uint256"},{"internalType":"uint256","name":"borrowShares","type":"uint256"},{"internalType":"uint128","name":"collateral","type":"uint128"},{"internalType":"uint128","name":"borrowAmount","type":"uint128"}],"stateMutability":"view","type":"function"}]
        return self.w3.eth.contract(address=PROTOCOLS["MORPHO"], abi=abi)

    def connect_db(self):
        try:
            self.conn = psycopg2.connect(DB_PARAMS)
            self.conn.autocommit = True
            logger.info("Connected to TimescaleDB")
        except Exception as e:
            logger.error(f"DB Connection failed: {e}")

    def scrape_blocks(self, start_block, end_block, step=2000):
        logger.info(f"Scanning range {start_block} to {end_block}...")
        
        aave_supply = "0x" + self.w3.keccak(text="Supply(address,address,address,uint256,uint16)").hex()
        aave_borrow = "0x" + self.w3.keccak(text="Borrow(address,address,address,uint256,uint256,uint256,uint16)").hex()
        morpho_supply = "0x" + self.w3.keccak(text="Supply(bytes32,address,address,uint256,uint256)").hex()
        
        candidates = [] 
        
        for block in range(start_block, end_block, step):
            to_block = min(block + step, end_block)
            f_hex, t_hex = hex(block), hex(to_block)
            
            # 1. Aave Scan
            try:
                logs = self.w3.eth.get_logs({"fromBlock": f_hex, "toBlock": t_hex, "address": PROTOCOLS["AAVE_V3"], "topics": [[aave_supply, aave_borrow]]})
                for log in logs:
                    if len(log['topics']) > 2:
                        user = "0x" + log['topics'][2].hex()[-40:]
                        candidates.append(("AaveV3", Web3.to_checksum_address(user), "GLOBAL"))
            except Exception as e:
                logger.debug(f"Aave scan block {block} failed: {e}")

            # 2. Morpho Scan
            try:
                logs = self.w3.eth.get_logs({"fromBlock": f_hex, "toBlock": t_hex, "address": PROTOCOLS["MORPHO"], "topics": [morpho_supply]})
                for log in logs:
                    if len(log['topics']) > 3:
                        market_id = log['topics'][1].hex()
                        user = "0x" + log['topics'][3].hex()[-40:]
                        candidates.append(("MorphoBlue", Web3.to_checksum_address(user), market_id))
            except Exception as e:
                logger.debug(f"Morpho scan block {block} failed: {e}")

            if len(candidates) >= 100:
                self.hydrate_batch(candidates)
                candidates = []
            
            time.sleep(0.01) # High velocity
            
        if candidates:
            self.hydrate_batch(candidates)

    def hydrate_batch(self, candidates):
        logger.info(f"Hydrating {len(candidates)} candidates...")
        successful = 0
        for proto, user, market in candidates:
            try:
                if proto == "AaveV3":
                    data = self.aave_pool.functions.getUserAccountData(user).call()
                    # Aave V3 Base is USD 8 decimals
                    debt_usd = Decimal(data[1]) / Decimal(10**8)
                    collat_usd = Decimal(data[0]) / Decimal(10**8)
                    hf = data[5] / 1e18
                else: # Morpho
                    market_bytes = Web3.to_bytes(hexstr=market)
                    data = self.morpho_contract.functions.position(market_bytes, user).call()
                    # Morpho values depend on asset decimals, simplified for MVP
                    debt_usd = Decimal(data[3]) / Decimal(10**18) 
                    collat_usd = Decimal(data[2]) / Decimal(10**18)
                    hf = 1.1 if data[3] > 0 else 100.0
                
                if debt_usd == 0 and collat_usd == 0: continue
                
                self._upsert(user, market, proto, hf, debt_usd, collat_usd, data[1] if proto == "AaveV3" else data[3])
                successful += 1
            except Exception as e:
                logger.debug(f"Hydration fail for {user}: {e}")
        logger.info(f"Successfully processed {successful} whales into database.")

    def _upsert(self, address, market, proto, hf, debt_usd, collat_usd, debt_raw):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO borrower_state (address, market_id, protocol, hf_current, hf_prev, hf_delta, debt_raw, debt_usd, collateral_raw, collateral_usd, last_update_block)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (address, market_id) DO UPDATE SET
                    hf_current = EXCLUDED.hf_current, debt_raw = EXCLUDED.debt_raw, debt_usd = EXCLUDED.debt_usd,
                    collateral_usd = EXCLUDED.collateral_usd, updated_at = NOW()
            """, (address, market, proto, hf, hf, 0.0, debt_raw, debt_usd, 0, collat_usd, self.w3.eth.block_number))

    def run(self):
        logger.info("="*60)
        logger.info("VACUUM V3.3 - INITIALIZED")
        logger.info("="*60)
        self.connect_db()
        while True:
            try:
                curr = self.w3.eth.block_number
                # 500k blocks scan (~11 days historical)
                self.scrape_blocks(curr - 500000, curr, step=5000)
                logger.info("Deep Cycle Complete. Dormant for 4 hours.")
                time.sleep(14400)
            except Exception as e:
                logger.error(f"Global error: {e}")
                time.sleep(60)

if __name__ == "__main__":
    DeepIndexer().run()
