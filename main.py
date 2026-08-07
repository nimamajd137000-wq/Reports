import flet as ft
import sqlite3
import uuid
import os
from datetime import datetime
import pandas as pd

DB_NAME = "app_database.db"

# --- 1. توابع محاسباتی، نرمال‌سازی و تاریخ شمسی ---

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

# --- 2. مدیریت پایگاه داده SQLite ---

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            full_name TEXT,
            personnel_code TEXT,
            department TEXT,
            phone TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id TEXT PRIMARY KEY,
            username TEXT,
            project_name TEXT,
            title TEXT,
            action_type TEXT,
            priority TEXT,
            progress INTEGER,
            start_time TEXT,
            end_time TEXT,
            jalali_date TEXT,
            description TEXT,
            status TEXT,
            score INTEGER,
            feedback TEXT,
            is_archived INTEGER DEFAULT 0
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
            status TEXT,
            assigned_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', '1234')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('action_types', 'بررسی,پیگیری,جلسه,توسعه,سایر')")
    conn.commit()
    conn.close()

    os.makedirs("profiles", exist_ok=True)
    os.makedirs("archive", exist_ok=True)

# --- 3. برنامه اصلی Flet ---

def main(page: ft.Page):
    init_db()
    page.title = "سامانه مدیریت گزارش‌ها و ارجاعات"
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

    def update_action_types(new_types):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE settings SET value=? WHERE key='action_types'", (new_types,))
        conn.commit()
        conn.close()

    # --- صفحه ورود / ثبت نام ---

    def show_login():
        page.clean()
        user_in = ft.TextField(label="نام کاربری", width=300)
        pass_in = ft.TextField(label="رمز عبور", password=True, can_reveal_password=True, width=300)
        msg_text = ft.Text(color=ft.colors.RED_500)

        def login_user(e):
            username = normalize_persian_text(user_in.value)
            password = pass_in.value
            if not username or not password:
                msg_text.value = "لطفاً تمامی فیلدها را وارد کنید"
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
                show_register(username, password)
            page.update()

        def login_admin(e):
            password = pass_in.value
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
                msg_text.value = "رمز مدیریت نادرست است (پیش‌فرض: 1234)"
            page.update()

        page.add(
            ft.Column(
                [
                    ft.Icon(ft.icons.ASSESSMENT_ROUNDED, size=60, color=ft.colors.BLUE_700),
                    ft.Text("سامانه مدیریت فعالیت‌ها و گزارش‌ها", size=20, weight=ft.FontWeight.BOLD),
                    user_in, pass_in,
                    ft.ElevatedButton("ورود / ثبت‌نام کارشناس", on_click=login_user, width=300),
                    ft.OutlinedButton("ورود مدیریت", on_click=login_admin, width=300),
                    msg_text
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    def show_register(username, password):
        page.clean()
        name_in = ft.TextField(label="نام و نام خانوادگی", width=300)
        code_in = ft.TextField(label="کد پرسنلی", width=300)
        dept_in = ft.TextField(label="واحد شغلی / دپارتمان", width=300)
        phone_in = ft.TextField(label="شماره تلفن", width=300)

        def save_register(e):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                (username, password, name_in.value, code_in.value, dept_in.value, phone_in.value)
            )
            conn.commit()
            conn.close()

            with open(f"profiles/{username}.txt", "w", encoding="utf-8") as f:
                f.write(f"Name: {name_in.value}\nCode: {code_in.value}\nDept: {dept_in.value}\nPhone: {phone_in.value}")

            current_user["username"] = username
            current_user["is_admin"] = False
            show_expert_panel()

        page.add(
            ft.Column(
                [
                    ft.Text(f"تکمیل پروفایل هوشمند کارشناس: {username}", size=18, weight=ft.FontWeight.BOLD),
                    name_in, code_in, dept_in, phone_in,
                    ft.ElevatedButton("ثبت و ورود به برنامه", on_click=save_register, width=300)
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER
            )
        )

    # --- پنل کارشناس ---

    def show_expert_panel():
        page.clean()

        # فرم ثبت گزارش
        proj_in = ft.TextField(label="نام پروژه", width=250)
        title_in = ft.TextField(label="عنوان فعالیت", width=250)
        
        action_opts = get_action_types()
        action_dropdown = ft.Dropdown(
            label="نوع اقدام",
            options=[ft.dropdown.Option(x) for x in action_opts],
            width=200
        )
        custom_action = ft.TextField(label="نوع اقدام جدید", width=200)

        priority_dropdown = ft.Dropdown(
            label="اولویت",
            options=[ft.dropdown.Option("عادی"), ft.dropdown.Option("مهم"), ft.dropdown.Option("فوری")],
            value="عادی",
            width=150
        )
        progress_in = ft.TextField(label="درصد پیشرفت", value="100", width=150)
        start_t = ft.TextField(label="زمان شروع", width=150)
        end_t = ft.TextField(label="زمان پایان", width=150)
        desc_in = ft.TextField(label="شرح کامل فعالیت", multiline=True, width=500, min_lines=3)
        status_dropdown = ft.Dropdown(
            label="وضعیت",
            options=[ft.dropdown.Option("انجام شده"), ft.dropdown.Option("در حال انجام"), ft.dropdown.Option("معوق")],
            value="انجام شده",
            width=200
        )
        msg_text = ft.Text()

        def submit_report(e):
            act_type = custom_action.value if custom_action.value else action_dropdown.value
            if not title_in.value or not act_type:
                msg_text.value = "عنوان و نوع اقدام الزامی است"
                msg_text.color = ft.colors.RED_500
                page.update()
                return

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                (
                    str(uuid.uuid4()),
                    current_user["username"],
                    proj_in.value,
                    title_in.value,
                    act_type,
                    priority_dropdown.value,
                    int(progress_in.value) if progress_in.value.isdigit() else 100,
                    start_t.value,
                    end_t.value,
                    get_current_jalali_date(),
                    desc_in.value,
                    status_dropdown.value,
                    None, None
                )
            )
            conn.commit()
            conn.close()

            if custom_action.value and custom_action.value not in action_opts:
                action_opts.append(custom_action.value)
                update_action_types(",".join(action_opts))

            msg_text.value = "گزارش با موفقیت ثبت شد"
            msg_text.color = ft.colors.GREEN_500
            filter_my_reports(None)
            page.update()

        # لیست و سیستم فیلتر گزارش‌های کارشناس
        search_keyword = ft.TextField(label="جستجو در کلیدواژه/عنوان/شرح", width=250)
        search_date = ft.TextField(label="فیلتر تاریخ (مثلاً 1403/01/15)", width=200)
        my_reports_list = ft.Column()

        def filter_my_reports(e):
            my_reports_list.controls.clear()
            kw = normalize_persian_text(search_keyword.value)
            dt = normalize_persian_text(search_date.value)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            query = "SELECT project_name, title, action_type, priority, progress, jalali_date, status, score, feedback, description FROM reports WHERE username=? AND is_archived=0"
            params = [current_user["username"]]

            if dt:
                query += " AND jalali_date LIKE ?"
                params.append(f"%{dt}%")
            if kw:
                query += " AND (title LIKE ? OR project_name LIKE ? OR description LIKE ?)"
                params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])

            query += " ORDER BY jalali_date DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                score_str = f" | امتیاز مدیر: {r[7]}/10 - بازخورد: {r[8]}" if r[7] else ""
                my_reports_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(f"پروژه: {r[0]} | عنوان: {r[1]}", weight=ft.FontWeight.BOLD),
                                ft.Text(f"نوع: {r[2]} | اولویت: {r[3]} | پیشرفت: {r[4]}% | تاریخ: {r[5]} | وضعیت: {r[6]}{score_str}"),
                                ft.Text(f"شرح فعالیت: {r[9]}", color=ft.colors.GREY_700)
                            ])
                        )
                    )
                )
            page.update()

        search_keyword.on_change = filter_my_reports
        search_date.on_change = filter_my_reports

        # خروجی اکسل گزارش کارشناس همراه با اطلاعات شناسایی
        def export_my_reports(e):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT full_name, personnel_code, department, phone FROM users WHERE username=?", (current_user["username"],))
            u_info = cursor.fetchone()

            df_reports = pd.read_sql_query(
                "SELECT project_name AS 'نام پروژه', title AS 'عنوان فعالیت', action_type AS 'نوع اقدام', priority AS 'اولویت', progress AS 'درصد پیشرفت', start_time AS 'زمان شروع', end_time AS 'زمان پایان', jalali_date AS 'تاریخ', description AS 'شرح کامل', status AS 'وضعیت' FROM reports WHERE username=?",
                conn, params=(current_user["username"],)
            )
            conn.close()

            df_user = pd.DataFrame([{
                'نام کاربری': current_user["username"],
                'نام و نام خانوادگی': u_info[0] if u_info else '',
                'کد پرسنلی': u_info[1] if u_info else '',
                'دپارتمان': u_info[2] if u_info else '',
                'تلفن': u_info[3] if u_info else ''
            }])

            full_name = u_info[0] if u_info and u_info[0] else current_user["username"]
            filename = f"گزارش_{full_name}_{get_current_jalali_date().replace('/', '-')}.xlsx"

            with pd.ExcelWriter(filename) as writer:
                df_reports.to_excel(writer, sheet_name="لیست گزارش‌ها", index=False)
                df_user.to_excel(writer, sheet_name="اطلاعات_کارشناس", index=False)

            msg_text.value = f"خروجی با نام '{filename}' ذخیره شد."
            msg_text.color = ft.colors.BLUE
            page.update()

        # فایل پیکر وارد کردن شرح انتظارات مدیر
        def file_picker_expectations_result(e: ft.FilePickerResultEvent):
            if e.files:
                file_path = e.files[0].path
                try:
                    df = pd.read_excel(file_path)
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    for _, row in df.iterrows():
                        cursor.execute(
                            "INSERT INTO assigned_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                str(uuid.uuid4()),
                                current_user["username"],
                                str(row.get('عنوان دستور کار', row.get('title', 'دستور کار'))),
                                str(row.get('توضیحات کامل', row.get('description', ''))),
                                str(row.get('مهلت انجام', row.get('deadline', ''))),
                                str(row.get('اولویت', row.get('priority', 'عادی'))),
                                "جدید",
                                get_current_jalali_date()
                            )
                        )
                    conn.commit()
                    conn.close()
                    msg_text.value = "فایل شرح انتظارات مدیر با موفقیت وارد دیتابیس شد."
                    msg_text.color = ft.colors.GREEN_500
                    filter_assigned_tasks(None)
                except Exception as ex:
                    msg_text.value = f"خطا در خواندن فایل اکسل: {str(ex)}"
                    msg_text.color = ft.colors.RED_500
                page.update()

        expectations_picker = ft.FilePicker(on_result=file_picker_expectations_result)
        page.overlay.append(expectations_picker)

        # فیلتر و مشاهده شرح انتظارات مدیر
        task_search_kw = ft.TextField(label="جستجو در عنوان/توضیحات", width=250)
        task_search_dt = ft.TextField(label="فیلتر تاریخ مهلت/ثبت", width=200)
        assigned_tasks_list = ft.Column()

        def filter_assigned_tasks(e):
            assigned_tasks_list.controls.clear()
            kw = normalize_persian_text(task_search_kw.value)
            dt = normalize_persian_text(task_search_dt.value)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            query = "SELECT title, description, deadline, priority, assigned_date FROM assigned_tasks WHERE username=?"
            params = [current_user["username"]]

            if dt:
                query += " AND (deadline LIKE ? OR assigned_date LIKE ?)"
                params.extend([f"%{dt}%", f"%{dt}%"])
            if kw:
                query += " AND (title LIKE ? OR description LIKE ?)"
                params.extend([f"%{kw}%", f"%{kw}%"])

            cursor.execute(query, params)
            tasks = cursor.fetchall()
            conn.close()

            for t in tasks:
                assigned_tasks_list.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(f"دستور کار: {t[0]} (اولویت: {t[3]})", weight=ft.FontWeight.BOLD, color=ft.colors.RED_700),
                                ft.Text(f"مهلت: {t[2]} | تاریخ ثبت: {t[4]}"),
                                ft.Text(f"توضیحات: {t[1]}")
                            ])
                        )
                    )
                )
            page.update()

        task_search_kw.on_change = filter_assigned_tasks
        task_search_dt.on_change = filter_assigned_tasks

        # ویرایش پروفایل شخصی
        def show_edit_profile(e):
            page.clean()
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("SELECT password, full_name, personnel_code, department, phone FROM users WHERE username=?", (current_user["username"],))
            u_data = cursor.fetchone()
            conn.close()

            p_pass = ft.TextField(label="رمز عبور جدید", value=u_data[0], password=True, width=300)
            p_name = ft.TextField(label="نام و نام خانوادگی", value=u_data[1], width=300)
            p_code = ft.TextField(label="کد پرسنلی", value=u_data[2], width=300)
            p_dept = ft.TextField(label="بخش / دپارتمان", value=u_data[3], width=300)
            p_phone = ft.TextField(label="شماره تلفن", value=u_data[4], width=300)

            def save_profile_changes(ev):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET password=?, full_name=?, personnel_code=?, department=?, phone=? WHERE username=?",
                    (p_pass.value, p_name.value, p_code.value, p_dept.value, p_phone.value, current_user["username"])
                )
                conn.commit()
                conn.close()
                show_expert_panel()

            page.add(
                ft.AppBar(title=ft.Text("ویرایش پروفایل شخصی")),
                p_name, p_code, p_dept, p_phone, p_pass,
                ft.ElevatedButton("ذخیره تغییرات", on_click=save_profile_changes),
                ft.OutlinedButton("بازگشت", on_click=lambda ev: show_expert_panel())
            )

        filter_my_reports(None)
        filter_assigned_tasks(None)

        page.add(
            ft.AppBar(
                title=ft.Text(f"پنل کارشناس: {current_user['username']}"),
                actions=[
                    ft.IconButton(ft.icons.PERSON, on_click=show_edit_profile, tooltip="ویرایش پروفایل"),
                    ft.IconButton(ft.icons.LOGOUT, on_click=lambda e: show_login())
                ]
            ),
            ft.Tabs(
                selected_index=0,
                tabs=[
                    ft.Tab(
                        text="ثبت و مشاهده گزارش‌ها",
                        content=ft.Column([
                            ft.Text("ثبت فعالیت جدید", size=18, weight=ft.FontWeight.BOLD),
                            ft.Row([proj_in, title_in, priority_dropdown], wrap=True),
                            ft.Row([action_dropdown, custom_action, progress_in], wrap=True),
                            ft.Row([start_t, end_t, status_dropdown], wrap=True),
                            desc_in,
                            ft.Row([
                                ft.ElevatedButton("ثبت گزارش", on_click=submit_report),
                                ft.OutlinedButton("خروجی اکسل گزارش‌ها برای مدیر", on_click=export_my_reports)
                            ]),
                            msg_text,
                            ft.Divider(),
                            ft.Text("گزارش‌های ثبت شده (با امکان فیلتر و جستجو)", size=18, weight=ft.FontWeight.BOLD),
                            ft.Row([search_keyword, search_date]),
                            my_reports_list
                        ])
                    ),
                    ft.Tab(
                        text="شرح انتظارات و دستور کارها",
                        content=ft.Column([
                            ft.Row([
                                ft.Text("دستور کارهای ارسالی مدیر", size=18, weight=ft.FontWeight.BOLD),
                                ft.ElevatedButton("وارد کردن فایل اکسل انتظارات مدیر", icon=ft.icons.UPLOAD_FILE, on_click=lambda _: expectations_picker.pick_files())
                            ]),
                            ft.Row([task_search_kw, task_search_dt]),
                            assigned_tasks_list
                        ])
                    )
                ]
            )
        )

    # --- پنل مدیریت ---

    def show_admin_panel():
        page.clean()

        # 1. داشبورد و فیلتر جامع گزارش‌های کارشناسان
        admin_search_kw = ft.TextField(label="جستجو در کلیدواژه/عنوان", width=200)
        admin_search_dt = ft.TextField(label="فیلتر تاریخ شمسی", width=150)
        admin_search_user = ft.TextField(label="نام کارشناس", width=150)
        admin_msg = ft.Text()

        admin_reports_view = ft.Column()

        def filter_admin_reports(e):
            admin_reports_view.controls.clear()
            kw = normalize_persian_text(admin_search_kw.value)
            dt = normalize_persian_text(admin_search_dt.value)
            u_name = normalize_persian_text(admin_search_user.value)

            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            query = "SELECT id, username, project_name, title, jalali_date, description, score, feedback FROM reports WHERE is_archived=0"
            params = []

            if dt:
                query += " AND jalali_date LIKE ?"
                params.append(f"%{dt}%")
            if u_name:
                query += " AND username LIKE ?"
                params.append(f"%{u_name}%")
            if kw:
                query += " AND (title LIKE ? OR project_name LIKE ? OR description LIKE ?)"
                params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])

            query += " ORDER BY jalali_date DESC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            for r in rows:
                score_in = ft.TextField(label="امتیاز (1-10)", value=str(r[6]) if r[6] else "", width=100)
                feedback_in = ft.TextField(label="بازخورد", value=r[7] if r[7] else "", width=250)
                report_id = r[0]

                def save_score(ev, r_id=report_id, s_field=score_in, f_field=feedback_in):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("UPDATE reports SET score=?, feedback=? WHERE id=?", (int(s_field.value) if s_field.value.isdigit() else None, f_field.value, r_id))
                    conn.commit()
                    conn.close()
                    admin_msg.value = "امتیاز و بازخورد ثبت شد."
                    admin_msg.color = ft.colors.GREEN_500
                    page.update()

                admin_reports_view.controls.append(
                    ft.Card(
                        content=ft.Container(
                            padding=10,
                            content=ft.Column([
                                ft.Text(f"کارشناس: {r[1]} | پروژه: {r[2]} | عنوان: {r[3]} | تاریخ: {r[4]}", weight=ft.FontWeight.BOLD),
                                ft.Text(f"شرح: {r[5]}"),
                                ft.Row([score_in, feedback_in, ft.ElevatedButton("ثبت امتیاز", on_click=save_score)])
                            ])
                        )
                    )
                )
            page.update()

        admin_search_kw.on_change = filter_admin_reports
        admin_search_dt.on_change = filter_admin_reports
        admin_search_user.on_change = filter_admin_reports

        # 2. وارد کردن فایل اکسل گزارش کارشناس توسط مدیر
        def file_picker_reports_result(e: ft.FilePickerResultEvent):
            if e.files:
                file_path = e.files[0].path
                try:
                    excel_file = pd.ExcelFile(file_path)
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()

                    # ۱. بروزرسانی اطلاعات کارشناس در صورت وجود برگه مربوطه
                    if "اطلاعات_کارشناس" in excel_file.sheet_names:
                        df_user = pd.read_excel(excel_file, "اطلاعات_کارشناس")
                        for _, row in df_user.iterrows():
                            u_username = str(row.get('نام کاربری', ''))
                            if u_username:
                                cursor.execute(
                                    "INSERT OR REPLACE INTO users (username, password, full_name, personnel_code, department, phone) VALUES (?, COALESCE((SELECT password FROM users WHERE username=?), '1234'), ?, ?, ?, ?)",
                                    (u_username, u_username, str(row.get('نام و نام خانوادگی', '')), str(row.get('کد پرسنلی', '')), str(row.get('دپارتمان', '')), str(row.get('تلفن', '')))
                                )

                    # ۲. افزودن گزارش‌های ثبت‌شده کارشناس
                    sheet_name = "لیست گزارش‌ها" if "لیست گزارش‌ها" in excel_file.sheet_names else excel_file.sheet_names[0]
                    df_reports = pd.read_excel(excel_file, sheet_name)
                    
                    for _, row in df_reports.iterrows():
                        cursor.execute(
                            "INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)",
                            (
                                str(uuid.uuid4()),
                                str(row.get('نام کاربری', row.get('username', 'ناشناس'))),
                                str(row.get('نام پروژه', '')),
                                str(row.get('عنوان فعالیت', '')),
                                str(row.get('نوع اقدام', 'عمومی')),
                                str(row.get('اولویت', 'عادی')),
                                int(row.get('درصد پیشرفت', 100)) if str(row.get('درصد پیشرفت', '100')).isdigit() else 100,
                                str(row.get('زمان شروع', '')),
                                str(row.get('زمان پایان', '')),
                                str(row.get('تاریخ', get_current_jalali_date())),
                                str(row.get('شرح کامل', '')),
                                str(row.get('وضعیت', 'انجام شده')),
                                None, None
                            )
                        )
                    conn.commit()
                    conn.close()
                    admin_msg.value = "فایل گزارش کارشناس و مشخصات او با موفقیت وارد دیتابیس شد."
                    admin_msg.color = ft.colors.GREEN_500
                    filter_admin_reports(None)
                except Exception as ex:
                    admin_msg.value = f"خطا در خواندن فایل گزارش: {str(ex)}"
                    admin_msg.color = ft.colors.RED_500
                page.update()

        report_picker = ft.FilePicker(on_result=file_picker_reports_result)
        page.overlay.append(report_picker)

        # 3. ارجاع کار مدیر و دو نوع خروجی اکسل (کلی / اختصاصی)
        target_user = ft.TextField(label="نام کاربری کارشناس", width=200)
        task_title = ft.TextField(label="عنوان دستور کار", width=250)
        task_deadline = ft.TextField(label="مهلت انجام", width=150)
        task_priority = ft.Dropdown(
            label="اولویت",
            options=[ft.dropdown.Option("عادی"), ft.dropdown.Option("مهم"), ft.dropdown.Option("فوری")],
            value="مهم",
            width=150
        )
        task_desc = ft.TextField(label="توضیحات کامل", multiline=True, width=500)

        def submit_assigned_task(e):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO assigned_tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), target_user.value, task_title.value, task_desc.value, task_deadline.value, task_priority.value, "جدید", get_current_jalali_date())
            )
            conn.commit()
            conn.close()
            admin_msg.value = "دستور کار جدید برای کارشناس ثبت شد."
            admin_msg.color = ft.colors.GREEN_500
            page.update()

        # خروجی اکسل کلی ارجاع کار
        def export_all_tasks(e):
            conn = sqlite3.connect(DB_NAME)
            df = pd.read_sql_query(
                "SELECT username AS 'نام کاربری کارشناس', title AS 'عنوان دستور کار', description AS 'توضیحات کامل', deadline AS 'مهلت انجام', priority AS 'اولویت', assigned_date AS 'تاریخ ثبت' FROM assigned_tasks", conn
            )
            conn.close()
            df.to_excel("دستور_کارهای_کلی_مدیر.xlsx", index=False)
            admin_msg.value = "فایل 'دستور_کارهای_کلی_مدیر.xlsx' با موفقیت ساخته شد."
            admin_msg.color = ft.colors.BLUE
            page.update()

        # خروجی اکسل اختصاصی ارجاع کار برای کارشناس مشخص
        def export_expert_tasks(e):
            if not target_user.value:
                admin_msg.value = "لطفاً ابتدا نام کاربری کارشناس را وارد کنید"
                admin_msg.color = ft.colors.RED_500
                page.update()
                return

            conn = sqlite3.connect(DB_NAME)
            df = pd.read_sql_query(
                "SELECT username AS 'نام کاربری کارشناس', title AS 'عنوان دستور کار', description AS 'توضیحات کامل', deadline AS 'مهلت انجام', priority AS 'اولویت', assigned_date AS 'تاریخ ثبت' FROM assigned_tasks WHERE username=?",
                conn, params=(target_user.value,)
            )
            conn.close()
            fname = f"دستور_کار_اختصاصی_{target_user.value}.xlsx"
            df.to_excel(fname, index=False)
            admin_msg.value = f"فایل اختصاصی '{fname}' ساخته شد."
            admin_msg.color = ft.colors.BLUE
            page.update()

        # 4. خروجی جامع و بایگانی
        def export_comprehensive_excel(e):
            conn = sqlite3.connect(DB_NAME)
            with pd.ExcelWriter("گزارش_جامع_مدیریت.xlsx") as writer:
                pd.read_sql_query("SELECT username AS 'نام کاربری', project_name AS 'پروژه', title AS 'عنوان', action_type AS 'نوع', priority AS 'اولویت', progress AS 'پیشرفت', start_time AS 'شروع', end_time AS 'پایان', jalali_date AS 'تاریخ', description AS 'شرح', status AS 'وضعیت', score AS 'امتیاز', feedback AS 'بازخورد' FROM reports", conn).to_excel(writer, sheet_name="لیست گزارش‌ها", index=False)
                pd.read_sql_query("SELECT username AS 'نام کاربری', full_name AS 'نام کامل', personnel_code AS 'کد پرسنلی', department AS 'دپارتمان', phone AS 'تلفن' FROM users", conn).to_excel(writer, sheet_name="پروفایل کارشناسان", index=False)
                pd.read_sql_query("SELECT username AS 'کارشناس', title AS 'عنوان', description AS 'توضیحات', deadline AS 'مهلت', priority AS 'اولویت' FROM assigned_tasks", conn).to_excel(writer, sheet_name="ارجاعات مدیر", index=False)
            conn.close()
            admin_msg.value = "فایل جامع 'گزارش_جامع_مدیریت.xlsx' خروجی گرفته شد."
            admin_msg.color = ft.colors.BLUE
            page.update()

        def archive_old_reports(e):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("UPDATE reports SET is_archived=1 WHERE is_archived=0")
            conn.commit()
            conn.close()

            filter_admin_reports(None)
            admin_msg.value = "تمامی گزارش‌های فعال به بخش آرشیو منتقل شدند."
            admin_msg.color = ft.colors.ORANGE_500
            page.update()

        filter_admin_reports(None)

        page.add(
            ft.AppBar(title=ft.Text("پنل مدیریت"), actions=[ft.IconButton(ft.icons.LOGOUT, on_click=lambda e: show_login())]),
            ft.Tabs(
                selected_index=0,
                tabs=[
                    ft.Tab(
                        text="بررسی گزارش‌ها و ورود اکسل",
                        content=ft.Column([
                            ft.Row([
                                ft.ElevatedButton("وارد کردن فایل گزارش کارشناس", icon=ft.icons.UPLOAD_FILE, on_click=lambda _: report_picker.pick_files())
                            ]),
                            admin_msg,
                            ft.Divider(),
                            ft.Text("فیلتر و جستجوی گزارش‌های کارشناسان", size=18, weight=ft.FontWeight.BOLD),
                            ft.Row([admin_search_kw, admin_search_dt, admin_search_user]),
                            admin_reports_view
                        ])
                    ),
                    ft.Tab(
                        text="ارجاع کار و خروجی اکسل",
                        content=ft.Column([
                            ft.Text("ثبت و ارسال دستور کار جدید", size=18, weight=ft.FontWeight.BOLD),
                            ft.Row([target_user, task_title, task_priority, task_deadline], wrap=True),
                            task_desc,
                            ft.Row([
                                ft.ElevatedButton("ثبت دستور کار", on_click=submit_assigned_task),
                                ft.OutlinedButton("خروجی اکسل کلی ارجاعات", on_click=export_all_tasks),
                                ft.OutlinedButton("خروجی اکسل اختصاصی کارشناس", on_click=export_expert_tasks)
                            ], wrap=True)
                        ])
                    ),
                    ft.Tab(
                        text="خروجی جامع و بایگانی",
                        content=ft.Column([
                            ft.Text("مدیریت خروجی‌های کلی و بایگانی", size=18, weight=ft.FontWeight.BOLD),
                            ft.ElevatedButton("تولید خروجی اکسل جامع (۳ برگه مجزا)", on_click=export_comprehensive_excel, width=300),
                            ft.ElevatedButton("انتقال گزارش‌های جاری به آرشیو", on_click=archive_old_reports, width=300, color=ft.colors.RED_500)
                        ])
                    )
                ]
            )
        )

    show_login()

ft.app(target=main)
