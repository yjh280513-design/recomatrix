import streamlit as st
import pandas as pd
import requests
import hashlib
import json
import plotly.express as px
from collections import Counter

# --- 1. 설정 및 API ---
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
# 주현님이 새로 주신 웹 앱 URL입니다!
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzFQtfn4g5tcK8k2XCX01hNUynOpbMk1usnmHwuRw1-dGa555-igK8YA_9qLKKkh9nFVg/exec"
SHEET_ID = "1HUaqiosq1k_arbsxcwlCyP_4v3A6Ymrz1R-jIcgUiss"
SHEET_READ_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

# OTT 정보 및 바로가기 검색 주소 매핑
OTT_INFO = {
    "Netflix": {"name": "넷플릭스", "url": "https://www.netflix.com/search?q="},
    "Disney Plus": {"name": "디즈니+", "url": "https://www.disneyplus.com/search?q="},
    "Wavve": {"name": "웨이브", "url": "https://www.wavve.com/search/search?searchKeyword="},
    "Watcha": {"name": "왓챠", "url": "https://watcha.com/search?query="},
    "Coupang Play": {"name": "쿠팡플레이", "url": "https://www.coupangplay.com/search?q="},
    "TVING": {"name": "티빙", "url": "https://www.tving.com/search?keyword="},
    "Laftel": {"name": "라프텔", "url": "https://laftel.net/search?q="}
}

# --- 2. 유틸리티 함수 ---
def tmdb_api(endpoint, params={}):
    params['api_key'] = API_KEY
    params['language'] = 'ko-KR'
    try:
        res = requests.get(f"{BASE_URL}{endpoint}", params=params)
        return res.json()
    except: return {}

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def send_to_google(data):
    try:
        requests.post(WEB_APP_URL, data=json.dumps(data))
        return True
    except: return False

@st.cache_data(ttl=5)
def load_data():
    try:
        df = pd.read_csv(SHEET_READ_URL)
        return df.dropna(subset=['user_id'])
    except:
        return pd.DataFrame(columns=['user_id', 'password', 'title', 'rating', 'poster_path', 'media_type', 'content_id'])

# --- 3. 앱 설정 및 로그인 ---
st.set_page_config(page_title="RecoMatrix Pro v3.5", layout="wide")
df = load_data()

if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix")
    t1, t2 = st.tabs(["로그인", "회원가입"])
    with t1:
        u = st.text_input("아이디")
        p = st.text_input("비밀번호", type="password")
        if st.button("접속"):
            user_check = df[(df['user_id'].astype(str) == u) & (df['password'].astype(str) == make_hashes(p))]
            if not user_check.empty:
                st.session_state['user_id'] = u
                st.rerun()
            else: st.error("정보가 일치하지 않습니다.")
    with t2:
        nu, np = st.text_input("새 아이디"), st.text_input("새 비번", type="password")
        if st.button("가입 완료"):
            if nu and np:
                send_to_google({"user_id": nu, "password": make_hashes(np), "title": "SYSTEM", "rating": 0, "poster_path": "", "media_type": "", "content_id": "", "action": "add"})
                st.success("가입 성공! 로그인 탭으로 이동하세요.")
    st.stop()

# --- 4. 사이드바 (메뉴 & 취향 분석) ---
USER_ID = st.session_state['user_id']
my_df = df[(df['user_id'].astype(str) == USER_ID) & (~df['title'].isin(["SYSTEM", "가입환영"]))]

st.sidebar.title(f"👤 {USER_ID}님")
page = st.sidebar.radio("메뉴 이동", ["🔍 작품 검색", "📚 내 라이브러리", "✨ 통합 추천"])
selected_otts = st.sidebar.multiselect("📺 구독 OTT 선택", [v["name"] for v in OTT_INFO.values()], default=[v["name"] for v in OTT_INFO.values()])

if not my_df.empty:
    st.sidebar.divider()
    st.sidebar.subheader("📊 장르 취향 분석")
    # 간단한 장르 통계 로직 (애니메이션 여부 포함)
    genre_data = ["애니메이션" if "애니" in str(t) else "기타" for t in my_df['title']]
    fig = px.pie(names=list(Counter(genre_data).keys()), values=list(Counter(genre_data).values()), hole=0.5)
    fig.update_layout(showlegend=False, height=220, margin=dict(t=0, b=0, l=0, r=0))
    st.sidebar.plotly_chart(fig, use_container_width=True)

if st.sidebar.button("로그아웃"):
    del st.session_state['user_id']
    st.rerun()

