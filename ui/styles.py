import streamlit as st
import markdown as md


def apply_styles():
    """
    전체 앱 CSS 스타일 적용 함수
    app.py 에서 가장 먼저 호출해야 함
    """
    st.markdown("""
    <style>

    /* ─────────────────────────────────────────
       1. 전체 배경 + 기본 설정
    ───────────────────────────────────────── */
    .stApp {
        background-color: #f7f8fc;
    }

    /* ─────────────────────────────────────────
       2. 헤더
    ───────────────────────────────────────── */
    .main-header {
        background: linear-gradient(135deg, #1f4e79, #2e75b6);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
        text-align: center;
    }

    .main-header h1 {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
    }

    .main-header p {
        font-size: 0.95rem;
        margin: 8px 0 0 0;
        opacity: 0.85;
    }

    /* ─────────────────────────────────────────
       3. 사이드바
       ② 수정 : * !important 제거
          → 드롭다운 메뉴 글씨 사라지는 버그 방지
    ───────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background-color: #1f4e79;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }

    /* ─────────────────────────────────────────
       4. 채팅 말풍선
    ───────────────────────────────────────── */
    .chat-user-wrap {
        display: flex;
        justify-content: flex-end;
        margin: 12px 0;
    }

    .chat-user {
        background: linear-gradient(135deg, #1f4e79, #2e75b6);
        color: white;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        max-width: 70%;
        font-size: 0.95rem;
        line-height: 1.6;
        box-shadow: 0 2px 8px rgba(31,78,121,0.2);
    }

    .chat-ai-wrap {
        display: flex;
        justify-content: flex-start;
        margin: 12px 0;
    }

    .chat-ai {
        background: white;
        color: #2c3e50;
        padding: 12px 18px;
        border-radius: 18px 18px 18px 4px;
        max-width: 75%;
        font-size: 0.95rem;
        line-height: 1.6;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        border-left: 4px solid #2e75b6;
    }

    /* ① 수정 : 마크다운 렌더링 스타일 추가 */
    .chat-ai p { margin: 0 0 8px 0; }
    .chat-ai p:last-child { margin-bottom: 0; }
    .chat-ai ul, .chat-ai ol { margin: 8px 0; padding-left: 20px; }
    .chat-ai li { margin: 4px 0; }
    .chat-ai strong { font-weight: 700; color: #1f4e79; }
    .chat-ai code {
        background: #f0f4ff;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-family: monospace;
    }
    .chat-ai pre {
        background: #f0f4ff;
        padding: 12px;
        border-radius: 8px;
        overflow-x: auto;
        font-size: 0.85rem;
    }

    .chat-label {
        font-size: 0.75rem;
        color: #888;
        margin-bottom: 4px;
    }

    .chat-label-right {
        text-align: right;
    }

    /* ─────────────────────────────────────────
       5. 출처 카드
    ───────────────────────────────────────── */
    .source-card {
        background: #f0f4ff;
        border: 1px solid #d0dff5;
        border-radius: 10px;
        padding: 10px 14px;
        margin: 6px 0;
        font-size: 0.85rem;
        color: #2c3e50;
        transition: all 0.2s;
    }

    .source-card:hover {
        background: #dce8ff;
        border-color: #2e75b6;
    }

    .source-title {
        font-weight: bold;
        color: #1f4e79;
        margin-bottom: 4px;
    }

    .source-preview {
        color: #666;
        font-size: 0.8rem;
        line-height: 1.4;
    }

    /* ─────────────────────────────────────────
       6. 토큰 정보
    ───────────────────────────────────────── */
    .token-info {
        background: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 0.8rem;
        color: #666;
        margin-top: 8px;
        display: flex;
        gap: 16px;
    }

    /* ─────────────────────────────────────────
       7. 배지
    ───────────────────────────────────────── */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: bold;
    }

    .badge-success { background: #d4edda; color: #155724; }
    .badge-info    { background: #d1ecf1; color: #0c5460; }
    .badge-warning { background: #fff3cd; color: #856404; }

    /* ─────────────────────────────────────────
       8. 버튼
    ───────────────────────────────────────── */
    .stButton > button {
        background: linear-gradient(135deg, #1f4e79, #2e75b6);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 0.95rem;
        font-weight: bold;
        width: 100%;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #2e75b6, #3a8fd1);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(31,78,121,0.3);
    }

    /* ─────────────────────────────────────────
       9. 입력창
       ③ 수정 : 느슨한 셀렉터로 변경
    ───────────────────────────────────────── */
    .stTextInput input,
    .stTextArea textarea {
        border-radius: 10px;
        border: 2px solid #e0e0e0;
        padding: 10px 14px;
        font-size: 0.95rem;
        transition: border 0.2s;
    }

    .stTextInput input:focus,
    .stTextArea textarea:focus {
        border-color: #2e75b6;
        box-shadow: 0 0 0 3px rgba(46,117,182,0.15);
    }

    /* ─────────────────────────────────────────
       10. 섹션 + 빈 상태
    ───────────────────────────────────────── */
    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: #1f4e79;
        margin: 16px 0 8px 0;
        padding-bottom: 6px;
        border-bottom: 2px solid #2e75b6;
    }

    .empty-state {
        text-align: center;
        padding: 48px 24px;
        color: #aaa;
    }

    .empty-state h3 {
        font-size: 1.2rem;
        margin-bottom: 8px;
        color: #ccc;
    }

    .empty-state p {
        font-size: 0.9rem;
    }

    </style>
    """, unsafe_allow_html=True)


