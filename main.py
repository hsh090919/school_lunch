
import re
from itertools import combinations

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# 1. 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="급식 규칙 찾기",
    page_icon="🍱",
    layout="wide"
)

st.title("🍱 급식 규칙 찾기")

st.markdown(
    "송탄고 중식 184일의 식단을 분석하여 "
    "어떤 메뉴들이 함께 등장하는지 연관 규칙을 찾아봅니다."
)

DATA_URL = (
    "https://raw.githubusercontent.com/it-teacher-go/"
    "data-share-/main/songtan_meals_184.csv"
)


# --------------------------------------------------
# 2. 데이터 불러오기
# --------------------------------------------------

@st.cache_data
def load_data():

    df = pd.read_csv(DATA_URL, encoding="utf-8")

    required_columns = ["날짜", "식사", "메뉴"]

    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"CSV에 '{col}' 열이 없습니다.")

    df = df[required_columns].copy()
    df = df.dropna(subset=["메뉴"])

    return df


# --------------------------------------------------
# 3. 메뉴 전처리
# --------------------------------------------------

def clean_menu(menu):

    # 괄호와 괄호 안의 내용 제거
    menu = str(menu)
    menu = re.sub(r"\([^)]*\)", "", menu)

    return menu.strip()


def make_transactions(df):

    transactions = []

    for menu_text in df["메뉴"]:

        menus = str(menu_text).split("|")

        cleaned = set()

        for menu in menus:

            menu = clean_menu(menu)

            if menu:
                cleaned.add(menu)

        transactions.append(cleaned)

    return transactions


# --------------------------------------------------
# 4. 연관 규칙 분석
# --------------------------------------------------

def find_association_rules(transactions):

    total_days = len(transactions)

    # 메뉴별 등장 일수
    menu_counts = {}

    for basket in transactions:

        for menu in basket:

            menu_counts[menu] = (
                menu_counts.get(menu, 0) + 1
            )

    # 메뉴 쌍별 동시 등장 일수
    pair_counts = {}

    for basket in transactions:

        for menu_a, menu_b in combinations(
            sorted(basket), 2
        ):

            pair = (menu_a, menu_b)

            pair_counts[pair] = (
                pair_counts.get(pair, 0) + 1
            )

    # 연관 규칙 생성
    rules = []

    for (menu_a, menu_b), count in pair_counts.items():

        support = count / total_days

        support_a = menu_counts[menu_a] / total_days
        support_b = menu_counts[menu_b] / total_days

        # A → B
        confidence_ab = count / menu_counts[menu_a]
        lift_ab = confidence_ab / support_b

        rules.append({
            "조건": menu_a,
            "결과": menu_b,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ab,
            "향상도": lift_ab
        })

        # B → A
        confidence_ba = count / menu_counts[menu_b]
        lift_ba = confidence_ba / support_a

        rules.append({
            "조건": menu_b,
            "결과": menu_a,
            "동시": count,
            "지지도": support,
            "신뢰도": confidence_ba,
            "향상도": lift_ba
        })

    rules_df = pd.DataFrame(rules)

    return rules_df, menu_counts, pair_counts


# --------------------------------------------------
# 5. 데이터 분석 실행
# --------------------------------------------------

try:

    df = load_data()

    transactions = make_transactions(df)

    rules_df, menu_counts, pair_counts = (
        find_association_rules(transactions)
    )

except Exception as e:

    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()


total_days = len(transactions)
total_menus = len(menu_counts)
total_pairs = len(pair_counts)


# --------------------------------------------------
# 6. 데이터 요약
# --------------------------------------------------

st.subheader("📊 데이터 분석 요약")

col1, col2, col3 = st.columns(3)

col1.metric("급식 일수", f"{total_days}일")
col2.metric("메뉴 종류 수", f"{total_menus}개")
col3.metric("함께 나온 메뉴 쌍", f"{total_pairs:,}쌍")

st.divider()


# --------------------------------------------------
# 7. 연관 규칙 탐색
# --------------------------------------------------

st.subheader("🔍 연관 규칙 탐색")

col1, col2 = st.columns([2, 1])