# --- 5. 상세 페이지 표시 로직 ---
if 'view_detail' in st.session_state:
    r = st.session_state['view_detail']
    st.button("🔙 목록으로 돌아가기", on_click=lambda: st.session_state.pop('view_detail'))
    st.divider()
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
    with c2:
        title = r.get('title', r.get('name'))
        st.title(title)
        st.write(f"📅 **개봉/방영**: {r.get('release_date', r.get('first_air_date', '정보없음'))}")
        st.write(f"📝 **줄거리**: {r.get('overview', '줄거리 정보가 없습니다.')}")
        
        # OTT 정보 확인 및 버튼 생성
        providers = tmdb_api(f"/{r.get('media_type', 'movie')}/{r['id']}/watch/providers").get('results', {}).get('KR', {}).get('flatrate', [])
        st.write("### 📺 지금 바로 보기")
        if providers:
            for p in providers:
                p_name = p['provider_name']
                # 매핑된 정보가 있으면 링크 버튼 생성
                for key, info in OTT_INFO.items():
                    if key in p_name or info["name"] in p_name:
                        st.link_button(f"🔗 {info['name']}에서 검색", f"{info['url']}{title}")
        else: st.write("현재 스트리밍 중인 OTT 정보가 없습니다.")
        
        # 보관소 저장 섹션
        st.divider()
        my_rate = st.slider("이 작품은 몇 점인가요?", 0.5, 5.0, 4.0, 0.5)
        if st.button("내 보관소에 저장"):
            send_to_google({"user_id": USER_ID, "password": "", "title": title, "rating": my_rate, "poster_path": r.get('poster_path',''), "media_type": r.get('media_type'), "content_id": r['id'], "action": "add"})
            st.success("저장되었습니다!")
            st.cache_data.clear()
    st.stop()

# --- 6. 각 페이지 메인 콘텐츠 ---

# (1) 검색 페이지
if page == "🔍 작품 검색":
    st.header("🔍 새로운 작품 찾기")
    q = st.text_input("보고 싶은 영화나 애니메이션 제목을 입력하세요")
    if q:
        res = tmdb_api("/search/multi", {"query": q})["results"]
        for r in res[:5]:
            if r.get('media_type') in ['movie', 'tv']:
                title = r.get('title', r.get('name'))
                col1, col2 = st.columns([1, 5])
                with col1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                with col2:
                    st.subheader(title)
                    if st.button("상세 정보 보기", key=f"src_{r['id']}"):
                        st.session_state['view_detail'] = r
                        st.rerun()

# (2) 내 라이브러리 및 수정
elif page == "📚 내 라이브러리":
    st.header("📚 내 라이브러리")
    if not my_df.empty:
        for idx, row in my_df.iterrows():
            with st.expander(f"{row.title} (현재 ⭐{row.rating})"):
                c1, c2 = st.columns([1, 3])
                with c1: st.image(f"https://image.tmdb.org/t/p/w500{row.poster_path}", width=150)
                with c2:
                    new_rate = st.slider("평점 수정하기", 0.5, 5.0, float(row.rating), 0.5, key=f"edit_{row.content_id}")
                    if st.button("수정 완료 및 시트 반영", key=f"btn_{row.content_id}"):
                        send_to_google({"user_id": USER_ID, "content_id": row.content_id, "rating": new_rate, "action": "update"})
                        st.success("시트에 수정 요청을 보냈습니다! 잠시 후 데이터가 반영됩니다.")
                        st.cache_data.clear()
    else: st.info("아직 평점을 매긴 작품이 없습니다.")

# (3) 통합 추천 서비스
elif page == "✨ 통합 추천":
    st.header("✨ 주현님을 위한 추천 리스트")
    high_rated = my_df[my_df['rating'] >= 4.0].tail(3)
    if not high_rated.empty:
        for _, pick in high_rated.iterrows():
            st.subheader(f"🍿 '{pick.title}'과(와) 비슷한 추천작")
            recoms = tmdb_api(f"/{pick.media_type}/{int(pick.content_id)}/recommendations")["results"]
            cols = st.columns(5)
            count = 0
            for r in recoms:
                if count >= 5: break
                # OTT 필터링 로직 (선택한 OTT에 있는 것만 노출 시도)
                with cols[count]:
                    st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path','')}")
                    st.caption(r.get('title', r.get('name')))
                    if st.button("상세보기", key=f"rec_{r['id']}"):
                        st.session_state['view_detail'] = r
                        st.rerun()
                count += 1
    else: st.warning("평점 4점 이상의 작품이 있어야 정교한 추천이 가능합니다.")
