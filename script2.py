"""Сценарій 2. Запуск: python -m streamlit run script2.py."""
import csv
import os
import tempfile
from math import isfinite
from pathlib import Path

import pandas as pd
import streamlit as st

CSV_PATH = Path(__file__).with_name("school_employees_db.csv")
FIELDS = ["employees_id", "first_name", "last_name", "position", "base_rate",
          "work_experience", "driving_experience", "salary"]


class Employee:
    def __init__(self, row: dict) -> None:
        self.employees_id = int(row["employees_id"])
        self.first_name = row["first_name"]
        self.last_name = row["last_name"]
        self.position = row["position"]
        self.base_rate = float(row["base_rate"])
        self.work_experience = float(row["work_experience"])
        self.driving_experience = float(row["driving_experience"])

    def calculate_salary(self) -> float:
        return round(self.base_rate, 2)


class Teacher(Employee):
    def calculate_salary(self) -> float:
        return round(self.base_rate * self.work_experience / 30, 2)


class Director(Teacher):
    def calculate_salary(self) -> float:
        return round(self.base_rate * self.work_experience / 50 + self.driving_experience * 500, 2)


class SecurityGuard(Employee):
    def calculate_salary(self) -> float:
        return round(self.base_rate + self.work_experience * 250, 2)


def make_employee(row: dict) -> Employee:
    employee_class = {"Директор": Director, "Вчитель": Teacher, "Охоронець": SecurityGuard}
    return employee_class[row["position"]](row)


def read_employees(path: Path = CSV_PATH) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames != FIELDS:
            raise ValueError("Заголовки CSV мають бути: " + ",".join(FIELDS))
        rows = list(reader)
    ids = set()
    for line, row in enumerate(rows, start=2):
        try:
            employee = make_employee(row)
            if employee.employees_id in ids:
                raise ValueError("Повторюється ID працівника.")
            ids.add(employee.employees_id)
            for field in ("base_rate", "work_experience", "driving_experience", "salary"):
                value = float(row[field])
                if not isfinite(value) or value < 0:
                    raise ValueError(f"{field}: потрібне скінченне невід’ємне число.")
            if not row["first_name"].strip() or not row["last_name"].strip():
                raise ValueError("Ім’я і прізвище не можуть бути порожніми.")
            if None in row:
                raise ValueError("Зайві значення у рядку CSV.")
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise ValueError(f"Рядок {line}: {error}") from error
    return rows


def save_employee(original: dict, base_rate: float, work_experience: float,
                  driving_experience: float, path: Path = CSV_PATH) -> float:
    """Оновити один запис; основний CSV замінюється тільки після повного запису."""
    values = (base_rate, work_experience, driving_experience)
    if any(not isfinite(value) or value < 0 for value in values):
        raise ValueError("Ставка та стаж мають бути скінченними невід’ємними числами.")
    rows = read_employees(path)  # Читаємо актуальну базу перед збереженням.
    current = next((row for row in rows if row["employees_id"] == original["employees_id"]), None)
    if current != original:
        raise ValueError("Запис працівника змінився або був видалений. Оновіть сторінку й повторіть редагування.")
    employee = make_employee(current)
    employee.base_rate = base_rate
    employee.work_experience = work_experience
    employee.driving_experience = driving_experience
    salary = employee.calculate_salary()
    if not isfinite(salary):
        raise ValueError("Значення надто великі для розрахунку зарплати.")
    current.update(base_rate=str(base_rate), work_experience=str(work_experience),
                   driving_experience=str(driving_experience), salary=f"{salary:.2f}")
    temporary_path = None
    try:
        # Тимчасовий файл створюється в тій самій папці, що й база.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="",
                                         dir=path.parent, prefix=".employees_", suffix=".tmp", delete=False) as file:
            temporary_path = Path(file.name)
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    return salary


def main() -> None:
    st.set_page_config(page_title="Зарплати працівників", layout="wide")
    st.title("Зарплати та умови праці")
    st.caption("База: school_employees_db.csv · Зміни зберігаються у цей самий файл.")
    try:
        rows = read_employees()
    except (OSError, ValueError) as error:
        st.error(f"Не вдалося відкрити базу працівників: {error}")
        st.stop()
    if not rows:
        st.info("У базі немає працівників.")
        st.stop()
    if "saved_message" in st.session_state:
        st.success(st.session_state.pop("saved_message"))

    by_id = {row["employees_id"]: row for row in rows}
    selected_id = st.selectbox("Виберіть працівника", list(by_id),
                               format_func=lambda key: f"ID {key} · {by_id[key]['last_name']} "
                                                       f"{by_id[key]['first_name']} · {by_id[key]['position']}")
    selected = by_id[selected_id]
    employee = make_employee(selected)
    st.subheader(f"{employee.last_name} {employee.first_name} — {employee.position}")
    # Ключі містять ID: умови одного працівника не переходять до іншого.
    base_rate = st.number_input("Базова ставка, грн", min_value=0.0, value=employee.base_rate,
                                step=100.0, key=f"base_{selected_id}")
    work_label = "Загальний стаж роботи, років" if isinstance(employee, SecurityGuard) else "Педагогічний стаж, років"
    work_experience = st.number_input(work_label, min_value=0.0, value=employee.work_experience,
                                      step=1.0, key=f"work_{selected_id}")
    # Для інших посад поле з CSV зберігаємо без змін, хоча формула його не використовує.
    driving_experience = employee.driving_experience
    if isinstance(employee, Director):
        driving_experience = st.number_input("Стаж керування, років", min_value=0.0,
                                             value=employee.driving_experience, step=1.0,
                                             key=f"management_{selected_id}")
        st.write("Формула: ставка × педагогічний стаж / 50 + стаж керування × 500.")
    elif isinstance(employee, SecurityGuard):
        st.write("Формула: ставка + загальний стаж × 250.")
    else:
        st.write("Формула: ставка × педагогічний стаж / 30.")
    employee.base_rate, employee.work_experience = base_rate, work_experience
    employee.driving_experience = driving_experience
    salary = employee.calculate_salary()
    st.metric("Зарплата за введеними умовами, грн", f"{salary:.2f}")
    st.caption(f"Збережена зарплата: {float(selected['salary']):.2f} грн. "
               "Попередній перегляд не змінює CSV до натискання кнопки.")

    if st.button("Розрахувати та зберегти", type="primary"):
        try:
            saved_salary = save_employee(selected, base_rate, work_experience, driving_experience)
        except (OSError, ValueError) as error:
            st.error(f"Зміни не збережено: {error}")
        else:
            st.session_state.saved_message = (f"Дані працівника ID {selected_id} збережено. "
                                              f"Зарплата: {saved_salary:.2f} грн.")
            st.rerun()
    st.subheader("Актуальна таблиця працівників")
    frame = pd.DataFrame(rows, columns=FIELDS)
    display = frame.copy()
    for field in ("employees_id", "base_rate", "work_experience", "driving_experience", "salary"):
        display[field] = pd.to_numeric(display[field])
    display = display.rename(columns={"employees_id": "ID", "first_name": "Ім’я", "last_name": "Прізвище",
                                     "position": "Посада", "base_rate": "Базова ставка",
                                     "work_experience": "Стаж роботи", "driving_experience": "Стаж керування",
                                     "salary": "Зарплата"})
    st.dataframe(display, hide_index=True)
    st.download_button("Завантажити актуальну базу працівників (CSV)",
                       frame.to_csv(index=False).encode("utf-8-sig"), "school_employees_db.csv", "text/csv",
                       on_click="ignore")


if __name__ == "__main__":
    main()
