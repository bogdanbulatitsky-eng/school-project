"""Сценарій 2: розрахунок зарплат і збереження умов праці."""
from pathlib import Path
import pandas as pd
import streamlit as st

FILE = Path(__file__).with_name("school_employees_db.csv")


class Employee:
    def __init__(self, full_name: str, base_rate: float, work_experience: float,
                 driving_experience: float = 0) -> None:
        self.full_name = full_name
        self.base_rate = base_rate
        self.work_experience = work_experience
        self.driving_experience = driving_experience


class Director(Employee):
    def calculate_salary(self) -> float:
        return round(self.base_rate * self.work_experience / 50 + self.driving_experience * 500, 2)


class Teacher(Employee):
    def calculate_salary(self) -> float:
        return round(self.base_rate * self.work_experience / 30, 2)


class SecurityGuard(Employee):
    def calculate_salary(self) -> float:
        return round(self.base_rate + self.work_experience * 250, 2)


def main() -> None:
    st.set_page_config(page_title="Сценарій 2", layout="wide")
    st.title("Сценарій 2. Зарплати працівників")
    try:
        data = pd.read_csv(FILE)
    except (OSError, ValueError) as error:
        st.error(f"Не вдалося прочитати school_employees_db.csv: {error}")
        st.stop()
    if data.empty:
        st.info("У базі немає працівників.")
        st.stop()

    index = st.selectbox("Оберіть працівника", data.index,
                         format_func=lambda i: f"{data.loc[i, 'employees_id']}: "
                         f"{data.loc[i, 'last_name']} {data.loc[i, 'first_name']} ({data.loc[i, 'position']})")
    row = data.loc[index]
    rate = st.number_input("Базова ставка", min_value=0.0, value=float(row["base_rate"]), key=f"rate_{index}")
    work = st.number_input("Стаж роботи, років", min_value=0.0, value=float(row["work_experience"]), key=f"work_{index}")
    management = float(row["driving_experience"])
    name = row["last_name"] + " " + row["first_name"]
    if row["position"] == "Директор":
        management = st.number_input("Стаж керування, років", min_value=0.0,
                                     value=management, key=f"management_{index}")
        employee = Director(name, rate, work, management)
    elif row["position"] == "Вчитель":
        employee = Teacher(name, rate, work)
    elif row["position"] == "Охоронець":
        employee = SecurityGuard(name, rate, work)
    else:
        st.error("Невідома посада працівника.")
        st.stop()
    salary = employee.calculate_salary()
    st.write("Розрахована зарплата, грн:", salary)

    if st.button("Зберегти зміни"):
        updated = data.copy()
        updated.loc[index, ["base_rate", "work_experience", "driving_experience", "salary"]] = [rate, work, management, salary]
        # Спочатку записуємо тимчасовий файл, потім замінюємо основну базу.
        temporary = FILE.with_suffix(".tmp")
        try:
            updated.to_csv(temporary, index=False, encoding="utf-8-sig")
            temporary.replace(FILE)
        except OSError as error:
            st.error(f"Не вдалося зберегти зміни: {error}")
        else:
            data = updated
            st.success("Дані збережено у school_employees_db.csv.")
    st.dataframe(data, hide_index=True)
    st.download_button("Завантажити CSV", data.to_csv(index=False).encode("utf-8-sig"),
                       "school_employees_db.csv", "text/csv", on_click="ignore")


if __name__ == "__main__":
    main()
