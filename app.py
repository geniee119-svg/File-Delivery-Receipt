import streamlit as st
import google.generativeai as genai
from PIL import Image
import base64

# --- 앱 기본 설정 ---
st.set_page_config(page_title="MBC NET 파일 인수증", layout="centered")

# --- 사내 전용 폰트(MBC NEW L.ttf) 로드 및 CSS 적용 ---
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
        
        /* 1. 앱 전체 폰트 적용 */
        html, body, [class*="st-"] {{
            font-family: 'MBC_NEW_L', sans-serif !important;
        }}
        
        /* 2. 상단 보라색 포인트 띠 */
        [data-testid="stHeader"] {{
            background-color: transparent;
            border-top: 8px solid #684CDB;
        }}
        
        /* 3. 입력창 포커스 색상 */
        div[data-baseweb="input"] > div {{
            border-color: #684CDB !important;
        }}

        /* 4. 사이드바 화살표 완벽 고정 (텍스트 제거 및 색상 유지) */
        [data-testid="collapsedControl"] span,
        [data-testid="stSidebarCollapseButton"] span {{
            display: none !important; /* keyboard_double 등 텍스트 제거 */
        }}
        [data-testid="collapsedControl"] svg,
        [data-testid="stSidebarCollapseButton"] svg {{
            fill: #684CDB !important;
            color: #684CDB !important;
            width: 28px !important;
            height: 28px !important;
        }}

        /* 5. 대화창 이모티콘(아바타) 완벽 제거 */
        [data-testid="stChatMessageAvatar"] {{
            display: none !important;
        }}
        .stChatMessage {{
            padding-left: 0 !important;
            gap: 0.5rem !important;
        }}

        /* 6. 코드 블록 폰트 통일 */
        .stCodeBlock code, .stCodeBlock pre {{
            font-family: 'MBC_NEW_L', monospace !important;
            font-size: 14px !important;
        }}

        /* 7. 전송 버튼 위치 및 디자인 미세 조정 */
        [data-testid="stChatInputButton"] {{
            color: #684CDB !important;
        }}
        </style>
    """, unsafe_allow_html=True)

except FileNotFoundError:
    st.error(f"사내 폰트 파일을 찾을 수 없습니다: '{font_file}'")

# --- 1. 보안 설정: 비밀번호 확인 ---
def check_password():
    if "password_entered" not in st.session_state:
        st.session_state["password_entered"] = False

    if not st.session_state["password_entered"]:
        # 비밀번호 입력창에도 타이틀 축소 적용을 위해 위에 배치
        st.markdown("<h4 style='text-align: center; color: #4A4A4A;'>mbcnet 파일 인수증 생성기</h4>", unsafe_allow_html=True)
        pwd = st.text_input("팀 전용 접속 비밀번호를 입력하세요", type="password")
        if st.button("접속"):
            if pwd == st.secrets["APP_PASSWORD"]:
                st.session_state["password_entered"] = True
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")
        return False
    return True

if check_password():
    # --- 타이틀 축소 표시 ---
    st.markdown("<h4 style='text-align: center; color: #4A4A4A; font-weight: bold; margin-bottom: 20px;'>mbcnet 파일 인수증 생성기</h4>", unsafe_allow_html=True)

    # --- 2. 사이드바 (프로그램 관리) ---
    with st.sidebar:
        st.markdown("### 프로그램 관리")
        if "custom_codes" not in st.session_state:
            st.session_state["custom_codes"] = {}

        with st.form("new_program_form", clear_on_submit=True):
            new_name = st.text_input("프로그램명")
            new_code = st.text_input("영문 코드")
            submitted = st.form_submit_button("추가하기", use_container_width=True)
            
            if submitted:
                if new_name and new_code:
                    clean_name = new_name.replace(" ", "")
                    st.session_state["custom_codes"][clean_name] = new_code
                    st.success(f"'{clean_name}' 등록 완료")
        
        if st.session_state["custom_codes"]:
            st.markdown("---")
            for name, code in st.session_state["custom_codes"].items():
                st.markdown(f"- {name}: `{code}`")
            if st.button("목록 초기화", use_container_width=True):
                st.session_state["custom_codes"] = {}
                st.rerun()

    # --- 3. 제미나이 설정 ---
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash')

    def get_prompt():
        custom_section = ""
        if st.session_state["custom_codes"]:
            custom_section = "\n[추가된 신규 프로그램 코드]\n"
            for name, code in st.session_state["custom_codes"].items():
                custom_section += f"- {name}: {code}\n"
        
        return f"""
당신은 방송 편성 데이터 정제 전문가입니다. 이미지의 파일 목록을 분석하여 파일 인수증 텍스트를 작성하세요.

[작업 규칙]
1. 회차 추출: 파일명 왼쪽에서 가장 먼저 등장하는 숫자(회/화)를 회차로 확정.
2. 프로그램명: [코드표] 명칭 사용, 띄어쓰기 제거.
3. 아이디: [영문코드 5자리] + [회차 4자리 숫자].
4. 포맷: 각 항목은 '탭(Tab)'으로 구분, 목록은 '줄바꿈'으로 구분 (마크다운 표 금지).
5. 열 구성: [아이디] (탭) [영상 길이] (탭) [본방]프로그램명+회차 (탭) [비고]

[기본 코드표]
- 어영차바다야: NBOBA / 로컬판타지: NBFCF / 인생내컷: NBJCB / 테마기행길: NBDHA
- 보통의존재: NBRBB / 시사토론: NBFKB / 제주엔: NBKBH / 톡톡동해인: NBTBA
- 문화콘서트난장: NBDEA / 맛나면좋은친구: NBNCA / 인생굿샷: NBIFA / 문화요: NBCCE
- 어서와한국은처음이지: NCVJA / 취미로운생활: NAABJ / 팔도맛지도: NAABI
- 어린왕자원정대: NBQCC / 소통의고수3시즌: NBKGF / 여기이슈강원: NBIKA
- 신농사직설6시즌: NBCCH / 시민의품격: NBCCG / 다정다감: NBFCG / 이슈잇다: NBKKA
{custom_section}
결과물(탭 구분 텍스트)만 출력하고 인사말은 생략하세요.
"""

    # --- 4. 대화 기록 ---
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            if msg["type"] == "text": st.markdown(msg["content"])
            elif msg["type"] == "code": st.code(msg["content"], language="text")
            elif msg["type"] == "image": st.image(msg["content"], width=400)

    # --- 5. 채팅 입력 (이미지 첨부 포함) ---
    prompt_input = st.chat_input("이미지를 업로드하거나 궁금한 점을 입력하세요", accept_file=True, file_type=["png", "jpg", "jpeg"])

    if prompt_input:
        # 텍스트 입력 처리
        if prompt_input.text:
            st.session_state["messages"].append({"role": "user", "type": "text", "content": prompt_input.text})
        
        # 이미지 입력 처리
        if prompt_input.files:
            img = Image.open(prompt_input.files[0])
            st.session_state["messages"].append({"role": "user", "type": "image", "content": img})
            
            with st.spinner('데이터 분석 중...'):
                try:
                    # 제미나이 분석 요청 (프롬프트 + 이미지)
                    response = model.generate_content([get_prompt(), img])
                    st.session_state["messages"].append({"role": "assistant", "type": "code", "content": response.text})
                except Exception as e:
                    st.error(f"오류 발생: {e}")
        
        st.rerun()
