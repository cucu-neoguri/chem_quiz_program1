# app.py
# 화학식(시성식) 암기 & 테스트 앱 - Streamlit
# matplotlib 제거, images/ 폴더 기반 그림 불러오기

import random
import streamlit as st
import pandas as pd
import os

# ---- 전역 설정 ----
st.set_page_config(page_title="화학식 퀴즈", page_icon="🧪", layout="wide")

# ---- 프로젝트 폴더 기준 images 폴더 ----
PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))
IMAGES_FOLDER = os.path.join(PROJECT_FOLDER, "images")

# ---- 데이터셋 ----
SUBSTANCES = [
    {"name_ko": "물", "formula": "H2O", "aka": [], "structure_desc": "굽은 구조, O 중심, 비공유전자쌍 2쌍"},
    {"name_ko": "이산화탄소", "formula": "CO2", "aka": [], "structure_desc": "직선형, O=C=O"},
    {"name_ko": "암모니아", "formula": "NH3", "aka": [], "structure_desc": "삼각뿔, N에 비공유전자쌍 1쌍"},
    {"name_ko": "에텐", "formula": "C2H4", "aka": ["에틸렌"], "structure_desc": "이중결합 C=C, sp2"},
    {"name_ko": "에인", "formula": "C2H2", "aka": ["아세틸렌"], "structure_desc": "삼중결합 C≡C, 선형, sp"},
    {"name_ko": "포름알데히드", "formula": "HCHO", "aka": ["메탄알"], "structure_desc": "알데하이드, H2C=O"},
    {"name_ko": "시안화수소", "formula": "HCN", "aka": ["청산수소"], "structure_desc": "H–C≡N 삼중결합"},
]

# 이름→동의어 매핑
ALT_NAMES = {}
for s in SUBSTANCES:
    ALT_NAMES.setdefault(s["name_ko"], set()).add(s["name_ko"])
    for a in s.get("aka", []):
        ALT_NAMES[s["name_ko"]].add(a)

# formula → 표기 정규화
def norm_formula(f: str) -> str:
    return (f.replace("₀","0").replace("₁","1").replace("₂","2").replace("₃","3")
              .replace("₄","4").replace("₅","5").replace("₆","6").replace("₇","7")
              .replace("₈","8").replace("₉","9").upper())

# 한글 정답 비교
def norm_korean(s: str) -> str:
    s = s.strip().lower()
    repl = "()-[]{}·,."
    for ch in repl:
        s = s.replace(ch, " ")
    s = " ".join(s.split())
    return s

def is_korean_answer_correct(user: str, target_korean_name: str) -> bool:
    u = norm_korean(user)
    targets = {norm_korean(n) for n in ALT_NAMES.get(target_korean_name, {target_korean_name})}
    return u in targets

# ---- 이미지 불러오기 ----
MOLECULE_IMAGES = {
    "H2O": "h2o.png",
    "CO2": "co2.png",
    "NH3": "nh3.png",
    "C2H4": "c2h4.png",
    "C2H2": "c2h2.png",
    "HCHO": "hcho.png",
    "HCN": "hcn.png",
}

def get_structure_image(formula: str):
    key = formula.upper()
    filename = MOLECULE_IMAGES.get(key)
    if filename:
        path = os.path.join(IMAGES_FOLDER, filename)
        if os.path.exists(path):
            return path
    return None  # 없으면 None 반환

# ---- 세션 상태 ----
if "wrong_notes" not in st.session_state:
    st.session_state.wrong_notes = []
if "score" not in st.session_state:
    st.session_state.score = 0
if "total" not in st.session_state:
    st.session_state.total = 0

# ---- 유틸 ----
def pick_substance():
    return random.choice(SUBSTANCES)

def substance_by_formula(formula: str):
    f = norm_formula(formula)
    for s in SUBSTANCES:
        if norm_formula(s["formula"]) == f:
            return s
    return None

# ---- UI 상단 ----
st.title("🧪 화학식 암기 & 테스트")
st.caption("기본테마(이름↔시성식, 구조식→이름/시성식) + 시험테마(개념/응용).  그림 문제의 정답은 **한글 이름**으로 입력!")

