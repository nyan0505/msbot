from __future__ import annotations

from microsoft_agents.hosting.core import ActivityHandler, TurnContext, TypingIndicator
from microsoft_agents.activity import ActivityTypes  # noqa: F401 (imported for clarity)

from tools.llm import call_llm
from tools.m365_search import format_sources, get_obo_token, search_m365


class TeamsBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext) -> None:
        text = (turn_context.activity.text or "").strip()

        if not text or text.strip("/").lower() == "agent":
            await turn_context.send_activity(
                "질문을 입력해주세요.\n예시: `/agent 지난주 팀 회의 내용 요약해줘`"
            )
            return

        # /agent 커맨드 파싱
        if text.lower().startswith("/agent"):
            text = text[len("/agent"):].strip()

        if not text:
            await turn_context.send_activity(
                "질문을 입력해주세요.\n예시: `/agent 지난주 팀 회의 내용 요약해줘`"
            )
            return

        # 타이핑 인디케이터 — 처리 완료 또는 응답 전송 시 자동 중단
        async with TypingIndicator(turn_context):
            try:
                graph_token = self._try_get_graph_token(turn_context)
                search_results = await search_m365(text, user_token=graph_token)
                context_str = format_sources(search_results)
                answer = await call_llm(text, context=context_str)

                if search_results:
                    source_lines = "\n".join(
                        f"- [{r['source_type']}] {r['source_label']}"
                        for r in search_results
                    )
                    answer = f"{answer}\n\n---\n**참고 자료:**\n{source_lines}"

                await turn_context.send_activity(answer)

            except TimeoutError as e:
                await turn_context.send_activity(f"⏱️ 응답 시간 초과: {e}")
            except ConnectionError as e:
                await turn_context.send_activity(f"🔌 서버 연결 실패: {e}")
            except Exception as e:
                await turn_context.send_activity(f"처리 중 오류가 발생했습니다: {e}")

    @staticmethod
    def _try_get_graph_token(turn_context: TurnContext) -> str | None:
        """Teams SSO 토큰을 추출하여 OBO Graph 토큰으로 교환 시도."""
        channel_data = turn_context.activity.channel_data or {}
        sso_token = channel_data.get("ssoToken")
        if not sso_token:
            return None
        try:
            return get_obo_token(sso_token)
        except PermissionError:
            return None