with col1:

    selected_menu = st.selectbox(
        "좁혀 보기 - 메뉴 선택",
        ["전체 메뉴"] + sorted(menu_counts.keys()),
        key="rule_menu"
    )

with col2:

    sort_option = st.selectbox(
        "정렬 기준",
        ["향상도 순", "신뢰도 순", "동시 순"],
        key="rule_sort"
    )


# --------------------------------------------------
# 8. 최소 동시 일수 슬라이더
# --------------------------------------------------

min_days = st.slider(
    "최소 동시 일수",
    min_value=1,
    max_value=10,
    value=1,
    step=1,
    help="선택한 일수보다 적게 함께 나온 메뉴 규칙은 제외합니다."
)


# --------------------------------------------------
# 9. 메뉴 및 동시 일수 필터링
# --------------------------------------------------

filtered_df = rules_df.copy()

# 선택 메뉴로 좁히기
if selected_menu != "전체 메뉴":

    filtered_df = filtered_df[
        (filtered_df["조건"] == selected_menu)
        | (filtered_df["결과"] == selected_menu)
    ]

# 최소 동시 일수 적용
filtered_df = filtered_df[
    filtered_df["동시"] >= min_days
].copy()


# --------------------------------------------------
# 10. 정렬
# --------------------------------------------------

sort_columns = {
    "향상도 순": "향상도",
    "신뢰도 순": "신뢰도",
    "동시 순": "동시"
}

sort_column = sort_columns[sort_option]

filtered_df = filtered_df.sort_values(
    by=[sort_column, "동시", "신뢰도"],
    ascending=[False, False, False]
).reset_index(drop=True)


# --------------------------------------------------
# 11. 연관 규칙 표
# --------------------------------------------------

st.subheader("📋 함께 등장한 메뉴의 연관 규칙")

st.caption(
    "각 메뉴 쌍은 조건과 결과를 바꾼 양방향 규칙으로 표시됩니다."
)

# 남은 규칙 수 표시
st.write(
    f"현재 조건에 맞는 규칙: **{len(filtered_df):,}개**"
)

if len(filtered_df) > 0:

    display_df = filtered_df.copy()

    display_df["지지도"] = (
        display_df["지지도"].map(lambda x: f"{x:.3f}")
    )

    display_df["신뢰도"] = (
        display_df["신뢰도"].map(lambda x: f"{x:.3f}")
    )

    display_df["향상도"] = (
        display_df["향상도"].map(lambda x: f"{x:.3f}")
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500
    )

else:

    st.info(
        "선택한 조건에 해당하는 연관 규칙이 없습니다. "
        "최소 동시 일수를 낮춰 보세요."
    )


# --------------------------------------------------
# 12. 향상도 TOP 10 그래프
# --------------------------------------------------

st.divider()

st.subheader("📈 향상도 TOP 10")

st.markdown(
    "향상도가 높은 규칙일수록 두 메뉴가 우연히 함께 등장하는 "
    "경우보다 더 자주 함께 등장하는 경향이 있습니다."
)

