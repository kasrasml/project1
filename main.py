from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.spinner import Spinner
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.graphics import Color, Rectangle, Line, RoundedRectangle
from kivy.uix.anchorlayout import AnchorLayout
from kivy.properties import StringProperty
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import relationship
import ast
import json
import traceback
import re
import os
import requests
from dotenv import load_dotenv
import logging
from sqlalchemy.exc import SQLAlchemyError
import threading
import sys
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import inspect
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


# Load environment variables
load_dotenv()

TOGETHER_API_KEY = 'e5929ad7b6b2905df8c1108e0d909684aca3bc25141ee4b08321a1be986fef81'
# TOGETHER_API_KEY = os.getenv('TOGETHER_API_KEY')
TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"

# Database setup
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

class MedicalRecord(Base):
    __tablename__ = 'medical_records'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    age = Column(Integer)
    gender = Column(String)
    country = Column(String)
    previous_illnesses = Column(String)
    previous_surgeries = Column(String)
    allergies = Column(String)
    health_concerns = Column(String)
    current_medications = Column(String)
    alcohol_use = Column(Boolean)
    alcohol_frequency = Column(String)
    tobacco_use = Column(Boolean)
    tobacco_frequency = Column(String)
    substance_use = Column(Boolean)
    substance_frequency = Column(String)
    substance_type = Column(String)
    height_cm = Column(Float)
    height_ft_in = Column(String)
    weight_kg = Column(Float)
    weight_lbs = Column(Float)
    diabetes = Column(Boolean)
    diabetes_type = Column(String)
    diabetes_type_other = Column(String)
    diabetes_treatment = Column(String)
    blood_pressure = Column(Boolean)
    blood_pressure_type = Column(String)
    blood_pressure_current = Column(String)
    blood_pressure_type_other = Column(String)
    heart_condition = Column(Boolean)
    heart_condition_details = Column(String)
    heart_surgery = Column(Boolean)
    heart_surgery_year = Column(Integer)
    heart_surgery_type = Column(String)
    physical_activity = Column(Boolean)
    physical_activity_details = Column(String)
    mental_health = Column(Boolean)
    mental_health_conditions = Column(String)
    mental_health_treatment = Column(String)
    mental_health_other = Column(String)
    sleep = Column(Boolean)
    sleep_issues = Column(String)
    sleep_issues_other = Column(String)
    sleep_treatment = Column(String)
    disability = Column(String)
    vaccination_history = Column(String)
    hospitalization_records = Column(String)
    additional_health_info = Column(Boolean)
    additional_health_info_details = Column(String)
    consent = Column(Boolean, default=False)   

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

class Symptom(Base):
    __tablename__ = 'symptoms'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    keyword = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Database class
class Database:
    def __init__(self):
        self.engine = create_engine('postgresql://postgres.owdlwnulwgaikqurlisb:wDeAmJHq9yPztTZu@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_medical_record(self, user_id):
        session = self.Session()
        try:
            return session.query(MedicalRecord).filter_by(user_id=user_id).first()
        except:
            return None
        finally:
            session.close()
            
    def update_password(self, email, new_password):
        session = self.Session()
        try:
            user = session.query(User).filter(User.email == email).one()
            hashed_password = generate_password_hash(new_password)
            user.password = hashed_password
            session.commit()
            return True
        except NoResultFound:
            print(f"No user found with email: {email}")
            return False
        except Exception as e:
            print(f"Error updating password: {e}")
            session.rollback()
            return False
        finally:
            session.close()
    def save_medical_record(self, user_id, data):
        session = self.Session()
        try:
            existing_record = session.query(MedicalRecord).filter_by(user_id=user_id).first()
            
            def convert_value(key, value):
                if isinstance(value, list):
                    return ', '.join(map(str, value))
                elif isinstance(value, str):
                    if value.lower() in ('yes', 'true', 'i have', 'i agree'):
                        return True
                    elif value.lower() in ('no', 'false', 'i do not', 'i have no'):
                        return False
                return value

            # Get the column information of the MedicalRecord model
            columns = inspect(MedicalRecord).mapper.columns
            column_types = {}
            for column in columns:
                print(f"Column: {column.key}, Type: {column.type}")
                column_types[column.key] = column.type
            
            if existing_record:
                for key, value in data.items():
                    if hasattr(existing_record, key):
                        converted_value = convert_value(key, value)
                        # Check if the column is Boolean and the value is not already a boolean
                        if key in column_types and isinstance(column_types[key], Boolean) and not isinstance(converted_value, bool):
                            converted_value = bool(converted_value)
                        setattr(existing_record, key, converted_value)
            else:
                converted_data = {}
                for key, value in data.items():
                    if key in column_types:
                        converted_value = convert_value(key, value)
                        # Check if the column is Boolean and the value is not already a boolean
                        if isinstance(column_types[key], Boolean) and not isinstance(converted_value, bool):
                            converted_value = bool(converted_value)
                        converted_data[key] = converted_value
                new_record = MedicalRecord(user_id=user_id, **converted_data)
                session.add(new_record)
            
            session.commit()
            print("Medical record saved successfully")
            return True
        except Exception as e:
            print(f"Error saving medical record: {str(e)}")
            print("Traceback:")
            traceback.print_exc()
            session.rollback()
            return False
        finally:
            session.close() 
                       
    def user_exists(self, username, email):
        session = self.Session()
        try:
            user = session.query(User).filter((User.username == username) | (User.email == email)).first()
            return user is not None
        finally:
            session.close()

    def create_user(self, username, email, password):
        session = self.Session()
        try:
            hashed_password = generate_password_hash(password)
            new_user = User(username=username, email=email, password=hashed_password)
            session.add(new_user)
            session.commit()
            return new_user.id
        except:
            session.rollback()
            return None
        finally:
            session.close()

    def get_user(self, username):
        session = self.Session()
        try:
            return session.query(User).filter(User.username == username).first()
        finally:
            session.close()

# Session manager
class SessionManager:
    def __init__(self):
        self.current_user_id = None

    def set_user(self, user_id):
        self.current_user_id = user_id

    def get_user_id(self):
        return self.current_user_id

    def clear_user(self):
        self.current_user_id = None

# API utilities
def make_together_api_call(prompt, system_message):
    headers = {
        "Authorization": f"Bearer {TOGETHER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 512,
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 50,
        "repetition_penalty": 1,
        "stop": ["</s>", "[/INST]", "[INST]"]
    }

    response = requests.post(TOGETHER_API_URL, json=data, headers=headers)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content'].strip()

def extract_keywords(chat_text):
    if not TOGETHER_API_KEY:
        return "Error: Together API key not set. Unable to extract keywords."
    system_message = "You are a medical keyword extractor."
    prompt = f"Extract important medical keywords (symptoms or medical history) from the following chat:\n\n{chat_text}\n\nReturn only the extracted keywords, separated by commas."
    try:
        return make_together_api_call(prompt, system_message)
    except Exception as e:
        return f"Error extracting keywords: {str(e)}"

def generate_health_recommendations(user_data, extracted_keywords):
    if not TOGETHER_API_KEY:
        return "Error: Together API key not set. Unable to generate recommendations."

    system_message = "You are a health recommendation system. Provide only a single paragraph of maximum 170 words."

    # Check for consent
    if not user_data.get('consent', False):
        prompt = f"Provide general health recommendations based on the following extracted keywords, without using any specific user data:\n\nExtracted Keywords:\n{extracted_keywords}\n\nProvide general, actionable recommendations for improving overall health and addressing any concerns related to the extracted keywords. Limit your response to a single paragraph of maximum 170 words."
    else:
        prompt = f"Based on the following user data and extracted keywords, provide health, self-care, and medical recommendations:\n\nUser Data:\n{user_data}\n\nExtracted Keywords:\n{extracted_keywords}\n\nConsider all aspects of the patient's health, including age, weight, height, gender, medical history, medications, lifestyle factors, physical measurements, chronic conditions, physical activity, mental health, sleep issues, disabilities, and vaccination history.\n\nProvide specific, actionable recommendations for improving overall health, managing existing conditions, and addressing any concerns related to the extracted keywords. Limit your response to a single paragraph of maximum 170 words."

    try:
        return make_together_api_call(prompt, system_message)
    except Exception as e:
        return f"Error generating health recommendations: {str(e)}"

# UI Components
class CenteredButton(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        self.background_color = kwargs.pop('background_color', (0.2, 0.6, 1, 1))
        self.text_color = kwargs.pop('text_color', (1, 1, 1, 1))
        super(CenteredButton, self).__init__(**kwargs)
        self.halign = 'center'
        self.valign = 'middle'
        self.size_hint_y = None
        self.height = dp(50)
        self.color = self.text_color
        self.font_size = sp(14)
        self.bind(size=self.update_background, pos=self.update_background)
        self.update_background()

    def on_size(self, *args):
        self.text_size = self.size

    def update_background(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.background_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10,])

    def on_press(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*(0.2, 0.6, 1, 1))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10,])

    def on_release(self):
        self.update_background()

class StyledTextInput(TextInput):
    def __init__(self, **kwargs):
        super(StyledTextInput, self).__init__(**kwargs)
        self.background_color = [1, 1, 1, 1]
        self.foreground_color = [0, 0, 0, 1]
        self.cursor_color = [0, 0, 0, 1]
        self.multiline = False
        self.size_hint = (None, None)
        self.size = (dp(300), dp(50))
        self.font_size = dp(16)
        self.padding = [dp(15), dp(15), dp(15), dp(15)]
        self.border = [1, 1, 1, 1]
        self.border_color = [0.7, 0.7, 0.7, 1]

class ClickableLabel(Label):
    def __init__(self, **kwargs):
        self.register_event_type('on_click')
        super(ClickableLabel, self).__init__(**kwargs)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.dispatch('on_click')
            return True
        return super(ClickableLabel, self).on_touch_down(touch)

    def on_click(self):
        pass
    
# Screen classes
class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        layout = FloatLayout()

        with layout.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(size=self._update_rect, pos=self._update_rect)

        logo = Image(source=resource_path('assets/logo.png'), size_hint=(None, None), size=(dp(100), dp(100)))
        logo.pos_hint = {'center_x': 0.5, 'top': 1.03}
        layout.add_widget(logo)

        welcome_label = Label(text='Welcome Back', font_size=dp(48), color=(0, 0, 0, 1))
        welcome_label.pos_hint = {'center_x': 0.5, 'top': 1.25}
        layout.add_widget(welcome_label)

        welcome_label2 = Label(text='Login to your account', font_size=dp(16), color=(0, 0, 0, 1))
        welcome_label2.pos_hint = {'center_x': 0.5, 'top': 1.17}
        layout.add_widget(welcome_label2)

        input_layout = BoxLayout(orientation='vertical', spacing=dp(20), size_hint=(None, None), width=dp(300), height=dp(160))
        input_layout.pos_hint = {'center_x': 0.5, 'center_y': 0.50}

        self.username_input = StyledTextInput(hint_text='Username')
        self.password_input = StyledTextInput(hint_text='Password', password=True)

        input_layout.add_widget(self.username_input)
        input_layout.add_widget(self.password_input)
        layout.add_widget(input_layout)

        login_button = CenteredButton(
            text='LOGIN',
            size_hint=(None, None),
            size=(dp(300), dp(50))
        )
        login_button.pos_hint = {'center_x': 0.5, 'y': 0.17}
        login_button.bind(on_press=self.login)
        layout.add_widget(login_button)

        register_label = ClickableLabel(
            text="Don't have an account? Register",
            size_hint=(None, None),
            size=(dp(300), dp(30)),
            color=(0.2, 0.6, 1, 1),
            underline=True
        )
        register_label.pos_hint = {'center_x': 0.5, 'y': 0.07}
        register_label.bind(on_click=self.go_to_register)
        layout.add_widget(register_label)

        # Add Forgot Password link
        forgot_password_label = ClickableLabel(
            text="Forgot Password?",
            size_hint=(None, None),
            size=(dp(300), dp(30)),
            color=(0.2, 0.6, 1, 1),
            underline=True
        )
        forgot_password_label.pos_hint = {'center_x': 0.5, 'y': 0.02}
        forgot_password_label.bind(on_click=self.go_to_forgot_password)
        layout.add_widget(forgot_password_label)

        self.add_widget(layout)
        
        
    def go_to_forgot_password(self, instance):
        App.get_running_app().switch_screen('forgot_password')
    

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def login(self, instance):
        username = self.username_input.text
        password = self.password_input.text

        if not username or not password:
            self.show_popup("Error", "Please enter both username and password.")
            return

        app = App.get_running_app()
        user = app.database.get_user(username)

        if user and check_password_hash(user.password, password):
            app.session_manager.set_user(user.id)
            app.switch_screen('dashboard')
        else:
             self.show_popup("Error", "Invalid username or password.")

    def go_to_register(self, instance):
        App.get_running_app().switch_screen('register')

    def go_to_forgot_password(self, instance):
        App.get_running_app().switch_screen('forgot_password')

    def show_popup(self, title, content):
        content_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        close_button = Button(text='x', size_hint=(None, None), size=(20, 20),
                              pos_hint={'right': 1, 'top': 1})
        close_button.background_color = (0.7, 0.7, 0.7, 1)
        content_layout.add_widget(close_button)
        content_layout.add_widget(Label(text=content))
        popup = Popup(title=title,
                      content=content_layout,
                      size_hint=(None, None), size=(300, 150))
        close_button.bind(on_press=popup.dismiss)
        popup.open()
        
