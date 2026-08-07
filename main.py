import flet as ft
import sqlite3
import uuid
import os
import pandas as pd
from datetime import datetime

DB_NAME = "app_database.db"

# --- 1. توابع محاسباتی و تاریخ شمسی (دقیقاً طبق منطق کد اولیه) ---

def normalize_persian_text(text):
    if not text:
        return ""
    translation_table = str.maketrans({
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9',
        '٠': '0', '١': '1', '٢': '2', '٣': '3', '٤': '4',
        '٥': '5', '٦': '6', '٧': '7', '٨': '8', '٩': '9',
        '-': '/'
    })
    return str(text).translate(translation_table).strip()

def gregorian_to_jalali(gy, gm, gd):
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = (gy + 1) if gm > 2 else gy
    days = (365 * gy) + ((gy2 + 3) // 4) - ((gy2 + 99) // 100) + ((gy2 + 399) // 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + (days // 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + ((days - 186) // 30)
        jd = 1 + ((days - 186) % 30)
    return f"{jy}/{jm:02d}/{jd:02d}"

def get_current_jalali_date():
    now = datetime.now()
    return gregorian_to_jalali(now.year, now.month, now.day)

# --- 2. آماده‌سازی پایگاه داده ---

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            personnel_code TEXT,
            department TEXT,
            phone TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            username TEXT,
            title TEXT,
            action_type TEXT,
            priority TEXT,
            jalali_date TEXT,
            description TEXT,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assigned_tasks (
            id TEXT PRIMARY KEY,
            username TEXT,
            title TEXT,
            description TEXT,
            deadline TEXT,
            priority TEXT,
            status TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', 'admin123')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('action_types', 'بررسی,پیگیری,جلسه,توسعه,سایر')")
    conn.commit()
    conn.close()

# --- 3. برنامه اصلی و رابط کاربری (Flet UI) ---

def main(page: ft.Page):
    init_db()
    page.title = "سامانه مدیریت گزارش‌ها"
    page.rtl = True
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO

    current_user = {"username": None, "is_admin": False}

    def get_action_types():
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key='action_types'")
        row = cursor.fetchone()
        conn.close()
        return row[0].split(',') if row else ["عمومی"]

    # --- صفحات برنامه ---

    def show_login():
        page.clean()
        
        user_input = ft.TextField(label="نام کاربری", width=300)
        pass_input = ft.TextField(label="رمز عبور", password=True, can_reveal_password=True, width=300)
        msg_text = ft.Text(color=ft.colors.RED_500)

        def handle_login(e):
            username = normalize_persian_text(user_input.value)
            password = pass_input.value

            if not username or not password:
                msg_text.value = "لطفاً تمام فیلدها را پر کنید"
                page.update()
                return

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE username=?", (username,))
            user = cursor.fetchone()
            conn.close()

            if user:
                if user[0] == password:
                    current_user["username"] = username
                    current_user["is_admin"] = False
                    show_expert_panel()
                else:
                    msg_text.value = "رمز عبور اشتباه است"
            else:
                # ثبت‌نام کاربر جدید
                show_register(username, password)
            page.update()

        def handle_admin_login(e):
            password = pass_input.value
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key='admin_password'")
            admin_pwd = cursor.fetchone()[0]
            conn.close()

            if password == admin_pwd:
                current_user["username"] = "مدیر"
                current_user["is_admin"] = True
                show_admin_panel()
            else:
                msg_text.value = "رمز مدیریت اشتباه است"
            page.update()

        page.add(
            ft.Column(
                [
                    ft.Text("ورود به سامانه مدیریت گزارش‌ها", size=22, weight=ft.FontWeight.BOLD),
                    user_input,
                    pass_input,
                    ft.ElevatedButton("ورود / ثبت‌نام کارشناس", on_click=handle_login, width=300),
                    ft.OutlinedButton("ورود مدیریت", on_click=handle_admin_login, width=300),
                    msg_text
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    def show_register(username, password):
        page.clean()
        p_code = ft.TextField(label="کد پرسنلی", width=300)
        dept = ft.TextField(label="دپارتمان / واحد", width=300)
        phone = ft.TextField(label="شماره تماس", width=300)

        def save_user(e):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?)",
                (username, password, p_code.value, dept.value, phone.value)
            )
            conn.commit()
            conn.close()
            current_user["username"] = username
            current_user["is_admin"] = False
            show_expert_panel()

        page.add(
            ft.Column(
                [
                    ft.Text(f"تکمیل اطلاعات ثبت‌نام برای {username}", size=18, weight=ft.FontWeight.BOLD),
                    p_code, dept, phone,
                    ft.ElevatedButton("ثبت و ورود", on_click=save_user, width=300)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    def show_expert_panel():
        page.clean()

        title_in = ft.TextField(label="عنوان فعالیت", width=400)
        action_dropdown = ft.Dropdown(
            label="نوع اقدام",
            options=[ft.dropdown.Option(x) for x in get_action_types()],
            width=200
        )
        priority_dropdown = ft.Dropdown(
            label="اولویت",
            options=[ft.dropdown.Option("عادی"), ft.dropdown.Option("مهم"), ft.dropdown.Option("فوری")],
            value="عادی",
            width=180
        )
        desc_in = ft.TextField(label="شرح فعالیت", multiline=True, width=400, min_lines=3)
        status_dropdown = ft.Dropdown(
            label="وضعیت",
            options=[ft.dropdown.Option("انجام شده"), ft.dropdown.Option("در حال انجام"), ft.dropdown.Option("معوق")],
            value="انجام شده",
            width=200
        )
        msg_text = ft.Text()

        def submit_report(e):
            if not title_in.value or not action_dropdown.value:
                msg_text.value = "عنوان و نوع اقدام الزامی است"
                msg_text.color = ft.colors.RED_500
                page.update()
                return

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    current_user["username"],
                    title_in.value,
                    action_dropdown.value,
                    priority_dropdown.value,
                    get_current_jalali_date(),
                    desc_in.value,
                    status_dropdown.value
                )
            )
            conn.commit()
            conn.close()

            title_in.value = ""
            desc_in.value = ""
            msg_text.value = "گزارش با موفقیت ثبت شد"
            msg_text.color = ft.colors.GREEN_500
            load_reports_list()
            page.update()

        reports_list = ft.Column()

        def load_reports_list():
            reports_list.controls.clear()
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT title, action_type, priority, jalali_date, status FROM reports WHERE username=? ORDER BY jalali_date DESC", (current_user["username"],))
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                reports_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(f"عنوان: {r[0]}", weight=ft.FontWeight.BOLD),
                                ft.Text(f"نوع: {r[1]} | اولویت: {r[2]} | تاریخ: {r[3]} | وضعیت: {r[4]}")
                            ])
                        )
                    )
                )

        load_reports_list()

        page.add(
            ft.AppBar(title=ft.Text(f"پنل کارشناس: {current_user['username']}"), actions=[ft.IconButton(ft.icons.LOGOUT, on_click=lambda e: show_login())]),
            ft.Text("ثبت گزارش جدید", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([title_in, action_dropdown, priority_dropdown], wrap=True),
            desc_in,
            ft.Row([status_dropdown, ft.ElevatedButton("ثبت گزارش", on_click=submit_report)]),
            msg_text,
            ft.Divider(),
            ft.Text("گزارش‌های ثبت شده شما", size=18, weight=ft.FontWeight.BOLD),
            reports_list
        )

    def show_admin_panel():
        page.clean()

        all_reports_list = ft.Column()
        search_in = ft.TextField(label="جستجو بر اساس کارشناس / کلیدواژه / تاریخ", width=300)

        def load_all_reports(e=None):
            all_reports_list.controls.clear()
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()

            query = "SELECT username, title, action_type, priority, jalali_date, status FROM reports"
            params = []
            if search_in.value:
                val = f"%{search_in.value}%"
                query += " WHERE username LIKE ? OR title LIKE ? OR description LIKE ? OR jalali_date LIKE ?"
                params = [val, val, val, val]

            query += " ORDER BY jalali_date DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                all_reports_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(f"کارشناس: {r[0]} | عنوان: {r[1]}", weight=ft.FontWeight.BOLD),
                                ft.Text(f"نوع: {r[2]} | اولویت: {r[3]} | تاریخ: {r[4]} | وضعیت: {r[5]}")
                            ])
                        )
                    )
                )
            page.update()

        load_all_reports()

        page.add(
            ft.AppBar(title=ft.Text("پنل مدیریت سیستم"), actions=[ft.IconButton(ft.icons.LOGOUT, on_click=lambda e: show_login())]),
            ft.Row([search_in, ft.ElevatedButton("جستجو", on_click=load_all_reports)]),
            ft.Divider(),
            ft.Text("کلیه گزارش‌های سیستم", size=18, weight=ft.FontWeight.BOLD),
            all_reports_list
        )

    show_login()

ft.app(target=main)
