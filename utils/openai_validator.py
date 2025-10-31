# utils/openai_validator.py

import os
import numpy as np
from openai import OpenAI

def calculate_similarity(expected: str, actual: str) -> float:
    if not expected or not actual:
        print("⚠️ Empty input for similarity check")
        return 0.0

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = "text-embedding-3-small"

    try:
        emb_expected = client.embeddings.create(model=model, input=expected).data[0].embedding
        emb_actual = client.embeddings.create(model=model, input=actual).data[0].embedding

        similarity = np.dot(emb_expected, emb_actual) / (
            np.linalg.norm(emb_expected) * np.linalg.norm(emb_actual)
        )

        print(f"🔍 Similarity Score: {similarity:.3f}")
        return round(float(similarity), 3)

    except Exception as e:
        print(f"❌ Error generating embeddings: {e}")
        return 0.0
