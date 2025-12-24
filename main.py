import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import unicodedata
from pathlib import Path
import io

# 페이지 설정
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    page_icon="🌱",
    layout="wide"
)

# 한글 폰트 설정
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# 학교별 EC 조건
SCHOOL_INFO = {
    "송도고": {"ec": 1.0, "color": "#4A90E2"},
    "하늘고": {"ec": 2.0, "color": "#50C878"},
    "아라고": {"ec": 4.0, "color": "#F39C12"},
    "동산고": {"ec": 8.0, "color": "#E74C3C"}
}

@st.cache_data
def normalize_filename(filename):
    """파일명 정규화 (NFC/NFD 양방향)"""
    nfc = unicodedata.normalize("NFC", filename)
    nfd = unicodedata.normalize("NFD", filename)
    return nfc, nfd

@st.cache_data
def find_file_safe(directory, pattern):
    """한글 파일명 안전 검색"""
    data_path = Path(directory)
    if not data_path.exists():
        return []
    
    found_files = []
    for file_path in data_path.iterdir():
        if file_path.is_file():
            nfc_name, nfd_name = normalize_filename(file_path.name)
            nfc_pattern, nfd_pattern = normalize_filename(pattern)
            
            if nfc_pattern in nfc_name or nfd_pattern in nfd_name or \
               nfc_pattern in nfd_name or nfd_pattern in nfc_name:
                found_files.append(file_path)
    
    return found_files

@st.cache_data
def load_environment_data():
    """환경 데이터 로딩"""
    data_dict = {}
    
    for school in SCHOOL_INFO.keys():
        files = find_file_safe("data", f"{school}_환경데이터.csv")
        
        if not files:
            st.warning(f"⚠️ {school} 환경데이터 파일을 찾을 수 없습니다.")
            continue
        
        try:
            df = pd.read_csv(files[0], encoding='utf-8-sig')
            data_dict[school] = df
        except Exception as e:
            st.error(f"❌ {school} 환경데이터 로딩 실패: {e}")
    
    return data_dict

@st.cache_data
def load_growth_data():
    """생육 결과 데이터 로딩"""
    files = find_file_safe("data", "4개교_생육결과데이터.xlsx")
    
    if not files:
        st.error("❌ 생육 결과 데이터 파일을 찾을 수 없습니다.")
        return {}
    
    try:
        excel_file = pd.ExcelFile(files[0])
        data_dict = {}
        
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
            
            # 시트명에서 학교명 추출
            for school in SCHOOL_INFO.keys():
                if school in sheet_name:
                    data_dict[school] = df
                    break
        
        return data_dict
    except Exception as e:
        st.error(f"❌ 생육 결과 데이터 로딩 실패: {e}")
        return {}

def create_metric_cards(env_data, growth_data):
    """주요 지표 카드"""
    col1, col2, col3, col4 = st.columns(4)
    
    # 총 개체수
    total_samples = sum(len(df) for df in growth_data.values())
    col1.metric("🌱 총 개체수", f"{total_samples}개")
    
    # 평균 온도
    if env_data:
        avg_temp = sum(df['temperature'].mean() for df in env_data.values()) / len(env_data)
        col2.metric("🌡️ 평균 온도", f"{avg_temp:.1f}°C")
    
    # 평균 습도
    if env_data:
        avg_humidity = sum(df['humidity'].mean() for df in env_data.values()) / len(env_data)
        col3.metric("💧 평균 습도", f"{avg_humidity:.1f}%")
    
    # 최적 EC
    col4.metric("⭐ 최적 EC", "2.0 dS/m", help="하늘고 실험 결과 기준")