class ForgotPasswordScreen(Screen):
    def __init__(self, **kwargs):
        super(ForgotPasswordScreen, self).__init__(**kwargs)
        
        self.confirmation_code = None
        self.code_expiration = None

        layout = FloatLayout()

        with layout.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(size=self._update_rect, pos=self._update_rect)

        logo = Image(source=resource_path('assets/logo.png'), size_hint=(None, None), size=(dp(120), dp(120)))
        logo.pos_hint = {'center_x': 0.5, 'top': 1.03}
        layout.add_widget(logo)
      
        recover_label = Label(
            text='Change your password',
            font_size=dp(20),
            color=(0, 0, 0, 1),
            pos_hint={'center_x': 0.5, 'top': 1.28}
        )
        layout.add_widget(recover_label)

        input_layout = BoxLayout(orientation='vertical', spacing=dp(20), size_hint=(None, None), width=dp(300), height=dp(280))
        input_layout.pos_hint = {'center_x': 0.5, 'center_y': 0.5}

        email_layout = BoxLayout(orientation='horizontal', spacing=dp(10), size_hint=(1, None), height=dp(50))
        
        email_input_layout = BoxLayout(orientation='horizontal', size_hint=(0.5, 1))
        self.email_input = StyledTextInput(hint_text='Email', size_hint=(1, None), height=dp(50))
        email_input_layout.add_widget(self.email_input)
        
        self.send_code_button = CenteredButton(
            text='Send Code',
            size_hint=(0.2, None),
            height=dp(50)
        )
        self.send_code_button.bind(on_press=self.send_confirmation_code)

        email_layout.add_widget(email_input_layout)
        email_layout.add_widget(self.send_code_button)

        input_layout.add_widget(email_layout)
        
        self.code_input = StyledTextInput(hint_text='Confirmation Code', disabled=True)
        self.new_password_input = StyledTextInput(hint_text='New Password', password=True, disabled=True)
        self.confirm_password_input = StyledTextInput(hint_text='Confirm New Password', password=True, disabled=True)

        input_layout.add_widget(self.code_input)
        input_layout.add_widget(self.new_password_input)
        input_layout.add_widget(self.confirm_password_input)

        layout.add_widget(input_layout)

        self.change_password_button = CenteredButton(
            text='Change Password',
            size_hint=(None, None),
            size=(dp(300), dp(50)),
            disabled=True
        )
        self.change_password_button.pos_hint = {'center_x': 0.5, 'y': 0.15}
        self.change_password_button.bind(on_press=self.change_password)
        layout.add_widget(self.change_password_button)

        back_label = ClickableLabel(
            text="Back to Login",
            size_hint=(None, None),
            size=(dp(300), dp(30)),
            color=(0.2, 0.6, 1, 1),
            underline=True
        )
        back_label.pos_hint = {'center_x': 0.5, 'y': 0.05}
        back_label.bind(on_click=self.go_back_to_login)
        layout.add_widget(back_label)

        self.add_widget(layout)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def send_confirmation_code(self, instance):
        email = self.email_input.text
        if not email:
            self.show_popup("Error", "Please enter your email address.")
            return

        self.confirmation_code = ''.join(random.choices(string.digits, k=6))
        self.code_expiration = datetime.now() + timedelta(minutes=5)

        if self.send_email(email, self.confirmation_code):
            self.show_popup("Success", "Confirmation code sent to your email.\n Valid for 5 minutes.")
            self.activate_password_change_fields()
        else:
            self.show_popup("Error", "Failed to send confirmation code. Please try again.")

    def activate_password_change_fields(self):
        self.code_input.disabled = False
        self.new_password_input.disabled = False
        self.confirm_password_input.disabled = False
        self.change_password_button.disabled = False
        self.send_code_button.disabled = True
        self.email_input.disabled = True

    def change_password(self, instance):
        entered_code = self.code_input.text
        new_password = self.new_password_input.text
        confirm_password = self.confirm_password_input.text
        email = self.email_input.text

        if not entered_code or not new_password or not confirm_password:
            self.show_popup("Error", "Please fill in all fields.")
            return

        if new_password != confirm_password:
            self.show_popup("Error", "Passwords do not match.")
            return

        if not self.confirmation_code or datetime.now() > self.code_expiration:
            self.show_popup("Error", "Confirmation code has expired. Please request a new one.")
            return

        if entered_code != self.confirmation_code:
            self.show_popup("Error", "Invalid confirmation code.")
            return

        app = App.get_running_app()
        if app.database.update_password(email, new_password):
            self.show_popup("Success", "Password changed successfully.")
            Clock.schedule_once(lambda dt: self.go_back_to_login(None), 2)
        else:
            self.show_popup("Error", "Failed to update password. Please try again.")

    def send_email(self, email, code):
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        sender_email = "alirah83@gmail.com"
        sender_password = "dpas bgxw llut kyyc"  # Use App Password here

        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = email
        message["Subject"] = "Password Reset Confirmation Code"

        body = f"Your confirmation code is: {code}\nThis code is valid for 5 minutes."
        message.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.ehlo()  # Can be omitted
                server.starttls()
                server.ehlo()  # Can be omitted
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, email, message.as_string())
            return True
        except Exception as e:
            print(f"Failed to send email: {e}")
            return False
       
    def go_back_to_login(self, instance):
        App.get_running_app().switch_screen('login')

    def show_popup(self, title, content):
        content_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        close_button = Button(text='x', size_hint=(None, None), size=(20, 20),
                              pos_hint={'right': 1, 'top': 1})
        close_button.background_color = (0.7, 0.7, 0.7, 1)
        content_layout.add_widget(close_button)
        content_layout.add_widget(Label(text=content))
        popup = Popup(title=title,
                      content=content_layout,
                      size_hint=(None, None), size=(300, 190))
        close_button.bind(on_press=popup.dismiss)
        popup.open()

 
                
class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super(RegisterScreen, self).__init__(**kwargs)
        layout = FloatLayout()
        
        with layout.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.rect = Rectangle(size=layout.size, pos=layout.pos)
        layout.bind(size=self._update_rect, pos=self._update_rect)
        
        logo = Image(source=resource_path('assets/logo.png'), size_hint=(None, None), size=(dp(100), dp(100)))
        logo.pos_hint = {'center_x': 0.5, 'top': 1.03}
        layout.add_widget(logo)
        
        welcome_label = Label(text='Register', font_size=dp(48), color=(0, 0, 0, 1))
        welcome_label.pos_hint = {'center_x': 0.5, 'top': 1.35}
        layout.add_widget(welcome_label)
        
        welcome_label2 = Label(text='Create your account', font_size=dp(16), color=(0, 0, 0, 1))
        welcome_label2.pos_hint = {'center_x': 0.5, 'top': 1.27}
        layout.add_widget(welcome_label2)
        
        input_layout = BoxLayout(orientation='vertical', spacing=dp(20), size_hint=(None, None), width=dp(300), height=dp(240))
        input_layout.pos_hint = {'center_x': 0.5, 'center_y': 0.50}
        
        self.username_input = StyledTextInput(hint_text='Username')
        self.email_input = StyledTextInput(hint_text='Email')
        self.password_input = StyledTextInput(hint_text='Password', password=True)
        self.confirm_password_input = StyledTextInput(hint_text='Confirm Password', password=True)
        
        input_layout.add_widget(self.username_input)
        input_layout.add_widget(self.email_input)
        input_layout.add_widget(self.password_input)
        input_layout.add_widget(self.confirm_password_input)
        layout.add_widget(input_layout)
        
        register_button = CenteredButton(
            text='REGISTER',
            size_hint=(None, None),
            size=(dp(300), dp(50))
        )
        register_button.pos_hint = {'center_x': 0.5, 'y': 0.15}
        register_button.bind(on_press=self.register)
        layout.add_widget(register_button)

        login_label = ClickableLabel(
            text="Already have an account? Login",
            size_hint=(None, None),
            size=(dp(300), dp(30)),
            color=(0.2, 0.6, 1, 1),
            underline=True
        )
        login_label.pos_hint = {'center_x': 0.5, 'y': 0.05}
        login_label.bind(on_click=self.go_to_login)
        layout.add_widget(login_label)

        self.add_widget(layout)


    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def register(self, instance):
        username = self.username_input.text
        email = self.email_input.text
        password = self.password_input.text
        confirm_password = self.confirm_password_input.text
        
        if not username or not email or not password:
            self.show_popup("Error", "All fields are required.")
            return
        
        if password != confirm_password:
            self.show_popup("Error", "Passwords do not match.")
            return
        
        app = App.get_running_app()
        
        if app.database.user_exists(username, email):
            self.show_popup("Error", "Username or email already exists.")
            return
        
        user_id = app.database.create_user(username, email, password)
        
        if user_id:
            self.show_popup("Success", "Registration successful. Please log in.")
            app.switch_screen('login')
        else:
            self.show_popup("Error", "Registration failed. Please try again.")

    def go_to_login(self, instance):
        App.get_running_app().switch_screen('login')

    def show_popup(self, title, content):
        content_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        close_button = Button(text='x', size_hint=(None, None), size=(20, 20),
                              pos_hint={'right': 1, 'top': 1})
        close_button.background_color = (0.7, 0.7, 0.7, 1)
        content_layout.add_widget(close_button)
        content_layout.add_widget(Label(text=content))
        popup = Popup(title=title,
                      content=content_layout,
                      size_hint=(None, None), size=(300, 150))
        close_button.bind(on_press=popup.dismiss)
        popup.open()

