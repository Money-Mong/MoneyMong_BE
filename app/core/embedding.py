# app/utils/embedding.py
# app/utils/embedding.py

from langchain_community.embeddings import HuggingFaceEmbeddings

# HuggingFace embedding model (Ko/En/Ja 용)
embedding_model = HuggingFaceEmbeddings(
    model_name="sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja",
    model_kwargs={"device": "cpu"},  # CPU 사용, GPU 있으면 "cuda"
    encode_kwargs={"normalize_embeddings": True},
)

def get_query_embedding(text: str):
    """
    사용자 질문을 임베딩 벡터(list[float])로 변환.
    """
    return embedding_model.embed_query(text)


# import os
# from openai import OpenAI

# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# EMBEDDING_MODEL = "text-embedding-3-small"  # pdf-parser에서 사용한 모델과 동일하게

# def get_query_embedding(text: str):
#     """
#     사용자 질문을 임베딩 벡터(list[float])로 변환.
#     """
#     response = client.embeddings.create(
#         model=EMBEDDING_MODEL,
#         input=text,
#     )
#     return response.data[0].embedding
