import sqlite3
import uuid
import os
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout

# --- 1. Database Initialization ---
DB_NAME = "app_database.db"

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
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('admin_password', 'admin123')")
    conn.commit()
    conn.close()

init_db()

# --- 2. Screens (UI) ---

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        layout.add_widget(Label(text="سامانه مدیریت گزارش‌ها (اندروید)", font_size=24))
        
        self.username_input = TextInput(hint_text="نام کاربری", multiline=False)
        self.password_input = TextInput(hint_text="رمز عبور", password=True, multiline=False)
        
        layout.add_widget(self.username_input)
        layout.add_widget(self.password_input)
        
        btn_login = Button(text="ورود کارشناس", size_hint_y=None, height=50)
        btn_login.bind(on_press=self.login_user)
        
        btn_admin = Button(text="ورود مدیر", size_hint_y=None, height=50)
        btn_admin.bind(on_press=self.login_admin)
        
        layout.add_widget(btn_login)
        layout.add_widget(btn_admin)
        
        self.msg_label = Label(text="", color=(1, 0, 0, 1))
        layout.add_widget(self.msg_label)
        
        self.add_widget(layout)

    def login_user(self, instance):
        user = self.username_input.text
        pwd = self.password_input.text
        if not user or not pwd:
            self.msg_label.text = "لطفاً نام کاربری و رمز را وارد کنید"
            return
            
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username=?", (user,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == pwd:
            self.manager.current = 'expert_dashboard'
        else:
            self.msg_label.text = "نام کاربری یا رمز عبور اشتباه است"

    def login_admin(self, instance):
        pwd = self.password_input.text
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key='admin_password'")
        admin_pwd = cursor.fetchone()[0]
        conn.close()
        
        if pwd == admin_pwd:
            self.manager.current = 'admin_dashboard'
        else:
            self.msg_label.text = "رمز مدیریت اشتباه است"


class ExpertDashboard(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text="پنل کارشناس", font_size=20))
        
        # فرم ثبت گزارش سریع
        self.title_input = TextInput(hint_text="عنوان فعالیت", multiline=False)
        self.desc_input = TextInput(hint_text="شرح فعالیت", multiline=True)
        
        layout.add_widget(self.title_input)
        layout.add_widget(self.desc_input)
        
        btn_submit = Button(text="ثبت گزارش", size_hint_y=None, height=50)
        btn_submit.bind(on_press=self.submit_report)
        layout.add_widget(btn_submit)
        
        btn_back = Button(text="خروج", size_hint_y=None, height=50)
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))
        layout.add_widget(btn_back)
        
        self.add_widget(layout)

    def submit_report(self, instance):
        # ذخیره نمونه گزارش در دیتابیس
        if self.title_input.text:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reports VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), "user", self.title_input.text, "اقدام اولیه", "عادی", "1403/01/01", self.desc_input.text, "انجام شده")
            )
            conn.commit()
            conn.close()
            self.title_input.text = ""
            self.desc_input.text = ""


class AdminDashboard(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text="پنل مدیریت", font_size=20))
        
        btn_back = Button(text="خروج به صفحه ورود", size_hint_y=None, height=50)
        btn_back.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))
        layout.add_widget(btn_back)
        
        self.add_widget(layout)

# --- 3. Main Application Class ---
class ReportSystemApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(ExpertDashboard(name='expert_dashboard'))
        sm.add_widget(AdminDashboard(name='admin_dashboard'))
        return sm

if __name__ == '__main__':
    ReportSystemApp().run()
