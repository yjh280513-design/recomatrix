import streamlit as st
import pandas as pd
import requests
import hashlib
import json
import plotly.express as px
from collections import Counter
import random
import time

# --- 1. 설정 및 API ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbTeG_23IIXkpwV_aYFvIyrVbLcQYMtyPG4bWcfl-PkFemL66uscFaLdrTWZYDxABjjmw/exec"
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# 장르 ID 매핑 (더 세밀한 분석을 위함)
GENRE_MAP = {
    28: "액션", 12: "모험", 16: "애니메이션", 35: "코미디", 80: "범죄", 99: "다큐", 
    18: "드라마", 10751: "가족", 14: "판타지", 36: "역사", 27: "공포", 10402: "음악", 
    9648: "미스터리", 10749: "로맨스", 878: "SF", 10770: "TV 영화", 53: "스릴러", 
    10752: "전쟁", 37: "서부", 10759: "액션&모험", 10762: "키즈", 10765: "SF&판타지"
}

def tmdb_api(endpoint, params={}):
    params['api_key'] = API_KEY
    params['language'] = 'ko-KR'
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", params=params)
        return res.json()
    except: return {}

def send_to_google(data):
    try:
        res = requests.post(WEB_APP_URL, data=json.dumps(data))
        return True if res.status_code == 200 else False
    except: return False

@st.cache_data(ttl=1) # 저장/수정 즉시 반영을 위해 캐시 시간 단축
def load_data():
    try:
        # 모든 ID 컬럼을 문자열로 읽어 데이터 매칭 오류 원천 차단
        df = pd.read_csv(SHEET_READ_URL, dtype={'content_id': str, 'user_id': str, 'rating': float})
        return df.dropna(subset=['user_id'])
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 2. 앱 설정 및 로그인/회원가입 (복구 완료) ---
st.set_page_config(page_title="RecoMatrix Pro v5.0", layout="wide")
df = load_data()

if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    tab1, tab2 = st.tabs(["🔐 로그인", "📝 회원가입"])
    
    with tab1:
        u = st.text_input("아이디", key="login_u")
        p = st.text_input("비밀번호", type="password", key="login_p")
        if st.button("접속"):
            pw_hash = hashlib.sha256(str.encode(p)).hexdigest()
            user_check = df[(df['user_id'] == u) & (df['password'] == pw_hash)]
            if not user_check.empty:
                st.session_state['user_id'] = u
                st.rerun()
            else: st.error("로그인 정보가 틀렸습니다.")
            
    with tab2:
        nu = st.text_input("새 아이디", key="join_u")
        np = st.text_input("새 비밀번호", type="password", key="join_p")
        if st.button("가입 신청"):
            if nu and np:
                pw_h = hashlib.sha256(str.encode(np)).hexdigest()
                send_to_google({"user_id": nu, "password": pw_h, "title": "SYSTEM", "rating": 0, "poster_path": "", "media_type": "", "content_id": "0", "action": "add"})
                st.success("가입 완료! 로그인 탭에서 접속하세요.")
                st.cache_data.clear()
    st.stop()

# --- 3. 데이터 및 세션 관리 ---
USER_ID = str(st.session_state['user_id'])
my_df = df[(df['user_id'] == USER_ID) & (df['title'] != "SYSTEM")]
my_content_ids = my_df['content_id'].tolist()

def clear_detail():
    if 'view_detail' in st.session_state: del st.session_state['view_detail']

# --- 4. 사이드바 (장르 취향 세분화 분석) ---
page = st.sidebar.radio("메뉴 이동", ["✨ 통합 추천", "📚 내 라이브러리", "🔍 작품 검색"], on_change=clear_detail)

