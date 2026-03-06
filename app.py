import streamlit as st
import google.generativeai as genai
from PIL import Image
import base64

# --- 1. 앱 기본 설정 및 비밀번호 확인 ---
st.set_page_config(page_title="MBC NET 파일 인수증", layout="centered")

def check_password():
    """비밀번호 확인 로직"""
    if "password_entered" not in st.session_state:
        st.session_state["password_entered"] = False

    if not st.session_state["password_entered"]:
        # 비밀번호 입력창
        pwd = st.text_input("팀 전용 접속 비밀번호를 입력하세요", type="password", key="pwd_input")
        
        # 비밀번호 확인 (secrets.toml 파일에 APP_PASSWORD 설정 필요)
        if pwd == st.secrets.get("APP_PASSWORD"):
            st.session_state["password_entered"] = True
            st.rerun() # 비밀번호가 맞으면 앱을 다시 실행하여 화면 갱신
        elif pwd:
            st.error("비밀번호가 일치하지 않습니다.")
        return False
    return True

# 비밀번호가 확인되지 않으면 앱 실행을 중단
if not check_password():
    st.stop()


# --- 2. 사내 전용 폰트 및 CSS 스타일링 적용 ---
font_file = "MBC NEW L.ttf"
try:
    with open(font_file, "rb") as f:
        font_data = f.read()
        font_b64 = base64.b64encode(font_data).decode("utf-8")

    st.markdown(f"""
        <style>
        /* 폰트 정의 */
        @font-face {{
            font-family: 'MBC_NEW_L';
            src: url(data:font/ttf;charset=utf-8;base64,{font_b64}) format('truetype');
        }}
        
        /* 전체 폰트 적용 */
        html, body, p, div, span, input, button, textarea, label, li, h1, h2, h3, h4, h5, h6 {{
            font-family: 'MBC_NEW_L', sans-serif !important;
        }}

        /* 아이콘 폰트 충돌 방지 */
        .material-symbols-rounded, .material-symbols-outlined {{
            font-family: 'Material Symbols Rounded', sans-serif !important;
        }}
        
        /* 상단 보라색 포인트 띠 */
        [data-testid="stHeader"] {{
            background-color: transparent;
            border-top: 8px solid #684CDB;
        }}
        
        /* 입력창 포커스 색상 */
        div[data-baseweb="input"] > div {{
            border-color: #684CDB !important;
        }}

        /* 사이드바 화살표 버튼 색상 통일 (핵심 수정) */
        [data-testid="stSidebarCollapsedControl"] svg,
        [data-testid="stSidebarCollapseButton"] svg {{
            fill: #684CDB !important;
            color: #684CDB !important;
            width: 32px !important;
            height: 32px !important;
        }}
        
        /* 화살표 호버 효과 */
        [data-testid="stSidebarCollapsedControl"]:hover,
        [data-testid="stSidebarCollapseButton"]:hover {{
            background-color: rgba(104, 76, 219, 0.1) !important;
            border-radius: 50%;
        }}

        /* 코드 블록 폰트 및 스타일 통일 (핵심 수정) */
        .stCodeBlock code, .stCodeBlock pre {{
            font-family: 'MBC_NEW_L', monospace !important; /* 폰트 통일 */
            font-size: 16px !important; /* 크기 통일 */
            line-height: 1.6 !important;
            background-color: #f8f9fa !important; /* 배경색 통일 */
            color: #333 !important; /* 글자색 통일 */
        }}
        </style>
    """, unsafe_allow_html=True)

except FileNotFoundError:
    # 폰트 파일이 없을 경우 경고 메시지 표시 (앱 실행은 계속됨)
    st.warning(f"사내 폰트 파일('{font_file}')을 찾을 수 없어 기본 폰트가 적용됩니다.")


# --- 3. Gemini AI 모델 설정 및 프롬프트 정의 ---
# secrets.toml 파일에 GEMINI_API_KEY 설정 필요
genai.configure(api_key=st.secrets.get("GEMINI_API_KEY"))
# 사용 가능한 최신 모델로 설정 (필요시 변경)
model = genai.GenerativeModel('gemini-1.5-flash')

