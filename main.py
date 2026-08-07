import flet as ft
import sqlite3
from datetime import datetime

# ==================== ۱. مدیریت دیتابیس ====================
def init_db():
    conn = sqlite3.connect("activity_reports.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expert_name TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# ==================== ۲. رابط کاربری و منطق برنامه ====================
def main(page: ft.Page):
    init_db()
    page.title = "سامانه گزارش فعالیت"
    page.rtl = True
    page.scroll = ft.ScrollMode.AUTO
    page.theme_mode = ft.ThemeMode.LIGHT

    # فیلدها و کادرهای ورودی (آیکون‌ها به ft.Icons تغییر یافتند)
    txt_expert = ft.TextField(label="نام کارشناس", icon=ft.Icons.PERSON)
    txt_date = ft.TextField(
        label="تاریخ ثبت", 
        value=datetime.now().strftime("%Y-%m-%d"), 
        icon=ft.Icons.CALENDAR_TODAY
    )
    txt_desc = ft.TextField(
        label="شرح فعالیت", 
        multiline=True, 
        min_lines=3, 
        icon=ft.Icons.DESCRIPTION
    )
    dd_status = ft.Dropdown(
        label="وضعیت",
        value="انجام شده",
        options=[
            ft.dropdown.Option("انجام شده"),
            ft.dropdown.Option("نیازمند پیگیری"),
        ],
        icon=ft.Icons.CHECK_CIRCLE
    )

    # لیست کارت‌های نمایش گزارش
    lv_reports = ft.ListView(expand=True, spacing=10, padding=10)

    # تابع بارگذاری اطلاعات از دیتابیس
    def load_reports(e=None):
        lv_reports.controls.clear()
        conn = sqlite3.connect("activity_reports.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, expert_name, date, status, description FROM reports ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()

        for r in rows:
            lv_reports.controls.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.ListTile(
                                leading=ft.Icon(ft.Icons.ASSIGNMENT),
                                title=ft.Text(f"{r[1]} - {r[2]}", weight=ft.FontWeight.BOLD),
                                subtitle=ft.Text(f"وضعیت: {r[3]}\n{r[4]}"),
                            )
                        ]),
                        padding=10
                    )
                )
            )
        page.update()

    # تابع ثبت گزارش جدید
    def add_report(e):
        if not txt_expert.value or not txt_desc.value:
            snack = ft.SnackBar(content=ft.Text("لطفاً تمامی فیلدها را پر کنید."))
            page.overlay.append(snack)
            snack.open = True
            page.update()
            return

        conn = sqlite3.connect("activity_reports.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO reports (expert_name, date, description, status) VALUES (?, ?, ?, ?)",
            (txt_expert.value, txt_date.value, txt_desc.value, dd_status.value)
        )
        conn.commit()
        conn.close()

        txt_desc.value = ""
        snack = ft.SnackBar(content=ft.Text("گزارش با موفقیت ثبت شد."))
        page.overlay.append(snack)
        snack.open = True
        load_reports()

    # دکمه ثبت
    btn_submit = ft.ElevatedButton("ثبت گزارش", icon=ft.Icons.ADD, on_click=add_report)

    # افزودن المان‌ها به صفحه
    page.add(
        ft.Text("ثبت فعالیت جدید", size=20, weight=ft.FontWeight.BOLD),
        txt_expert,
        txt_date,
        dd_status,
        txt_desc,
        btn_submit,
        ft.Divider(),
        ft.Text("لیست گزارش‌ها", size=20, weight=ft.FontWeight.BOLD),
        lv_reports
    )

    load_reports()

# ==================== ۳. اجرای برنامه ====================
if __name__ == "__main__":
    ft.app(target=main)
