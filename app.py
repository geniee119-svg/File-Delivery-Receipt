import streamlit as st
import google.generativeai as genai
from PIL import Image

# --- 1. 보안 설정: 비밀번호 확인 ---
def check_password():
    if "password_entered" not in st.session_state:
        st.session_state["password_entered"] = False

    if not st.session_state["password_entered"]:
        st.text_input("팀 전용 접속 비밀번호를 입력하세요", type="password", key="pwd")
        if st.session_state["pwd"] == st.secrets["APP_PASSWORD"]:
            st.session_state["password_entered"] = True
            st.rerun()
        elif st.session_state["pwd"]:
            st.error("비밀번호가 일치하지 않습니다.")
        return False
    return True

# 비밀번호가 맞을 때만 아래 메인 화면이 열립니다.
if check_password():
    # --- 2. 메인 화면 구성 ---
    st.title("📺 방송 편성 파일 인수증 자동 생성기")
    st.write("영상 목록 캡처본(이미지)을 올리면 엑셀용 표 데이터를 추출합니다.")
    
    # API 키 세팅 (Streamlit Secrets에서 가져옴)
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash') # 빠르고 가벼운 비전 모델

    # --- 3. 파일 업로드 기능 ---
    uploaded_file = st.file_uploader("여기에 목록 이미지를 드래그 앤 드롭 하세요", type=["png", "jpg", "jpeg"])

    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='업로드된 원본 이미지', use_column_width=True)
        
        if st.button("파일 인수증 추출 실행"):
            with st.spinner('제미나이가 이미지를 읽고 데이터를 정제하고 있습니다...'):
                # --- 4. 핵심 AI 프롬프트 (규칙 및 코드표 내장) ---
                prompt = """
당신은 방송 편성 데이터 정제 전문가입니다. 
첨부된 이미지(영상 목록 캡처본)를 분석하여 '파일 인수증' 텍스트를 작성해야 합니다.

[작업 규칙]
1. 파일명 맨 앞에 있는 숫자를 '회차'로 최우선 인식합니다. 맨 앞에 숫자가 없다면 파일명 중간에 있는 회차(예: 31회, 40화 등)를 찾아 적용합니다.
2. 프로그램명은 띄어쓰기를 모두 없애고 아래 [코드표]의 공식 명칭으로 통일합니다. (예: 테마기행 길 -> 테마기행길, 시토 -> 시사토론)
3. 아이디 생성 규칙: [영문 코드 5자리] + [회차 4자리 숫자(빈자리는 0으로 채움)]. 예: 82회 -> 0082
4. 출력 포맷: 엑셀에 바로 붙여넣을 수 있게 각 항목을 '탭(Tab)'으로만 구분합니다. 마크다운 표 형태(|)는 절대 사용하지 마세요.
5. 열 구성: [아이디] (탭) [영상 길이(예: 00:45:00)] (탭) [본방]프로그램명+회차 (탭) [비고(빈칸)]

[프로그램 코드표]
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

위 규칙과 코드표를 엄격하게 적용하여 탭으로 구분된 텍스트 결과물만 출력하세요. 다른 부연 설명이나 인사말은 절대 하지 마세요.
                """
                
                try:
                    response = model.generate_content([prompt, image])
                    st.success("✨ 작업이 완료되었습니다! 아래 박스 우측 상단의 '복사' 아이콘을 눌러 엑셀 A1 셀에 붙여넣으세요.")
                    st.code(response.text, language="text")
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")