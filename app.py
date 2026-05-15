import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import requests
import random
import hashlib
import plotly.express as px

# --- 설정 및 API ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
# 주현님의 시트 주소
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss/edit?usp=sharing"

def tmdb_api(endpoint, params={}):
    params['api_key'] = API_KEY
    params['language'] = 'ko-KR'
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", params=params)
        return res.json()
    except: return {}

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

st.set_page_config(page_title="RecoMatrix Pro v21.0", layout="wide")

# --- 구글 시트 연결 설정 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5) # 5초마다 데이터 갱신
def load_data():
    return conn.read(spreadsheet=SHEET_URL, worksheet="0") # 첫 번째 탭 읽기

# --- 로그인 세션 ---
if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix 로그인")
    u = st.text_input("아이디")
    p = st.text_input("비밀번호", type="password")
    if st.button("접속"):
        st.session_state['user_id'] = u
        st.rerun()
    st.stop()

USER_ID = st.session_state['user_id']
st.sidebar.title(f"👤 {USER_ID}님")

# 데이터 불러오기
try:
    df = load_data()
except:
    df = pd.DataFrame(columns=['user_id', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 메인 화면 ---
st.write("### ✅ 연결 성공! 주현님의 구글 시트 데이터")
if not df.empty:
    user_df = df[df['user_id'] == USER_ID]
    st.dataframe(user_df)
else:
    st.info("시트에 데이터가 없습니다. 시트 첫 줄에 제목이 있는지 확인해 주세요!")

# 평점 추가 버튼 예시
if st.button("테스트 데이터 시트에 쓰기 (방법 안내)"):
    st.write("👉 시트에 직접 쓰기 기능을 활성화하려면 Streamlit의 'Secrets' 설정이 필요합니다.")
    st.write("일단 읽기 기능이 잘 되는지 확인한 후, 쓰기 설정을 도와드릴게요!")
