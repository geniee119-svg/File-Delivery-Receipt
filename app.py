import streamlit as st
import google.generativeai as genai
from PIL import Image
import base64

# --- 앱 기본 설정 ---
st.set_page_config(page_title="MBC NET 파일 인수증", layout="centered")

# --- 사내 전용 폰트 로드 및 CSS 적용 (UI 개선) ---
font_file = "MBC NEW L.ttf"

try:
    with open(font_file, "rb") as f:
        font_data = f.read()
        font_b64 = base64.b64encode(font_data).decode("utf-8")

    st.markdown(f"""
        <style>
        @font-face {{
            font-family: 'MBC_NEW_L';
            src: url(data:font/ttf;charset=utf-8;base64,{font_b64}) format('truetype');
        }}
        
        /* 1. 전체 폰트 및 배경 깔끔화 */
        html, body, [class*="st-"] {{
            font-family: 'MBC_NEW_L', sans-serif !important;
        }}

        /* 2. 상단 보라색 포인트 띠 유지 */
        [data-testid="stHeader"] {{
            background-color: transparent;
            border-top: 8px solid #684CDB;
        }}

        /* 3. 사이드바 화살표 오류 해결 (아이콘 텍스트 강제 제거 및 삼각형 고정) */
        [data-testid="collapsedControl"] span, 
        [data-testid="stSidebarCollapseButton"] span {{
            display: none !important; /* 'double_arrow_right' 글자 노출 차단 */
        }}
        [data-testid="collapsedControl"] svg, 
        [data-testid="stSidebarCollapseButton"] svg {{
            fill: #684CDB !important;
            color: #684CDB !important;
            width: 24px !important;
            height: 24px !important;
            visibility: visible !important;
        }}

        /* 4. 이모티콘 및 아바타 영역 완전 삭제 (통일성 확보) */
        /* 대화창 내부/외부 이모티콘 상자 자체를 제거하여 텍스트만 깔끔하게 노출 */
        [data-testid="stChatMessageAvatar"] {{
            display: none !important;
        }}
        .stChatMessage {{
            padding-left: 0 !important;
            margin-bottom: 10px !important;
        }}
        /* 대화창 테두리 통일 */
        [data-testid="stChatMessageContent"] {{
            padding: 15px !important;
            border-radius: 10px !important;
            background-color: #f8f9fa !important;
        }}

        /* 5. 코드 블록 및 텍스트 정렬 */
        .stCodeBlock code {{
            font-family: 'MBC_NEW_L', monospace !important;
            font-size: 14px !important;
        }}
        
        /* 6. 입력창 디자인 */
        div[data-baseweb="input"] > div {{
            border-color: #684CDB !important;
        }}
        </style>
    """, unsafe_allow_html=True)
except FileNotFoundError:
    st.error("폰트 파일을 찾을 수 없습니다.")

# --- 1. 보안 설정: 비밀번호 확인 ---
def check_password():
    if "password_entered" not in st.session_state:
        st.session_state["password_entered"] = False
    if not st.session_state["password_entered"]:
        st.text_input("접속 비밀번호를 입력하세요", type="password", key="pwd_input")
        if st.session_state["pwd_input"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_entered"] = True
            st.rerun()
        return False
    return True

if check_password():
    # --- 제목 삭제 (요청사항 반영) ---
    # st.title이나 제목 텍스트를 모두 삭제하여 깔끔한 화면 구성

    # --- 2. 사이드바 관리 ---
    with st.sidebar:
        st.markdown("### ⚙️ 프로그램 관리")
        if "custom_codes" not in st.session_state:
            st.session_state["custom_codes"] = {}

        with st.form("new_program", clear_on_submit=True):
            n = st.text_input("프로그램명")
            c = st.text_input("영문 코드")
            if st.form_submit_button("추가", use_container_width=True):
                if n and c:
                    st.session_state["custom_codes"][n.replace(" ","")] = c
                    st.success(f"{n} 등록 완료")
        
        if st.session_state["custom_codes"]:
            if st.button("목록 초기화"):
                st.session_state["custom_codes"] = {}
                st.rerun()

    # --- 3. 제미나이 설정 및 정교화된 프롬프트 ---
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')

    def get_prompt():
        custom = ""
        for n, c in st.session_state["custom_codes"].items():
            custom += f"- {n}: {c}\n"
        
        # 정제 로직을 더욱 엄격하게 지시
        return f"""
방송 편성 데이터 정제 전문가로서 다음 규칙을 엄격히 준수하십시오.

[작업 규칙]
1. 회차(ID 생성용): 파일명 문자열 시작점에서 가장 먼저 발견되는 숫자(예: 39회 -> 0039)만 사용.
2. 프로그램명: [코드표]와 일치하게 정제, 띄어쓰기 완전 제거.
3. 출력 형식: [ID(9자리)] [탭] [길이(HH:MM:SS)] [탭] [본방]프로그램명+회차 [탭] [비고]
4. 반드시 탭(Tab)으로 열을 구분하고, 한 줄에 하나씩만 작성.
5. 인사말, 부연 설명 없이 텍스트 결과만 출력.

[코드표]
- 어영차바다야: NBOBA / 로컬판타지: NBFCF / 인생내컷: NBJCB / 테마기행길: NBDHA
- 보통의존재: NBRBB / 시사토론: NBFKB / 제주엔: NBKBH / 톡톡동해인: NBTBA
- 문화콘서트난장: NBDEA / 맛나면좋은친구: NBNCA / 인생굿샷: NBIFA / 문화요: NBCCE
- 어서와한국은처음이지: NCVJA / 취미로운생활: NAABJ / 팔도맛지도: NAABI
- 어린왕자원정대: NBQCC / 소통의고수3시즌: NBKGF / 여기이슈강원: NBIKA
- 신농사직설6시즌: NBCCH / 시민의품격: NBCCG / 다정다감: NBFCG / 이슈잇다: NBKKA
{custom}
"""

    # --- 4. 대화 기록 (통일된 레이아웃) ---
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        # avatar=None을 통해 기본 아이콘 완전 차단
        with st.chat_message(msg["role"], avatar=None):
            if msg["type"] == "text": st.write(msg["content"])
            elif msg["type"] == "code": st.code(msg["content"], language="text")
            elif msg["type"] == "image": st.image(msg["content"], width=450)

    # --- 5. 입력창 ---
    inp = st.chat_input("이미지를 올리거나 대화를 입력하세요", accept_file=True, file_type=["png", "jpg", "jpeg"])

    if inp:
        if inp.text:
            st.session_state["messages"].append({"role": "user", "type": "text", "content": inp.text})
        if inp.files:
            img = Image.open(inp.files[0])
            st.session_state["messages"].append({"role": "user", "type": "image", "content": img})
            with st.spinner('정제 중...'):
                try:
                    res = model.generate_content([get_prompt(), img])
                    st.session_state["messages"].append({"role": "assistant", "type": "code", "content": res.text})
                except Exception as e:
                    st.error(f"오류: {e}")
        st.rerun()
