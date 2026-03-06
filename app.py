import streamlit as st
import google.generativeai as genai

st.title("🛠️ 제미나이 API 진단기")
st.write("현재 발급받은 API 키로 접속 가능한 AI 모델의 목록을 확인합니다.")

# 비밀 금고에서 API 키 가져오기
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

if st.button("사용 가능한 모델 목록 불러오기"):
    with st.spinner("구글 서버에 메뉴판을 요청하는 중..."):
        try:
            available_models = []
            for m in genai.list_models():
                # generateContent(텍스트/이미지 생성) 기능이 있는 모델만 걸러냅니다.
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
            
            st.success("접속 성공! 아래 목록 중에 1.5 모델이 있는지 확인해 주세요.")
            st.write(available_models)
            
        except Exception as e:
            st.error(f"API 연결 자체에 실패했습니다. 키가 잘못되었을 수 있습니다: {e}")
