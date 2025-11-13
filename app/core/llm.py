# app/utils/llm.py


import os
from dotenv import load_dotenv
from langchain_upstage import ChatUpstage
from langchain_core.prompts import ChatPromptTemplate
from openai import OpenAI

load_dotenv()


UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")

# LangChain Upstage Chat LLM
llm = ChatUpstage(
    api_key=UPSTAGE_API_KEY,
    model="solar-pro2",    # 무료, 한국어 성능 매우 강함
    temperature=0.2,
    max_tokens=512
)

# 시스템 + 사용자 Prompt 템플릿
RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "너는 한국어 금융 리포트 분석 및 요약에 특화된 RAG AI 어시스턴트야. "
     "주어진 컨텍스트 내에서만 답변하고, 없는 정보는 지어내지 마."),
    ("user",
     "[Context]\n{context}\n\n[Question]\n{question}")
])


def generate_answer(question: str, context: str) -> str:
    """LangChain 체인 방식으로 답변 생성"""

    chain = RAG_PROMPT | llm  # Prompt → LLM 연결

    result = chain.invoke({
        "context": context,
        "question": question,
    })

    return result.content.strip()



'''
OpenAI구조
'''
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


'''
GPU에서 Qwen3vl
'''
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