class QuestionnaireScreen(Screen):
    def __init__(self, **kwargs):
        super(QuestionnaireScreen, self).__init__(**kwargs)
        self.fields = {}
        with self.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        root_layout = BoxLayout(orientation='vertical')
        
        self.scroll_view = ScrollView(size_hint=(1, 1))
        
        self.layout = GridLayout(cols=1, spacing=dp(12), size_hint_y=None, padding=dp(10))
        self.layout.bind(minimum_height=self.layout.setter('height'))
        
        self.add_fields()
        
        self.scroll_view.add_widget(self.layout)
        root_layout.add_widget(self.scroll_view)
        self.add_widget(root_layout)
        
        Window.bind(on_resize=self.on_window_resize)
        self.on_window_resize(Window, *Window.size)
        
        self._keyboard = Window.request_keyboard(self._keyboard_closed, self)
        self._keyboard.bind(on_key_down=self._on_keyboard_down)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def on_window_resize(self, instance, width, height):
        self.layout.height = max(height, self.layout.minimum_height)
        self.layout.width = width - dp(20)
        for child in self.layout.children:
            if isinstance(child, BoxLayout):
                for subchild in child.children:
                    if isinstance(subchild, Label):
                        subchild.text_size = (width - dp(20), None)

    def _keyboard_closed(self):
        self._keyboard.unbind(on_key_down=self._on_keyboard_down)
        self._keyboard = None

    def _on_keyboard_down(self, keyboard, keycode, text, modifiers, *args):
        if isinstance(keycode, tuple):
            key = keycode[1]
        else:
            key = keycode
        if key == 273 or key == 'up':
            self.scroll_up()
            return True
        elif key == 274 or key == 'down':
            self.scroll_down()
            return True
        return False

    def scroll_up(self):
        scroll_distance = dp(200)
        new_y = min(self.scroll_view.scroll_y + scroll_distance / self.layout.height, 1)
        Clock.schedule_once(lambda dt: setattr(self.scroll_view, 'scroll_y', new_y), 0)

    def scroll_down(self):
        scroll_distance = dp(200)
        new_y = max(self.scroll_view.scroll_y - scroll_distance / self.layout.height, 0)
        Clock.schedule_once(lambda dt: setattr(self.scroll_view, 'scroll_y', new_y), 0)
        
    def on_size(self, *args):
        self.text_size = self.size
        

    def add_fields(self):
        self.add_field('age', '* Age:', self.create_text_input(input_type='number', hint_text='Enter your age'))
        self.add_field('country', '* Country of Residence:', self.create_text_input(hint_text='Enter your country'))
        self.add_field('gender', '* Gender:', self.create_radio_group('gender', ['Male', 'Female', 'Non-Binary']))
        
        self.add_field('previous_illnesses', 'Previous Illnesses:', self.create_text_input(multiline=True, hint_text='List any previous illnesses'))
        self.add_field('previous_surgeries', 'Previous Surgeries:', self.create_text_input(multiline=True, hint_text='List any previous surgeries'))
        
        self.add_field('allergies', 'Allergies:', self.create_text_input(multiline=True))
        self.add_field('health_concerns', 'Special Health Problems or Concerns:', self.create_text_input(multiline=True))
        
        self.add_field('current_medications', 'Current Medications:', self.create_text_input(multiline=True))
        alcohol_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120))
        alcohol_radio = self.create_radio_group('alcohol_use', ['No', 'Yes'])
        alcohol_layout.add_widget(alcohol_radio)
        self.fields['alcohol_frequency'] = Spinner(
            text='Select Frequency',
            values=('Light', 'Moderate', 'Heavy'),
            size_hint_y=None,
            height=dp(40),
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1),
            font_size=dp(12),
            disabled=True
        )
        alcohol_layout.add_widget(self.fields['alcohol_frequency'])
        self.add_field('alcohol', 'Alcohol Use:', alcohol_layout)
        self.bind_radio_to_spinner('alcohol_use', self.fields['alcohol_frequency'])
        
        tobacco_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120))
        tobacco_radio = self.create_radio_group('tobacco_use', ['No', 'Yes'])
        tobacco_layout.add_widget(tobacco_radio)
        self.fields['tobacco_frequency'] = Spinner(
            text='Select Frequency',
            values=('Light', 'Moderate', 'Heavy'),
            size_hint_y=None,
            height=dp(40),
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1),
            font_size=dp(12),
            disabled=True
        )
        tobacco_layout.add_widget(self.fields['tobacco_frequency'])
        self.add_field('tobacco', 'Tobacco Use:', tobacco_layout)
        self.bind_radio_to_spinner('tobacco_use', self.fields['tobacco_frequency'])

        substance_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(160))
        substance_radio = self.create_radio_group('substance_use', ['No', 'Yes'])
        substance_layout.add_widget(substance_radio)
        self.fields['substance_frequency'] = Spinner(
            text='Select Frequency',
            values=('Light', 'Moderate', 'Heavy'),
            size_hint_y=None,
            height=dp(40),
            background_color=(0.2, 0.6, 1, 1),
            color=(1, 1, 1, 1),
            font_size=dp(12),
            disabled=True
        )
        substance_layout.add_widget(self.fields['substance_frequency'])
        self.fields['substance_type'] = self.create_text_input(hint_text='Specify Substance(s)')
        self.fields['substance_type'].disabled = True
        substance_layout.add_widget(self.fields['substance_type'])
        self.add_field('substance', 'Substance Use:', substance_layout)
        self.bind_radio_to_substance('substance_use', self.fields['substance_frequency'], self.fields['substance_type'])
            
        
        height_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        self.fields['height_cm'] = self.create_text_input(hint_text='cm', input_type='number')
        self.fields['height_ft_in'] = self.create_text_input(hint_text='ft.in', input_type='number')
        height_layout.add_widget(self.fields['height_cm'])
        height_layout.add_widget(self.fields['height_ft_in'])
        self.add_field('height', 'Height:', height_layout)
        
        weight_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        self.fields['weight_kg'] = self.create_text_input(hint_text='kg', input_type='number')
        self.fields['weight_lbs'] = self.create_text_input(hint_text='lbs', input_type='number')
        weight_layout.add_widget(self.fields['weight_kg'])
        weight_layout.add_widget(self.fields['weight_lbs'])
        self.add_field('weight', 'Weight:', weight_layout)
        
        diab_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(280))
        diab_radio = self.create_radio_group('diabetes', ['No known diabetes', 'Yes, I have diabetes'])
        diab_layout.add_widget(diab_radio)

        diab_type_layout = GridLayout(cols=1, size_hint_y=None, height=dp(160))
        diab_type_options = ['Type 1 diabetes', 'Type 2 diabetes', 'Other']
        self.fields['diabetes_type'] = self.create_radio_group_with_other('diabetes_type', diab_type_options)
        diab_type_layout.add_widget(self.fields['diabetes_type'])

        diab_layout.add_widget(diab_type_layout)

        self.fields['diabetes_treatment'] = self.create_text_input(hint_text='Treatment (if any)')
        self.fields['diabetes_treatment'].disabled = True  # Initially disabled
        diab_layout.add_widget(self.fields['diabetes_treatment'])

        self.add_field('diabetes', 'Diabetes:', diab_layout)
        self.bind_radio_to_diabetes('diabetes', self.fields['diabetes_type'], self.fields['diabetes_treatment'])
        
        
        bp_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(280))
        bp_radio = self.create_radio_group('blood_pressure', ['No known blood pressure issues', 'Yes, I have blood pressure issues'])
        bp_layout.add_widget(bp_radio)

        bp_type_layout = GridLayout(cols=1, size_hint_y=None, height=dp(160))
        bp_type_options = ['High blood pressure', 'Low blood pressure', 'Other']
        self.fields['blood_pressure_type'] = self.create_radio_group_with_other('blood_pressure_type', bp_type_options)
        bp_type_layout.add_widget(self.fields['blood_pressure_type'])

        bp_layout.add_widget(bp_type_layout)

        self.fields['blood_pressure_current'] = self.create_text_input(hint_text='Current blood pressure (if known)')
        bp_layout.add_widget(self.fields['blood_pressure_current'])

        self.add_field('blood_pressure', 'Blood Pressure:', bp_layout)
        self.bind_radio_to_bp('blood_pressure', self.fields['blood_pressure_type'], self.fields['blood_pressure_current'])
                

        
        heart_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120))
        heart_layout.add_widget(self.create_radio_group('heart_condition', ['No known heart condition', 'Yes, I have a heart condition']))
        self.fields['heart_condition_details'] = self.create_text_input(hint_text='Please specify')
        self.fields['heart_condition_details'].disabled = True
        heart_layout.add_widget(self.fields['heart_condition_details'])
        self.add_field('heart_condition', 'Heart Condition:', heart_layout)
        self.bind_radio_to_text_input('heart_condition', self.fields['heart_condition_details'])

        surgery_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(160))
        surgery_layout.add_widget(self.create_radio_group('heart_surgery', ['No, I have not had any heart surgery', 'Yes, I have had heart surgery']))
        self.fields['heart_surgery_year'] = self.create_text_input(hint_text='Year')
        self.fields['heart_surgery_type'] = self.create_text_input(hint_text='Type (if known)')
        self.fields['heart_surgery_year'].disabled = True
        self.fields['heart_surgery_type'].disabled = True
        surgery_layout.add_widget(self.fields['heart_surgery_year'])
        surgery_layout.add_widget(self.fields['heart_surgery_type'])
        self.add_field('heart_surgery', 'Heart Surgery:', surgery_layout)
        self.bind_radio_to_text_input('heart_surgery', self.fields['heart_surgery_year'])
        self.bind_radio_to_text_input('heart_surgery', self.fields['heart_surgery_type'])

        activity_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120))
        activity_layout.add_widget(self.create_radio_group('physical_activity', ['I do not engage in any regular physical activity or exercise', 'Yes, I engage in physical activity/exercise']))
        self.fields['physical_activity_details'] = self.create_text_input(hint_text='Type of activity')
        self.fields['physical_activity_details'].disabled = True
        activity_layout.add_widget(self.fields['physical_activity_details'])
        self.add_field('physical_activity', 'Physical Activity:', activity_layout)
        self.bind_radio_to_text_input('physical_activity', self.fields['physical_activity_details'])
        
        mental_layout = self.create_mental_health_layout()
        self.add_field('mental_health', 'Mental Health:', mental_layout)

        
        sleep_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(330))
        sleep_radio = self.create_radio_group('sleep', ['I have no issues with sleep', 'Yes, I have sleep-related issues'])
        sleep_layout.add_widget(sleep_radio)

        sleep_issues_layout = GridLayout(cols=1, size_hint_y=None, height=dp(200))
        sleep_issues_options = ['Insomnia', 'Excessive daytime sleepiness', 'Irregular sleep schedule', 'Other']
        self.fields['sleep_issues'] = self.create_radio_group_with_other('sleep_issues', sleep_issues_options)
        sleep_issues_layout.add_widget(self.fields['sleep_issues'])
        sleep_layout.add_widget(sleep_issues_layout)

        self.fields['sleep_treatment'] = self.create_text_input(hint_text='Currently receiving treatment for sleep issues(e.g. medication, sleep therapy)')
        sleep_layout.add_widget(self.fields['sleep_treatment'])

        self.add_field('sleep', 'Sleep:', sleep_layout)

        # Bind the main sleep radio buttons to enable/disable the sleep issues options
        for checkbox, option in self.fields['sleep']:
            checkbox.bind(active=lambda cb, value, o=option: self.toggle_sleep_options(value, o))



        
        self.add_field('disability', 'Disability (if any):', self.create_text_input())
        
        self.add_field('vaccination_history', 'Vaccination History:', self.create_text_input())
        self.add_field('hospitalization_records', 'Hospitalization Records:', self.create_text_input())
        
        additional_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(120))
        additional_layout.add_widget(self.create_radio_group('additional_health_info', ['No other relevant health information to share', 'Yes, there is additional health information']))
        self.fields['additional_health_info_details'] = self.create_text_input(hint_text='Please specify')
        self.fields['additional_health_info_details'].disabled = True
        additional_layout.add_widget(self.fields['additional_health_info_details'])
        self.add_field('additional_health_info', 'Additional Health Information:', additional_layout)
        self.bind_radio_to_text_input('additional_health_info', self.fields['additional_health_info_details'])
         
        consent_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(80))
        consent_label = Label(
            text='Consent for Use of Medical Information:',
            size_hint_y=None,
            height=dp(40),
            color=(0, 0, 0, 1),
            font_size=dp(14),
            halign='left'
        )
        consent_layout.add_widget(consent_label)

        consent_options = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        self.fields['consent'] = []

        for option in ['I Agree', 'I don\'t Agree']:
            option_layout = BoxLayout(orientation='horizontal', size_hint_x=0.5)
            radio_btn = CheckBox(group='consent', size_hint_x=None, width=dp(40), color=(0, 0, 0, 1))
            option_label = Label(
                text=option,
                size_hint_y=None,
                height=dp(40),
                color=(0, 0, 0, 1),
                font_size=dp(12)
            )
            option_layout.add_widget(radio_btn)
            option_layout.add_widget(option_label)
            consent_options.add_widget(option_layout)
            self.fields['consent'].append((radio_btn, option))

        consent_layout.add_widget(consent_options)
        self.layout.add_widget(consent_layout)

        
        button_layout = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(10), padding=[10, 5, 10, 5])
        
        submit_button = CenteredButton2(text='Submit')
        submit_button.bind(on_press=self.submit)
        button_layout.add_widget(submit_button)
        
        go_back_button = CenteredButton2(text='Go Back to Dashboard')
        go_back_button.bind(on_press=self.go_back_to_dashboard)
        button_layout.add_widget(go_back_button)
        
        self.layout.add_widget(button_layout)
        
    def bind_radio_to_substance(self, group_name, spinner, text_input):
        for checkbox, option in self.fields[group_name]:
            checkbox.bind(active=lambda cb, value, s=spinner, t=text_input, o=option: self.toggle_substance_fields(s, t, value, o))

    def toggle_substance_fields(self, spinner, text_input, value, option):
        if option == 'Yes' and value:
            spinner.disabled = False
            text_input.disabled = False
        elif option == 'No' and value:
            spinner.disabled = True
            text_input.disabled = True
            spinner.text = 'Select Frequency'
            text_input.text = '' 
            
    def bind_radio_to_diabetes(self, group_name, diab_type_layout, treatment_input):
        for checkbox, option in self.fields[group_name]:
            checkbox.bind(active=lambda cb, value, l=diab_type_layout, t=treatment_input, opt=option: self.toggle_diabetes_fields(l, t, value, opt))

        # Initially disable all options
        self.toggle_diabetes_fields(diab_type_layout, treatment_input, False, 'No known diabetes')

        # Bind the 'Other' checkbox to enable/disable its text input
        other_box = next((child for child in diab_type_layout.children if isinstance(child, BoxLayout) and any('Other' in c.text for c in child.children if isinstance(c, Label))), None)
        if other_box:
            other_checkbox = next((c for c in other_box.children if isinstance(c, CheckBox)), None)
            other_text_input = next((c for c in other_box.children if isinstance(c, TextInput)), None)
            if other_checkbox and other_text_input:
                other_checkbox.bind(active=lambda cb, val: setattr(other_text_input, 'disabled', not val))



    def toggle_diabetes_fields(self, diab_type_radio, treatment_input, value, option):
        if option == 'Yes, I have diabetes' and value:
            for child in diab_type_radio.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    if checkbox:
                        checkbox.disabled = False
            treatment_input.disabled = False
        elif option == 'No known diabetes' and value:
            for child in diab_type_radio.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    if checkbox:
                        checkbox.disabled = True
                        checkbox.active = False
                    text_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                    if text_input:
                        text_input.disabled = True
                        text_input.text = ''
            treatment_input.disabled = True
            treatment_input.text = ''

        # Handle the 'Other' option
        other_box = next((child for child in diab_type_radio.children if isinstance(child, BoxLayout) and any('Other' in c.text for c in child.children if isinstance(c, Label))), None)
        if other_box:
            other_checkbox = next((c for c in other_box.children if isinstance(c, CheckBox)), None)
            other_text_input = next((c for c in other_box.children if isinstance(c, TextInput)), None)
            if other_checkbox and other_text_input:
                other_checkbox.bind(active=lambda cb, val: setattr(other_text_input, 'disabled', not val))
                if option == 'Yes, I have diabetes' and value:
                    other_text_input.disabled = not other_checkbox.active
                else:
                    other_text_input.disabled = True

        # Ensure that when 'Yes, I have diabetes' is selected, the 'Other' text input is enabled if its checkbox is active
        if option == 'Yes, I have diabetes' and value:
            for child in diab_type_radio.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    label = next((c for c in child.children if isinstance(c, Label)), None)
                    text_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                    if checkbox and label and label.text == 'Other' and text_input:
                        text_input.disabled = not checkbox.active

    def toggle_sleep_options(self, value, option):
        print(f"Debug: Toggling sleep options: {value}, {option}")
        sleep_issues_field = self.fields.get('sleep_issues')
        sleep_treatment_field = self.fields.get('sleep_treatment')

        if option == 'Yes, I have sleep-related issues' and value:
            if isinstance(sleep_issues_field, GridLayout):
                for child in sleep_issues_field.children:
                    if isinstance(child, BoxLayout):
                        checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                        if checkbox:
                            checkbox.disabled = False
            if sleep_treatment_field:
                sleep_treatment_field.disabled = False
        else:
            if isinstance(sleep_issues_field, GridLayout):
                for child in sleep_issues_field.children:
                    if isinstance(child, BoxLayout):
                        checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                        if checkbox:
                            checkbox.disabled = True
                            checkbox.active = False
                        text_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                        if text_input:
                            text_input.disabled = True
                            text_input.text = ''
            if sleep_treatment_field:
                sleep_treatment_field.disabled = True
                sleep_treatment_field.text = ''

        # Handle the 'Other' option
        other_box = next((child for child in sleep_issues_field.children if isinstance(child, BoxLayout) and any('Other' in c.text for c in child.children if isinstance(c, Label))), None)
        if other_box:
            other_checkbox = next((c for c in other_box.children if isinstance(c, CheckBox)), None)
            other_text_input = next((c for c in other_box.children if isinstance(c, TextInput)), None)
            if other_checkbox and other_text_input:
                other_checkbox.bind(active=lambda cb, val: setattr(other_text_input, 'disabled', not val))
                other_text_input.disabled = not (value and other_checkbox.active)

        print("Debug: Sleep options toggled")  
                     
    def on_sleep_issue_checkbox_active(self, checkbox, value):
        if checkbox.text == 'Other':
            other_input = next((child for child in self.fields['sleep_issues'].children 
                                if isinstance(child, TextInput) and 
                                child.hint_text == 'Specify other'), None)
            if other_input:
                other_input.disabled = not value
                
    def on_other_checkbox_active(self, checkbox, value):
        if checkbox.group == 'mental_health_conditions':
            self.fields['mental_health_other'].disabled = not value
        elif checkbox.group == 'sleep_issues':
            other_input = next((child for child in self.fields['sleep_issues'].children 
                                if isinstance(child, TextInput) and 
                                child.hint_text == 'Specify other'), None)
            if other_input:
                other_input.disabled = not value

    def bind_radio_to_spinner(self, group_name, spinner):
        for checkbox, option in self.fields[group_name]:
            checkbox.bind(active=lambda cb, value, s=spinner, o=option: self.toggle_spinner(s, value, o))

    def toggle_spinner(self, spinner, value, option):
        if option in ['Yes', 'Yes, I have diabetes', 'Yes, I have blood pressure issues'] and value:
            spinner.disabled = False
        elif option in ['No', 'No known diabetes', 'No known blood pressure issues'] and value:
            spinner.disabled = True
            spinner.text = 'Select Type' if 'type' in spinner.text.lower() else 'Select Frequency'
    
    def bind_radio_to_bp(self, group_name, bp_type_radio, current_input):
        for checkbox, option in self.fields[group_name]:
            checkbox.bind(active=lambda cb, value, r=bp_type_radio, c=current_input, opt=option: self.toggle_bp_fields(r, c, value, opt))
        
        # Initially disable all options
        self.toggle_bp_fields(bp_type_radio, current_input, False, 'No known blood pressure issues')

    def toggle_bp_fields(self, bp_type_radio, current_input, value, option):
        if option == 'Yes, I have blood pressure issues' and value:
            for child in bp_type_radio.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    if checkbox:
                        checkbox.disabled = False
            current_input.disabled = False
        else:
            for child in bp_type_radio.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    if checkbox:
                        checkbox.disabled = True
                        checkbox.active = False
                    text_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                    if text_input:
                        text_input.disabled = True
                        text_input.text = ''
            current_input.disabled = True
            current_input.text = ''

        # Handle the 'Other' option
        other_box = next((child for child in bp_type_radio.children if isinstance(child, BoxLayout) and any('Other' in c.text for c in child.children if isinstance(c, Label))), None)
        if other_box:
            other_checkbox = next((c for c in other_box.children if isinstance(c, CheckBox)), None)
            other_text_input = next((c for c in other_box.children if isinstance(c, TextInput)), None)
            if other_checkbox and other_text_input:
                other_checkbox.bind(active=lambda cb, val: setattr(other_text_input, 'disabled', not val))
                if other_checkbox.active:
                    other_text_input.disabled = False

    def toggle_diab_fields(self, diab_type_radio, current_input, value, option):
        other_input = self.fields.get('diabetes_type_other')
        if option == 'Yes, I have diabetes' and value:
            for child in diab_type_radio.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    if checkbox:
                        checkbox.disabled = False
            if other_input:
                other_input.disabled = True
            current_input.disabled = False
        elif option == 'No known diabetes' and value:
            for child in diab_type_radio.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    if checkbox:
                        checkbox.disabled = True
                        checkbox.active = False
            if other_input:
                other_input.disabled = True
                other_input.text = ''
            current_input.disabled = True
            current_input.text = ''            

        # Enable/disable the 'Other' text input based on the 'Other' radio button
        other_radio = None
        for child in diab_type_radio.children:
            if isinstance(child, BoxLayout):
                checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                label = next((c for c in child.children if isinstance(c, Label)), None)
                if checkbox and label and label.text == 'Other':
                    other_radio = checkbox
                    break
        
        if other_radio and other_input:
            other_radio.bind(active=lambda cb, val: setattr(other_input, 'disabled', not val))



    def create_radio_group(self, group_name, options):
        layout = GridLayout(cols=1, size_hint_y=None, height=dp(len(options) * 40))
        self.fields[group_name] = []
        for option in options:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
            checkbox = CheckBox(group=group_name, size_hint_x=None, width=dp(40), color=(0, 0, 0, 1), active=False)
            self.fields[group_name].append((checkbox, option))
            row.add_widget(checkbox)
            row.add_widget(Label(
                text=option,
                size_hint_y=None,
                height=dp(40),
                halign='left',
                text_size=(None, None),
                color=(0, 0, 0, 1),
                font_size=sp(14)
            ))
            layout.add_widget(row)
        return layout

    def create_radio_group_with_other(self, group_name, options):
        layout = GridLayout(cols=1, size_hint_y=None, height=dp(len(options) * 40))
        for option in options:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
            checkbox = CheckBox(group=group_name, size_hint_x=None, width=dp(40), color=(0, 0, 0, 1), disabled=True, active=False)
            row.add_widget(checkbox)
        
            if option == 'Other':
                label = Label(text=option, size_hint_x=0.3, height=dp(40), color=(0, 0, 0, 1), font_size=sp(14))
                row.add_widget(label)
                other_input = TextInput(hint_text='Specify other', size_hint_x=0.7, height=dp(40), disabled=True)
                row.add_widget(other_input)
                self.fields[f'{group_name}_other'] = other_input  # Add this line
            else:
                row.add_widget(Label(text=option, height=dp(40), color=(0, 0, 0, 1), font_size=sp(14)))
        
            layout.add_widget(row)
        return layout


    def add_padding(self):
        padding_widget = Widget(size_hint_y=None, height=dp(10))
        self.layout.add_widget(padding_widget)
        self.layout.add_widget(Widget())

    def create_text_input(self, multiline=False, input_type='text', hint_text=''):
        return TextInput(
            multiline=multiline,
            input_type=input_type,
            hint_text=hint_text,
            size_hint_y=None,
            height=dp(70) if multiline else dp(40),
            font_size=sp(14),
            background_color=(1, 1, 1, 1),
            foreground_color=(0, 0, 0, 1),
            hint_text_color=(0, 0, 0, 0.5),
            padding=(dp(10), dp(10), dp(10), dp(10))
        )

    def add_field(self, field_name, label_text, widget):
        if isinstance(widget.height, str):
            widget_height = float(widget.height[:-2])
        else:
            widget_height = float(widget.height)

        field_layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(widget_height + 30))

        # Add the red star for mandatory fields
        if field_name in ['*age', '*country', '*gender']:
            field_layout.add_widget(Label(text='*', size_hint_x=0.1, color=(1, 0, 0, 1)))

        field_layout.add_widget(Label(
            text=label_text,
            size_hint_y=None,
            height=dp(30),
            halign='left',
            text_size=(self.width, None),
            color=(0, 0, 0, 1),
            font_size=sp(14)
        ))

        field_layout.add_widget(widget)

        self.layout.add_widget(field_layout)

        if isinstance(widget, (TextInput, Spinner, CheckBox)):
            self.fields[field_name] = widget

    def create_checkbox_group(self, group_name, options):
        layout = GridLayout(cols=1, size_hint_y=None, height=dp(len(options) * 40))
        self.fields[group_name] = []
        for option in options:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
            checkbox = CheckBox(size_hint_x=None, width=dp(40), color=(0, 0, 0, 1))
            self.fields[group_name].append((checkbox, option))
            row.add_widget(checkbox)
            row.add_widget(Label(
                text=option,
                size_hint_y=None,
                height=dp(40),
                halign='left',
                text_size=(None, None),
                color=(0, 0, 0, 1),
                font_size=sp(14)
            ))
            layout.add_widget(row)
        return layout

    def gather_data(self):
        data = {}

        for field_name, field in self.fields.items():
            if isinstance(field, TextInput):
                if field.input_type == 'number':
                    data[field_name] = float(field.text) if field.text else None
                else:
                    data[field_name] = field.text.strip() if field.text else None
            
            elif isinstance(field, Spinner):
                if field.text not in ['Select Frequency', 'Select Type', 'Select Gender']:
                    data[field_name] = field.text
                else:
                    data[field_name] = None
            
            elif isinstance(field, CheckBox):
                data[field_name] = field.active
            
            elif isinstance(field, list):
                if field_name in ['mental_health_conditions', 'sleep_issues']:
                    conditions = []
                    for checkbox, option in field:
                        if checkbox.active:
                            if option == 'Other':
                                other_text = self.fields.get(f'{field_name}_other', TextInput()).text.strip()
                                if other_text:
                                    conditions.append(f"Other: {other_text}")
                            else:
                                conditions.append(option)
                    data[field_name] = conditions if conditions else None
                elif field_name == 'consent':
                    data[field_name] = any(checkbox.active for checkbox, option in field if option == 'I Agree')
                else:
                    data[field_name] = [option for checkbox, option in field if checkbox.active]
            
            elif isinstance(field, GridLayout):
                if field_name in ['blood_pressure_type', 'diabetes_type', 'sleep_issues_type']:
                    selected_type = None
                    other_text = None
                    for child in field.children:
                        if isinstance(child, BoxLayout):
                            checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                            label = next((c for c in child.children if isinstance(c, Label)), None)
                            if checkbox and label and checkbox.active:
                                if label.text == 'Other':
                                    other_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                                    if other_input:
                                        other_text = other_input.text.strip()
                                else:
                                    selected_type = label.text
                                break
                    data[field_name] = selected_type
                    data[f'{field_name}_other'] = other_text

        # Handle sleep data
        sleep_radio = self.fields.get('sleep')
        if sleep_radio:
            data['sleep'] = any(checkbox.active for checkbox, option in sleep_radio if option == 'Yes, I have sleep-related issues')

        sleep_issues = self.fields.get('sleep_issues')
        if sleep_issues:
            selected_issues = []
            for child in sleep_issues.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    label = next((c for c in child.children if isinstance(c, Label)), None)
                    if checkbox and label and checkbox.active:
                        if label.text == 'Other':
                            other_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                            if other_input and other_input.text.strip():
                                selected_issues.append(f"Other: {other_input.text.strip()}")
                        else:
                            selected_issues.append(label.text)
            data['sleep_issues'] = selected_issues if selected_issues else None

        sleep_treatment = self.fields.get('sleep_treatment')
        if sleep_treatment:
            data['sleep_treatment'] = sleep_treatment.text.strip() if sleep_treatment.text else None

        # Add debug print statements
        print("Debug: Blood pressure data:", {k: v for k, v in data.items() if k.startswith('blood_pressure')})
        print("Debug: Mental health data:", {k: v for k, v in data.items() if k.startswith('mental_health')})
        print("Debug: Sleep issues data:", {k: v for k, v in data.items() if k.startswith('sleep')})
        print("Debug: Full data collected:", data)

        return data


    def submit(self, instance):
        data = self.gather_data()
        data['consent'] = bool(data.get('consent'))
        # Add debug print statement
        print("Debug: Data being saved:", data)
        mandatory_fields = ['age', 'country', 'gender']
        missing_fields = [field for field in mandatory_fields if not data.get(field)]
        
        if missing_fields:
            error_message = f"Please fill in the following mandatory fields: {', '.join(missing_fields)}"
            popup = DataPopup("Error", error_message)
            popup.open()
            return

        app = App.get_running_app()
        user_id = app.session_manager.get_user_id()
        if user_id:
            try:
                # Print the data being saved for debugging
                print("Data being saved:", data)
                
                # Format boolean fields
                boolean_fields = ['alcohol_use', 'tobacco_use', 'substance_use', 'diabetes', 'blood_pressure',
                                'heart_condition', 'heart_surgery', 'physical_activity', 'mental_health',
                                'sleep', 'additional_health_info', 'consent']
                for field in boolean_fields:
                    if field in data:
                        data[field] = 'Yes' in data[field][0] if isinstance(data[field], list) else bool(data[field])
                
                # Handle 'Other' options
                other_fields = ['blood_pressure_type', 'diabetes_type', 'sleep_issues']
                for field in other_fields:
                    if field in data and data[field] == 'Other':
                        data[field] = data.get(f'{field}_other', 'Other')
                    elif f'{field}_other' in data:
                        del data[f'{field}_other']
                
                # Handle sleep issues
                if 'sleep' in data:
                    data['sleep'] = bool(data['sleep'])
                if 'sleep_issues' in data and isinstance(data['sleep_issues'], list):
                    data['sleep_issues'] = ', '.join(data['sleep_issues'])
                
                # Handle mental health conditions
                if 'mental_health_conditions' in data and isinstance(data['mental_health_conditions'], list):
                    data['mental_health_conditions'] = ', '.join(data['mental_health_conditions'])
                
                success = app.database.save_medical_record(user_id, data)
                if success:
                    popup = DataPopup("Success", "Data successfully saved to database")
                    popup.open()
                    popup.bind(on_dismiss=lambda _: app.switch_screen('dashboard'))
                else:
                    error_message = "Failed to save data to database. Please try again."
                    popup = DataPopup("Error", error_message)
                    popup.open()
            except Exception as e:
                error_message = f"Error saving medical record: {str(e)}\n\nPlease contact support if this persists."
                popup = DataPopup("Error", error_message)
                popup.open()
        else:
            popup = DataPopup("Error", "User not logged in. Please log in and try again.")
            popup.open()


    def go_back_to_dashboard(self, instance):
        App.get_running_app().switch_screen('dashboard')

    def on_pre_enter(self):
        Window.bind(on_key_down=self._on_keyboard_down)
        user_data = self.load_user_data()
        if user_data:
            self.populate_fields(user_data)
        else:
            self.reset_fields()  # Reset fields if no data

    def reset_fields(self):
        for field_name, field in self.fields.items():
            if isinstance(field, TextInput):
                field.text = ''
                if field_name == 'country':
                    field.disabled = False
            elif isinstance(field, Spinner):
                field.text = field.values[0] if field.values else ''
            elif isinstance(field, CheckBox):
                field.active = False
            elif isinstance(field, list):
                for checkbox, _ in field:
                    checkbox.active = False
                    
    def on_pre_leave(self):
        Window.unbind(on_key_down=self._on_keyboard_down)

    def load_user_data(self):
        app = App.get_running_app()
        user_id = app.session_manager.get_user_id()
        if user_id:
            medical_record = app.database.get_medical_record(user_id)
            if medical_record:
                return medical_record.to_dict()
        return None
    
    def populate_mental_health(self, data):
        print("Debug: Populating mental health with data:", data)
        
        mental_health = data.get('mental_health', False)
        if mental_health:
            self.set_radio_option('mental_health', 'Yes, I have been diagnosed')
        else:
            self.set_radio_option('mental_health', 'No known mental health conditions')
        
        mental_health_conditions = self.parse_set_like_string(data.get('mental_health_conditions', '{}'))
        print("Debug: Parsed mental health conditions:", mental_health_conditions)
        
        conditions_layout = self.fields['mental_health_conditions']
        if isinstance(conditions_layout, GridLayout):
            for child in conditions_layout.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    label = next((c for c in child.children if isinstance(c, Label)), None)
                    if checkbox and label:
                        condition = label.text
                        # Remove quotes and whitespace for comparison
                        checkbox.active = any(cond.strip('" ').lower() == condition.lower() for cond in mental_health_conditions)
                        print(f"Debug: Setting {condition} checkbox to {checkbox.active}")
                        if condition == 'Other':
                            other_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                            if other_input:
                                other_input.disabled = not checkbox.active
                                other_input.text = data.get('mental_health_other', '')
        
        treatment_field = self.fields.get('mental_health_treatment')
        if treatment_field:
            treatment_field.disabled = not mental_health
            treatment_field.text = data.get('mental_health_treatment', '')
        
        self.toggle_mental_health_options(mental_health, 'Yes, I have been diagnosed' if mental_health else 'No known mental health conditions')
                
    def set_radio_option(self, field_name, value):
        print(f"Debug: Setting {field_name} to {value}")
        for radio_button, option in self.fields[field_name]:
            radio_button.active = (option == value)
        print(f"Debug: {field_name} set complete")

    def populate_fields(self, data):
        print("Debug: Populating fields with data:", data)
        print("Debug: Mental health data:", {
            'mental_health': data.get('mental_health'),
            'mental_health_conditions': data.get('mental_health_conditions'),
            'mental_health_treatment': data.get('mental_health_treatment')
        })

        for field_name, value in data.items():
            if field_name in self.fields:
                field = self.fields[field_name]
                if isinstance(field, TextInput):
                    field.text = str(value) if value is not None else ''
                    if field_name == 'country':
                        field.disabled = False
                elif isinstance(field, Spinner):
                    if value in field.values:
                        field.text = value
                elif isinstance(field, CheckBox):
                    field.active = bool(value)
                elif isinstance(field, list):
                    self.populate_radio_group(field_name, value)

        # Handle special cases
        self.handle_special_cases(data)

        # Populate mental health section
        mental_health_data = {
            'mental_health': bool(data.get('mental_health')),
            'mental_health_conditions': str(data.get('mental_health_conditions', '')),
            'mental_health_treatment': str(data.get('mental_health_treatment', ''))
        }
        self.populate_mental_health(mental_health_data)

        # Handle special boolean cases
        boolean_fields = [
            ('diabetes', 'Yes, I have diabetes', 'No known diabetes'),
            ('blood_pressure', 'Yes, I have blood pressure issues', 'No known blood pressure issues'),
            ('heart_condition', 'Yes, I have a heart condition', 'No known heart condition'),
            ('heart_surgery', 'Yes, I have had heart surgery', 'No, I have not had any heart surgery'),
            ('physical_activity', 'Yes, I engage in physical activity/exercise', 'I do not engage in any regular physical activity or exercise'),
            ('additional_health_info', 'Yes, there is additional health information', 'No other relevant health information to share'),
            ('mental_health', 'Yes, I have been diagnosed', 'No known mental health conditions'),
            ('sleep', 'Yes, I have sleep-related issues', 'No known sleep issues')
        ]

        for field_name, yes_option, no_option in boolean_fields:
            if field_name in data:
                value = data[field_name]
                if isinstance(value, bool):
                    self.set_radio_option(field_name, yes_option if value else no_option)
                elif isinstance(value, str):
                    self.set_radio_option(field_name, yes_option if value.lower() == 'yes' else no_option)

        # Handle mental health
        mental_health_value = data.get('mental_health')
        if mental_health_value is not None:
            if mental_health_value == True or (isinstance(mental_health_value, str) and mental_health_value.lower() == 'yes'):
                self.set_radio_option('mental_health', 'Yes, I have been diagnosed')
                
                mental_health_conditions = data.get('mental_health_conditions', '').split(', ') if data.get('mental_health_conditions') else []
                other_condition = None
                for condition in mental_health_conditions:
                    if condition.startswith('Other:'):
                        other_condition = condition.split(':', 1)[1].strip()
                        break
                
                for checkbox, option in self.fields['mental_health_conditions']:
                    if option in mental_health_conditions or (option == 'Other' and other_condition):
                        checkbox.active = True
                        if option == 'Other':
                            other_field = self.fields.get('mental_health_other')
                            if other_field:
                                other_field.disabled = False
                                other_field.text = other_condition or ''

                treatment_field = self.fields.get('mental_health_treatment')
                if treatment_field:
                    treatment_field.disabled = False
                    treatment_field.text = data.get('mental_health_treatment', '') or ''
            else:
                self.set_radio_option('mental_health', 'No known mental health conditions')


        # Handle blood pressure
        blood_pressure_value = data.get('blood_pressure')
        print(f"Debug: Blood pressure value from data: {blood_pressure_value}")

        bp_radio = self.fields.get('blood_pressure')
        bp_type_radio = self.fields.get('blood_pressure_type')
        current_bp_field = self.fields.get('blood_pressure_current')

        if blood_pressure_value == True:
            self.set_radio_option('blood_pressure', 'Yes, I have blood pressure issues')
            
            # Call toggle_bp_fields to enable the blood pressure type options
            if bp_radio and bp_type_radio and current_bp_field:
                self.toggle_bp_fields(bp_type_radio, current_bp_field, True, 'Yes, I have blood pressure issues')

            bp_type = data.get('blood_pressure_type')
            if bp_type and isinstance(bp_type_radio, GridLayout):
                for child in bp_type_radio.children:
                    if isinstance(child, BoxLayout):
                        checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                        label = next((c for c in child.children if isinstance(c, Label)), None)
                        if checkbox and label and label.text == bp_type:
                            checkbox.active = True
                            break

            # Handle the 'Other' option
            bp_type_other = data.get('blood_pressure_type_other')
            if bp_type_other:
                other_box = next((child for child in bp_type_radio.children if isinstance(child, BoxLayout) and any('Other' in c.text for c in child.children if isinstance(c, Label))), None)
                if other_box:
                    other_checkbox = next((c for c in other_box.children if isinstance(c, CheckBox)), None)
                    other_text_input = next((c for c in other_box.children if isinstance(c, TextInput)), None)
                    if other_checkbox and other_text_input:
                        other_checkbox.active = True
                        other_text_input.disabled = False
                        other_text_input.text = bp_type_other

            if current_bp_field:
                current_bp_field.text = str(data.get('blood_pressure_current', ''))
        else:
            self.set_radio_option('blood_pressure', 'No known blood pressure issues')
            if bp_radio and bp_type_radio and current_bp_field:
                self.toggle_bp_fields(bp_type_radio, current_bp_field, False, 'No known blood pressure issues')

        # Add debug prints
        print("Debug: Blood pressure value:", blood_pressure_value)
        print("Debug: Blood pressure type:", data.get('blood_pressure_type'))
        print("Debug: Blood pressure type other:", data.get('blood_pressure_type_other'))
        print("Debug: Blood pressure current:", data.get('blood_pressure_current'))
        if bp_radio:
            print("Debug: Blood pressure radio buttons:", [checkbox.active for checkbox, _ in bp_radio])
        if bp_type_radio and isinstance(bp_type_radio, GridLayout):
            print("Debug: Blood pressure type checkboxes:", [next((c.active for c in child.children if isinstance(c, CheckBox)), None) for child in bp_type_radio.children if isinstance(child, BoxLayout)])
                
                

        # Handle Country of Residence
        country_field = self.fields.get('country')
        if country_field:
            country_value = data.get('country', '')
            country_field.text = country_value or ''
            country_field.disabled = False  # Ensure it's always enabled   
            

        # Handle sleep
        sleep_value = data.get('sleep')
        print(f"Debug: Sleep value from data: {sleep_value}")

        if sleep_value is not None:
            sleep_option = 'Yes, I have sleep-related issues' if sleep_value else 'I have no issues with sleep'
            self.set_radio_option('sleep', sleep_option)
            print(f"Debug: Set radio option for sleep: {sleep_option}")

            if sleep_value:
                sleep_issues = data.get('sleep_issues', '')
                issues = self.parse_set_like_string(sleep_issues)
                self.populate_checkbox_grid('sleep_issues', issues)
                print(f"Debug: Populated sleep issues: {issues}")

                # Populate sleep treatment
                sleep_treatment_field = self.fields.get('sleep_treatment')
                if sleep_treatment_field:
                    sleep_treatment_field.text = data.get('sleep_treatment', '')
                    sleep_treatment_field.disabled = False
                    print(f"Debug: Set sleep treatment: {sleep_treatment_field.text}")
            else:
                # Disable sleep issues and treatment if no sleep issues
                self.toggle_sleep_options(False, 'I have no issues with sleep')
                    
                    
        # Handle other special cases
        self.handle_special_cases(data)

        print("Debug: Mental health conditions after population:", [option for checkbox, option in self.fields['mental_health_conditions'] if checkbox.active])
        print("Debug: Mental health other field:", self.fields.get('mental_health_other').text if self.fields.get('mental_health_other') else "Not found")

    def toggle_mental_health_fields(self, conditions_layout, treatment_input, value, option):
        if option == 'Yes, I have mental health conditions' and value:
            for child in conditions_layout.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    if checkbox:
                        checkbox.disabled = False
            treatment_input.disabled = False
        else:
            for child in conditions_layout.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    if checkbox:
                        checkbox.disabled = True
                        checkbox.active = False
                    text_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                    if text_input:
                        text_input.disabled = True
                        text_input.text = ''
            treatment_input.disabled = True
            treatment_input.text = ''

        # Handle the 'Other' option
        other_box = next((child for child in conditions_layout.children if isinstance(child, BoxLayout) and any('Other' in c.text for c in child.children if isinstance(c, Label))), None)
        if other_box:
            other_checkbox = next((c for c in other_box.children if isinstance(c, CheckBox)), None)
            other_text_input = next((c for c in other_box.children if isinstance(c, TextInput)), None)
            if other_checkbox and other_text_input:
                other_checkbox.bind(active=lambda cb, val: setattr(other_text_input, 'disabled', not val))        

    def parse_set_like_string(self, string):
        if not string:
            return set()
        return set(item.strip() for item in string.split(','))

    def populate_checkbox_grid(self, field_name, selected_options):
        field = self.fields.get(field_name)
        if isinstance(field, GridLayout):
            for child in field.children:
                if isinstance(child, BoxLayout):
                    checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                    label = next((c for c in child.children if isinstance(c, Label)), None)
                    if checkbox and label:
                        checkbox.active = label.text in selected_options
                        print(f"Debug: Setting {field_name} checkbox '{label.text}' to {checkbox.active}")
                        if label.text == 'Other':
                            other_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                            if other_input:
                                other_text = next((opt for opt in selected_options if opt.startswith('Other:')), '')
                                other_input.text = other_text.split(':', 1)[1].strip() if other_text else ''
                                other_input.disabled = not checkbox.active
                                print(f"Debug: Setting {field_name} 'Other' text to '{other_input.text}' and disabled to {other_input.disabled}")
                                
        def set_radio_option(self, field_name, option):
            print(f"Debug: Setting {field_name} to {option}")
            if field_name in self.fields:
                for checkbox, text in self.fields[field_name]:
                    checkbox.active = (text == option)
                    print(f"Debug: Checkbox for '{text}' set to {checkbox.active}")

                # After setting all checkboxes
                print(f"Debug: After setting {field_name}, radio buttons are: {[checkbox.active for checkbox, _ in self.fields[field_name]]}")

                for checkbox, text in self.fields[field_name]:
                    if checkbox.active:
                        # Trigger any associated logic
                        toggle_method_name = f'toggle_{field_name}_fields'
                        if hasattr(self, toggle_method_name):
                            toggle_method = getattr(self, toggle_method_name)
                            # Check the number of parameters the method expects
                            import inspect
                            params = inspect.signature(toggle_method).parameters
                            if len(params) == 3:  # self, value, option
                                print(f"Debug: Calling {toggle_method_name} with 2 parameters")
                                toggle_method(checkbox.active, option)
                            elif len(params) == 4:  # self, field1, field2, value, option
                                # Assuming the first two fields are the ones we need to toggle
                                fields = [f for f in self.fields.values() if isinstance(f, (GridLayout, TextInput))][:2]
                                if len(fields) == 2:
                                    print(f"Debug: Calling {toggle_method_name} with 4 parameters")
                                    toggle_method(fields[0], fields[1], checkbox.active, option)
                                else:
                                    print(f"Debug: Not enough fields for {toggle_method_name}")
                            else:
                                print(f"Debug: Unexpected number of parameters for {toggle_method_name}")
                        else:
                            print(f"Debug: No toggle method found for {field_name}")
            else:
                print(f"Debug: Field {field_name} not found in self.fields")
            
            # Force layout update
            if hasattr(self.ids, f'{field_name}_grid'):
                getattr(self.ids, f'{field_name}_grid').do_layout()
                print(f"Debug: Forced layout update for {field_name}_grid")
            
            print(f"Debug: Finished setting {field_name}")

    def set_radio_option(self, field_name, option_text):
        radio_group = self.fields.get(field_name)
        if radio_group and isinstance(radio_group, list):
            for checkbox, option in radio_group:
                if option == option_text:
                    checkbox.active = True
                else:
                    checkbox.active = False
        print(f"Debug: Set radio option for {field_name}: {option_text}")

                                 
    def populate_radio_group(self, field_name, value):
        for checkbox, option in self.fields[field_name]:
            if isinstance(value, bool):
                checkbox.active = (option.lower() == 'yes') if value else (option.lower() == 'no')
            else:
                checkbox.active = (str(value).lower() == option.lower()) if value is not None else False

    def populate_sleep(self, value):
        if isinstance(value, dict):
            # Set the main sleep checkbox
            for checkbox, option in self.fields['sleep']:
                if option == 'Yes, I have sleep-related issues':
                    checkbox.active = value.get('sleep', False)
                    self.toggle_sleep_options(checkbox.active, option)
                    break
            
            # Set sleep issues
            sleep_issues = value.get('sleep_issues', '').split(', ')
            sleep_issues_field = self.fields.get('sleep_issues')
            if isinstance(sleep_issues_field, GridLayout):
                for child in sleep_issues_field.children:
                    if isinstance(child, BoxLayout):
                        checkbox = next((c for c in child.children if isinstance(c, CheckBox)), None)
                        label = next((c for c in child.children if isinstance(c, Label)), None)
                        if checkbox and label:
                            checkbox.active = label.text in sleep_issues
                            if label.text == 'Other' and any(issue.startswith('Other:') for issue in sleep_issues):
                                other_issue = next(issue for issue in sleep_issues if issue.startswith('Other:'))
                                other_input = next((c for c in child.children if isinstance(c, TextInput)), None)
                                if other_input:
                                    other_input.text = other_issue.split(':', 1)[1].strip()
            
            # Set sleep treatment
            self.fields['sleep_treatment'].text = value.get('sleep_treatment', '')
        elif isinstance(value, bool):
            # If value is a boolean, just set the main sleep checkbox
            for checkbox, option in self.fields['sleep']:
                if option == 'Yes, I have sleep-related issues':
                    checkbox.active = value
                    self.toggle_sleep_options(value, option)
                    break
        else:
            # If value is neither a dict nor a bool, log an error or handle as needed
            print(f"Unexpected value type in populate_sleep: {type(value)}")


    def handle_special_cases(self, data):

        # Enable/disable fields based on populated data
        self.toggle_spinner(self.fields['alcohol_frequency'], data.get('alcohol_use') == True, 'Yes')
        self.toggle_spinner(self.fields['tobacco_frequency'], data.get('tobacco_use') == True, 'Yes')
        self.toggle_substance_fields(self.fields['substance_frequency'], self.fields['substance_type'], data.get('substance_use') == True, 'Yes')
        self.toggle_diabetes_fields(self.fields['diabetes_type'], self.fields['diabetes_treatment'], data.get('diabetes') == 'Yes, I have diabetes', 'Yes, I have diabetes')
        self.toggle_text_input(self.fields['heart_condition_details'], data.get('heart_condition') == True, 'Yes, I have a heart condition')
        self.toggle_text_input(self.fields['heart_surgery_year'], data.get('heart_surgery') == True, 'Yes, I have had heart surgery')
        self.toggle_text_input(self.fields['heart_surgery_type'], data.get('heart_surgery') == True, 'Yes, I have had heart surgery')
        self.toggle_text_input(self.fields['physical_activity_details'], data.get('physical_activity') == True, 'Yes, I engage in physical activity/exercise')
        self.toggle_text_input(self.fields['additional_health_info_details'], data.get('additional_health_info') == True, 'Yes, there is additional health information')

        self.toggle_bp_fields(self.fields['blood_pressure_type'], 
                            self.fields['blood_pressure_current'], 
                            data.get('blood_pressure') == True or data.get('blood_pressure') == 'Yes, I have blood pressure issues', 
                            'Yes, I have blood pressure issues')
                         
    def bind_radio_to_text_input(self, group_name, text_input):
        for checkbox, option in self.fields[group_name]:
            checkbox.bind(active=lambda cb, value, t=text_input, o=option: self.toggle_text_input(t, value, o))

    def toggle_text_input(self, text_input, value, option):
        if option.startswith('Yes') and value:
            text_input.disabled = False
        else:
            text_input.disabled = True
            text_input.text = ''

    def create_mental_health_layout(self):
        layout = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(330))

        # Main radio group
        main_radio = self.create_radio_group('mental_health', ['No known mental health conditions', 'Yes, I have been diagnosed'])
        layout.add_widget(main_radio)

        # Mental health conditions checkbox group
        conditions_layout = GridLayout(cols=1, size_hint_y=None, height=dp(200))
        conditions_options = ['Anxiety disorder', 'Depression', 'Bipolar disorder', 'Schizophrenia', 'Other']
        self.fields['mental_health_conditions'] = []
        for option in conditions_options:
            row = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
            checkbox = CheckBox(size_hint_x=None, width=dp(40), color=(0, 0, 0, 1), disabled=True)
            row.add_widget(checkbox)
            
            if option == 'Other':
                label = Label(text=option, size_hint_x=0.3, height=dp(40), color=(0, 0, 0, 1), font_size=sp(14))
                row.add_widget(label)
                self.fields['mental_health_other'] = self.create_text_input(hint_text='Specify other')
                self.fields['mental_health_other'].size_hint_x = 0.7
                self.fields['mental_health_other'].height = dp(40)
                self.fields['mental_health_other'].disabled = True
                row.add_widget(self.fields['mental_health_other'])
                
                # Bind the 'Other' checkbox to enable/disable the 'Other' text input
                checkbox.bind(active=self.on_other_checkbox_active)
            else:
                row.add_widget(Label(text=option, height=dp(40), color=(0, 0, 0, 1), font_size=sp(14)))
            
            self.fields['mental_health_conditions'].append((checkbox, option))
            conditions_layout.add_widget(row)
        
        layout.add_widget(conditions_layout)

        self.fields['mental_health_treatment'] = self.create_text_input(hint_text='Currently receiving treatment (e.g. therapy, medication)')
        self.fields['mental_health_treatment'].disabled = True
        layout.add_widget(self.fields['mental_health_treatment'])

        # Bind the main radio buttons to enable/disable the condition options
        for checkbox, option in self.fields['mental_health']:
            checkbox.bind(active=lambda cb, value, o=option: self.toggle_mental_health_options(value, o))

        return layout
        

    def toggle_mental_health_options(self, value, option):
        print(f"Debug: Toggling mental health options: {value}, {option}")
        mental_health_conditions = self.fields.get('mental_health_conditions')
        
        if mental_health_conditions is None:
            print("Error: mental_health_conditions field not found")
            return

        if option == 'Yes, I have been diagnosed' and value:
            for checkbox, _ in mental_health_conditions:
                checkbox.disabled = False
            self.fields['mental_health_treatment'].disabled = False
        else:
            for checkbox, _ in mental_health_conditions:
                checkbox.disabled = True  
            self.fields['mental_health_treatment'].disabled = True
            

        # Handle the 'Other' option
        other_item = next((item for item in mental_health_conditions if item[1] == 'Other'), None)
        if other_item:
            other_checkbox, _ = other_item
            other_text_input = self.fields.get('mental_health_other')
            if other_checkbox and other_text_input:
                other_checkbox.bind(active=lambda cb, val: setattr(other_text_input, 'disabled', not val))
                other_text_input.disabled = not (value and other_checkbox.active)

        print("Debug: Mental health options toggled")
                            
