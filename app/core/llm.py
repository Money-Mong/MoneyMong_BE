# app/utils/llm.py

import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage
from openai import OpenAI


load_dotenv()


UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")

# LangChain Upstage Chat LLM
llm = ChatUpstage(
    api_key=UPSTAGE_API_KEY,
    model="solar-pro2",  # 무료, 한국어 성능 매우 강함
    temperature=0.2,
    max_tokens=512,
)

# 시스템 + 사용자 Prompt 템플릿
RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "너는 한국어 금융 리포트 분석 및 요약에 특화된 RAG AI 어시스턴트야. "
            "주어진 컨텍스트 내에서만 답변하고, 없는 정보는 지어내지 마.",
        ),
        ("user", "[Context]\n{context}\n\n[Question]\n{question}"),
    ]
)


def generate_answer(question: str, context: str) -> str:
    """LangChain 체인 방식으로 답변 생성"""

    chain = RAG_PROMPT | llm  # Prompt → LLM 연결

    result = chain.invoke(
        {
            "context": context,
            "question": question,
        }
    )

    return result.content.strip()


CONVERSATION_RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "너는 한국어 금융 리포트 분석 및 요약에 특화된 RAG AI 어시스턴트야. "
            "주어진 컨텍스트와 대화 히스토리를 참고하여 답변하고, 없는 정보는 지어내지 마.",
        ),
        (
            "user",
            "[대화 히스토리]\n{history}\n\n[Context]\n{context}\n\n[현재 질문]\n{question}",
        ),
    ]
)


def generate_conversation_answer(
    question: str, context: str, history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    대화 히스토리를 포함한 답변 생성

    Args:
        question: 현재 질문
        context: RAG 검색 컨텍스트
        history: 이전 대화 히스토리 [{"role": "user/assistant", "content":"..."}]

    Returns:
        {
            "answer": str,
            "model": str,
            "token_usage": Dict
        }
    """

    # 대화 히스토리 포멧팅
    history_text = ""

    if history:
        for msg in history[-5:]:  # 최근 5개만
            role_name = "사용자" if msg["role"] == "user" else "어시스턴트"
            history_text += f"{role_name}: {msg['content']}\n"

    # TODO 프롬프트 교체
    chain = CONVERSATION_RAG_PROMPT | llm

    result = chain.invoke(
        {
            "history": history_text,
            "context": context,
            "question": question,
        }
    )

    # 토큰 사용량 추출 (LangChain response_metadata에서)
    token_usage = {}
    if hasattr(result, "response_metadata"):
        metadata = result.response_metadata
        token_usage = {
            "prompt": metadata.get("prompt_tokens", 0),
            "completion": metadata.get("completion_tokens", 0),
            "total": metadata.get("total_tokens", 0),
        }

    return {
        "answer": result.content.strip(),
        "model": "solar-pro2",
        "token_usage": token_usage,
    }


def generate_follow_up_questions(
    question: str, answer: str, context: str, num_questions: int = 3
) -> List[str]:
    """
    후속 질문 3개 생성
    """
    # TODO 프롬프트 교체
    FOLLOWUP_PROMPT = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "너는 사용자의 이해를 돕기 위한 후속 질문을 생성하는 AI야. "
                "답변 내용을 기반으로 자연스럽게 이어질 수 있는 질문 3개를 생성해.",
            ),
            (
                "user",
                "[질문]\n{question}\n\n[답변]\n{answer}\n\n[컨텍스트]\n{context}\n\n"
                "위 내용을 바탕으로 사용자가 궁금해할 만한 후속 질문 3개를 생성해줘. "
                "각 질문은 한 줄로, 번호 없이 작성해.",
            ),
        ]
    )

    chain = FOLLOWUP_PROMPT | llm
    result = chain.invoke(
        {
            "question": question,
            "answer": answer,
            "context": context[:300],  # 컨텍스트 일부만
        }
    )

    # 응답을 줄바꿈으로 분리하여 3개 추출
    questions = [q.strip() for q in result.content.strip().split("\n") if q.strip()]
    return questions[:num_questions]


"""
OpenAI구조
"""
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# CHAT_MODEL = "gpt-4o-mini"  # 요약/QA용

# def generate_answer_from_context(question: str, context: str) -> str:
#     """
#     context + question을 기반으로 LLM 답변 생성
#     """
#     system_prompt = (
#         "너는 한국어를 사용하는 금융 리포트 요약/질의응답 어시스턴트야. "
#         "항상 사용자의 질문에 대해, 주어진 컨텍스트를 최대한 활용해서 답변해. "
#         "컨텍스트에 없는 정보는 지어내지 말고, 모른다고 말해."
#     )

#     messages = [
#         {"role": "system", "content": system_prompt},
#         {
#             "role": "user",
#             "content": f"[Context]\n{context}\n\n[Question]\n{question}",
#         },
#     ]

#     resp = client.chat.completions.create(
#         model=CHAT_MODEL,
#         messages=messages,
#     )
#     return resp.choices[0].message.content.strip()


"""
GPU에서 Qwen3vl
"""
# from transformers import AutoProcessor, AutoModelForVision2Seq

# processor = AutoProcessor.from_pretrained("Qwen/Qwen3-VL-2B-Instruct")
# model = AutoModelForVision2Seq.from_pretrained("Qwen/Qwen3-VL-2B-Instruct").to("cuda")

# def generate_answer(question: str, context: str) -> str:
#     prompt = f"[Context]\n{context}\n\n[Question]\n{question}"
#     messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]

#     inputs = processor.apply_chat_template(
#         messages,
#         add_generation_prompt=True,
#         tokenize=True,
#         return_dict=True,
#         return_tensors="pt",
#     ).to(model.device)

#     outputs = model.generate(**inputs, max_new_tokens=256)
#     answer = processor.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)
#     return answer.strip()
