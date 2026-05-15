import streamlit as st
import pandas as pd
import requests
import random
import hashlib
import plotly.express as px

# --- 설정 및 API ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"

# 주현님의 시트 주소 (CSV 변환 주소로 자동 변경)
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

def tmdb_api(endpoint, params={}):
    params['api_key'] = API_KEY
    params['language'] = 'ko-KR'
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", params=params)
        return res.json()
    except: return {}

st.set_page_config(page_title="RecoMatrix Pro v21.0", layout="wide")

# --- 구글 시트 데이터 로드 ---
@st.cache_data(ttl=5)
def load_data():
    try:
        # 구글 시트를 CSV 형태로 직접 읽어옵니다. (설치 오류 없음!)
        return pd.read_csv(SHEET_URL)
    except Exception as e:
        st.error(f"시트를 읽어오지 못했습니다: {e}")
        return pd.DataFrame(columns=['user_id', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 로그인 세션 ---
if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix 로그인")
    u = st.text_input("아이디")
    if st.button("접속"):
        st.session_state['user_id'] = u
        st.rerun()
    st.stop()

USER_ID = st.session_state['user_id']
df = load_data()

# --- 메인 화면 ---
st.title(f"🚀 {USER_ID}님의 대시보드")
st.write("구글 스프레드시트와 직접 연결된 상태입니다.")

if not df.empty:
    user_df = df[df['user_id'].astype(str) == str(USER_ID)]
    if not user_df.empty:
        st.success(f"현재 {len(user_df)}개의 평점 데이터를 불러왔습니다.")
        st.dataframe(user_df, use_container_width=True)
    else:
        st.warning(f"'{USER_ID}' 계정으로 등록된 데이터가 시트에 없습니다.")
else:
    st.info("시트가 비어있거나 연결이 원활하지 않습니다. 구글 시트의 [공유] 설정이 [편집자]로 되어 있는지 확인해 주세요!")
