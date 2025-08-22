# app.py
# 화학식(시성식) 암기 & 테스트 앱 - Streamlit
# 기본테마(이름<->시성식, 구조식 그림→이름/시성식) + 시험테마(개념/응용)
# 답 규칙: 구조식/시성식 → "이름은 한글"로 입력. 이름 → 시성식은 영문/화학기호.

import random
import textwrap
from typing import List, Dict, Optional
import streamlit as st
import pandas as pd
import math

# ---- 전역 설정 ----
st.set_page_config(page_title="화학식 퀴즈", page_icon="🧪", layout="wide")

# ---- 데이터셋: 화학 I에서 자주 나오는 물질들 ----
# name_ko: 정답(한글)
# formula: 시성식(혹은 분자식)
# aka: 한글 별칭/동의어(정답 허용)
# structure_desc: 구조식/특징 텍스트
SUBSTANCES: List[Dict] = [
    {"name_ko": "물", "formula": "H2O", "aka": [], "structure_desc": "굽은 구조, O 중심, 비공유전자쌍 2쌍"},
    {"name_ko": "이산화탄소", "formula": "CO2", "aka": [], "structure_desc": "직선형, O=C=O"},
    {"name_ko": "일산화탄소", "formula": "CO", "aka": [], "structure_desc": "선형, C≡O 성분(공명)"},
    {"name_ko": "암모니아", "formula": "NH3", "aka": [], "structure_desc": "삼각뿔, N에 비공유전자쌍 1쌍"},
    {"name_ko": "메테인", "formula": "CH4", "aka": ["메탄"], "structure_desc": "정사면체, sp3"},
    {"name_ko": "에테인", "formula": "C2H6", "aka": ["에탄"], "structure_desc": "단일결합 C-C, sp3"},
    {"name_ko": "에텐", "formula": "C2H4", "aka": ["에틸렌"], "structure_desc": "이중결합 C=C, sp2"},
    {"name_ko": "에인", "formula": "C2H2", "aka": ["아세틸렌"], "structure_desc": "삼중결합 C≡C, 선형, sp"},
    {"name_ko": "메탄올", "formula": "CH3OH", "aka": [], "structure_desc": "알코올, -OH"},
    {"name_ko": "에탄올", "formula": "C2H5OH", "aka": ["알코올"], "structure_desc": "알코올, -OH"},
    {"name_ko": "포름알데히드", "formula": "HCHO", "aka": ["포르말데하이드", "메탄알"], "structure_desc": "알데하이드, H2C=O"},
    {"name_ko": "아세트산", "formula": "CH3COOH", "aka": ["초산"], "structure_desc": "카복실산, -COOH"},
    {"name_ko": "아세톤", "formula": "C3H6O", "aka": ["프로판온"], "structure_desc": "케톤, (CH3)2C=O"},
    {"name_ko": "과산화수소", "formula": "H2O2", "aka": [], "structure_desc": "H-O-O-H, 굽은"},
    {"name_ko": "오존", "formula": "O3", "aka": [], "structure_desc": "굽은, 공명구조"},
    {"name_ko": "질산", "formula": "HNO3", "aka": [], "structure_desc": "N=O 포함, -OH 하나"},
    {"name_ko": "황산", "formula": "H2SO4", "aka": [], "structure_desc": "S 중심, 이중결합 O 2개, -OH 2개"},
    {"name_ko": "염산", "formula": "HCl", "aka": [], "structure_desc": "단원자산, 수용액에서 강산"},
    {"name_ko": "수산화나트륨", "formula": "NaOH", "aka": ["가성소다"], "structure_desc": "염기, 이온화"},
    {"name_ko": "탄산칼슘", "formula": "CaCO3", "aka": ["석회석"], "structure_desc": "이온성 고체"},
    {"name_ko": "염화나트륨", "formula": "NaCl", "aka": ["소금"], "structure_desc": "이온결정"},
    {"name_ko": "질소", "formula": "N2", "aka": [], "structure_desc": "N≡N 삼중결합"},
    {"name_ko": "산소", "formula": "O2", "aka": [], "structure_desc": "O=O 이중결합"},
    {"name_ko": "암모늄 이온", "formula": "NH4+", "aka": ["암모늄"], "structure_desc": "정사면체 양이온"},
    {"name_ko": "시안화수소", "formula": "HCN", "aka": ["청산수소"], "structure_desc": "H–C≡N 삼중결합"},
    {"name_ko": "시안화칼륨", "formula": "KCN", "aka": [], "structure_desc": "K+ [C≡N]-"},
]