def plot_environment_comparison(env_data):
    """환경 데이터 비교 그래프"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    schools = list(env_data.keys())
    colors = [SCHOOL_INFO[school]["color"] for school in schools]
    
    # 평균 온도
    temps = [env_data[school]['temperature'].mean() for school in schools]
    fig.add_trace(
        go.Bar(x=schools, y=temps, marker_color=colors, name="온도", showlegend=False),
        row=1, col=1
    )
    
    # 평균 습도
    humidities = [env_data[school]['humidity'].mean() for school in schools]
    fig.add_trace(
        go.Bar(x=schools, y=humidities, marker_color=colors, name="습도", showlegend=False),
        row=1, col=2
    )
    
    # 평균 pH
    phs = [env_data[school]['ph'].mean() for school in schools]
    fig.add_trace(
        go.Bar(x=schools, y=phs, marker_color=colors, name="pH", showlegend=False),
        row=2, col=1
    )
    
    # EC 비교
    target_ecs = [SCHOOL_INFO[school]["ec"] for school in schools]
    actual_ecs = [env_data[school]['ec'].mean() for school in schools]
    
    fig.add_trace(
        go.Bar(x=schools, y=target_ecs, name="목표 EC", marker_color="lightgray"),
        row=2, col=2
    )
    fig.add_trace(
        go.Bar(x=schools, y=actual_ecs, name="실측 EC", marker_color=colors),
        row=2, col=2
    )
    
    # 레이아웃
    fig.update_yaxes(title_text="°C", row=1, col=1)
    fig.update_yaxes(title_text="%", row=1, col=2)
    fig.update_yaxes(title_text="pH", row=2, col=1)
    fig.update_yaxes(title_text="dS/m", row=2, col=2)
    
    fig.update_layout(
        height=600,
        showlegend=True,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
    )
    
    return fig

def plot_timeseries(school, env_data):
    """시계열 그래프"""
    if school not in env_data:
        st.warning(f"⚠️ {school} 데이터가 없습니다.")
        return
    
    df = env_data[school]
    
    # 온도 변화
    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=df.index, y=df['temperature'],
        mode='lines',
        name='온도',
        line=dict(color=SCHOOL_INFO[school]["color"], width=2)
    ))
    fig1.update_layout(
        title=f"{school} 온도 변화",
        xaxis_title="측정 시점",
        yaxis_title="온도 (°C)",
        height=300,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig1, use_container_width=True)
    
    # 습도 변화
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=df.index, y=df['humidity'],
        mode='lines',
        name='습도',
        line=dict(color=SCHOOL_INFO[school]["color"], width=2)
    ))
    fig2.update_layout(
        title=f"{school} 습도 변화",
        xaxis_title="측정 시점",
        yaxis_title="습도 (%)",
        height=300,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig2, use_container_width=True)
    
    # EC 변화 (목표선 포함)
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=df.index, y=df['ec'],
        mode='lines',
        name='실측 EC',
        line=dict(color=SCHOOL_INFO[school]["color"], width=2)
    ))
    fig3.add_hline(
        y=SCHOOL_INFO[school]["ec"],
        line_dash="dash",
        line_color="red",
        annotation_text=f"목표 EC: {SCHOOL_INFO[school]['ec']} dS/m"
    )
    fig3.update_layout(
        title=f"{school} EC 변화",
        xaxis_title="측정 시점",
        yaxis_title="EC (dS/m)",
        height=300,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig3, use_container_width=True)

def plot_growth_comparison(growth_data):
    """생육 결과 비교 그래프"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 생중량 ⭐", "평균 잎 수", "평균 지상부 길이", "개체수 비교"),
        vertical_spacing=0.15,
        horizontal_spacing=0.1
    )
    
    schools = list(growth_data.keys())
    colors = [SCHOOL_INFO[school]["color"] for school in schools]
    
    # 평균 생중량
    weights = [growth_data[school]['생중량(g)'].mean() for school in schools]
    fig.add_trace(
        go.Bar(x=schools, y=weights, marker_color=colors, name="생중량", showlegend=False),
        row=1, col=1
    )
    
    # 평균 잎 수
    leaves = [growth_data[school]['잎 수(장)'].mean() for school in schools]
    fig.add_trace(
        go.Bar(x=schools, y=leaves, marker_color=colors, name="잎 수", showlegend=False),
        row=1, col=2
    )
    
    # 평균 지상부 길이
    heights = [growth_data[school]['지상부 길이(mm)'].mean() for school in schools]
    fig.add_trace(
        go.Bar(x=schools, y=heights, marker_color=colors, name="지상부 길이", showlegend=False),
        row=2, col=1
    )
    
    # 개체수
    counts = [len(growth_data[school]) for school in schools]
    fig.add_trace(
        go.Bar(x=schools, y=counts, marker_color=colors, name="개체수", showlegend=False),
        row=2, col=2
    )
    
    # 레이아웃
    fig.update_yaxes(title_text="g", row=1, col=1)
    fig.update_yaxes(title_text="장", row=1, col=2)
    fig.update_yaxes(title_text="mm", row=2, col=1)
    fig.update_yaxes(title_text="개", row=2, col=2)
    
    fig.update_layout(
        height=600,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif", size=12)
    )
    
    return fig

