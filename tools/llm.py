from __future__ import annotations

import httpx
import config

_SYSTEM_PROMPT = (
    "당신은 사내 지식 검색을 돕는 AI 어시스턴트입니다. "
    "제공된 참고 자료를 바탕으로 정확하고 간결하게 한국어로 답변하세요. "
    "참고 자료가 없으면 일반 지식으로 답변하되, 사내 데이터를 찾을 수 없음을 명시하세요."
)


async def call_llm(user_message: str, context: str = "") -> str:
    system_content = (
        f"{_SYSTEM_PROMPT}\n\n[참고 자료]\n{context}" if context else _SYSTEM_PROMPT
    )
    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_message},
    ]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.BEARER_TOKEN}",
    }

    try:
        async with httpx.AsyncClient(timeout=config.LLM_TIMEOUT) as client:
            response = await client.post(
                config.LITELLM_BASE_URL,
                headers=headers,
                json={"model": config.LITELLM_MODEL, "messages": messages},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

    except httpx.TimeoutException:
        raise TimeoutError("LiteLLM 서버 응답 시간이 초과되었습니다.")
    except httpx.ConnectError:
        raise ConnectionError(
            "LiteLLM 서버에 연결할 수 없습니다. 서버 주소와 상태를 확인하세요."
        )
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"LiteLLM HTTP 오류 ({e.response.status_code}).")
    except Exception as e:
        raise RuntimeError(f"LLM 호출 오류: {e}")
