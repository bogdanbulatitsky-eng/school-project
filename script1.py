"""Сценарій 1. Запуск: python -m streamlit run script1.py."""
import csv
from datetime import date
from math import isfinite
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

CSV_PATH = Path(__file__).with_name("school_students_db.csv")
FIELDS = ["student_id", "first_name", "last_name", "gender", "year_birth", "class_name", "average_mark"]


class Student:
    """Один запис із вашого CSV."""

    def __init__(self, row: dict) -> None:
        self.student_id = int(row["student_id"])
        self.first_name = row["first_name"].strip()
        self.last_name = row["last_name"].strip()
        self.gender = row["gender"].strip().upper()
        self.year_birth = int(row["year_birth"])
        self.class_name = row["class_name"].strip()
        self.average_mark = float(row["average_mark"])
        if not self.first_name or not self.last_name or self.gender not in ("M", "F"):
            raise ValueError("Перевірте ім’я, прізвище та стать M/F.")
        if not 1900 <= self.year_birth <= date.today().year:
            raise ValueError("Неправильний рік народження.")
        if not isfinite(self.average_mark) or not 1 <= self.average_mark <= 12:
            raise ValueError("Середня оцінка повинна бути числом від 1 до 12.")

    def to_dict(self) -> dict:
        return {field: getattr(self, field) for field in FIELDS}


class SchoolClass:
    def __init__(self, name: str) -> None:
        number, letter = name.split("-")
        self.number = int(number)
        self.letter = letter
        self.students: list[Student] = []
        if not 1 <= self.number <= 12 or len(letter) != 1 or not letter.isalpha():
            raise ValueError("Клас має вигляд 10-A; допустимі номери 1–12.")

    def name(self) -> str:
        return f"{self.number}-{self.letter}"

    def promote(self) -> None:
        self.number += 1
        for student in self.students:
            student.class_name = self.name()


class School:
    """Школа об’єднує класи та виконує операції над ними."""

    def __init__(self) -> None:
        self.classes: list[SchoolClass] = []

    def statistics(self) -> dict:
        students = [s for classroom in self.classes for s in classroom.students]
        sizes = [len(c.students) for c in self.classes]
        total = len(students)
        boys = sum(s.gender == "M" for s in students)
        maximum, minimum = max(sizes, default=0), min(sizes, default=0)
        return {
            "total": total,
            "classes": len(self.classes),
            "boys": boys / total * 100 if total else 0,
            "girls": (total - boys) / total * 100 if total else 0,
            "average": total / len(sizes) if sizes else 0,
            "maximum": maximum,
            "minimum": minimum,
            "largest": ", ".join(c.name() for c in self.classes if len(c.students) == maximum),
            "smallest": ", ".join(c.name() for c in self.classes if len(c.students) == minimum),
        }

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame([s.to_dict() for c in self.classes for s in c.students], columns=FIELDS)

    def promote(self, graduation_grade: int) -> list[Student]:
        # Випускні та старші класи вибувають; решта переходять на рік уперед.
        graduates = [s for c in self.classes if c.number >= graduation_grade for s in c.students]
        self.classes = [c for c in self.classes if c.number < graduation_grade]
        for classroom in self.classes:
            classroom.promote()
        return graduates


def load_school(path: Path = CSV_PATH) -> School:
    school = School()
    classes = {}
    student_ids = set()
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != FIELDS:
            raise ValueError("Заголовки CSV мають бути: " + ",".join(FIELDS))
        for line, row in enumerate(reader, start=2):
            try:
                student = Student(row)
                if student.student_id in student_ids:
                    raise ValueError("Повторюється ID учня.")
                if student.class_name not in classes:
                    classes[student.class_name] = SchoolClass(student.class_name)
                classroom = classes[student.class_name]
                student.class_name = classroom.name()
                classroom.students.append(student)
                student_ids.add(student.student_id)
            except (ValueError, TypeError, KeyError, AttributeError) as error:
                raise ValueError(f"Рядок {line}: {error}") from error
    school.classes = sorted(classes.values(), key=lambda c: (c.number, c.letter))
    return school