if not my_df.empty:
    st.sidebar.divider()
    st.sidebar.subheader("📊 내 취향 상세 분석")
    
    # 세분화된 장르 추출 로직
    genres_collected = []
    for _, row in my_df.iterrows():
        # TMDB에서 장르 ID 가져오기 (성능을 위해 캐싱 권장되나 여기서는 직접 호출)
        m_info = tmdb_api(f"/{row.media_type}/{row.content_id}")
        if 'genres' in m_info:
            genres_collected.extend([g['name'] for g in m_info['genres']])
    
    if genres_collected:
        counts = Counter(genres_collected)
        fig = px.pie(names=list(counts.keys()), values=list(counts.values()), hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(showlegend=True, height=350, legend=dict(orientation="h", yanchor="bottom", y=-0.5))
        st.sidebar.plotly_chart(fig, use_container_width=True)
    else:
        st.sidebar.info("데이터 분석 중...")

if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

# --- 5. 상세보기 섹션 ---
if 'view_detail' in st.session_state:
    r = st.session_state['view_detail']
    st.button("🔙 목록으로", on_click=clear_detail)
    st.divider()
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
    with c2:
        title = r.get('title', r.get('name'))
        m_type = r.get('media_type', 'movie')
        st.title(title)
        st.write(f"📝 **줄거리**: {r.get('overview', '정보 없음')}")
        
        # 중복 저장 방지 및 저장 (수정 완료)
        curr_id = str(r['id'])
        if curr_id in my_content_ids:
            st.warning("✅ 이미 보관함에 있습니다.")
        else:
            score = st.slider("내 평점", 0.5, 5.0, 4.0, 0.5, key="det_slider")
            if st.button("보관소에 저장"):
                if send_to_google({"user_id": USER_ID, "title": title, "rating": score, "poster_path": r.get('poster_path',''), "media_type": m_type, "content_id": curr_id, "action": "add"}):
                    st.success("저장 성공!")
                    st.cache_data.clear()
                    st.rerun()

        # 비슷한 작품 추천
        st.divider()
        st.subheader("🍿 비슷한 작품 추천")
        recoms = tmdb_api(f"/{m_type}/{r['id']}/recommendations")["results"]
        if recoms:
            rows = st.columns(4)
            for i, rec in enumerate(recoms[:4]):
                with rows[i]:
                    st.image(f"https://image.tmdb.org/t/p/w500{rec.get('poster_path','')}")
                    if st.button("보기", key=f"rec_{rec['id']}"):
                        rec['media_type'] = m_type
                        st.session_state['view_detail'] = rec
                        st.rerun()
    st.stop()

# --- 6. 메인 페이지 ---
if page == "✨ 통합 추천":
    st.header("✨ 내 취향 통합 추천")
    high_rated = my_df[my_df['rating'] >= 4.0]
    if not high_rated.empty:
        if 'recom_list' not in st.session_state or st.button("🔄 새로고침"):
            all_recoms = []
            for _, row in high_rated.iterrows():
                res = tmdb_api(f"/{row.media_type}/{row.content_id}/recommendations")["results"]
                for item in res[:5]:
                    item['media_type'] = row.media_type
                    all_recoms.append(item)
            random.shuffle(all_recoms)
            st.session_state['recom_list'] = all_recoms[:12]

        cols = st.columns(4)
        for i, r in enumerate(st.session_state['recom_list']):
            with cols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                st.write(f"**{r.get('title', r.get('name'))}**")
                if st.button("상세보기", key=f"tr_{r['id']}_{i}"):
                    st.session_state['view_detail'] = r
                    st.rerun()
    else: st.info("평점 4점 이상 작품을 등록해 주세요!")

elif page == "📚 내 라이브러리":
    st.header("📚 내 라이브러리")
    if not my_df.empty:
        lcols = st.columns(4)
        for i, row in enumerate(my_df.itertuples()):
            with lcols[i % 4]:
                st.image(f"https://image.tmdb.org/t/p/w500{row.poster_path}")
                st.write(f"**{row.title}** (⭐{row.rating})")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("👁️", key=f"lib_v_{row.content_id}"):
                        detail = tmdb_api(f"/{row.media_type}/{row.content_id}")
                        detail['media_type'] = row.media_type
                        st.session_state['view_detail'] = detail
                        st.rerun()
                with c2:
                    with st.popover("✏️"):
                        new_r = st.slider("평점 수정", 0.5, 5.0, float(row.rating), 0.5, key=f"ed_{row.content_id}")
                        if st.button("변경", key=f"ok_{row.content_id}"):
                            if send_to_google({"user_id": USER_ID, "content_id": str(row.content_id), "rating": new_r, "action": "update"}):
                                st.success("변경됨")
                                st.cache_data.clear()
                                st.rerun()

elif page == "🔍 작품 검색":
    st.header("🔍 작품 검색")
    q = st.text_input("검색")
    if q:
        res = tmdb_api("/search/multi", {"query": q})["results"]
        for i, r in enumerate(res[:8]):
            if r.get('media_type') in ['movie', 'tv']:
                title = r.get('title', r.get('name'))
                c1, c2 = st.columns([1, 5])
                with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                with c2:
                    st.subheader(title)
                    cid = str(r['id'])
                    if cid in my_content_ids:
                        st.success("✅ 이미 보관함에 있습니다.")
                    else:
                        r_val = st.slider("평점", 0.5, 5.0, 4.0, 0.5, key=f"sr_{r['id']}")
                        if st.button("보관소 저장", key=f"sv_{r['id']}"):
                            if send_to_google({"user_id": USER_ID, "title": title, "rating": r_val, "poster_path": r.get('poster_path',''), "media_type": r['media_type'], "content_id": cid, "action": "add"}):
                                st.success("저장 완료!")
                                st.cache_data.clear()
                                st.rerun()
                    if st.button("상세 정보", key=f"dt_{r['id']}_{i}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
