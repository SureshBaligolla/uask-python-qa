# utils/openai_validator.py
import os
import time
import json
from typing import List, Dict
import numpy as np
from openai import OpenAI


CACHE_PATH = os.environ.get("EMBEDDING_CACHE", "reports/embeddings_cache.json")
EMBED_MODEL = "text-embedding-3-small"
MAX_BATCH = 64
RETRY_ATTEMPTS = 4
RETRY_BACKOFF = 1.5

# use a different name for the cached client instance
_client_instance = None

def _get_client():
    """Return a singleton OpenAI client instance."""
    global _client_instance
    if _client_instance is None:
        _client_instance = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client_instance

def _load_cache() -> Dict[str, List[float]]:
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}

def _save_cache(cache: Dict[str, List[float]]):
    os.makedirs(os.path.dirname(CACHE_PATH) or ".", exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as fh:
        json.dump(cache, fh, ensure_ascii=False, indent=2)

def _safe_embed_call(texts: List[str]):
    client = _get_client()
    for attempt in range(RETRY_ATTEMPTS):
        try:
            resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
            return [r.embedding for r in resp.data]
        except Exception as e:
            last = attempt == (RETRY_ATTEMPTS - 1)
            wait = (RETRY_BACKOFF ** attempt)
            if last:
                raise
            time.sleep(wait)

def embed_texts(texts: List[str]) -> Dict[str, List[float]]:
    texts = [t.strip() for t in texts]
    cache = _load_cache()
    to_request = [t for t in texts if t and t not in cache]

    if to_request:
        for i in range(0, len(to_request), MAX_BATCH):
            batch = to_request[i : i + MAX_BATCH]
            embeddings = _safe_embed_call(batch)
            for t, emb in zip(batch, embeddings):
                cache[t] = emb
        _save_cache(cache)

    return {t: cache[t] for t in texts if t in cache}

def _to_np(vec):
    arr = np.array(vec, dtype=float)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr
    return arr / norm

def cosine_similarity_from_vecs(a: List[float], b: List[float]) -> float:
    a_n = _to_np(a)
    b_n = _to_np(b)
    if a_n.size == 0 or b_n.size == 0:
        return 0.0
    sim = float(np.dot(a_n, b_n))
    return max(-1.0, min(1.0, sim))

def calculate_similarity(expected: str, actual: str) -> float:
    if not expected or not actual:
        return 0.0
    mapping = embed_texts([expected, actual])
    emb_e = mapping.get(expected.strip())
    emb_a = mapping.get(actual.strip())
    if not emb_e or not emb_a:
        return 0.0
    sim = cosine_similarity_from_vecs(emb_e, emb_a)
    sim_rounded = round(float(sim), 3)
    return sim_rounded

def check_hallucination(response: str, ground_truth_texts: List[str], threshold: float = 0.75):
    if not response or not ground_truth_texts:
        return 0.0, None, True
    texts = ground_truth_texts + [response]
    mapping = embed_texts(texts)
    response_emb = mapping.get(response.strip())
    best_score = -1.0
    best_src = None
    for src in ground_truth_texts:
        src_emb = mapping.get(src.strip())
        if not src_emb:
            continue
        score = cosine_similarity_from_vecs(src_emb, response_emb)
        if score > best_score:
            best_score = score
            best_src = src
    is_flagged = best_score < threshold
    return round(float(best_score), 3), best_src, is_flagged