# 이름→동의어 매핑
ALT_NAMES = {}
for s in SUBSTANCES:
    ALT_NAMES.setdefault(s["name_ko"], set()).add(s["name_ko"])
    for a in s.get("aka", []):
        ALT_NAMES[s["name_ko"]].add(a)

# formula → 표기 정규화(숫자 아래첨자 허용/불허 혼용 대비)
def norm_formula(f: str) -> str:
    return (f.replace("₀","0").replace("₁","1").replace("₂","2").replace("₃","3")
              .replace("₄","4").replace("₅","5").replace("₆","6").replace("₇","7")
              .replace("₈","8").replace("₉","9").upper())

# 한글 정답 비교(공백/괄호/기호 등 유연 매칭)
def norm_korean(s: str) -> str:
    s = s.strip().lower()
    # 괄호, 공백, 특수기호 약간 정리
    repl = "()-[]{}·,."
    for ch in repl:
        s = s.replace(ch, " ")
    s = " ".join(s.split())
    return s

def is_korean_answer_correct(user: str, target_korean_name: str) -> bool:
    u = norm_korean(user)
    targets = {norm_korean(n) for n in ALT_NAMES.get(target_korean_name, {target_korean_name})}
    return u in targets

# ---- 간단 구조식 그림: matplotlib로 몇 종만 그림 ----
# Streamlit 실행 환경에서만 쓰임. (코드만 제공해도 동작)
import io
import matplotlib.pyplot as plt

def draw_structure_image(key: str):
    """
    key: 구조식 그림이 있는 대표 분자 키(=formula 또는 별칭)
    준비된 그림: H2O, CO2, NH3, C2H4, C2H2, HCHO, HCN
    """
    k = key.upper()
    fig = plt.figure(figsize=(3, 2.2))
    ax = plt.gca()
    ax.axis("off")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)

    def text(x, y, s, size=18):
        ax.text(x, y, s, ha="center", va="center", fontsize=size)

    def bond(x1, y1, x2, y2, n=1, gap=0.15):
        # n=1,2,3 결합선
        if n == 1:
            ax.plot([x1, x2], [y1, y2], linewidth=2)
        else:
            # 평행선 오프셋
            dx = x2 - x1
            dy = y2 - y1
            L = math.hypot(dx, dy) or 1
            ox = -dy / L * gap
            oy = dx / L * gap
            for i in range(n):
                off = (i - (n-1)/2)
                ax.plot([x1 + off*ox, x2 + off*ox],
                        [y1 + off*oy, y2 + off*oy], linewidth=2)

    if k in ("H2O", "WATER"):
        # H–O–H (굽은)
        text(5, 3.6, "O")
        text(3.7, 2.4, "H", 16)
        text(6.3, 2.4, "H", 16)
        bond(4.6, 3.2, 3.9, 2.6, n=1)
        bond(5.4, 3.2, 6.1, 2.6, n=1)
    elif k in ("CO2",):
        # O=C=O (직선)
        text(3, 3, "O")
        text(5, 3, "C")
        text(7, 3, "O")
        bond(3.6, 3, 4.4, 3, n=2)
        bond(5.6, 3, 6.4, 3, n=2)
    elif k in ("NH3",):
        # 삼각뿔 투영: N 중심, H 세 개
        text(5, 3.4, "N")
        text(3.8, 2.2, "H", 16)
        text(6.2, 2.2, "H", 16)
        text(5, 4.8, "H", 16)
        bond(4.6, 3.2, 4.0, 2.4, n=1)
        bond(5.4, 3.2, 6.0, 2.4, n=1)
        bond(5.0, 3.6, 5.0, 4.5, n=1)
    elif k in ("C2H4", "ETHENE", "ETENE"):
        # H2C=CH2
        text(3.8, 3, "H", 14); text(4.6, 3, "C"); text(5.4, 3, "C"); text(6.2, 3, "H", 14)
        bond(4.8, 3, 5.2, 3, n=2)
        text(4.6, 4.2, "H", 14); bond(4.6, 3.2, 4.6, 4.0, n=1)
        text(4.6, 1.8, "H", 14); bond(4.6, 2.8, 4.6, 2.0, n=1)
        text(5.4, 4.2, "H", 14); bond(5.4, 3.2, 5.4, 4.0, n=1)
        text(5.4, 1.8, "H", 14); bond(5.4, 2.8, 5.4, 2.0, n=1)
    elif k in ("C2H2", "ACETYLENE", "에인", "아세틸렌"):
        # H–C≡C–H
        text(3.6, 3, "H", 14); text(4.6, 3, "C"); text(5.4, 3, "C"); text(6.4, 3, "H", 14)
        bond(4.8, 3, 5.2, 3, n=3)
        bond(3.8, 3, 4.4, 3, n=1)
        bond(5.6, 3, 6.2, 3, n=1)
    elif k in ("HCHO", "FORMALDEHYDE", "포름알데히드", "메탄알"):
        # H2C=O
        text(4.6, 3, "C"); text(5.6, 3, "O")
        bond(4.8, 3, 5.4, 3, n=2)
        text(4.6, 4.2, "H", 14); bond(4.6, 3.2, 4.6, 4.0, n=1)
        text(4.6, 1.8, "H", 14); bond(4.6, 2.8, 4.6, 2.0, n=1)
    elif k in ("HCN", "시안화수소", "청산수소"):
        # H–C≡N
        text(3.8, 3, "H", 14); text(4.8, 3, "C"); text(6.0, 3, "N")
        bond(4.9, 3, 5.8, 3, n=3)
        bond(4.0, 3, 4.6, 3, n=1)
    else:
        # 미지원: 텍스트 안내
        text(5, 3, "구조식 미리보기 없음", 12)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf

