import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# 한글 폰트 설정
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 데이터 로딩 함수 - 캐시 적용
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

@st.cache_data
def load_xlsx_data(file_path, sheet_name):
    return pd.read_excel(file_path, sheet_name=sheet_name, engine='openpyxl')

# EC별 학교 데이터 정보
school_info = {
    '송도고': {'EC 목표': 1.0, '개체수': 29, 'color': 'lightblue'},
    '하늘고': {'EC 목표': 2.0, '개체수': 45, 'color': 'lightgreen'},
    '아라고': {'EC 목표': 4.0, '개체수': 106, 'color': 'lightcoral'},
    '동산고': {'EC 목표': 8.0, '개체수': 58, 'color': 'lightgoldenrodyellow'}
}

# 파일 경로 정리 함수
def get_file_paths(directory, extension):
    return [str(file) for file in Path(directory).iterdir() if file.suffix == extension]

# 실험 개요 탭
def experiment_overview():
    st.title("🌱 극지식물 최적 EC 농도 연구")
    st.subheader("연구 배경 및 목적")
    st.write("""
        극지식물의 최적 EC 농도를 연구하여 다양한 환경에서의 생육 조건을 비교하고, 
        최적 EC 농도를 도출하는 것을 목표로 합니다.
    """)
    
    st.subheader("학교별 EC 조건")
    st.table(pd.DataFrame(school_info).T)
    
    total_plants = sum(school['개체수'] for school in school_info.values())
    avg_temperature = 22  # 예시 평균 온도 (변경 필요)
    avg_humidity = 60  # 예시 평균 습도 (변경 필요)
    optimal_ec = 2.0  # 예시 최적 EC (변경 필요)

    st.metric("총 개체수", total_plants)
    st.metric("평균 온도", f"{avg_temperature}°C")
    st.metric("평균 습도", f"{avg_humidity}%")
    st.metric("최적 EC", f"{optimal_ec} dS/m")

# 환경 데이터 탭
def environment_data():
    st.title("🌡️ 환경 데이터")
    
    # 학교 선택
    school = st.sidebar.selectbox("학교 선택", ['전체', '송도고', '하늘고', '아라고', '동산고'])
    
    # 데이터 로딩
    st.spinner('환경 데이터 로딩 중...')
    
    # 환경 데이터 파일 경로
    csv_files = get_file_paths('data', '.csv')
    if not csv_files:
        st.error("환경 데이터 파일을 찾을 수 없습니다.")
        return
    
    # 각 학교별 환경 데이터 로딩
    school_data = {school_name: load_data(file) for school_name, file in zip(
        ['송도고', '하늘고', '아라고', '동산고'],
        csv_files
    )}
    
    # 선택된 학교 데이터 표시
    if school != '전체':
        data = school_data.get(school, None)
        if data is None:
            st.error(f"{school}의 환경 데이터가 존재하지 않습니다.")
            return
        st.dataframe(data)

    # 2x2 서브플롯
    fig = make_subplots(rows=2, cols=2, subplot_titles=['평균 온도', '평균 습도', '평균 pH', '목표 EC vs 실측 EC'])
    
    for i, (school_name, data) in enumerate(school_data.items()):
        avg_temperature = data['temperature'].mean()
        avg_humidity = data['humidity'].mean()
        avg_ph = data['ph'].mean()
        avg_ec = data['ec'].mean()

        fig.add_trace(go.Bar(x=[school_name], y=[avg_temperature], name=f"{school_name} 온도", marker=dict(color='blue')), row=1, col=1)
        fig.add_trace(go.Bar(x=[school_name], y=[avg_humidity], name=f"{school_name} 습도", marker=dict(color='green')), row=1, col=2)
        fig.add_trace(go.Bar(x=[school_name], y=[avg_ph], name=f"{school_name} pH", marker=dict(color='red')), row=2, col=1)
        fig.add_trace(go.Bar(x=[school_name], y=[avg_ec], name=f"{school_name} 실측 EC", marker=dict(color='purple')), row=2, col=2)

    fig.update_layout(height=800, title_text="학교별 환경 데이터 비교")
    st.plotly_chart(fig)

# 생육 결과 탭
def growth_results():
    st.title("📊 생육 결과")
    
    # 데이터 로딩
    st.spinner('생육 데이터 로딩 중...')
    
    xlsx_files = get_file_paths('data', '.xlsx')
    if not xlsx_files:
        st.error("생육 데이터 파일을 찾을 수 없습니다.")
        return
    
    # XLSX 데이터 로딩
    growth_data = {}
    for school_name in school_info.keys():
        growth_data[school_name] = load_xlsx_data(xlsx_files[0], school_name)
    
    # EC별 평균 생중량 비교
    fig = make_subplots(rows=2, cols=2, subplot_titles=['평균 생중량', '평균 잎 수', '평균 지상부 길이', '개체수 비교'])
    
    for i, (school_name, data) in enumerate(growth_data.items()):
        avg_weight = data['생중량(g)'].mean()
        avg_leaf_count = data['잎 수(장)'].mean()
        avg_height = data['지상부 길이(mm)'].mean()

        fig.add_trace(go.Bar(x=[school_name], y=[avg_weight], name=f"{school_name} 생중량", marker=dict(color='orange')), row=1, col=1)
        fig.add_trace(go.Bar(x=[school_name], y=[avg_leaf_count], name=f"{school_name} 잎 수", marker=dict(color='yellow')), row=1, col=2)
        fig.add_trace(go.Bar(x=[school_name], y=[avg_height], name=f"{school_name} 지상부 길이", marker=dict(color='brown')), row=2, col=1)
        fig.add_trace(go.Bar(x=[school_name], y=[school_info[school_name]['개체수']], name=f"{school_name} 개체수", marker=dict(color='pink')), row=2, col=2)

    fig.update_layout(height=800, title_text="학교별 생육 결과 비교")
    st.plotly_chart(fig)

    # 생육 결과 다운로드 버튼
    buffer = io.BytesIO()
    growth_data['송도고'].to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    
    st.download_button(
        data=buffer,
        file_name="송도고_생육결과.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# 메인 함수
def main():
    st.set_page_config(page_title="극지식물 최적 EC 농도 연구", layout='wide')
    
    # 탭 생성
    tabs = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])
    
    with tabs[0]:
        experiment_overview()
    
    with tabs[1]:
        environment_data()
    
    with tabs[2]:
        growth_results()

if __name__ == "__main__":
    main()
