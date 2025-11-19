# app/core/llm.py

import os
import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage
from openai import OpenAI

from app.core.prompts import (
    UserLevel,
    get_document_rag_context_response_prompt,
    get_followup_questions_prompt,
    get_general_context_conversation_prompt,
    get_general_conversation_prompt,
)


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
            "너는 한국어 금융 리포트 분석 및 요약에 특화된 AI 어시스턴트야. "
            "컨텍스트가 제공되면 그 안에서만 답변하고, 없는 정보는 지어내지 마. "
            "컨텍스트가 없으면 일반적인 금융/경제 지식으로 친절하게 답변해.",
        ),
        (
            "user",
            "[대화 히스토리]\n{history}\n\n[Context]\n{context}\n\n[현재 질문]\n{question}",
        ),
    ]
)

# ===================================
# 대화형 RAG 응답 생성
# ===================================


def generate_conversation_answer(
    question: str,
    context: str,
    document_id: Optional[UUID] = None,
    history: Optional[List[Dict]] = None,
    user_level: UserLevel = UserLevel.INTERMEDIATE,
) -> Dict[str, Any]:
    """
    대화 히스토리를 포함한 답변 생성

    Args:
        question: 현재 질문
        context: RAG 검색 컨텍스트 (빈 문자열이면 일반 대화)
        history: 이전 대화 히스토리 [{"role": "user/assistant", "content":"..."}]
        user_level: 사용자 금융 지식 레벨 (기본: beginner)

    Returns:
        {
            "answer": str,
            "model": str,
            "token_usage": Dict
        }
    """

    # 1. 대화 히스토리 포맷팅
    history_text = ""
    if history:
        for msg in history[-5:]:  # 최근 5개만
            role_name = "사용자" if msg["role"] == "user" else "어시스턴트"
            history_text += f"{role_name}: {msg['content']}\n"

    # 2. document_id 유무에 따라 프롬프트 선택
    if document_id:
        retrieved_context = (
            f"[대화 히스토리]\n{history_text}\n\n[검색된 문서 정보]\n{context}"
        )

        prompt_text = get_document_rag_context_response_prompt(
            user_level=user_level,
            retrieved_context=retrieved_context,
            user_question=question,
        )
    else:
        # 2-1. 컨텍스트 유무에 따라 프롬프트 선택
        if context and context.strip():
            # RAG 모드: 컨텍스트 기반 답변
            # 히스토리와 검색 컨텍스트 결합
            retrieved_context = (
                f"[대화 히스토리]\n{history_text}\n\n[검색된 문서 정보]\n{context}"
            )

            prompt_text = get_general_context_conversation_prompt(
                user_level=user_level,
                retrieved_context=retrieved_context,
                user_question=question,
            )
        else:
            # 일반 대화 모드: 금융 지식 기반 답변
            # 히스토리만 컨텍스트로 사용 (필요시)
            if history_text:
                full_question = (
                    f"[이전 대화]\n{history_text}\n\n[현재 질문]\n{question}"
                )
            else:
                full_question = question

            prompt_text = get_general_conversation_prompt(
                user_level=user_level,
                user_question=full_question,
            )

    # 3. LLM 호출
    result = llm.invoke(prompt_text)

    # 4. 토큰 사용량 추출
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


# ===================================
# 후속 질문 생성
# ===================================


def generate_follow_up_questions(
    question: str,
    answer: str,
    context: str,
    user_level: UserLevel = UserLevel.INTERMEDIATE,
    num_questions: int = 3,
) -> List[str]:
    """
    후속 질문 생성 (XML 파싱)

    Args:
        question: 원래 질문
        answer: AI 답변
        context: 참조 컨텍스트
        user_level: 사용자 레벨
        num_questions: 생성할 질문 수 (기본: 3)

    Returns:
        ["질문1", "질문2", "질문3"]
    """

    # 1. 참조 텍스트 구성
    reference_text = (
        f"[원래 질문]\n{question}\n\n[AI 답변]\n{answer}\n\n[컨텍스트]\n{context[:300]}"
    )

    # 2. 프롬프트 생성
    prompt_text = get_followup_questions_prompt(
        user_level=user_level, reference_text=reference_text
    )

    # 3. LLM 호출
    result = llm.invoke(prompt_text)

    # 4. XML 파싱
    response_text = result.content.strip()

    # <question> 태그 추출
    question_pattern = r"<question>(.*?)</question>"
    questions = re.findall(question_pattern, response_text, re.DOTALL)

    # 공백 제거 및 정리
    questions = [q.strip() for q in questions if q.strip()]

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