def render_header():
    """상단 헤더 렌더링 함수"""
    st.markdown("""
    <div class="main-header">
        <h1>🧠 DocuMind AI</h1>
        <p>다중 문서 통합 분석 및 출처 추적 QA 시스템</p>
    </div>
    """, unsafe_allow_html=True)


def render_chat_message(role: str, content: str):
    """
    채팅 말풍선 렌더링 함수

    Args:
        role    : "user" 또는 "assistant"
        content : 메시지 내용

    ① 수정 : AI 답변을 markdown → HTML 변환 후 렌더링
             마크다운 문법이 그대로 노출되는 버그 방지
    """
    if role == "user":
        st.markdown(f"""
        <div class="chat-label chat-label-right">나 👤</div>
        <div class="chat-user-wrap">
            <div class="chat-user">{content}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # AI 답변 마크다운 → HTML 변환
        content_html = md.markdown(content)
        st.markdown(f"""
        <div class="chat-label">🧠 DocuMind AI</div>
        <div class="chat-ai-wrap">
            <div class="chat-ai">{content_html}</div>
        </div>
        """, unsafe_allow_html=True)


def render_source_card(source: dict):
    """
    출처 카드 렌더링 함수

    Args:
        source : {파일명, 페이지, 내용 미리보기}
    """
    st.markdown(f"""
    <div class="source-card">
        <div class="source-title">
            📄 {source['파일명']} / {source['페이지']}페이지
        </div>
        <div class="source-preview">
            {source['내용 미리보기']}...
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_empty_state():
    """파일 업로드 전 빈 화면 렌더링"""
    st.markdown("""
    <div class="empty-state">
        <h3>📂 문서를 업로드해주세요</h3>
        <p>왼쪽 사이드바에서 PDF, DOCX, XLSX, PPTX 파일을<br>
        업로드하면 AI가 문서를 분석하고 질문에 답변해드립니다.</p>
    </div>
    """, unsafe_allow_html=True)


def render_badge(text: str, badge_type: str = "info"):
    """
    상태 배지 렌더링 함수

    Args:
        text       : 배지 텍스트
        badge_type : "success", "info", "warning"
    """
    st.markdown(f"""
    <span class="badge badge-{badge_type}">{text}</span>
    """, unsafe_allow_html=True)