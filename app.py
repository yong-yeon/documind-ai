import streamlit as st
from ui.styles import apply_styles, render_header, render_chat_message, render_source_card, render_empty_state, render_badge

# 스타일 적용
apply_styles()

# 헤더
render_header()

# 채팅 말풍선 테스트
st.write("### 💬 채팅 말풍선 테스트")
render_chat_message("user", "서울 지하철 하루 평균 이용객 수는 얼마야?")
render_chat_message("assistant", "서울 지하철 하루 평균 이용객 수는 5,477천 명입니다. 주중 기준으로는 5,477천명, 주말 기준으로는 3,748천명입니다.")

st.divider()

# 출처 카드 테스트
st.write("### 📄 출처 카드 테스트")
render_source_card({
    "파일명": "2025년서울교통이용통계보고서.pdf",
    "페이지": 49,
    "내용 미리보기": "서울 지하철 하루 평균 이용객은 5,477천 명입니다."
})

st.divider()

# 빈 상태 테스트
st.write("### 📂 빈 상태 테스트")
render_empty_state()

st.divider()

# 배지 테스트
st.write("### 🏷 배지 테스트")
render_badge("문서 처리 완료", "success")
render_badge("PDF", "info")
render_badge("처리 중", "warning")