if len(filtered_df) > 0:

    top10 = (
        filtered_df
        .sort_values(
            by=["향상도", "동시", "신뢰도"],
            ascending=False
        )
        .head(10)
        .copy()
    )

    top10["규칙"] = (
        top10["조건"] + " → " + top10["결과"]
    )

    top10 = top10.sort_values(
        "향상도",
        ascending=True
    )

    fig = px.bar(
        top10,
        x="향상도",
        y="규칙",
        orientation="h",
        text="향상도",
        color="향상도",
        color_continuous_scale="Blues",
        labels={
            "향상도": "향상도",
            "규칙": "연관 규칙"
        },
        title="향상도가 높은 메뉴 연관 규칙 TOP 10"
    )

    fig.update_traces(
        texttemplate="%{text:.2f}",
        textposition="outside"
    )

    fig.update_layout(
        height=550,
        yaxis_title="",
        xaxis_title="향상도",
        showlegend=False,
        coloraxis_showscale=False,
        margin=dict(
            l=20,
            r=60,
            t=60,
            b=40
        )
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

else:

    st.info("그래프를 표시할 데이터가 없습니다.")


# --------------------------------------------------
# 13. 함께 나온 적 없는 짝
# --------------------------------------------------

st.divider()

st.subheader("🚫 함께 나온 적 없는 짝")

st.markdown(
    """
    메뉴 하나를 선택하면 그 메뉴와 같은 날 한 번도 나오지 않은
    다른 메뉴를 찾아줍니다.

    단, 해당 메뉴 자체는 혼자서 10일 이상 등장한 경우만 표시합니다.
    """
)

# 기존 '좁혀 보기'와 다른 별도 메뉴 선택
independent_menu = st.selectbox(
    "함께 나온 적 없는 짝 찾기 - 기준 메뉴 선택",
    sorted(menu_counts.keys()),
    key="never_together_menu"
)

# 선택한 메뉴가 나온 일수
selected_menu_days = menu_counts[independent_menu]

# 선택한 메뉴와 한 번도 함께 나오지 않은 메뉴 찾기
never_together = []

for other_menu, other_days in menu_counts.items():

    # 자기 자신 제외
    if other_menu == independent_menu:
        continue

    # 혼자서 10일 이상 등장한 메뉴만 대상
    if other_days < 10:
        continue

    # 두 메뉴가 함께 나온 적이 있는지 확인
    pair = tuple(sorted([independent_menu, other_menu]))

    together_days = pair_counts.get(pair, 0)

    # 함께 나온 적이 한 번도 없는 경우
    if together_days == 0:

        never_together.append({
            "메뉴": other_menu,
            "나온 날": other_days
        })


# 많이 나온 순서로 정렬
never_df = pd.DataFrame(
    never_together,
    columns=["메뉴", "나온 날"]
)

if not never_df.empty:

    never_df = never_df.sort_values(
        by=["나온 날", "메뉴"],
        ascending=[False, True]
    ).reset_index(drop=True)


# 기준 메뉴 등장 일수 표시
st.write(
    f"**'{independent_menu}' 등장 일수: "
    f"{selected_menu_days}일**"
)

st.write(
    f"함께 나온 적 없는 메뉴: **{len(never_df)}개**"
)

if len(never_df) > 0:

    st.dataframe(
        never_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )

else:

    st.info(
        "조건에 맞는 메뉴가 없습니다."
    )


# --------------------------------------------------
# 14. 연관 규칙 지표 설명
# --------------------------------------------------

st.divider()

st.subheader("💡 연관 규칙 지표 알아보기")

with st.expander("지지도, 신뢰도, 향상도란?"):

    st.markdown("""
    **① 지지도 (Support)**

    전체 급식 일수 중 두 메뉴가 함께 나온 비율입니다.

    - 지지도 = 두 메뉴가 함께 나온 횟수 ÷ 전체 급식 일수

    **② 신뢰도 (Confidence)**

    조건 메뉴가 나온 날 중 결과 메뉴도 함께 나온 비율입니다.

    - 신뢰도 = 두 메뉴가 함께 나온 횟수 ÷ 조건 메뉴가 나온 횟수

    **③ 향상도 (Lift)**

    조건 메뉴와 결과 메뉴가 우연히 함께 등장하는 경우보다
    얼마나 더 자주 함께 등장하는지를 나타냅니다.

    - 향상도 = 신뢰도 ÷ 결과 메뉴의 지지도

    **향상도 해석**

    - 향상도 > 1 : 함께 등장하는 경향이 있음
    - 향상도 = 1 : 서로 독립적으로 등장
    - 향상도 < 1 : 함께 등장하는 경향이 적음

    **④ 최소 동시 일수**

    메뉴 두 개가 함께 나온 날짜가 설정한 일수 이상인 규칙만
    표와 그래프에 표시합니다.

    **⑤ 함께 나온 적 없는 짝**

    선택한 메뉴와 함께 나온 기록이 한 번도 없으면서
    각각 10일 이상 등장한 메뉴를 보여줍니다.
    """)


# --------------------------------------------------
# 15. 하단 안내
# --------------------------------------------------

st.caption(
    "분석 데이터: 송탄고 중식 | "
    f"분석 급식 일수: {total_days}일 | "
    "메뉴 전처리: 괄호 및 괄호 안 내용 제거"
)
