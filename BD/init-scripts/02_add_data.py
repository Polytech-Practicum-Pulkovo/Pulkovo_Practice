import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()

# Параметры подключения к БД
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

# Путь к файлу Excel
EXCEL_PATH = "matrix.xlsx"

# Подключение к БД
conn = psycopg2.connect(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
    client_encoding='UTF8'
)
conn.autocommit = True
cursor = conn.cursor()

# --- Вспомогательные функции ---

def get_or_create_department(code, name, full_name):
    cursor.execute(
        """
        INSERT INTO department (code, name, full_name)
        VALUES (%s, %s, %s)
        ON CONFLICT (code) DO UPDATE
            SET name = EXCLUDED.name,
                full_name = EXCLUDED.full_name
        RETURNING id_department
        """,
        (code, name, full_name)
    )
    return cursor.fetchone()[0]

def get_or_create_position(name):
    cursor.execute("SELECT id_position FROM position WHERE name = %s", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO position (name) VALUES (%s) RETURNING id_position",
        (name,)
    )
    return cursor.fetchone()[0]

def get_or_create_training_type(name):
    cursor.execute("SELECT id_type FROM training_type WHERE name = %s", (name,))
    row = cursor.fetchone()
    if row:
        return row[0]
    cursor.execute(
        "INSERT INTO training_type (name) VALUES (%s) RETURNING id_type",
        (name,)
    )
    return cursor.fetchone()[0]

def get_or_create_program(program_code, name, id_type, time_period, time_to_complete=None):
    cursor.execute(
        """
        INSERT INTO program (program_code, name, id_type, time_to_complete, time_period, is_empty, is_active)
        VALUES (%s, %s, %s, %s, %s, false, true)
        ON CONFLICT (program_code) DO UPDATE
            SET name = EXCLUDED.name,
                id_type = EXCLUDED.id_type,
                time_to_complete = EXCLUDED.time_to_complete,
                time_period = EXCLUDED.time_period
        RETURNING id_program
        """,
        (program_code, name, id_type, time_to_complete, time_period)
    )
    return cursor.fetchone()[0]

# --- 1. Чтение Excel и загрузка справочников ---

df = pd.read_excel(EXCEL_PATH, sheet_name=0)
print("Доступные колонки в Excel:", df.columns.tolist())

# Поиск колонки с периодичностью
period_col = None
possible_names = ['Периодичность', 'Периодичность (мес)', 'Период', 'Период (мес)', 'Периодичность обучения']
for col in df.columns:
    if col.strip() in possible_names or 'период' in col.lower():
        period_col = col
        break

if period_col is None:
    print("Колонка 'Периодичность' не найдена, используем None")
else:
    print(f"Найдена колонка для периода: '{period_col}'")

# Кэши для избежания дублирующих запросов
departments_cache = {}
positions_cache = {}
training_types_cache = {}
programs_cache = {}

for index, row in df.iterrows():
    code = str(row['Код подразделения']).strip()
    dep_name = str(row['Наименование подразделения']).strip()
    full_name = str(row['Развернутое подразделение']).strip()
    position_name = str(row['Наименование должности']).strip()
    training_type_name = str(row['Тип обучения']).strip()
    
    if period_col is not None and pd.notna(row[period_col]):
        period = int(row[period_col])
    else:
        period = None

    program_code = str(row['Номер программы']).strip()
    program_name = str(row['Наименование программы']).strip()

    # Отдел
    if code not in departments_cache:
        dep_id = get_or_create_department(code, dep_name, full_name)
        departments_cache[code] = dep_id
    else:
        dep_id = departments_cache[code]

    # Должность
    if position_name not in positions_cache:
        pos_id = get_or_create_position(position_name)
        positions_cache[position_name] = pos_id
    else:
        pos_id = positions_cache[position_name]

    # Тип обучения
    if training_type_name not in training_types_cache:
        type_id = get_or_create_training_type(training_type_name)
        training_types_cache[training_type_name] = type_id
    else:
        type_id = training_types_cache[training_type_name]

    # Программа
    if program_code not in programs_cache:
        prog_id = get_or_create_program(program_code, program_name, type_id, period, None)
        programs_cache[program_code] = prog_id
    else:
        prog_id = programs_cache[program_code]