def get_prompt(custom_codes):
    """
    AI에게 전달할 프롬프트를 생성하는 함수.
    기존 작업 규칙과 코드표를 포함합니다.
    """
    custom_section = ""
    if custom_codes:
        custom_section = "\n[추가된 신규 프로그램 코드]\n"
        for name, code in custom_codes.items():
            custom_section += f"- {name}: {code}\n"
            
    return f"""
당신은 방송 편성 데이터 정제 전문가입니다. 
첨부된 이미지(영상 목록 캡처본)를 분석하여 '파일 인수증' 텍스트를 작성해야 합니다.

[작업 규칙]
1. 회차 추출 (매우 중요): 파일명 문자열을 왼쪽부터 읽었을 때 **가장 먼저 등장하는 숫자(숫자+회/화)**를 무조건 최종 회차로 확정합니다. 파일명 중간이나 프로그램명 뒤쪽에 다른 회차가 적혀 있더라도 절대 무시하세요. 
   - 예시: '39회_260125일_시토_40회' -> 39회 추출 (40회 무시)
   - 예시: '49회_64화_제주엔' -> 49회 추출 (64화 무시)
2. 프로그램명은 띄어쓰기를 모두 없애고 아래 [코드표]의 공식 명칭으로 통일합니다. (예: 테마기행 길 -> 테마기행길, 시토 -> 시사토론)
3. 아이디 생성 규칙: [영문 코드 5자리] + [회차 4자리 숫자(빈자리는 0으로 채움)]. 예: 82회 -> 0082
4. 출력 포맷: 엑셀에 바로 붙여넣을 수 있게 각 항목을 '탭(Tab)'으로만 구분하며, **각 영상 목록은 반드시 줄바꿈(Enter)으로 구분하여 한 줄에 하나씩 작성하세요.** 마크다운 표 형태(|)는 절대 사용하지 마세요.
5. 열 구성: [아이디] (탭) [영상 길이(예: 00:45:00)] (탭) [본방]프로그램명+회차 (탭) [비고(빈칸)]

[기존 프로그램 코드표]
- 어영차바다야: NBOBA
- 로컬판타지: NBFCF
- 인생내컷: NBJCB
- 테마기행길: NBDHA
- 보통의존재: NBRBB
- 시사토론: NBFKB
- 제주엔: NBKBH
- 톡톡동해인: NBTBA
- 문화콘서트난장: NBDEA
- 맛나면좋은친구: NBNCA
- 인생굿샷: NBIFA
- 문화요: NBCCE
- 어서와한국은처음이지: NCVJA
- 취미로운생활: NAABJ
- 팔도맛지도: NAABI
- 어린왕자원정대: NBQCC
- 소통의고수3시즌: NBKGF
- 여기이슈강원: NBIKA
- 신농사직설6시즌: NBCCH
- 시민의품격: NBCCG
- 다정다감: NBFCG
- 이슈잇다: NBKKA
{custom_section}

위 규칙과 코드표를 엄격하게 적용하여 탭으로 구분된 텍스트 결과물만 출력하세요. 다른 부연 설명이나 인사말은 절대 하지 마세요.
"""

# --- 4. 사이드바: 프로그램 관리 ---
with st.sidebar:
    st.markdown("### 프로그램 관리")
    st.write("기존 코드표에 없는 새 프로그램을 임시 등록합니다.")
    
    # 세션 상태에 커스텀 코드 저장소 초기화
    if "custom_codes" not in st.session_state:
        st.session_state["custom_codes"] = {}

    # 프로그램 추가 폼
    with st.form("new_program_form", clear_on_submit=True):
        new_name = st.text_input("프로그램명 (예: 신농사직설)")
        new_code = st.text_input("영문 코드 (예: NBCCH)")
        
        # 추가하기 버튼 클릭 시 동작
        if st.form_submit_button("추가하기", type="primary", use_container_width=True):
            if new_name and new_code:
                # 공백 제거 후 저장
                clean_name = new_name.replace(" ", "")
                st.session_state["custom_codes"][clean_name] = new_code
                st.success(f"'{clean_name}' 등록 완료")
            else:
                st.warning("프로그램명과 코드를 모두 입력해주세요.")
    
    # 추가된 프로그램 목록 표시
    if st.session_state["custom_codes"]:
        st.markdown("---")
        st.markdown("**[현재 추가된 프로그램]**")
        for name, code in st.session_state["custom_codes"].items():
            st.markdown(f"- **{name}**: `{code}`")
            
        # 목록 초기화 버튼
        if st.button("목록 초기화", use_container_width=True):
            st.session_state["custom_codes"] = {}
            st.rerun()


# --- 5. 메인 화면: 채팅 인터페이스 ---
# 세션 상태에 메시지 기록 초기화
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# 기존 메시지 출력
for msg in st.session_state["messages"]:
    # avatar=None을 설정하여 로봇/사용자 아이콘 제거 (핵심 수정)
    with st.chat_message(msg["role"], avatar=None):
        if msg["type"] == "text":
            st.markdown(msg["content"])
        elif msg["type"] == "code":
            # 코드 블록으로 출력하여 복사하기 쉽게 함
            st.code(msg["content"], language="text")
        elif msg["type"] == "image":
            st.image(msg["content"], width=400)

# 채팅 입력창 (이미지 파일 업로드 가능)
prompt_input = st.chat_input("이미지를 업로드하거나 메시지를 입력하세요", accept_file=True, file_type=["png", "jpg", "jpeg"])

# 사용자 입력 처리
if prompt_input:
    if isinstance(prompt_input, str):
        # 텍스트만 입력된 경우 (현재 로직상 이미지 처리가 주 목적이므로 안내 메시지 표시)
        st.session_state["messages"].append({"role": "assistant", "type": "text", "content": "파일 인수증 생성을 위해 이미지 파일을 업로드해주세요."})
        st.rerun()
    else:
        # 파일이 업로드된 경우
        user_text = prompt_input.text
        user_files = prompt_input.files
        
        if user_files:
            # 첫 번째 이미지를 가져옴
            img = Image.open(user_files[0])
            # 사용자 메시지에 이미지 추가 (아이콘 없이)
            st.session_state["messages"].append({"role": "user", "type": "image", "content": img})
            
            # AI 분석 실행
            with st.spinner('데이터를 분석하고 있습니다...'):
                try:
                    # 프롬프트와 이미지를 모델에 전달
                    prompt = get_prompt(st.session_state["custom_codes"])
                    response = model.generate_content([prompt, img])
                    # 분석 결과를 코드 블록 형태로 추가 (아이콘 없이)
                    st.session_state["messages"].append({"role": "assistant", "type": "code", "content": response.text})
                except Exception as e:
                    # 에러 발생 시 메시지 표시
                    st.session_state["messages"].append({"role": "assistant", "type": "text", "content": f"오류가 발생했습니다: {e}"})
        else:
            # 파일이 없는 경우 안내 메시지
            st.session_state["messages"].append({"role": "assistant", "type": "text", "content": "이미지가 확인되지 않았습니다. 파일 첨부 아이콘을 눌러 이미지를 올려주세요."})
        
        st.rerun()
