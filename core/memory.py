import os
import json
from datetime import datetime
import streamlit as st


def init_memory():
    """
    대화 메모리 초기화 함수
    session_state 에 chat_history 가 없으면 빈 리스트로 초기화
    """
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def add_message(role: str, content: str):
    """
    대화 기록에 메시지 추가 함수

    Args:
        role    : "user" 또는 "assistant"
        content : 메시지 내용
    """
    if "chat_history" not in st.session_state:
        init_memory()

    st.session_state.chat_history.append({
        "role": role,
        "content": content
    })


def get_chat_history() -> list:
    """
    현재 대화 기록 반환 함수

    Returns:
        chat_history : 대화 기록 리스트
    """
    if "chat_history" not in st.session_state:
        return []
    return st.session_state.chat_history


def get_history_as_string(max_turns: int = 5) -> str:
    """
    대화 기록을 문자열로 변환하는 함수
    rag.py 프롬프트의 {chat_history} 자리에 전달할 때 사용

    Args:
        max_turns : 포함할 최근 대화 수 (기본값 5)

    Returns:
        history_str : 문자열로 변환된 대화 기록
    """
    history = get_chat_history()

    if not history:
        return "이전 대화 없음"

    # 최근 max_turns * 2 개만 가져옴
    recent = history[-(max_turns * 2):]

    result = []
    for msg in recent:
        if msg["role"] == "user":
            result.append(f"사람 : {msg['content']}")
        else:
            result.append(f"AI : {msg['content']}")

    return "\n".join(result)


def clear_memory():
    """대화 기록 초기화 함수"""
    st.session_state.chat_history = []


def save_history_to_json() -> str:
    """
    대화 기록을 JSON 문자열로 반환하는 함수

    Returns:
        json_str : JSON 형태의 문자열
    """
    history = get_chat_history()

    if not history:
        return ""

    save_data = {
        "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        # 홀수 메시지일 때도 정확한 대화 수 계산
        "대화수": (len(history) + 1) // 2,
        "대화기록": history
    }

    return json.dumps(save_data, ensure_ascii=False, indent=2)


def get_message_count() -> dict:
    """
    대화 통계 반환 함수

    Returns:
        count : 질문 수, 답변 수 딕셔너리
    """
    history = get_chat_history()
    user_count = sum(1 for msg in history if msg["role"] == "user")
    assistant_count = sum(1 for msg in history if msg["role"] == "assistant")

    return {
        "질문 수": user_count,
        "답변 수": assistant_count,
        "전체 메시지": len(history)
    }


# ─────────────────────────────────────────
# 테스트 코드
# ─────────────────────────────────────────
def print_memory_test():
    """
    memory.py 테스트 함수
    Streamlit 없이 딕셔너리로 직접 테스트
    """
    print("=" * 40)
    print("  memory.py 테스트")
    print("=" * 40)

    # session_state 대신 딕셔너리로 직접 테스트
    history = []

    # 메시지 추가
    history.append({"role": "user", "content": "서울 지하철 이용객 수 알려줘"})
    history.append({"role": "assistant", "content": "서울 지하철 하루 평균 이용객은 603만명입니다."})
    history.append({"role": "user", "content": "버스는?"})
    history.append({"role": "assistant", "content": "서울 버스 하루 평균 이용객은 277만명입니다."})
    print("✅ 메시지 4개 추가 완료")

    # 대화 기록 확인
    print("\n--- 대화 기록 ---")
    for msg in history:
        role = "나" if msg["role"] == "user" else "AI"
        print(f"  {role} : {msg['content']}")

    # 문자열 변환 확인 (최근 2턴)
    print("\n--- 문자열 변환 (최근 2턴) ---")
    max_turns = 2
    recent = history[-(max_turns * 2):]
    result = []
    for msg in recent:
        if msg["role"] == "user":
            result.append(f"사람 : {msg['content']}")
        else:
            result.append(f"AI : {msg['content']}")
    print("\n".join(result))

    # 홀수 케이스 테스트
    print("\n--- 홀수 메시지 대화 수 계산 테스트 ---")
    for n in [1, 2, 3, 4, 5]:
        print(f"  메시지 {n}개 → 대화 수 : {(n + 1) // 2}")

    # JSON 저장 확인
    print("\n--- JSON 저장 ---")
    save_data = {
        "저장일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "대화수": (len(history) + 1) // 2,
        "대화기록": history
    }
    print(json.dumps(save_data, ensure_ascii=False, indent=2))

    # 통계 확인
    print("\n--- 대화 통계 ---")
    user_count = sum(1 for msg in history if msg["role"] == "user")
    assistant_count = sum(1 for msg in history if msg["role"] == "assistant")
    print(f"  질문 수 : {user_count}")
    print(f"  답변 수 : {assistant_count}")
    print(f"  전체 메시지 : {len(history)}")

    print("=" * 40)
    print("✅ memory.py 테스트 완료!")
    print("=" * 40)


if __name__ == "__main__":
    print_memory_test()