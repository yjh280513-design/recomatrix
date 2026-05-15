import streamlit as st
import sqlite3
import pandas as pd
import requests
from collections import Counter
import random
import hashlib
import plotly.express as px

# API 및 환경 변수
API_KEY = "73c1ed10665a72ed5da4d109b49fdefe"
BASE_URL = "https://api.themoviedb.org/3"
BLACKLIST = ["오버플로우", "Overflow"]

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

# --- 데이터베이스 설정 ---
def init_db():
    conn = sqlite3.connect('recomatrix.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)')
    c.execute('''CREATE TABLE IF NOT EXISTS ratings 
                 (user_id TEXT, title TEXT, rating REAL, poster_path TEXT, media_type TEXT, content_id INTEGER)''')
    conn.commit(); conn.close()

init_db()

# --- 로그인/세션 관리 ---
if 'user_id' not in st.session_state:
    st.title("🎬 RecoMatrix Pro 로그인")
    tab1, tab2 = st.tabs(["로그인", "회원가입"])
    with tab1:
        u = st.text_input("아이디", key="l_id")
        p = st.text_input("비밀번호", type="password", key="l_pw")
        if st.button("접속하기", use_container_width=True):
            conn = sqlite3.connect('recomatrix.db')
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username=? AND password=?', (u, make_hashes(p)))
            if c.fetchone():
                st.session_state['user_id'] = u; st.rerun()
            else: st.error("정보 불일치")
            conn.close()
    with tab2:
        ur = st.text_input("새 아이디", key="r_id")
        pr = st.text_input("새 비밀번호", type="password", key="r_pw")
        if st.button("가입 완료", use_container_width=True):
            if ur and pr:
                conn = sqlite3.connect('recomatrix.db')
                conn.cursor().execute('INSERT INTO users VALUES (?,?)', (ur, make_hashes(pr)))
                conn.commit(); conn.close()
                st.success("가입 성공! 로그인해 주세요.")
    st.stop()

USER_ID = st.session_state['user_id']
if 'view' not in st.session_state: st.session_state['view'] = 'main'
if 'selected_content' not in st.session_state: st.session_state['selected_content'] = None

def get_user_ratings():
    conn = sqlite3.connect('recomatrix.db')
    df = pd.read_sql(f"SELECT * FROM ratings WHERE user_id='{USER_ID}'", conn)
    conn.close()
    return df

df = get_user_ratings()
rated_ids = df['content_id'].tolist() if not df.empty else []

# --- 사이드바 내비게이션 ---
with st.sidebar:
    st.title(f"👤 {USER_ID}님")
    menu = st.radio("메뉴", ["🎯 통합 추천", "📚 내 보관소", "⚙️ 평점 추가"])
    if st.button("🚪 로그아웃"): del st.session_state['user_id']; st.rerun()

    if menu == "🎯 통합 추천": st.session_state['view'] = 'main'; st.session_state['selected_content'] = None
    elif menu == "📚 내 보관소": st.session_state['view'] = 'library'; st.session_state['selected_content'] = None
    elif menu == "⚙️ 평점 추가": st.session_state['view'] = 'add'; st.session_state['selected_content'] = None

# --- 상세 페이지 함수 ---
def show_detail_page():
    item = st.session_state['selected_content']
    d = tmdb_api(f"/{item['type']}/{item['id']}")
    st.title(f"📖 {d.get('title', d.get('name'))}")
    c1, c2 = st.columns([1, 2])
    with c1: st.image(f"https://image.tmdb.org/t/p/w500{d.get('poster_path')}", use_container_width=True)
    with c2:
        st.subheader("줄거리"); st.write(d.get('overview', "정보 없음"))
        st.divider()
        st.subheader("🔍 연관 키워드 추천")
        k_res = tmdb_api(f"/{item['type']}/{item['id']}/keywords")
        ks = k_res.get('keywords' if item['type']=='movie' else 'results', [])
        if ks:
            sims = tmdb_api(f"/discover/{item['type']}", {"with_keywords": ks[0]['id']})["results"]
            clean = [s for s in sims if s['id'] not in rated_ids and s['id'] != item['id']][:4]
            sc = st.columns(4)
            for i, s in enumerate(clean):
                with sc[i]:
                    st.image(f"https://image.tmdb.org/t/p/w500{s.get('poster_path')}", use_container_width=True)
                    if st.button("상세보기", key=f"sim_{s['id']}"):
                        st.session_state['selected_content'] = {'id': s['id'], 'type': item['type']}; st.rerun()
    if st.button("🔙 뒤로 가기"): st.session_state['selected_content'] = None; st.rerun()