def draw_charts(school: School) -> None:
    if not school.classes:
        st.info("У школі немає класів для побудови графіків.")
        return
    classes = pd.DataFrame([{"number": c.number, "letter": c.letter, "count": len(c.students)}
                            for c in school.classes])
    students = school.to_frame()
    left, right = st.columns(2)
    with left:
        st.subheader("Учні за паралелями")
        counts = classes.groupby("number")["count"].sum()
        fig, ax = plt.subplots(figsize=(7, 3.4), layout="constrained")
        ax.bar(counts.index, counts.values, color="steelblue")
        ax.set(xlabel="Паралель", ylabel="Кількість учнів", xticks=counts.index)
        st.pyplot(fig)
        plt.close(fig)
    with right:
        st.subheader("Середня наповненість за літерами")
        means = classes.groupby("letter")["count"].mean()
        fig, ax = plt.subplots(figsize=(7, 3.4), layout="constrained")
        ax.bar(means.index, means.values, color="orange")
        ax.set(xlabel="Літера класу", ylabel="Учнів у класі в середньому")
        st.pyplot(fig)
        plt.close(fig)
    if students.empty:
        return
    st.subheader("Кількість учнів за роком народження")
    births = students.groupby("year_birth").size()
    fig, ax = plt.subplots(figsize=(13, 3), layout="constrained")
    ax.plot(births.index, births.values, marker="o", color="green")
    ax.set(xlabel="Рік народження", ylabel="Кількість учнів", xticks=births.index)
    ax.ticklabel_format(axis="x", style="plain", useOffset=False)
    st.pyplot(fig)
    plt.close(fig)
    st.subheader("Середні оцінки учнів за класами")
    fig, ax = plt.subplots(figsize=(14, 4), layout="constrained")
    for index, classroom in enumerate(school.classes):
        # Зміщуємо точки трохи вбік, щоб однакові оцінки менше перекривалися.
        x = [index + (s.student_id % 9 - 4) * 0.045 for s in classroom.students]
        ax.scatter(x, [s.average_mark for s in classroom.students], s=15, alpha=0.35, color="purple")
    ax.set_xticks(range(len(school.classes)), [c.name() for c in school.classes], rotation=90)
    ax.set(xlabel="Клас", ylabel="Середня оцінка", ylim=(0.5, 12.5))
    ax.grid(axis="y", alpha=0.2)
    st.pyplot(fig)
    plt.close(fig)


def main() -> None:
    st.set_page_config(page_title="Аналітика учнів", layout="wide")
    st.title("Аналітика учнів та переведення класів")
    st.caption("Джерело: school_students_db.csv · Формат класів і полів збережено як у вашій базі.")
    if st.button("Перечитати CSV / скасувати моделювання"):
        for key in ("school", "before", "promoted", "graduates", "used_grade"):
            st.session_state.pop(key, None)
    if "school" not in st.session_state:
        try:
            st.session_state.school = load_school()
        except (OSError, ValueError) as error:
            st.error(f"Не вдалося відкрити school_students_db.csv: {error}")
            st.stop()
        st.session_state.before = st.session_state.school.statistics()
        st.session_state.promoted = False
    school = st.session_state.school
    graduation_grade = st.selectbox("Випускний клас", [11, 12], index=0,
                                    disabled=st.session_state.promoted)
    older = sum(len(c.students) for c in school.classes if c.number > graduation_grade)
    if older:
        st.warning(f"У CSV є {older} учнів у класах старше {graduation_grade}-го. "
                   "Під час переведення вони також вибудуть зі складу діючих класів; "
                   "список усіх вибулих можна буде завантажити окремо.")
    if st.button("Перевести на наступний навчальний рік", disabled=st.session_state.promoted):
        st.session_state.used_grade = graduation_grade
        st.session_state.graduates = school.promote(graduation_grade)
        st.session_state.promoted = True
        st.rerun()
    if st.session_state.promoted:
        graduates = st.session_state.graduates
        grade = st.session_state.used_grade
        regular = sum(int(s.class_name.split("-")[0]) == grade for s in graduates)
        st.success(f"Переведення виконано. Випускників {grade}-го класу: {regular}. "
                   f"Записів старших класів: {len(graduates) - regular}. Перші класи відсутні.")
        graduates_df = pd.DataFrame([s.to_dict() for s in graduates], columns=FIELDS)
        st.download_button("Завантажити список вибулих (CSV)",
                           graduates_df.to_csv(index=False).encode("utf-8-sig"), "students_completed.csv", "text/csv",
                           on_click="ignore")

    stats = school.statistics()
    first, second, third = st.columns(3)
    first.metric("Загалом учнів", stats["total"])
    second.metric("Кількість класів", stats["classes"])
    third.metric("Середня наповненість", f"{stats['average']:.2f}")
    st.write(f"**Хлопці:** {stats['boys']:.2f}% · **Дівчата:** {stats['girls']:.2f}%")
    st.write(f"**Найбільші класи:** {stats['largest'] or 'немає'}; учнів у кожному: {stats['maximum']}")
    st.write(f"**Найменші класи:** {stats['smallest'] or 'немає'}; учнів у кожному: {stats['minimum']}")
    if st.session_state.promoted:
        before = st.session_state.before
        comparison = pd.DataFrame({"Показник": ["Учнів", "Класів", "Хлопці, %", "Дівчата, %", "Середня наповненість"],
                                   "До": [before[k] for k in ("total", "classes", "boys", "girls", "average")],
                                   "Після": [stats[k] for k in ("total", "classes", "boys", "girls", "average")]})
        st.dataframe(comparison.round(2), hide_index=True)
    frame = school.to_frame()
    st.download_button("Завантажити поточну таблицю учнів (CSV)",
                       frame.to_csv(index=False).encode("utf-8-sig"), "school_students_db.csv", "text/csv",
                       key=f"students_csv_{st.session_state.promoted}", on_click="ignore")
    st.caption("Переведення моделюється у пам’яті. Вихідний CSV учнів не перезаписується; "
               "оновлену базу можна завантажити кнопкою.")
    draw_charts(school)
    with st.expander("Переглянути таблицю учнів"):
        st.dataframe(frame, hide_index=True)


if __name__ == "__main__":
    main()