class CenteredButton2(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super(CenteredButton2, self).__init__(**kwargs)
        self.halign = 'center'
        self.valign = 'middle'
        self.size_hint_y = None
        self.height = dp(50)
        self.color = (1, 1, 1, 1)  # White text
        self.font_size = sp(14)
        self.background_color = (0.2, 0.6, 1, 1)  # Blue background
        self.bind(size=self.update_background, pos=self.update_background)

    def on_size(self, *args):
        self.text_size = self.size

    def update_background(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.background_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10,])          

    def on_press(self):
        self.background_color = (0.2, 0.6, 1, 1)  # Darker blue when pressed
        self.update_background()

    def on_release(self):
        self.background_color = (0.2, 0.6, 1, 1)  # Original blue when released
        self.update_background()
        
class DataPopup(Popup):
    def __init__(self, title, message, **kwargs):
        super(DataPopup, self).__init__(**kwargs)
        self.title = title
        self.size_hint = (0.9, 0.3)  # Increased height to 80% of the screen
        self.height = dp(150)  # Set a minimum height
        
        content = ScrollView(size_hint=(1, 1))
        layout = GridLayout(cols=1, spacing=10, size_hint_y=None)
        layout.bind(minimum_height=layout.setter('height'))
        
        if isinstance(message, dict):
            for key, value in message.items():
                layout.add_widget(Label(text=f"{key}: {value}", size_hint_y=None, height=40))
        else:
            layout.add_widget(Label(text=message, size_hint_y=None, height=40))
        
        content.add_widget(layout)
        self.content = content


