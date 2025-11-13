# app/core/context_builder.py

def build_context(chunks, max_length=700):
    """
    여러 chunk의 'content'를 조합하여 context 문자열 생성
    """
    merged_text = "\n\n".join(row.content for row in chunks)

    # 너무 길면 자르기
    return merged_text[:max_length]