def plot_weight_distribution(growth_data):
    """생중량 분포 박스플롯"""
    fig = go.Figure()
    
    for school in growth_data.keys():
        fig.add_trace(go.Box(
            y=growth_data[school]['생중량(g)'],
            name=school,
            marker_color=SCHOOL_INFO[school]["color"]
        ))
    
    fig.update_layout(
        title="학교별 생중량 분포",
        yaxis_title="생중량 (g)",
        height=400,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    
    return fig

def plot_correlations(growth_data):
    """상관관계 산점도"""
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("잎 수 vs 생중량", "지상부 길이 vs 생중량"),
        horizontal_spacing=0.12
    )
    
    for school in growth_data.keys():
        df = growth_data[school]
        
        # 잎 수 vs 생중량
        fig.add_trace(
            go.Scatter(
                x=df['잎 수(장)'],
                y=df['생중량(g)'],
                mode='markers',
                name=school,
                marker=dict(color=SCHOOL_INFO[school]["color"], size=8)
            ),
            row=1, col=1
        )
        
        # 지상부 길이 vs 생중량
        fig.add_trace(
            go.Scatter(
                x=df['지상부 길이(mm)'],
                y=df['생중량(g)'],
                mode='markers',
                name=school,
                marker=dict(color=SCHOOL_INFO[school]["color"], size=8),
                showlegend=False
            ),
            row=1, col=2
        )
    
    fig.update_xaxes(title_text="잎 수 (장)", row=1, col=1)
    fig.update_xaxes(title_text="지상부 길이 (mm)", row=1, col=2)
    fig.update_yaxes(title_text="생중량 (g)", row=1, col=1)
    fig.update_yaxes(title_text="생중량 (g)", row=1, col=2)
    
    fig.update_layout(
        height=400,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    
    return fig

def main():
    """메인 앱"""
    st.title("🌱 극지식물 최적 EC 농도 연구")
    
    # 데이터 로딩
    with st.spinner("📂 데이터 로딩 중..."):
        env_data = load_environment_data()
        growth_data = load_growth_data()
    
    if not env_data or not growth_data:
        st.error("❌ 데이터 파일을 찾을 수 없습니다. data 폴더를 확인해주세요.")
        return
    
    # 사이드바
    st.sidebar.title("🔍 학교 선택")
    selected_school = st.sidebar.selectbox(
        "분석할 학교를 선택하세요",
        ["전체"] + list(SCHOOL_INFO.keys())
    )
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])
    
    # Tab 1: 실험 개요
    with tab1:
        st.header("연구 배경 및 목적")
        st.markdown("""
        ### 🎯 연구 목적
        극지식물(남극좀새풀)의 최적 EC(전기전도도) 농도를 찾기 위한 실험입니다.
        4개 학교에서 서로 다른 EC 조건으로 식물을 재배하여 생육 결과를 비교 분석합니다.
        
        ### 🔬 실험 설계
        - **실험 기간**: 장기 모니터링
        - **측정 항목**: 온도, 습도, pH, EC, 생중량, 잎 수, 지상부/지하부 길이
        - **비교 분석**: EC 농도별 생육 차이 규명
        """)
        
        st.subheader("🏫 학교별 EC 조건")
        
        # EC 조건 표
        ec_df = pd.DataFrame([
            {
                "학교명": school,
                "EC 목표 (dS/m)": info["ec"],
                "개체수": len(growth_data[school]) if school in growth_data else 0,
                "색상": info["color"]
            }
            for school, info in SCHOOL_INFO.items()
        ])
        
        st.dataframe(
            ec_df.style.background_gradient(subset=['EC 목표 (dS/m)'], cmap='YlOrRd'),
            hide_index=True,
            use_container_width=True
        )
        
        st.divider()
        
        st.subheader("📌 주요 지표")
        create_metric_cards(env_data, growth_data)
    
    # Tab 2: 환경 데이터
    with tab2:
        st.header("🌡️ 환경 데이터 분석")
        
        if selected_school == "전체":
            st.subheader("학교별 환경 평균 비교")
            fig = plot_environment_comparison(env_data)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.subheader(f"{selected_school} 환경 데이터 시계열")
            plot_timeseries(selected_school, env_data)
        
        # 원본 데이터
        with st.expander("📋 환경 데이터 원본 보기"):
            if selected_school == "전체":
                for school, df in env_data.items():
                    st.write(f"**{school}**")
                    st.dataframe(df, use_container_width=True)
                    
                    # CSV 다운로드
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📥 {school} CSV 다운로드",
                        data=csv,
                        file_name=f"{school}_환경데이터.csv",
                        mime="text/csv",
                        key=f"csv_{school}"
                    )
            else:
                if selected_school in env_data:
                    df = env_data[selected_school]
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label=f"📥 {selected_school} CSV 다운로드",
                        data=csv,
                        file_name=f"{selected_school}_환경데이터.csv",
                        mime="text/csv"
                    )
    
    # Tab 3: 생육 결과
    with tab3:
        st.header("📊 생육 결과 분석")
        
        # 핵심 결과 카드
        st.subheader("🥇 핵심 결과: EC별 평균 생중량")
        
        cols = st.columns(len(growth_data))
        max_weight = 0
        max_school = ""
        
        for idx, (school, df) in enumerate(growth_data.items()):
            avg_weight = df['생중량(g)'].mean()
            if avg_weight > max_weight:
                max_weight = avg_weight
                max_school = school
            
            with cols[idx]:
                st.metric(
                    label=f"{school} (EC {SCHOOL_INFO[school]['ec']})",
                    value=f"{avg_weight:.2f}g"
                )
        
        st.success(f"⭐ **최적 EC 농도**: {max_school} (EC {SCHOOL_INFO[max_school]['ec']} dS/m) - 평균 생중량 {max_weight:.2f}g")
        
        st.divider()
        
        # EC별 생육 비교
        st.subheader("📈 EC별 생육 비교")
        fig = plot_growth_comparison(growth_data)
        st.plotly_chart(fig, use_container_width=True)
        
        # 생중량 분포
        st.subheader("📊 학교별 생중량 분포")
        fig_box = plot_weight_distribution(growth_data)
        st.plotly_chart(fig_box, use_container_width=True)
        
        # 상관관계 분석
        st.subheader("🔗 상관관계 분석")
        fig_corr = plot_correlations(growth_data)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        # 원본 데이터
        with st.expander("📋 생육 데이터 원본 보기"):
            if selected_school == "전체":
                for school, df in growth_data.items():
                    st.write(f"**{school}** (개체수: {len(df)}개)")
                    st.dataframe(df, use_container_width=True)
            else:
                if selected_school in growth_data:
                    df = growth_data[selected_school]
                    st.dataframe(df, use_container_width=True)
            
            # XLSX 다운로드 (전체)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                for school, df in growth_data.items():
                    df.to_excel(writer, sheet_name=school, index=False)
            buffer.seek(0)
            
            st.download_button(
                label="📥 전체 생육 데이터 XLSX 다운로드",
                data=buffer,
                file_name="4개교_생육결과데이터.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