# ---- 세션 상태 ----
if "wrong_notes" not in st.session_state:
    st.session_state.wrong_notes = []  # (문항, 정답, 사용자입력)
if "score" not in st.session_state:
    st.session_state.score = 0
if "total" not in st.session_state:
    st.session_state.total = 0

# ---- 유틸 ----
def pick_substance() -> Dict:
    return random.choice(SUBSTANCES)

def substance_by_formula(formula: str) -> Optional[Dict]:
    f = norm_formula(formula)
    for s in SUBSTANCES:
        if norm_formula(s["formula"]) == f:
            return s
    return None

# ---- UI 상단 ----
st.title("🧪 화학식 암기 & 테스트")
st.caption("기본테마(이름↔시성식, 구조식→이름/시성식) + 시험테마(개념/응용).  그림 문제의 정답은 **한글 이름**으로 입력!")

# ---- 홈: 암기 / 테스트 ----
tab_home, tab_mem, tab_test, tab_wrong = st.tabs(["홈", "암기", "테스트", "오답노트"])

with tab_home:
    st.header("시작하기")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("암기")
        st.write("이름·시성식·구조 특징을 한 눈에. 구조식 그림 미리보기 지원(일부).")
        st.page_link("app.py", label="➡️ 상단 탭 '암기'로 이동", icon="📚")
    with c2:
        st.subheader("테스트")
        st.write("기본테마(기초 암기)와 시험테마(응용/개념). 주관식 또는 오지선다.")
        st.page_link("app.py", label="➡️ 상단 탭 '테스트'로 이동", icon="📝")

with tab_mem:
    # 우상단 "테스트" 버튼처럼 보이게
    cA, cB = st.columns([4,1])
    with cB:
        if st.button("📝 테스트로 이동"):
            st.switch_page("app.py")  # 같은 파일 내 탭 이동 대체

    st.subheader("📚 암기 목록")
    # 검색/필터
    q = st.text_input("검색(한글 이름/시성식/특징):").strip().lower()
    df = pd.DataFrame(SUBSTANCES)
    df_view = df.copy()
    if q:
        df_view = df_view[
            df_view["name_ko"].str.lower().str.contains(q) |
            df_view["formula"].str.lower().str.contains(q) |
            df_view["structure_desc"].str.lower().str.contains(q)
        ]
    # 표 보여주기
    st.dataframe(df_view[["name_ko","formula","structure_desc"]], use_container_width=True, hide_index=True)

    # 구조식 미리보기(그림)
    st.markdown("---")
    st.markdown("### 🔍 구조식 미리보기 (일부 분자)")
    selected = st.selectbox(
        "분자 선택(그림 제공: H2O, CO2, NH3, C2H4, C2H2, HCHO, HCN)",
        options=["선택하세요"] + [f'{s["name_ko"]} ({s["formula"]})' for s in SUBSTANCES]
    )
    if selected != "선택하세요":
        formula = selected.split("(")[-1].strip(")")
        buf = draw_structure_image(formula)
        st.image(buf, caption=selected, use_column_width=False)

