import psycopg2
import logging
import os
from pathlib import Path

# Load credentials from .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("VERIFY")

DB_PARAMS = (
    f"dbname={os.environ.get('LIQUIDATION_DB_NAME', 'liquidation_engine')} "
    f"user={os.environ.get('LIQUIDATION_DB_USER', 'sovereign')} "
    f"password={os.environ.get('LIQUIDATION_DB_PASSWORD', '')} "
    f"host={os.environ.get('LIQUIDATION_DB_HOST', 'localhost')}"
)

def verify():
    try:
        conn = psycopg2.connect(DB_PARAMS)
        cur = conn.cursor()
        
        cur.execute("SELECT count(*) FROM borrower_state")
        count = cur.fetchone()[0]
        logger.info(f"DB COUNT: {count}")
        
        cur.execute("SELECT value FROM system_status WHERE key = 'predicted_eth_price'")
        row = cur.fetchone()
        price = row[0] if row else "N/A"
        logger.info(f"PRICE: {price}")
        
        if count > 0:
            cur.execute("SELECT address, hf_current, debt_usd, protocol FROM borrower_state WHERE debt_usd > 0 ORDER BY hf_current ASC LIMIT 3")
            rows = cur.fetchall()
            logger.info("TOP CANDIDATES:")
            for r in rows:
                logger.info(f" - {r[0]}: HF={r[1]}, Debt=${r[2]}, Protocol={r[3]}")
                
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Verification failed: {e}")

if __name__ == "__main__":
    verify()