# --- 메인 로직 분기 ---
if st.session_state['selected_content']:
    show_detail_page()
else:
    if st.session_state['view'] == 'main':
        st.title("🎯 주현님의 실시간 취향 분석 리포트")
        if not df.empty:
            all_gs = []
            for _, r in df.iterrows():
                dg = tmdb_api(f"/{r['media_type']}/{r['content_id']}")
                if 'genres' in dg: all_gs.extend([g['name'] for g in dg['genres']])
            if all_gs:
                fig = px.pie(pd.DataFrame(Counter(all_gs).items(), columns=['장르', '횟수']), 
                             values='횟수', names='장르', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
            
            st.divider()
            st.subheader("🧬 취향 키워드 융합 추천")
            all_ks_ids = []; k_map = {}
            for _, r in df[df['rating'] >= 4.0].iterrows():
                k_res = tmdb_api(f"/{r['media_type']}/{r['content_id']}/keywords")
                for k in k_res.get('keywords' if r['media_type']=='movie' else 'results', []):
                    all_ks_ids.append(k['id']); k_map[k['id']] = k['name']
            
            unique_ks = list(set(all_ks_ids))
            if len(unique_ks) >= 2:
                random.shuffle(unique_ks)
                set1 = unique_ks[:2]
                st.write(f"#### 💡 현재 융합 키워드: **{k_map[set1[0]]}, {k_map[set1[1]]}**")
                recs = tmdb_api("/discover/movie", {"with_keywords": ",".join(map(str, set1))})["results"]
                recs += tmdb_api("/discover/tv", {"with_keywords": "|".join(map(str, set1))})["results"]
                final = [r for r in recs if r['id'] not in rated_ids and not any(b in r.get('title', r.get('name', '')) for b in BLACKLIST)]
                random.shuffle(final)
                cols = st.columns(4)
                for i, r in enumerate(final[:8]):
                    with cols[i % 4]:
                        st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path')}", use_container_width=True)
                        if st.button("상세 정보", key=f"main_{r['id']}"):
                            st.session_state['selected_content'] = {'id': r['id'], 'type': 'movie' if 'title' in r else 'tv'}; st.rerun()
        else: st.info("평점을 추가하면 분석이 시작됩니다!")

    elif st.session_state['view'] == 'library':
        st.title("📚 내 보관소")
        for idx, row in df.iloc[::-1].iterrows():
            c1, c2, c3 = st.columns([1, 3, 1])
            with c1: st.image(row['poster_path'], width=100)
            with c2: 
                st.subheader(row['title'])
                st.write(f"내 평점: {row['rating']} ⭐")
            with c3:
                if st.button("삭제", key=f"del_{row['content_id']}"):
                    conn = sqlite3.connect('recomatrix.db')
                    conn.cursor().execute("DELETE FROM ratings WHERE user_id=? AND content_id=?", (USER_ID, row['content_id']))
                    conn.commit(); conn.close(); st.rerun()
            st.divider()

    elif st.session_state['view'] == 'add':
        st.title("⚙️ 평점 추가")
        q = st.text_input("검색")
        if q:
            res = tmdb_api("/search/multi", {"query": q})["results"]
            for r in [x for x in res if x.get('media_type') in ['movie', 'tv']][:5]:
                c1, c2 = st.columns([1, 4])
                with c1: st.image(f"https://image.tmdb.org/t/p/w500{r.get('poster_path')}", width=100)
                with c2:
                    st.write(f"### {r.get('title', r.get('name'))}")
                    if r['id'] in rated_ids: st.warning("이미 등록됨")
                    else:
                        score = st.slider("평점", 0.5, 5.0, 4.5, 0.5, key=f"s_{r['id']}")
                        if st.button("저장", key=f"b_{r['id']}"):
                            conn = sqlite3.connect('recomatrix.db')
                            conn.cursor().execute("INSERT INTO ratings VALUES (?,?,?,?,?,?)", 
                                (USER_ID, r.get('title', r.get('name')), score, f"https://image.tmdb.org/t/p/w500{r.get('poster_path')}", r['media_type'], r['id']))
                            conn.commit(); conn.close(); st.success("저장 완료!"); st.rerun()