print("Основные справочники загружены.")

# --- 2. Генерация тестовых данных (новый подход) ---

def generate_test_data():
    # Получаем существующие отделы, должности, типы обучения
    cursor.execute("SELECT id_department FROM department LIMIT 1")
    dep_row = cursor.fetchone()
    if not dep_row:
        print("Нет отделов, создайте их из Excel")
        return
    dep_id = dep_row[0]

    cursor.execute("SELECT id_position FROM position LIMIT 1")
    pos_row = cursor.fetchone()
    if not pos_row:
        print("Нет должностей, создайте их из Excel")
        return
    pos_id = pos_row[0]

    cursor.execute("SELECT id_type FROM training_type LIMIT 1")
    type_row = cursor.fetchone()
    if not type_row:
        # Создаём тип обучения, если нет
        cursor.execute(
            "INSERT INTO training_type (name) VALUES ('Тестовый тип') RETURNING id_type"
        )
        type_id = cursor.fetchone()[0]
    else:
        type_id = type_row[0]

    # Создаём программу с кодом 'TEST_PROGRAM'
    program_code = 'TEST_PROGRAM'
    program_name = 'Тестовая программа'
    time_period = 36  # можно взять из Excel, но для теста 36
    prog_id = get_or_create_program(program_code, program_name, type_id, time_period, None)

    # Создаём сотрудника (один)
    first_name = 'Тест'
    last_name = 'Тестов'
    middle_name = 'Тестович'
    email = 'test@example.com'
    password_hash = 'test_hash'
    employee_number = 9999  # уникальный номер

    cursor.execute(
        """
        INSERT INTO employee (id_department, id_position, employee_number, first_name, last_name, middle_name, email, password_hash)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (employee_number) DO NOTHING
        RETURNING id_employee
        """,
        (dep_id, pos_id, employee_number, first_name, last_name, middle_name, email, password_hash)
    )
    emp_row = cursor.fetchone()
    if emp_row:
        emp_id = emp_row[0]
        print(f"Создан сотрудник: {first_name} {last_name} (ID: {emp_id})")
    else:
        cursor.execute("SELECT id_employee FROM employee WHERE employee_number = %s", (employee_number,))
        emp_id = cursor.fetchone()[0]
        print(f"Сотрудник с номером {employee_number} уже существует, ID: {emp_id}")

    # Создаём тему
    topic_name = 'Тестовая тема'
    cursor.execute(
        "INSERT INTO topic (id_program, name) VALUES (%s, %s) RETURNING id_topic",
        (prog_id, topic_name)
    )
    topic_id = cursor.fetchone()[0]
    print(f"Создана тема: '{topic_name}' (ID: {topic_id})")


    script_dir = os.path.dirname(os.path.abspath(__file__))      
    project_root = os.path.dirname(os.path.dirname(script_dir)) 
    file_path = os.path.join(project_root, 'catalogs', 'regulations_main.pdf')
    # Проверим существование файла (необязательно)
    if not os.path.exists(file_path):
        print(f"Предупреждение: файл {file_path} не найден, но ссылка будет сохранена.")
    cursor.execute(
        "INSERT INTO learning_material (id_topic, file_link) VALUES (%s, %s)",
        (topic_id, file_path)
    )
    print(f"Добавлен материал с файлом: {file_path}")

    print("Тестовая программа, сотрудник, тема и материал успешно созданы.")

# Запускаем генерацию тестовых данных
generate_test_data()

# Закрываем соединение
cursor.close()
conn.close()
print("Скрипт завершён.")