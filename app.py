import pandas as pd
import streamlit as st
import os
import json
from datetime import datetime
from hashlib import sha256
import pytz

# Пути к файлам
USERS_FILE = "users.json"
PLAYERS_FILE = "players.json"
SUPERVISORS_FILE = "supervisors.json"
STATUSES_FILE = "statuses.json"

# Инициализация файлов, если они отсутствуют
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({"123": {"password": sha256("Admin$2024!Secure".encode()).hexdigest(), "role": "admin"}}, f)

if not os.path.exists(PLAYERS_FILE):
    with open(PLAYERS_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(SUPERVISORS_FILE):
    with open(SUPERVISORS_FILE, "w") as f:
        json.dump(["qwe123"], f)

if not os.path.exists(STATUSES_FILE):
    with open(STATUSES_FILE, "w") as f:
        json.dump({}, f)

# Загрузка данных из файлов
with open(USERS_FILE, "r") as f:
    users = json.load(f)

with open(PLAYERS_FILE, "r") as f:
    steam_id_to_name_supervisor = json.load(f)

with open(SUPERVISORS_FILE, "r") as f:
    supervisors = json.load(f)

with open(STATUSES_FILE, "r") as f:
    player_statuses = json.load(f)

# Сохранение данных
def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def save_players():
    with open(PLAYERS_FILE, "w") as f:
        json.dump(steam_id_to_name_supervisor, f)

def save_supervisors():
    with open(SUPERVISORS_FILE, "w") as f:
        json.dump(supervisors, f)

def save_statuses():
    with open(STATUSES_FILE, "w") as f:
        json.dump(player_statuses, f)

# Преобразование SteamID64 в формат STEAM_1:X:Y
def steamid64_to_steamid(steamid64):
    try:
        steamid64 = int(steamid64)
        base_id = 76561197960265728
        account_id = steamid64 - base_id
        y = account_id % 2
        z = account_id // 2
        return f"STEAM_1:{y}:{z}"
    except (ValueError, TypeError):
        return None

# Функция для корректировки формата STEAM_0:X:Y на STEAM_1:X:Y
def fix_steamid_format(steamid):
    if steamid.startswith("STEAM_0:"):
        return steamid.replace("STEAM_0:", "STEAM_1:", 1)
    return steamid

# Проверка и удаление статусов по дате окончания
def check_and_clean_statuses():
    today = datetime.now().date()
    to_remove = [steam_id for steam_id, details in player_statuses.items()
                 if datetime.strptime(details["end_date"], "%Y-%m-%d").date() < today]
    for steam_id in to_remove:
        del player_statuses[steam_id]
    save_statuses()

# Получение нормы тикетов для игрока
def get_ticket_quota(status_details, day_of_week):
    default_quota = 60
    reduced_quota = 30  # Пониженная норма
    if status_details.get("status") in ["отпуск", "мороз"]:
        return 0
    if status_details.get("return_day") == day_of_week:
        return reduced_quota
    return default_quota

# Авторизация
def authenticate_user(username, password):
    hashed_password = sha256(password.encode()).hexdigest()
    user = users.get(username)
    if user and user["password"] == hashed_password:
        return user["role"]
    return None

# Проверка роли пользователя
def is_admin():
    return st.session_state.get("role") == "admin"

def is_supervisor():
    return st.session_state.get("role") == "следящий"

# Состояние авторизации
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None

if not st.session_state["authenticated"]:
    st.title("Авторизация")
    username = st.text_input("Логин:", key="login_input")
    password = st.text_input("Пароль:", type="password", key="password_input")
    if st.button("Войти", key="login_button"):
        role = authenticate_user(username, password)
        if role:
            st.session_state["authenticated"] = True
            st.session_state["role"] = role
            st.success(f"Добро пожаловать, {username}!")
        else:
            st.error("Неверный логин или пароль.")
else:
    # Очистка истёкших статусов
    check_and_clean_statuses()

    # Кнопка выхода
    if st.button("Выйти", key="logout_button"):
        st.session_state.clear()
        st.stop()

    # Интерфейс после авторизации
    st.title("Система управления тикетами")

    if is_admin():
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            "Статистика тикетов",
            "Добавление игрока",
            "Удаление игрока",
            "Управление статусами",
            "Регистрация следящего",
            "Удаление следящего"
        ])
    elif is_supervisor():
        tab1, tab2, tab3, tab4 = st.tabs([
            "Статистика тикетов",
            "Добавление игрока",
            "Удаление игрока",
            "Управление статусами"
        ])

    # Вкладка 1: Статистика тикетов
    with tab1:
        st.subheader("Статистика тикетов")
        uploaded_file = st.file_uploader("Загрузите CSV-файл статистики", type="csv", key="upload_stats")

        if uploaded_file:
            data = pd.read_csv(uploaded_file)
            data['SteamID'] = data['SteamID'].astype(str)
            data['FormattedSteamID'] = data['SteamID'].apply(steamid64_to_steamid)

            selected_supervisor = st.selectbox("Выберите следящего:", supervisors, key="select_supervisor_stats")
            day_choice = st.radio("Выберите день:", ["Четверг", "Воскресенье"], key="day_choice_stats")
            today_date = datetime.now().strftime("%d.%m.%Y")

            ticket_column = "WeekAmount"
            filtered_ids = [
                steam_id for steam_id, details in steam_id_to_name_supervisor.items()
                if details["supervisor"] == selected_supervisor
            ]
            filtered_data = data[data['FormattedSteamID'].isin(filtered_ids)]

            # Отображаем статистику игроков
            st.subheader("Статистика игроков:")
            player_stats = []
            for _, row in filtered_data.iterrows():
                steam_id = row['FormattedSteamID']
                nickname = steam_id_to_name_supervisor.get(steam_id, {}).get("name", "Unknown")
                tickets = row.get(ticket_column, 0)
                status_details = player_statuses.get(steam_id, {})
                ticket_quota = get_ticket_quota(status_details, day_choice)

                # Добавляем информацию об отпуске/морозе
                status_text = ""
                if status_details.get("status") == "отпуск":
                    status_text = " (Отпуск 📅)"
                elif status_details.get("status") == "мороз":
                    status_text = " (Мороз ❄️)"

                player_stats.append(f"{nickname} - {tickets}{status_text}")

            # Отображаем статистику как список
            for stat in player_stats:
                st.write(stat)

            # Формируем отчет
            moscow_tz = pytz.timezone("Europe/Moscow")
            today_date = datetime.now(moscow_tz).strftime("%d.%m.%Y")
            report_lines = [
                f"# Статистика за {day_choice} состава \"{selected_supervisor}\" ({today_date})"
            ]
            for _, row in filtered_data.iterrows():
                steam_id = row['FormattedSteamID']
                discord = steam_id_to_name_supervisor.get(steam_id, {}).get("discord", "Unknown")
                tickets = row.get(ticket_column, 0)
                status_details = player_statuses.get(steam_id, {})

                if status_details.get("status") == "отпуск":
                    report_lines.append(f"@{discord} - Отпуск 📅")
                elif status_details.get("status") == "мороз":
                    report_lines.append(f"@{discord} - Мороз ❄️")
                else:
                    if day_choice == "Воскресенье":
                        if tickets >= 60:
                            status = "[отыграл норму] ✅"
                        elif 50 <= tickets < 60:
                            status = "[ничего не делаем] ✅"
                        elif 35 <= tickets < 50:
                            status = "[+1 предупреждение] ❌"
                        elif 15 <= tickets < 35:
                            status = "[+1 выговор] ❌"
                        else:
                            status = "[инактив, причину в ЛС] ❌"
                        report_lines.append(f"@{discord} - {tickets} тикетов {status}")
                    else:
                        report_lines.append(f"@{discord} - {tickets} тикетов")

            # Отображаем отчет
            report_text = "\n".join(report_lines)
            st.text_area("Отчет:", value=report_text, height=300, key="report_area")

    # Вкладка 2: Добавление игрока
    with tab2:
        st.subheader("Добавление игрока")
        new_steam_id = st.text_input("Введите SteamID64 или STEAM_1:X:Y:", key="add_player_steam_id")
        new_nickname = st.text_input("Введите никнейм:", key="add_player_nickname")
        new_discord = st.text_input("Введите Discord:", key="add_player_discord")
        new_supervisor = st.selectbox("Выберите следящего:", supervisors, key="add_player_supervisor")

        if st.button("Добавить игрока", key="add_player_button"):
            if new_steam_id and new_nickname and new_discord and new_supervisor:
                # Проверяем, если введён SteamID64, то конвертируем его в STEAM_1:X:Y
                if new_steam_id.startswith("STEAM_1:"):
                    formatted_id = new_steam_id
                else:
                    formatted_id = steamid64_to_steamid(new_steam_id)
                    if not formatted_id:
                        # Если это не SteamID64, проверяем на формат STEAM_0:X:Y
                        formatted_id = fix_steamid_format(new_steam_id)

                if not formatted_id:
                    st.error("Некорректный SteamID.")
                elif formatted_id not in steam_id_to_name_supervisor:
                    steam_id_to_name_supervisor[formatted_id] = {
                        "name": new_nickname,
                        "discord": new_discord,
                        "supervisor": new_supervisor
                    }
                    save_players()
                    st.success(f"Игрок {new_nickname} добавлен!")
                else:
                    st.error("Игрок с таким SteamID уже существует.")
            else:
                st.error("Заполните все поля.")

    # Вкладка 3: Удаление игрока
    with tab3:
        st.subheader("Удаление игрока")
        selected_supervisor = st.selectbox("Выберите следящего:", supervisors, key="delete_supervisor")
        players = {k: v for k, v in steam_id_to_name_supervisor.items() if v["supervisor"] == selected_supervisor}
        selected_player = st.selectbox("Выберите игрока:", [v["name"] for v in players.values()], key="delete_player")
        steam_id = next((k for k, v in players.items() if v["name"] == selected_player), None)

        if st.button("Удалить игрока", key="delete_player_button"):
            if steam_id:
                del steam_id_to_name_supervisor[steam_id]
                save_players()
                st.success(f"Игрок {selected_player} удалён.")
            else:
                st.error("Игрок не найден.")

    # Вкладка 4: Управление статусами
    with tab4:
        st.subheader("Управление статусами")
        selected_supervisor = st.selectbox("Выберите следящего:", supervisors, key="status_supervisor")
        players = {k: v for k, v in steam_id_to_name_supervisor.items() if v["supervisor"] == selected_supervisor}
        selected_player = st.selectbox("Выберите игрока:", [v["name"] for v in players.values()], key="status_player")
        steam_id = next((k for k, v in players.items() if v["name"] == selected_player), None)
        new_status = st.radio("Статус игрока:", ["Нет", "Отпуск", "Мороз"], key="status_choice")
        end_date = st.date_input("Дата окончания статуса:", key="status_end_date")

        if st.button("Обновить статус", key="update_status_button"):
            if new_status == "Нет":
                player_statuses.pop(steam_id, None)
                save_statuses()
                st.success(f"Статус для {selected_player} удалён.")
            else:
                player_statuses[steam_id] = {"status": new_status.lower(), "end_date": str(end_date)}
                save_statuses()
                st.success(f"Статус {new_status} установлен для {selected_player} до {end_date}.")

    # Вкладка 5: Регистрация следящего
    if is_admin():
        with tab5:
            st.subheader("Регистрация следящего")
            supervisor_login = st.text_input("Введите логин для следящего:", key="register_supervisor_login")
            supervisor_password = st.text_input("Введите пароль для следящего:", type="password", key="register_supervisor_password")

            if st.button("Зарегистрировать следящего", key="register_supervisor_button"):
                if supervisor_login and supervisor_password:
                    hashed_password = sha256(supervisor_password.encode()).hexdigest()
                    users[supervisor_login] = {"password": hashed_password, "role": "следящий"}
                    save_users()
                    supervisors.append(supervisor_login)
                    save_supervisors()
                    st.success(f"Следящий {supervisor_login} зарегистрирован.")
                else:
                    st.error("Заполните все поля.")

    # Вкладка 6: Удаление следящего
    if is_admin():
        with tab6:
            st.subheader("Удаление следящего")
            selected_supervisor = st.selectbox("Выберите следящего для удаления:", supervisors, key="remove_supervisor")
            if st.button("Удалить следящего", key="remove_supervisor_button"):
                supervisors.remove(selected_supervisor)
                save_supervisors()
                users.pop(selected_supervisor, None)
                save_users()
                st.success(f"Следящий {selected_supervisor} удалён.")
