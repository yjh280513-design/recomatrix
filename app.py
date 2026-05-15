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

# OTT 정보 정의 (추천 필터 및 상세 정보용)
OTT_INFO = {
    "Netflix": {"name": "넷플릭스", "url": "https://www.netflix.com/search?q="},
    "Disney Plus": {"name": "디즈니+", "url": "https://www.disneyplus.com/search?q="},
    "Wavve": {"name": "웨이브", "url": "https://www.wavve.com/search/search?searchKeyword="},
    "Watcha": {"name": "왓챠", "url": "https://watcha.com/search?query="},
    "Coupang Play": {"name": "쿠팡플레이", "url": "https://www.coupangplay.com/search?q="},
    "TVING": {"name": "티빙", "url": "https://www.tving.com/search?keyword="}
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
        # 데이터 전송 시 모든 ID를 문자열로 변환하여 구글 시트 오류 방지
        data['content_id'] = str(data.get('content_id', ''))
        data['user_id'] = str(data.get('user_id', ''))
        res = requests.post(WEB_APP_URL, data=json.dumps(data))
        return True if res.status_code == 200 else False
    except: return False

@st.cache_data(ttl=1)
def load_data():
    try:
        df = pd.read_csv(SHEET_READ_URL, dtype={'content_id': str, 'user_id': str})
        return df.dropna(subset=['user_id'])
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 2. 로그인 및 회원가입 ---
st.set_page_config(page_title="RecoMatrix Pro v5.1", layout="wide")
df = load_data()

if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    tab1, tab2 = st.tabs(["🔐 로그인", "📝 회원가입"])
    with tab1:
        u = st.text_input("아이디")
        p = st.text_input("비밀번호", type="password")
        if st.button("접속"):
            pw_hash = hashlib.sha256(str.encode(p)).hexdigest()
            user_check = df[(df['user_id'] == u) & (df['password'] == pw_hash)]
            if not user_check.empty:
                st.session_state['user_id'] = u
                st.rerun()
            else: st.error("정보가 틀렸습니다.")
    with tab2:
        nu = st.text_input("새 아이디")
        np = st.text_input("새 비밀번호", type="password")
        if st.button("가입 신청"):
            if nu and np:
                pw_h = hashlib.sha256(str.encode(np)).hexdigest()
                send_to_google({"user_id": nu, "password": pw_h, "title": "SYSTEM", "rating": 0, "poster_path": "", "media_type": "", "content_id": "0", "action": "add"})
                st.success("가입 완료!")
    st.stop()

# --- 3. 데이터 준비 (가입환영 숨기기 적용) ---
USER_ID = str(st.session_state['user_id'])
# 'SYSTEM' 혹은 '가입환영'이라는 제목을 가진 행은 리스트에서 제외합니다.
my_df = df[(df['user_id'] == USER_ID) & (~df['title'].str.contains("SYSTEM|가입환영", na=False))]
my_content_ids = my_df['content_id'].unique().tolist()

def clear_detail():
    if 'view_detail' in st.session_state: del st.session_state['view_detail']

# --- 4. 사이드바 (OTT 필터 및 분석) ---
st.sidebar.title(f"👤 {USER_ID}님")
page = st.sidebar.radio("메뉴", ["✨ 통합 추천", "📚 내 라이브러리", "🔍 검색"], on_change=clear_detail)

# OTT 선호 필터 (추천 시 활용)
st.sidebar.divider()
selected_ott = st.sidebar.multiselect("🍿 선호 OTT 선택 (추천 반영)", list(OTT_INFO.keys()), default=list(OTT_INFO.keys()))

if not my_df.empty:
    st.sidebar.subheader("📊 취향 분석")
    genres = []
    for _, row in my_df.iterrows():
        m_info = tmdb_api(f"/{row.media_type}/{row.content_id}")
        if 'genres' in m_info: genres.extend([g['name'] for g in m_info['genres']])
    if genres:
        fig = px.pie(names=list(Counter(genres).keys()), values=list(Counter(genres).values()), hole=0.4)
        fig.update_layout(height=250, margin=dict(l=0, r=0, b=0, t=0), showlegend=False)
        st.sidebar.plotly_chart(fig, use_container_width=True)

# --- 5. 상세보기 레이어 (OTT 알려주기 복구) ---
if 'view_detail' in st.session_state:
    r = st.session_state['view_detail']
    st.button("🔙 목록으로", on_click=clear_detail)
    st.divider()
    c1, c2 = st.columns([1, 2])
    with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
    with c2:
        title = r.get('title', r.get('name'))
        m_type = r.get('media_type', 'movie')
        st.title(title)
        st.write(f"📝 **줄거리**: {r.get('overview', '정보 없음')}")
        
        # OTT 정보 출력 (복구됨)
        providers = tmdb_api(f"/{m_type}/{r['id']}/watch/providers").get('results', {}).get('KR', {}).get('flatrate', [])
        st.write("### 📺 시청 가능한 OTT")
        found_ott = False
        if providers:
            for p in providers:
                p_name = p['provider_name']
                for ott_key, info in OTT_INFO.items():
                    if ott_key.lower() in p_name.lower() or info['name'] in p_name:
                        st.link_button(f"🚀 {info['name']}에서 바로보기", f"{info['url']}{title}")
                        found_ott = True
        if not found_ott: st.info("현재 이용 가능한 OTT 정보가 없습니다.")

        st.divider()
        cid = str(r['id'])
        if cid in my_content_ids:
            st.warning("✅ 이미 저장된 작품입니다.")
        else:
            score = st.slider("내 평점", 0.5, 5.0, 4.0, 0.5)
            if st.button("보관소 저장"):
                if send_to_google({"user_id": USER_ID, "title": title, "rating": score, "poster_path": r.get('poster_path',''), "media_type": m_type, "content_id": cid, "action": "add"}):
                    st.success("저장 완료!")
                    st.cache_data.clear()
                    st.rerun()
    st.stop()

# --- 6. 페이지별 메인 화면 ---
if page == "✨ 통합 추천":
    st.header("✨ 내 취향 기반 추천")
    high_rated = my_df[my_df['rating'] >= 4.0]
    if not high_rated.empty:
        if 'recom_list' not in st.session_state or st.button("🔄 새로고침"):
            all_recoms = []
            for _, row in high_rated.sample(min(len(high_rated), 5)).iterrows():
                res = tmdb_api(f"/{row.media_type}/{row.content_id}/recommendations")["results"]
                for item in res[:10]:
                    item['media_type'] = row.media_type
                    # 선택한 OTT에서 볼 수 있는 것만 필터링 (골라서 추천 기능)
                    p_info = tmdb_api(f"/{item['media_type']}/{item['id']}/watch/providers").get('results', {}).get('KR', {}).get('flatrate', [])
                    if any(any(ott.lower() in p['provider_name'].lower() for ott in selected_ott) for p in p_info):
                        all_recoms.append(item)
            st.session_state['recom_list'] = all_recoms[:12]
        
        if st.session_state['recom_list']:
            cols = st.columns(4)
            for i, r in enumerate(st.session_state['recom_list']):
                with cols[i % 4]:
                    st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                    st.write(f"**{r.get('title', r.get('name'))}**")
                    if st.button("상세보기", key=f"rec_{r['id']}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
        else: st.warning("선택하신 OTT에서 볼 수 있는 추천작을 찾지 못했습니다. 필터를 넓혀보세요!")
    else: st.info("평점 4점 이상의 작품을 먼저 등록해 주세요.")

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
                    if st.button("👁️", key=f"lv_{row.content_id}"):
                        detail = tmdb_api(f"/{row.media_type}/{row.content_id}")
                        detail['media_type'] = row.media_type
                        st.session_state['view_detail'] = detail
                        st.rerun()
                with c2:
                    with st.popover("✏️"):
                        new_r = st.slider("수정", 0.5, 5.0, float(row.rating), 0.5, key=f"ed_{row.content_id}")
                        if st.button("OK", key=f"up_{row.content_id}"):
                            if send_to_google({"user_id": USER_ID, "content_id": str(row.content_id), "rating": new_r, "action": "update"}):
                                st.success("수정됨")
                                st.cache_data.clear()
                                st.rerun()
    else: st.info("라이브러리가 비어 있습니다.")

elif page == "🔍 검색":
    st.header("🔍 작품 검색")
    q = st.text_input("영화/TV 제목 입력")
    if q:
        res = tmdb_api("/search/multi", {"query": q})["results"]
        for r in res[:8]:
            if r.get('media_type') in ['movie', 'tv']:
                c1, c2 = st.columns([1, 5])
                with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                with c2:
                    st.subheader(r.get('title', r.get('name')))
                    cid = str(r['id'])
                    if cid in my_content_ids: st.success("이미 보관함에 있습니다.")
                    else:
                        rv = st.slider("평점", 0.5, 5.0, 4.0, 0.5, key=f"s_{r['id']}")
                        if st.button("보관소 저장", key=f"b_{r['id']}"):
                            if send_to_google({"user_id": USER_ID, "title": r.get('title', r.get('name')), "rating": rv, "poster_path": r.get('poster_path',''), "media_type": r['media_type'], "content_id": cid, "action": "add"}):
                                st.success("저장 완료!")
                                st.cache_data.clear()
                                st.rerun()
                    if st.button("상세보기", key=f"d_{r['id']}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
