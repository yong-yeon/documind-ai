import json                   # JSON 직렬화
from datetime import datetime  # 저장 일시 기록
import streamlit as st         # session_state로 대화 기록 유지


def init_memory():
    # Streamlit은 버튼 클릭/입력마다 전체 코드를 재실행하므로 session_state로 대화 기록을 유지
    if "chat_history" not in st.session_state:  # 첫 실행 시에만 초기화
        st.session_state.chat_history = []


def add_message(role: str, content: str):
    if "chat_history" not in st.session_state:  # 혹시 init_memory가 호출되지 않은 경우 대비
        init_memory()
    st.session_state.chat_history.append({"role": role, "content": content})  # 메시지 추가


def get_chat_history() -> list:
    return st.session_state.get("chat_history", [])  # 없으면 빈 리스트 반환


def get_history_as_string(max_turns: int = 5) -> str:
    # 프롬프트의 {chat_history} 자리에 주입할 문자열로 변환
    history = get_chat_history()
    if not history:
        return "이전 대화 없음"

    recent = history[-(max_turns * 2):]  # 질문+답변 한 쌍이 2개이므로 max_turns * 2개 슬라이싱
    result = []
    for msg in recent:
        prefix = "사람" if msg["role"] == "user" else "AI"  # 역할에 따라 레이블 지정
        result.append(f"{prefix} : {msg['content']}")
    return "\n".join(result)  # 줄바꿈으로 구분해 하나의 문자열로 합침


def clear_memory():
    st.session_state.chat_history = []  # 빈 리스트로 덮어써 대화 기록 초기화


def save_history_to_json() -> str:
    history = get_chat_history()
    if not history:
        return ""  # 저장할 내용이 없으면 빈 문자열 반환
    save_data = {
        "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "대화수":   (len(history) + 1) // 2,  # 홀수 메시지일 때도 대화 수를 정확히 계산
        "대화기록": history,
    }
    return json.dumps(save_data, ensure_ascii=False, indent=2)  # 한글 유지, 들여쓰기 포함


def get_message_count() -> dict:
    history = get_chat_history()
    return {
        "질문 수":    sum(1 for msg in history if msg["role"] == "user"),       # user 메시지 개수
        "답변 수":    sum(1 for msg in history if msg["role"] == "assistant"),  # assistant 메시지 개수
        "전체 메시지": len(history),
    }
