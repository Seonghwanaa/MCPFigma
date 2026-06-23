import os
import pandas as pd
import pymysql
import streamlit as st
import plotly.express as px
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="MariaDB Dashboard", layout="wide")
st.title("MariaDB 대시보드")


@st.cache_resource
def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        db=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def run_query(sql: str) -> pd.DataFrame:
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(sql)
        return pd.DataFrame(cursor.fetchall())


# --- 사이드바: DB 연결 상태 확인 ---
with st.sidebar:
    st.header("연결 정보")
    st.code(
        f"host : {os.getenv('DB_HOST')}\n"
        f"port : {os.getenv('DB_PORT')}\n"
        f"db   : {os.getenv('DB_NAME')}\n"
        f"user : {os.getenv('DB_USER')}",
        language="ini",
    )

    if st.button("연결 테스트"):
        try:
            get_connection()
            st.success("연결 성공!")
        except Exception as e:
            st.error(f"연결 실패: {e}")

# --- 테이블 목록 조회 ---
try:
    tables_df = run_query("SHOW TABLES")
    table_list = tables_df.iloc[:, 0].tolist()
except Exception as e:
    st.error(f"DB 연결 오류: {e}\n\n`.env` 파일의 연결 정보를 확인해 주세요.")
    st.stop()

with st.sidebar:
    st.divider()
    selected_table = st.selectbox("테이블 선택", table_list)

    row_limit = st.number_input("최대 행 수", min_value=10, max_value=10000, value=500, step=100)

    custom_query = st.text_area("직접 쿼리 입력 (선택)", placeholder=f"SELECT * FROM {selected_table} WHERE ...")

# --- 데이터 로드 ---
query = custom_query.strip() if custom_query.strip() else f"SELECT * FROM `{selected_table}` LIMIT {row_limit}"

try:
    df = run_query(query)
except Exception as e:
    st.error(f"쿼리 오류: {e}")
    st.stop()

st.subheader(f"테이블: `{selected_table}`  — {len(df):,}행 × {len(df.columns)}열")

# --- 탭 구성 ---
tab_table, tab_chart, tab_summary = st.tabs(["데이터 테이블", "차트", "요약 통계"])

with tab_table:
    st.dataframe(df, use_container_width=True, height=450)

with tab_chart:
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    categorical_cols = df.select_dtypes(exclude="number").columns.tolist()

    if not numeric_cols:
        st.info("숫자형 컬럼이 없어 차트를 그릴 수 없습니다.")
    else:
        col1, col2, col3 = st.columns(3)
        chart_type = col1.selectbox("차트 유형", ["막대 차트", "라인 차트", "파이 차트", "산점도", "히스토그램"])
        y_col = col2.selectbox("Y축 (수치)", numeric_cols)
        x_col = col3.selectbox(
            "X축 (범주/수치)",
            categorical_cols + numeric_cols,
            index=0 if categorical_cols else 0,
        )

        plot_df = df[[x_col, y_col]].dropna()

        if chart_type == "막대 차트":
            fig = px.bar(plot_df, x=x_col, y=y_col, title=f"{x_col} vs {y_col}")
        elif chart_type == "라인 차트":
            fig = px.line(plot_df, x=x_col, y=y_col, title=f"{x_col} vs {y_col}")
        elif chart_type == "파이 차트":
            agg = plot_df.groupby(x_col)[y_col].sum().reset_index()
            fig = px.pie(agg, names=x_col, values=y_col, title=f"{y_col} 비율")
        elif chart_type == "산점도":
            fig = px.scatter(plot_df, x=x_col, y=y_col, title=f"{x_col} vs {y_col}")
        else:  # 히스토그램
            fig = px.histogram(df, x=y_col, title=f"{y_col} 분포")

        st.plotly_chart(fig, use_container_width=True)

with tab_summary:
    st.dataframe(df.describe(include="all").T, use_container_width=True)
