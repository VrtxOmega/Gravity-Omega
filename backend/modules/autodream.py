import sqlite3
import json
import struct
import numpy as np
import os
import logging

log = logging.getLogger('autodream')

def run_autodream():
    """
    autoDream Idle Consolidation
    - Scans provenance CAS for duplicate embeddings (cosine > 0.95) -> merge
    - Promotes TIER_C fragments with high retrieval counts to TIER_B
    """
    log.info("[autodream] Starting idle consolidation pass.")
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'provenance_cas', 'embedding_index.db')
    
    if not os.path.exists(db_path):
        log.warning("[autodream] No embedding_index.db found. Skipping.")
        return

    try:
        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        cursor = db.cursor()

        # 1. Promote heavily retrieved TIER_C fragments
        cursor.execute("UPDATE embeddings SET tier = 'B' WHERE tier = 'C' AND retrieval_count >= 5")
        promoted = cursor.rowcount
        if promoted > 0:
            log.info(f"[autodream] Promoted {promoted} TIER_C fragments to TIER_B.")

        # 2. Merge duplicate embeddings (cosine > 0.95)
        cursor.execute("SELECT content_hash, embedding, retrieval_count FROM embeddings")
        rows = cursor.fetchall()
        
        hash_list = []
        embed_list = []
        
        for row in rows:
            b = row['embedding']
            if not b: continue
            try:
                vec_len = len(b) // 4
                vec = struct.unpack(f"{vec_len}f", b)
                embed_list.append(np.array(vec, dtype=np.float32))
                hash_list.append(row['content_hash'])
            except Exception:
                pass
                
        if embed_list:
            vectors = np.stack(embed_list)
            # Normalize for cosine similarity
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1
            vectors_norm = vectors / norms
            
            sim_matrix = np.dot(vectors_norm, vectors_norm.T)
            
            # Upper triangle without diagonal to find pairs
            triu = np.triu(sim_matrix, k=1)
            duplicates = np.where(triu > 0.95)
            
            to_delete = set()
            to_merge_counts = {}
            
            for i, j in zip(*duplicates):
                if i in to_delete or j in to_delete:
                    continue
                # Keep i, delete j
                delete_hash = hash_list[j]
                to_delete.add(delete_hash)
                
                count_j = rows[j]['retrieval_count']
                if count_j > 0:
                    keep_hash = hash_list[i]
                    to_merge_counts[keep_hash] = to_merge_counts.get(keep_hash, 0) + count_j

            if to_delete:
                del_hashes = list(to_delete)
                placeholders = ','.join(['?'] * len(del_hashes))
                cursor.execute(f"DELETE FROM embeddings WHERE content_hash IN ({placeholders})", del_hashes)
                log.info(f"[autodream] Merged {len(del_hashes)} duplicate/highly-similar fragments.")
                
            for h_id, extra_count in to_merge_counts.items():
                cursor.execute("UPDATE embeddings SET retrieval_count = retrieval_count + ? WHERE content_hash = ?", (extra_count, h_id))

        db.commit()
    except Exception as e:
        log.error(f"[autodream] Error during consolidation: {e}")
    finally:
        if 'db' in locals():
            db.close()
    
    log.info("[autodream] Idle consolidation complete.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run_autodream()