tab_home, tab_mem, tab_test, tab_wrong = st.tabs(["홈", "암기", "테스트", "오답노트"])

with tab_home:
    st.header("시작하기")
    st.write("이름·시성식·구조 특징을 한 눈에 볼 수 있고, 구조식 그림을 일부 지원합니다.")

with tab_mem:
    st.subheader("📚 암기 목록")
    df = pd.DataFrame(SUBSTANCES)
    st.dataframe(df[["name_ko","formula","structure_desc"]], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### 🔍 구조식 미리보기")
    selected = st.selectbox(
        "분자 선택(그림 제공: H2O, CO2, NH3, C2H4, C2H2, HCHO, HCN)",
        options=["선택하세요"] + [f'{s["name_ko"]} ({s["formula"]})' for s in SUBSTANCES]
    )
    if selected != "선택하세요":
        formula = selected.split("(")[-1].strip(")")
        img_path = get_structure_image(formula)
        if img_path:
            st.image(img_path, caption=selected, use_column_width=False)
        else:
            st.info(f"그림 준비되지 않은 분자입니다. 구조 특징: {substance_by_formula(formula)['structure_desc']}")

with tab_test:
    st.subheader("📝 테스트")
    theme = st.radio("테마 선택", ["기본테마"], horizontal=True)
    mode = st.radio("문항 유형", ["주관식", "오지선다"], horizontal=True)

    def make_basic_question():
        s = pick_substance()
        qtype = random.choice(["name_to_formula", "formula_to_name", "structure_to_name"])
        has_img = s["formula"].upper() in MOLECULE_IMAGES

        if qtype == "name_to_formula":
            return {"qtext": f"{s['name_ko']}의 시성식(분자식)은?", "correct": norm_formula(s["formula"]), "answer_type":"formula", "show_image": False}
        elif qtype == "formula_to_name":
            return {"qtext": f"시성식 {s['formula']} 의 한글 이름은?", "correct": s["name_ko"], "answer_type":"korean", "show_image": False}
        else:
            return {"qtext": "아래 구조식의 한글 이름은?", "correct": s["name_ko"], "answer_type":"korean", "show_image": True, "formula": s["formula"]}

    if "current_q" not in st.session_state:
        st.session_state.current_q = make_basic_question()

    if st.button("🔄 새 문제 생성"):
        st.session_state.current_q = make_basic_question()

    qblock = st.session_state.current_q
    st.markdown(f"#### {qblock['qtext']}")

    if qblock.get("show_image"):
        img_path = get_structure_image(qblock.get("formula"))
        if img_path:
            st.image(img_path, width=240)
        else:
            s = substance_by_formula(qblock.get("formula"))
            st.info(f"그림 준비되지 않은 분자입니다. 구조 특징: {s['structure_desc']}")

    if mode == "주관식":
        user = st.text_input(f"정답 입력")
        if st.button("채점"):
            correct = False
            if qblock["answer_type"]=="korean":
                correct = is_korean_answer_correct(user, qblock["correct"])
            else:
                correct = norm_formula(user) == norm_formula(qblock["correct"])
            st.session_state.total += 1
            if correct:
                st.session_state.score +=1
                st.success("✅ 정답!")
                st.session_state.current_q = make_basic_question()
            else:
                st.error(f"❌ 오답. 정답: {qblock['correct']}")
                st.session_state.wrong_notes.append((qblock['qtext'], qblock['correct'], user))
    else:
        s_correct = qblock["correct"]
        choices = set([s_correct])
        while len(choices)<4:
            choices.add(pick_substance()["name_ko"] if qblock["answer_type"]=="korean" else norm_formula(pick_substance()["formula"]))
        choices = list(choices)
        random.shuffle(choices)
        sel = st.radio("정답 선택", choices)
        if st.button("채점"):
            st.session_state.total += 1
            if (qblock["answer_type"]=="korean" and is_korean_answer_correct(sel, s_correct)) or (qblock["answer_type"]=="formula" and sel==s_correct):
                st.session_state.score +=1
                st.success("✅ 정답!")
                st.session_state.current_q = make_basic_question()
           
