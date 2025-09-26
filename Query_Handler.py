from typing import List
from Data_Handler import embed_query

def query_to_vector(query: str) -> List[float]:
    return embed_query(query)