class CenteredButton4(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        self.background_color = kwargs.pop('background_color', (0.2, 0.6, 1, 1))
        self.text_color = kwargs.pop('text_color', (1, 1, 1, 1))
        super(CenteredButton4, self).__init__(**kwargs)
        self.halign = 'center'
        self.valign = 'middle'
        self.size_hint_y = None
        self.height = dp(50)
        self.color = self.text_color
        self.font_size = sp(14)
        self.bind(size=self.update_background, pos=self.update_background)
        self.update_background()

    def on_size(self, *args):
        self.text_size = self.size

    def update_background(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.background_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10,])

    def on_press(self):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*(0.2, 0.6, 1, 1))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10,])

    def on_release(self):
        self.update_background()

class StyledTextInput2(TextInput):
    def __init__(self, **kwargs):
        super(StyledTextInput2, self).__init__(**kwargs)
        self.background_color = [1, 1, 1, 1]
        self.foreground_color = [0, 0, 0, 1]
        self.cursor_color = [0, 0, 0, 1]
        self.multiline = True
        self.font_size = dp(16)
        self.padding = [dp(15), dp(15), dp(15), dp(15)]
        self.border = [1, 1, 1, 1]
        self.border_color = [0.7, 0.7, 0.7, 1]


class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super(ChatScreen, self).__init__(**kwargs)
        
        self.layout = FloatLayout()
        
        with self.layout.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.rect = Rectangle(size=self.layout.size, pos=self.layout.pos)
        self.layout.bind(size=self._update_rect, pos=self._update_rect)
        
        self.chat_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10), size_hint=(1, 1))
        
        self.chat_box = BoxLayout(orientation='vertical', size_hint=(1, 0.7))
        with self.chat_box.canvas.before:
            Color(1, 1, 1, 1)
            self.chat_rect = Rectangle(size=self.chat_box.size, pos=self.chat_box.pos)
        self.chat_box.bind(size=self._update_chat_rect, pos=self._update_chat_rect)
        
        self.chat_scroll = ScrollView(size_hint=(1, 1))
        self.chat_content = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(10), padding=dp(10))
        self.chat_content.bind(minimum_height=self.chat_content.setter('height'))
        self.chat_scroll.add_widget(self.chat_content)
        self.chat_box.add_widget(self.chat_scroll)
        
        self.input_layout = BoxLayout(orientation='vertical', size_hint=(1, None), spacing=dp(10))
        self.message_input = StyledTextInput2(hint_text='Type your message...', multiline=True, size_hint=(1, None), height=dp(100))
        self.input_layout.add_widget(self.message_input)
        self.input_layout.bind(minimum_height=self.input_layout.setter('height'))
        
        self.button_layout = BoxLayout(size_hint=(1, None), height=dp(50), spacing=dp(10))
        self.send_button = CenteredButton4(text='Send to AI', size_hint=(0.33, 1))
        self.send_button.bind(on_press=self.send_message)
        self.clear_button = CenteredButton4(text='Clear Chat', size_hint=(0.33, 1))
        self.clear_button.bind(on_press=self.clear_chat)
        self.back_button = CenteredButton4(text='Dashboard', size_hint=(0.34, 1))
        self.back_button.bind(on_press=self.go_to_dashboard)
        self.button_layout.add_widget(self.send_button)
        self.button_layout.add_widget(self.clear_button)
        self.button_layout.add_widget(self.back_button)
        
        self.chat_layout.add_widget(self.chat_box)
        self.chat_layout.add_widget(self.input_layout)
        self.chat_layout.add_widget(self.button_layout)
        
        self.layout.add_widget(self.chat_layout)
        
        self.loading_layout = FloatLayout(size_hint=(1, 1))
        self.loading_layout.opacity = 0
        self.layout.add_widget(self.loading_layout)

        self.add_widget(self.layout)
        
        self.engine = create_engine('postgresql://postgres.owdlwnulwgaikqurlisb:wDeAmJHq9yPztTZu@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
        self.Session = sessionmaker(bind=self.engine)

        self.circle_angle = 0
        self.circle_event = None

        Window.bind(size=self._update_layout)

    def _update_layout(self, instance, value):
        window_height = Window.height
        self.message_input.height = min(dp(150), window_height * 0.2)
        self.input_layout.height = self.message_input.height + dp(20)
        self.chat_box.size_hint = (1, 1 - (self.input_layout.height + self.button_layout.height) / window_height)

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def _update_chat_rect(self, instance, value):
        self.chat_rect.pos = instance.pos
        self.chat_rect.size = instance.size

    def send_message(self, instance):
        if App.get_running_app().get_current_user_id() is None:
            print("Error: You must be logged in to send messages.")
            return
        
        message = self.message_input.text.strip()
        if message:
            self.display_message("ME: " + message, is_user=True)
            
            if self.is_greeting(message):
                self.display_message("MED END: Hello, how can I help you?", is_user=False)
            else:
                keywords = extract_keywords(message)
                self.save_keywords_to_db(keywords)
                
                self.show_loading_indicator()
                
                threading.Thread(target=self.process_ai_response, args=(keywords,)).start()
            
            self.message_input.text = ''

    def is_greeting(self, message):
        greetings = [
            r'\b(hi|hello|hey|good morning|good afternoon|good evening)\b',  # English
            r'\b(hej|hallå|god morgon|god dag|god kväll)\b',  # Swedish
            r'\b(hei|moi|terve|huomenta|päivää|iltaa)\b'  # Finnish
        ]
        
        for pattern in greetings:
            if re.search(pattern, message.lower()):
                return True
        return False

    def process_ai_response(self, keywords):
        user_data = self.get_user_data_from_db()
        ai_response = generate_health_recommendations(user_data, keywords)
        Clock.schedule_once(lambda dt: self.display_ai_response(ai_response), 0)

    def display_ai_response(self, ai_response):
        self.hide_loading_indicator()
        self.display_message("MED END Recommendation: " + ai_response, is_user=False)

    def show_loading_indicator(self):
        self.loading_layout.opacity = 1
        self.start_rotating_circle()

    def hide_loading_indicator(self):
        self.loading_layout.opacity = 0
        self.stop_rotating_circle()

    def start_rotating_circle(self):
        self.circle_event = Clock.schedule_interval(self.update_circle, 1/30)

    def stop_rotating_circle(self):
        if self.circle_event:
            self.circle_event.cancel()

    def update_circle(self, dt):
        self.circle_angle += 10
        if self.circle_angle >= 360:
            self.circle_angle = 0
        
        self.loading_layout.canvas.clear()
        with self.loading_layout.canvas:
            Color(0, 0.7, 0.9)  # Light blue color
            Line(circle=(self.loading_layout.center_x, self.loading_layout.center_y, dp(30)), width=dp(3))
            Color(0, 0.7, 0.9, 0.8)
            Line(circle=(self.loading_layout.center_x, self.loading_layout.center_y, dp(30)), width=dp(3), angle_start=self.circle_angle, angle_end=self.circle_angle + 90)

    def display_message(self, message, is_user):
        text_input = TextInput(
            text=message,
            size_hint_y=None,
            readonly=True,
            multiline=True,
            background_color=(0.9, 0.9, 0.9, 1) if is_user else (1, 1, 1, 1)
        )
        text_input.color = (0, 0, 0, 1)
        text_input.padding = [10, 2]
        text_input.font_size = '14sp'
        
        text_input.width = Window.width * 0.9
        
        def adjust_height(instance, *args):
            instance.height = max(instance.minimum_height, instance.minimum_height + 5)
        
        text_input.bind(text=adjust_height, size=adjust_height)
        
        Clock.schedule_once(lambda dt: adjust_height(text_input), 0)
        
        self.chat_content.add_widget(text_input)
        Clock.schedule_once(lambda dt: setattr(self.chat_scroll, 'scroll_y', 0))

    def clear_chat(self, instance):
        self.chat_content.clear_widgets()

    def go_to_dashboard(self, instance):
        App.get_running_app().switch_screen('dashboard')

    def save_keywords_to_db(self, keywords):
        session = self.Session()
        try:
            user_id = App.get_running_app().get_current_user_id()
            if user_id is None:
                print("Error: No user is currently logged in.")
                return

            for keyword in keywords.split(','):
                keyword = keyword.strip()
                if len(keyword) > 3:
                    symptom = Symptom(user_id=user_id, keyword=keyword)
                    session.add(symptom)
            session.commit()
        except Exception as e:
            print(f"Error saving keywords to database: {str(e)}")
            session.rollback()
        finally:
            session.close()

    def get_user_data_from_db(self):
        session = self.Session()
        try:
            user_id = App.get_running_app().get_current_user_id()
            if user_id is None:
                print("Error: No user is currently logged in.")
                return {}

            medical_record = session.query(MedicalRecord).filter_by(user_id=user_id).first()
            if medical_record:
                user_data = medical_record.to_dict()
                # Ensure consent is included in the user_data
                user_data['consent'] = medical_record.consent
                return user_data
            return {}
        finally:
            session.close()
        


class JustifiedLabel(Label):
    text = StringProperty('')

    def __init__(self, **kwargs):
        super(JustifiedLabel, self).__init__(**kwargs)
        self.bind(size=self.update_text_size)

    def update_text_size(self, instance, value):
        self.text_size = (self.width - dp(20), None)

    def on_text(self, instance, value):
        self.update_text_size(None, None)

class CenteredButton3(ButtonBehavior, Label):
    def __init__(self, **kwargs):
        super(CenteredButton3, self).__init__(**kwargs)
        self.halign = 'center'
        self.valign = 'middle'
        self.size_hint_y = None
        self.height = dp(50)
        self.color = (1, 1, 1, 1)  # White text
        self.font_size = sp(14)
        self.background_color = (0.2, 0.6, 1, 1)  # Blue background
        self.bind(size=self.update_background, pos=self.update_background)

    def on_size(self, *args):
        self.text_size = self.size

    def update_background(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.background_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[10,])

    def on_press(self):
        self.background_color = (0.1, 0.5, 0.9, 1)  # Darker blue when pressed
        self.update_background()

    def on_release(self):
        self.background_color = (0.2, 0.6, 1, 1)  # Original blue when released
        self.update_background()

class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super(DashboardScreen, self).__init__(**kwargs)

        with self.canvas.before:
            Color(0.95, 0.95, 0.95, 1)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self.update_rect, size=self.update_rect)

        main_layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        top_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(60))

        logo_layout = AnchorLayout(anchor_x='center', anchor_y='center')
        logo = Image(source=resource_path('assets/logo.png'), size_hint=(None, None), size=(dp(150), dp(50)))
        logo_layout.add_widget(logo)
        top_layout.add_widget(logo_layout)

        logout_layout = AnchorLayout(anchor_x='right', anchor_y='center')
        logout_button = CenteredButton3(
            text='Logout',
            size_hint=(None, None),
            size=(dp(70), dp(35))
        )
        logout_button.bind(on_press=self.logout)
        logout_layout.add_widget(logout_button)
        top_layout.add_widget(logout_layout)

        content_layout = BoxLayout(orientation='vertical', spacing=20)

        user_info_layout = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_y=None, height=dp(150))
        user_content = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(200))

        user_photo = Image(source=resource_path('assets/user_photo.png'), size_hint=(None, None), size=(dp(80), dp(80)))
        photo_layout = AnchorLayout(anchor_x='center', anchor_y='center', size_hint_y=None, height=dp(90))
        photo_layout.add_widget(user_photo)
        user_content.add_widget(photo_layout)

        self.user_name_label = Label(text='', font_size='20sp', color=(0, 0, 0, 1), size_hint_y=None, height=dp(30))
        self.user_location_label = Label(text='', font_size='16sp', color=(0, 0, 0, 1), size_hint_y=None, height=dp(20))
        self.user_age_label = Label(text='', font_size='16sp', color=(0, 0, 0, 1), size_hint_y=None, height=dp(20))

        user_content.add_widget(self.user_name_label)
        user_content.add_widget(self.user_location_label)
        user_content.add_widget(self.user_age_label)

        user_info_layout.add_widget(user_content)
        content_layout.add_widget(user_info_layout)


        # Add 20px margin-top
        content_layout.add_widget(Widget(size_hint_y=None, height=dp(20)))

        # Add the new text here with improved layout and justified text
        instruction_box = BorderedBox()
        instruction_label = JustifiedLabel(
            text="In order to help you as much as possible, please first click on the Medical Questionnaire button and answer the questions correctly.",
            size_hint_y=None,
            color=(0.5, 0.1, 0.3, 1),
            font_size=sp(18)
        )
        instruction_label.bind(
            texture_size=lambda *x: setattr(instruction_label, 'height', instruction_label.texture_size[1])
        )
        instruction_box.add_widget(instruction_label)
        content_layout.add_widget(instruction_box)


        buttons_layout = BoxLayout(orientation='horizontal', spacing=20, pos_hint={'center_x': 0.5})
        medical_questioner_button = CenteredButton3(
            text='Medical Questionnaire',
            size_hint=(0.5, None),
            height=dp(50)
        )
        medical_questioner_button.bind(on_press=self.go_to_questionnaire)
        ai_chat_button = CenteredButton3(
            text='AI Chat',
            size_hint=(0.5, None),
            height=dp(50)
        )
        ai_chat_button.bind(on_press=self.go_to_chat)
        buttons_layout.add_widget(medical_questioner_button)
        buttons_layout.add_widget(ai_chat_button)
        content_layout.add_widget(buttons_layout)

        main_layout.add_widget(top_layout)
        main_layout.add_widget(content_layout)

        self.add_widget(main_layout)

        self.engine = create_engine('postgresql://postgres.owdlwnulwgaikqurlisb:wDeAmJHq9yPztTZu@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres')
        self.Session = sessionmaker(bind=self.engine)

    def on_enter(self):
        self.update_user_info()

    def update_user_info(self):
        session = self.Session()
        try:
            user_id = App.get_running_app().get_current_user_id()
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                self.user_name_label.text = f"Hello {user.username}"
                
                medical_record = session.query(MedicalRecord).filter_by(user_id=user_id).first()
                if medical_record:
                    self.user_location_label.text = f"Country: {medical_record.country}"
                    self.user_age_label.text = f"Age: {medical_record.age}"
                else:
                    self.user_location_label.text = "Country: Not available"
                    self.user_age_label.text = "Age: Not available"
            else:
                self.user_name_label.text = "Hello User"
                self.user_location_label.text = "Country: Not available"
                self.user_age_label.text = "Age: Not available"
        except Exception as e:
            print(f"Error fetching user info: {str(e)}")
            self.user_name_label.text = "Hello, User"
            self.user_location_label.text = "Country: Not available"
            self.user_age_label.text = "Age: Not available"
        finally:
            session.close()

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def go_to_questionnaire(self, instance):
        App.get_running_app().switch_screen('questionnaire')

    def go_to_chat(self, instance):
        App.get_running_app().switch_screen('chat')

    def logout(self, instance):
        App.get_running_app().logout()
        
        
