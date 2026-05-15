import streamlit as st
import pandas as pd
import requests
import hashlib

# --- 설정 및 API ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
# 주현님의 시트 주소 (CSV 출력 모드)
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

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

# --- 데이터 로드 기능 ---
@st.cache_data(ttl=5)
def load_data():
    try:
        return pd.read_csv(SHEET_URL)
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 메인 로직 ---
df = load_data()

if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix 로그인")
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    
    with tab1:
        u = st.text_input("아이디", key="l_id")
        p = st.text_input("비밀번호", type="password", key="l_pw")
        if st.button("접속하기"):
            # 시트에서 아이디와 비번 확인
            user_row = df[(df['user_id'].astype(str) == u) & (df['password'].astype(str) == make_hashes(p))]
            if not user_row.empty:
                st.session_state['user_id'] = u
                st.rerun()
            else:
                st.error("정보가 일치하지 않습니다.")
                
    with tab2:
        st.subheader("새 계정 만들기")
        new_u = st.text_input("아이디 설정", key="r_id")
        new_p = st.text_input("비밀번호 설정", type="password", key="r_pw")
        if st.button("회원가입 완료"):
            if new_u in df['user_id'].astype(str).values:
                st.warning("이미 존재하는 아이디입니다.")
            elif new_u and new_p:
                st.info("구글 시트에 직접 기록하는 기능은 보안 설정이 필요합니다.")
                st.write("👉 **지금 바로 사용하시려면:**")
                st.write(f"1. [구글 시트]({SHEET_URL.replace('/export?format=csv', '')})를 엽니다.")
                st.write(f"2. 아래 정보를 시트 빈 줄에 직접 한 줄만 써주세요!")
                st.code(f"{new_u}, {make_hashes(new_p)}, , , , , ")
                st.success("한 줄만 쓰면 바로 로그인이 가능해집니다!")
    st.stop()

# --- 로그인 이후 화면 ---
USER_ID = st.session_state['user_id']
st.sidebar.title(f"👤 {USER_ID}님")
if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

st.title(f"✨ {USER_ID}님의 추천 리스트")
st.write("현재 구글 시트에서 데이터를 실시간으로 가져오고 있습니다.")

# 내가 매긴 평점 보기
my_data = df[df['user_id'].astype(str) == USER_ID]
if not my_data.dropna(subset=['title']).empty:
    st.dataframe(my_data[['title', 'rating', 'media_type']])
else:
    st.info("아직 등록된 평점이 없습니다. 아래에서 검색해 보세요!")

# 검색 및 추가 기능
q = st.text_input("🔍 작품 검색")
if q:
    results = tmdb_api("/search/multi", {"query": q})["results"]
    for r in results[:5]:
        if r.get('media_type') in ['movie', 'tv']:
            col1, col2 = st.columns([1, 4])
            with col1:
                st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path')}", width=100)
            with col2:
                title = r.get('title', r.get('name'))
                st.subheader(title)
                if st.button("이 작품 찜하기", key=f"btn_{r['id']}"):
                    st.success(f"'{title}' 정보가 확인되었습니다. 구글 시트에 이 제목을 써주세요!")