with tab_test:
    st.subheader("📝 테스트")
    theme = st.radio("테마 선택", ["기본테마", "시험테마"], horizontal=True)
    mode = st.radio("문항 유형", ["주관식", "오지선다"], horizontal=True)
    st.markdown("> ⛳ **채점 규칙 요약**  \n"
                "- 구조식 → **한글 이름**으로 입력  \n"
                "- 시성식 → **한글 이름**으로 입력  \n"
                "- 이름 → 시성식은 **영문/화학기호**로 입력  ")

    # --- 문항 생성 ---
    # 기본테마: 이름→시성식, 시성식→이름, 구조식(그림)→이름, (옵션) 구조식→시성식
    # 시험테마: 개념/다중결합/전자쌍/분자기하 등
    def make_basic_question():
        s = pick_substance()
        qtype = random.choice(["name_to_formula", "formula_to_name", "structure_to_name", "structure_to_formula"])
        # 구조식 그림은 지원하는 분자 위주, 아니면 텍스트 선구조식
        has_img = norm_formula(s["formula"]) in ("H2O","CO2","NH3","C2H4","C2H2","HCHO","HCN")

        if qtype == "name_to_formula":
            qtext = f"Q. **{s['name_ko']}**의 시성식(분자식)은?"
            correct = norm_formula(s["formula"])
            input_hint = "예: H2O, CO2 (영문/숫자)"
            answer_type = "formula"
            payload = {"show_image": False}
        elif qtype == "formula_to_name":
            qtext = f"Q. 시성식 **{s['formula']}** 의 한글 이름은?"
            correct = s["name_ko"]
            input_hint = "예: 물, 이산화탄소 (한글)"
            answer_type = "korean"
            payload = {"show_image": False}
        elif qtype == "structure_to_name":
            qtext = f"Q. 아래 **구조식**의 한글 이름은?"
            correct = s["name_ko"]
            input_hint = "예: 물, 이산화탄소 (한글)"
            answer_type = "korean"
            payload = {"show_image": True, "image_key": s["formula"] if has_img else None, "fallback": s["structure_desc"]}
        else:  # structure_to_formula
            qtext = f"Q. 아래 **구조식**의 시성식은?"
            correct = norm_formula(s["formula"])
            input_hint = "예: H2O, CO2 (영문/숫자)"
            answer_type = "formula"
            payload = {"show_image": True, "image_key": s["formula"] if has_img else None, "fallback": s["structure_desc"]}

        return {"substance": s, "qtext": qtext, "correct": correct, "answer_type": answer_type, "input_hint": input_hint, "payload": payload}

    # 시험테마 문항 은행
    CONCEPT_BANK = [
        {
            "q": "다음 중 **삼중결합(≡)** 을 갖는 분자는?",
            "options": ["이산화탄소", "물", "에인(아세틸렌)", "메테인"],
            "answer": "에인(아세틸렌)",
            "explain": "C2H2는 C≡C 삼중결합을 가진다."
        },
        {
            "q": "물(H2O)의 루이스 구조식에서 산소 원자의 **비공유 전자쌍** 개수는?",
            "options": ["0쌍", "1쌍", "2쌍", "3쌍", "4쌍"],
            "answer": "2쌍",
            "explain": "산소의 최외각 전자 6개 중 2쌍이 비공유 전자쌍."
        },
        {
            "q": "이산화탄소(CO2)의 **분자 기하**는?",
            "options": ["굽은", "삼각평면", "직선형", "정사면체"],
            "answer": "직선형",
            "explain": "O=C=O, 중심 탄소의 전자영역 기하가 선형."
        },
        {
            "q": "시안화수소(HCN)에서 C와 N 사이의 결합 차수(다중결합)는?",
            "options": ["단일", "이중", "삼중", "4중"],
            "answer": "삼중",
            "explain": "C≡N."
        },
        {
            "q": "암모니아(NH3)의 **분자 기하**는?",
            "options": ["직선형", "삼각뿔", "정사면체", "삼각평면"],
            "answer": "삼각뿔",
            "explain": "전자영역은 정사면체형, 비공유전자쌍 1쌍으로 삼각뿔."
        },
        {
            "q": "다음 중 **이중결합(═)** 을 포함하는 것은?",
            "options": ["에테인", "에텐", "메테인", "암모니아"],
            "answer": "에텐",
            "explain": "C2H4는 C=C 이중결합."
        },
    ]

    def make_exam_question():
        item = random.choice(CONCEPT_BANK)
        if mode == "오지선다":
            return {"type": "mcq", **item}
        else:
            # 주관식: 정답 키워드 매칭(한글)
            return {"type": "short", "q": item["q"], "answer": item["answer"], "explain": item["explain"]}

    # 문항 하나 생성 & 표시
    if "current_q" not in st.session_state:
        st.session_state.current_q = None

    if st.button("🔄 새 문제 생성"):
        st.session_state.current_q = None

    if st.session_state.current_q is None:
        st.session_state.current_q = make_basic_question() if theme == "기본테마" else make_exam_question()

    qblock = st.session_state.current_q

    # --- 표시 & 응답 ---
    if theme == "기본테마":
        st.markdown(f"#### {qblock['qtext']}")
        # 구조식 그림
        payload = qblock.get("payload", {})
        if payload.get("show_image"):
            if payload.get("image_key"):
                img_buf = draw_structure_image(payload["image_key"])
                st.image(img_buf, width=240)
            else:
                st.info(f"그림 준비되지 않은 분자입니다. 구조 특징: {payload.get('fallback','-')}")
        # 입력/객관식
        if mode == "주관식":
            user = st.text_input(f"정답 입력 ({qblock['input_hint']})")
            if st.button("채점"):
                correct = False
                if qblock["answer_type"] == "korean":
                    correct = is_korean_answer_correct(user, qblock["correct"])
                else:  # formula
                    correct = norm_formula(user) == norm_formula(qblock["correct"])
                st.session_state.total += 1
                if correct:
                    st.session_state.score += 1
                    st.success("✅ 정답!")
                    st.session_state.current_q = None
                else:
                    st.error(f"❌ 오답. 정답: {qblock['correct']}")
                    st.session_state.wrong_notes.append((qblock['qtext'], qblock['correct'], user))
        else:
            # 오지선다: 보기 4개 구성
            s_correct = qblock["correct"]
            choices = set()
            if qblock["answer_type"] == "korean":
                # 이름 보기
                choices.add(s_correct)
                while len(choices) < 4:
                    choices.add(pick_substance()["name_ko"])
            else:
                # 시성식 보기
                choices.add(norm_formula(s_correct))
                while len(choices) < 4:
                    choices.add(norm_formula(pick_substance()["formula"]))
            choices = list(choices)
            random.shuffle(choices)
            sel = st.radio("정답 선택", choices, index=None)
            if st.button("채점"):
                st.session_state.total += 1
                if sel is not None and (
                    (qblock["answer_type"] == "korean" and is_korean_answer_correct(sel, s_correct)) or
                    (qblock["answer_type"] == "formula" and norm_formula(sel) == norm_formula(s_correct))
                ):
                    st.session_state.score += 1
                    st.success("✅ 정답!")
                    st.session_state.current_q = None
                else:
                    st.error(f"❌ 오답. 정답: {s_correct}")
                    st.session_state.wrong_notes.append((qblock['qtext'], s_correct, str(sel)))

    else:  # 시험테마
        st.markdown(f"#### {qblock['q']}")
        if mode == "오지선다" and qblock["type"] == "mcq":
            opts = qblock["options"]
            sel = st.radio("정답 선택", opts, index=None)
            if st.button("채점"):
                st.session_state.total += 1
                if sel == qblock["answer"]:
                    st.session_state.score += 1
                    st.success("✅ 정답!")
                    st.info("해설: " + qblock["explain"])
                    st.session_state.current_q = None
                else:
                    st.error(f"❌ 오답. 정답: {qblock['answer']}")
                    st.info("해설: " + qblock["explain"])
                    st.session_state.wrong_notes.append((qblock['q'], qblock['answer'], str(sel)))
        else:
            # 주관식
            user = st.text_input("정답(한글로 입력)")
            if st.button("채점"):
                st.session_state.total += 1
                if is_korean_answer_correct(user, qblock["answer"]):
                    st.session_state.score += 1
                    st.success("✅ 정답!")
                    st.info("해설: " + qblock["explain"])
                    st.session_state.current_q = None
                else:
                    st.error(f"❌ 오답. 정답: {qblock['answer']}")
                    st.info("해설: " + qblock["explain"])
                    st.session_state.wrong_notes.append((qblock['q'], qblock['answer'], user))

    # 점수판
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("맞힌 개수", st.session_state.score)
    with c2:
        st.metric("푼 문항 수", st.session_state.total)
    with c3:
        rate = 0 if st.session_state.total == 0 else round(100*st.session_state.score/st.session_state.total, 1)
        st.metric("정답률(%)", rate)

with tab_wrong:
    st.subheader("❗ 오답노트")
    if not st.session_state.wrong_notes:
        st.info("오답이 없습니다. 테스트를 먼저 진행해 보세요.")
    else:
        dfw = pd.DataFrame(st.session_state.wrong_notes, columns=["문항", "정답", "내 답"])
        st.dataframe(dfw, use_container_width=True, hide_index=True)
        if st.button("오답노트 초기화"):
            st.session_state.wrong_notes = []
            st.success("오답노트를 비웠습니다.")
