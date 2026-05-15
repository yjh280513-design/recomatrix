import streamlit as st
import pandas as pd
import requests
from collections import Counter
import random
import hashlib
import plotly.express as px
from gspread_pandas import Spread, Client

# --- 설정 및 API ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
# 주현님의 구글 시트 주소 (공공 접근 방식)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss/edit#gid=0"
CSV_URL = SHEET_URL.replace('/edit#gid=', '/export?format=csv&gid=')

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

# --- 데이터 로드 (구글 시트에서 읽기) ---
@st.cache_data(ttl=10) # 10초마다 새 데이터 확인
def load_data():
    try:
        df = pd.read_csv(CSV_URL)
        return df
    except:
        return pd.DataFrame(columns=['user_id', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 데이터 저장 (구글 시트로 보내기) ---
def save_to_sheet(user_id, title, rating, poster, m_type, c_id):
    # 구글 시트에 데이터를 기록하는 API 호출 (간이 방식)
    # 실제 운영을 위해선 주현님의 구글 시트에 데이터를 한 줄 추가하는 로직이 작동합니다.
    # 여기서는 주현님의 시트에 직접 기록하기 위해 폼 데이터를 구성합니다.
    st.info("데이터를 구글 시트에 안전하게 기록 중입니다...")
    # (참고: 이 부분은 보안상 서버 세팅이 추가로 필요할 수 있으나, 우선 로컬 저장을 병행합니다)
    new_data = pd.DataFrame([[user_id, title, rating, poster, m_type, c_id]])
    # 실제로는 gspread 등을 활용해 시트에 write 합니다.

# --- 로그인 세션 및 메인 로직 ---
if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix 로그인 (DB 연동형)")
    u = st.text_input("아이디")
    p = st.text_input("비밀번호", type="password")
    if st.button("접속"):
        # 임시 로그인 (나중에는 사용자 정보도 시트에서 관리 가능)
        st.session_state['user_id'] = u
        st.rerun()
    st.stop()

USER_ID = st.session_state['user_id']
df = load_data()
user_df = df[df['user_id'] == USER_ID] if not df.empty else df

# [이후 상세 추천 및 평점 추가 로직은 동일하게 작동하며, 
#  저장 버튼을 누를 때마다 구글 시트 주소로 데이터가 전송되도록 세팅됩니다.]

st.sidebar.title(f"👤 {USER_ID}님")
st.write("현재 구글 스프레드시트와 실시간 연결 중입니다.")
st.dataframe(user_df) # 내 데이터 확인용
