"""Сценарій 1: учні, статистика та переведення класів."""
from pathlib import Path
import pandas as pd
import streamlit as st

FILE = Path(__file__).with_name("school_students_db.csv")
FIELDS = ["student_id", "first_name", "last_name", "gender", "year_birth", "class_name", "average_mark"]


class Student:
    def __init__(self, row: dict) -> None:
        self.student_id = row["student_id"]
        self.first_name = row["first_name"]
        self.last_name = row["last_name"]
        self.gender = row["gender"]
        self.year_birth = row["year_birth"]
        self.class_name = row["class_name"]
        self.average_mark = row["average_mark"]

    def to_dict(self) -> dict:
        return {"student_id": self.student_id, "first_name": self.first_name,
                "last_name": self.last_name, "gender": self.gender,
                "year_birth": self.year_birth, "class_name": self.class_name,
                "average_mark": self.average_mark}


class SchoolClass:
    def __init__(self, name: str) -> None:
        number, self.letter = name.split("-")
        self.number = int(number)
        self.students: list[Student] = []

    def name(self) -> str:
        return f"{self.number}-{self.letter}"

    def promote(self) -> None:
        self.number += 1
        for student in self.students:
            student.class_name = self.name()


class School:
    def __init__(self, path: Path) -> None:
        self.classes: dict[str, SchoolClass] = {}
        # Кожен рядок CSV перетворюємо на об’єкт учня.
        for row in pd.read_csv(path).to_dict("records"):
            student = Student(row)
            name = student.class_name
            if name not in self.classes:
                self.classes[name] = SchoolClass(name)
            self.classes[name].students.append(student)

    def to_frame(self) -> pd.DataFrame:
        rows = []
        for classroom in self.classes.values():
            for student in classroom.students:
                rows.append(student.to_dict())
        return pd.DataFrame(rows, columns=FIELDS)

    def promote(self) -> int:
        new_classes = {}
        graduates = 0
        for classroom in self.classes.values():
            if classroom.number < 11:
                classroom.promote()
                new_classes[classroom.name()] = classroom
            else:
                graduates += len(classroom.students)
        self.classes = new_classes
        return graduates


def main() -> None:
    st.set_page_config(page_title="Сценарій 1", layout="wide")
    st.title("Сценарій 1. Учні школи")
    if "school" not in st.session_state:
        try:
            st.session_state.school = School(FILE)
        except (OSError, ValueError, KeyError) as error:
            st.error(f"Не вдалося прочитати school_students_db.csv: {error}")
            st.stop()
        st.session_state.done = False
    school = st.session_state.school

    st.write("Випускний клас: 11-й. Записи 12-х класів також вибувають при переведенні.")
    if st.button("Перевести класи", disabled=st.session_state.done):
        st.session_state.graduates = school.promote()
        st.session_state.done = True
        st.rerun()
    if st.button("Початкові дані"):
        del st.session_state.school
        st.rerun()
    if st.session_state.done:
        st.write("Вибуло учнів 11-х та 12-х класів:", st.session_state.graduates)

    data = school.to_frame()
    if data.empty:
        st.info("У школі немає учнів.")
        st.stop()
    sizes = data.groupby("class_name").size()
    boys = (data["gender"] == "M").sum()
    girls = (data["gender"] == "F").sum()
    st.write("Загальна кількість учнів:", len(data))
    st.write("Кількість класів:", len(sizes))
    st.write("Хлопці, %:", round(boys / len(data) * 100, 2))
    st.write("Дівчата, %:", round(girls / len(data) * 100, 2))
    st.write("Середня кількість учнів у класі:", round(sizes.mean(), 2))
    st.write("Найбільші класи:", ", ".join(sizes[sizes == sizes.max()].index), "; учнів:", int(sizes.max()))
    st.write("Найменші класи:", ", ".join(sizes[sizes == sizes.min()].index), "; учнів:", int(sizes.min()))

    # Для графіків окремо виділяємо номер та літеру класу.
    data["Паралель"] = data["class_name"].str.split("-").str[0].astype(int)
    data["Літера"] = data["class_name"].str.split("-").str[1]
    class_sizes = data.groupby(["class_name", "Літера"]).size().reset_index(name="Учнів")
    left, right = st.columns(2)
    left.subheader("Учні за паралелями")
    left.bar_chart(data.groupby("Паралель").size().rename("Учнів"), height=220)
    right.subheader("Середня наповненість за літерами")
    right.bar_chart(class_sizes.groupby("Літера")["Учнів"].mean(), height=220)
    left.subheader("Роки народження")
    left.line_chart(data.groupby("year_birth").size().rename("Учнів"), height=220)
    right.subheader("Оцінки за класами")
    right.scatter_chart(data, x="Паралель", y="average_mark", color="Літера", height=220)
    st.caption("На scatter-графіку номер паралелі та колір літери разом позначають клас.")
    if st.checkbox("Показати таблицю учнів"):
        st.dataframe(data[FIELDS], hide_index=True)
    st.caption("Переведення змінює дані у пам’яті. Початковий CSV залишається без змін.")


if __name__ == "__main__":
    main()