class BorderedBox(BoxLayout):
    def __init__(self, **kwargs):
        super(BorderedBox, self).__init__(**kwargs)
        self.padding = dp(15)
        self.size_hint_y = None
        self.bind(minimum_height=self.setter('height'))
        
        with self.canvas.before:
            Color(0.9, 0.9, 0.9, 1)  # Light gray background
            self.bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
            
            # Shadow (drawn behind the main rectangle)
            Color(0, 0, 0, 0.1)  # Semi-transparent black
            self.shadow_rect = RoundedRectangle(pos=(self.x + dp(2), self.y - dp(2)), 
                                                size=self.size, radius=[dp(10)])
        
        self.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        self.shadow_rect.pos = (self.x + dp(2), self.y - dp(2))
        self.shadow_rect.size = self.size


class MedicalApp(App):
    def build(self):
        self.database = Database()
        self.session_manager = SessionManager()
      
        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(RegisterScreen(name='register'))
        sm.add_widget(ForgotPasswordScreen(name='forgot_password'))
        sm.add_widget(QuestionnaireScreen(name='questionnaire'))
        sm.add_widget(ChatScreen(name='chat'))
        sm.add_widget(DashboardScreen(name='dashboard'))
        
        Window.bind(on_request_close=self.on_request_close)
        
        return sm
    
    def on_request_close(self, *args):
        self.show_exit_popup()
        return True

    def show_exit_popup(self):
        box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        box.add_widget(Label(text='Are you sure you want to exit?'))
        
        buttons = BoxLayout(spacing=30)
        yes_button = Button(text='Yes', size_hint=(None, None), size=(110, 30))
        no_button = Button(text='No', size_hint=(None, None), size=(110, 30))
        
        buttons.add_widget(yes_button)
        buttons.add_widget(no_button)
        box.add_widget(buttons)

        popup = Popup(title='Exit Confirmation', content=box, size_hint=(None, None), size=(300, 200))
        
        yes_button.bind(on_release=self.stop)
        no_button.bind(on_release=popup.dismiss)
        
        popup.open()
        
    def switch_screen(self, screen_name):
        self.root.current = screen_name

    def logout(self):
        self.session_manager.clear_user()
        self.switch_screen('login')

    def get_current_user_id(self):
        return self.session_manager.get_user_id()

if __name__ == '__main__':
    MedicalApp().run()
