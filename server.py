from flask import Flask, jsonify, request, send_from_directory, session
from flask_cors import CORS
import json
import os
from datetime import datetime
import hashlib
import uuid
from werkzeug.utils import secure_filename
from PIL import Image
import io

app = Flask(__name__, static_folder='public')
# Исправленный CORS - убрал слеш в конце
CORS(app, supports_credentials=True, origins=[
    'http://localhost:5000',
    'https://flask-student-system-ag1l.onrender.com'
])
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-this')
app.config['UPLOAD_FOLDER'] = 'public/images/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Создаем папки если их нет
os.makedirs('data', exist_ok=True)
os.makedirs('public/images/uploads', exist_ok=True)

# Пути к файлам данных (для режима JSON)
STUDENTS_FILE = os.path.join('data', 'students.json')
USERS_FILE = os.path.join('data', 'users.json')

# Флаг для определения режима работы
USE_POSTGRESQL = os.environ.get('DATABASE_URL') is not None

print(f"🔧 Режим работы: {'PostgreSQL' if USE_POSTGRESQL else 'JSON'}")


# ========== ОБЩИЕ ФУНКЦИИ ДЛЯ ВСЕХ РЕЖИМОВ ==========

def load_data(filename, default_data=None):
    """Загрузка данных из файла (для JSON режима)"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default_data if default_data is not None else []
    except Exception as e:
        print(f"❌ Ошибка загрузки {filename}: {e}")
        # Если файл поврежден, создаем заново
        if os.path.exists(filename):
            backup_file = f"{filename}.backup"
            os.rename(filename, backup_file)
            print(f"⚠️ Файл {filename} поврежден, создан бэкап: {backup_file}")
        return default_data if default_data is not None else []


def save_data(filename, data):
    """Сохранение данных в файл (для JSON режима)"""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения {filename}: {e}")
        return False


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


if USE_POSTGRESQL:
    # Импортируем PostgreSQL только если есть DATABASE_URL
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import urllib.parse

    DATABASE_URL = os.environ.get('DATABASE_URL')


    def get_db_connection():
        """Создает соединение с PostgreSQL"""
        try:
            parsed_url = urllib.parse.urlparse(DATABASE_URL)
            conn = psycopg2.connect(
                database=parsed_url.path[1:],
                user=parsed_url.username,
                password=parsed_url.password,
                host=parsed_url.hostname,
                port=parsed_url.port,
                sslmode='require'
            )
            return conn
        except Exception as e:
            print(f"❌ Ошибка подключения к PostgreSQL: {e}")
            raise


    def init_postgresql():
        """Инициализация PostgreSQL"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Создаем таблицы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(20) DEFAULT 'student',
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS students (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    course INTEGER NOT NULL,
                    status VARCHAR(20) DEFAULT 'studying',
                    description TEXT,
                    full_info TEXT,
                    institution VARCHAR(255),
                    skills JSONB DEFAULT '[]',
                    links JSONB DEFAULT '{}',
                    photo VARCHAR(255) DEFAULT '/images/default.jpg',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER
                )
            ''')

            conn.commit()
            print("✅ Таблицы созданы/проверены")

            # Проверяем есть ли данные
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]

            if user_count == 0:
                # Добавляем тестовых пользователей
                admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
                student_hash = hashlib.sha256("student123".encode()).hexdigest()

                cursor.execute('''
                    INSERT INTO users (username, password, role, email)
                    VALUES (%s, %s, %s, %s)
                ''', ('admin', admin_hash, 'admin', 'admin@college.ru'))

                cursor.execute('''
                    INSERT INTO users (username, password, role, email)
                    VALUES (%s, %s, %s, %s)
                ''', ('student1', student_hash, 'student', 'student1@college.ru'))

                # Добавляем тестовых студентов
                cursor.execute('''
                    INSERT INTO students (name, course, status, description, full_info, institution, skills, links)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ''', (
                    'Иван Иванов', 1, 'studying',
                    'Backend-разработчик, увлекается Python и SQL',
                    'Студент 1 курса, изучает Python и базы данных.',
                    'Колледж информационных технологий №1',
                    json.dumps(['Python', 'SQL', 'PostgreSQL']),
                    json.dumps({"github": "https://github.com/ivanov"})
                ))

                conn.commit()
                print("✅ PostgreSQL: добавлены тестовые данные")

            cursor.close()
            conn.close()
            print("✅ PostgreSQL готов к работе")

        except Exception as e:
            print(f"❌ Ошибка инициализации PostgreSQL: {e}")
            raise  # Пробрасываем ошибку дальше

else:
    print("ℹ️ Используется режим JSON (локальная разработка)")


def init_data():
    """Инициализация данных"""
    print("\n🔧 ИНИЦИАЛИЗАЦИЯ ДАННЫХ")

    if USE_POSTGRESQL:
        try:
            init_postgresql()
        except Exception as e:
            print(f"⚠️ Не удалось инициализировать PostgreSQL: {e}")
            print("⚠️ Попытка продолжить работу в JSON режиме...")
    else:
        # Инициализация JSON файлов
        if not os.path.exists(USERS_FILE):
            admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
            student_hash = hashlib.sha256("student123".encode()).hexdigest()

            initial_users = [
                {
                    "id": 1,
                    "username": "admin",
                    "password": admin_hash,
                    "role": "admin",
                    "email": "admin@college.ru",
                    "createdAt": datetime.now().isoformat()
                },
                {
                    "id": 2,
                    "username": "student1",
                    "password": student_hash,
                    "role": "student",
                    "email": "student1@college.ru",
                    "createdAt": datetime.now().isoformat()
                }
            ]
            save_data(USERS_FILE, initial_users)
            print(f"✅ JSON: создан файл пользователей")

        if not os.path.exists(STUDENTS_FILE):
            initial_students = [
                {
                    "id": 1,
                    "name": "Иван Иванов",
                    "course": 1,
                    "status": "studying",
                    "description": "Backend-разработчик, увлекается Python и SQL",
                    "fullInfo": "Студент 1 курса, изучает Python и базы данных.",
                    "institution": "Колледж информационных технологий №1",
                    "skills": ["Python", "SQL", "PostgreSQL"],
                    "links": {"github": "https://github.com/ivanov"},
                    "photo": "/images/default.jpg",
                    "createdAt": datetime.now().isoformat(),
                    "updatedAt": datetime.now().isoformat(),
                    "userId": 1
                }
            ]
            save_data(STUDENTS_FILE, initial_students)
            print(f"✅ JSON: создан файл студентов")


# ========== API МАРШРУТЫ ==========

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/admin')
def admin():
    return send_from_directory('public', 'admin.html')


@app.route('/add-student')
def add_student_page():
    """Страница добавления студента"""
    return send_from_directory('public', 'add-student.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('public', path)


# ========== STUDENTS API ==========

@app.route('/api/students', methods=['GET'])
def get_students():
    """Получить всех студентов"""
    try:
        if USE_POSTGRESQL:
            try:
                # PostgreSQL версия
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                cursor.execute('SELECT * FROM students ORDER BY id')
                students = cursor.fetchall()

                result = []
                for student in students:
                    result.append({
                        "id": student['id'],
                        "name": student['name'],
                        "course": student['course'],
                        "status": student['status'],
                        "description": student['description'],
                        "fullInfo": student['full_info'],
                        "institution": student['institution'],
                        "skills": student['skills'] if student['skills'] else [],
                        "links": student['links'] if student['links'] else {},
                        "photo": student['photo'],
                        "createdAt": student['created_at'].isoformat(),
                        "updatedAt": student['updated_at'].isoformat(),
                        "userId": student['user_id']
                    })

                cursor.close()
                conn.close()
            except Exception as db_error:
                print(f"❌ Ошибка БД при получении студентов: {db_error}")
                return jsonify({"error": "Ошибка базы данных"}), 500

        else:
            # JSON версия
            students = load_data(STUDENTS_FILE, [])
            result = students

        # Сортировка для авторизованных пользователей
        if 'user_id' in session:
            current_user_id = session['user_id']
            result.sort(key=lambda x: (0 if x.get('userId') == current_user_id else 1, x['id']))

        return jsonify(result)

    except Exception as e:
        print(f"❌ Ошибка получения студентов: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Получить студента по ID"""
    try:
        if USE_POSTGRESQL:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute('SELECT * FROM students WHERE id = %s', (student_id,))
            student = cursor.fetchone()

            cursor.close()
            conn.close()

            if not student:
                return jsonify({"error": "Студент не найден"}), 404

            result = {
                "id": student['id'],
                "name": student['name'],
                "course": student['course'],
                "status": student['status'],
                "description": student['description'],
                "fullInfo": student['full_info'],
                "institution": student['institution'],
                "skills": student['skills'] if student['skills'] else [],
                "links": student['links'] if student['links'] else {},
                "photo": student['photo'],
                "createdAt": student['created_at'].isoformat(),
                "updatedAt": student['updated_at'].isoformat(),
                "userId": student['user_id']
            }

        else:
            students = load_data(STUDENTS_FILE, [])
            student = next((s for s in students if s.get('id') == student_id), None)

            if not student:
                return jsonify({"error": "Студент не найден"}), 404

            result = student

        return jsonify(result)

    except Exception as e:
        print(f"❌ Ошибка получения студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students', methods=['POST'])
def create_student():
    """Создать нового студента"""
    try:
        # Проверяем авторизацию
        if 'user_id' not in session:
            return jsonify({"error": "Требуется авторизация"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"error": "Нет данных"}), 400

        # Обязательные поля
        required_fields = ['name', 'course', 'description', 'institution']
        for field in required_fields:
            if field not in data or not str(data.get(field, '')).strip():
                return jsonify({"error": f"Поле '{field}' обязательно"}), 400

        current_user_id = session['user_id']
        current_role = session.get('role', 'student')

        if USE_POSTGRESQL:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute('''
                INSERT INTO students (name, course, status, description, full_info, institution, 
                                    skills, links, photo, user_id, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING *
            ''', (
                data['name'].strip(),
                int(data.get('course', 1)),
                data.get('status', 'studying'),
                data['description'].strip(),
                data.get('fullInfo', data['description'].strip()),
                data['institution'].strip(),
                json.dumps(data.get('skills', [])),
                json.dumps(data.get('links', {})),
                data.get('photo', '/images/default.jpg'),
                current_user_id if current_role != 'admin' else None
            ))

            new_student = cursor.fetchone()
            conn.commit()

            result = {
                "id": new_student['id'],
                "name": new_student['name'],
                "course": new_student['course'],
                "status": new_student['status'],
                "description": new_student['description'],
                "fullInfo": new_student['full_info'],
                "institution": new_student['institution'],
                "skills": new_student['skills'] if new_student['skills'] else [],
                "links": new_student['links'] if new_student['links'] else {},
                "photo": new_student['photo'],
                "createdAt": new_student['created_at'].isoformat(),
                "updatedAt": new_student['updated_at'].isoformat(),
                "userId": new_student['user_id']
            }

            cursor.close()
            conn.close()

        else:
            students = load_data(STUDENTS_FILE, [])
            new_id = max([s.get('id', 0) for s in students], default=0) + 1

            new_student = {
                "id": new_id,
                "name": data['name'].strip(),
                "course": int(data.get('course', 1)),
                "status": data.get('status', 'studying'),
                "description": data['description'].strip(),
                "fullInfo": data.get('fullInfo', data['description'].strip()),
                "institution": data['institution'].strip(),
                "skills": data.get('skills', []),
                "links": data.get('links', {}),
                "photo": data.get('photo', '/images/default.jpg'),
                "createdAt": datetime.now().isoformat(),
                "updatedAt": datetime.now().isoformat(),
                "userId": current_user_id if current_role != 'admin' else None
            }

            students.append(new_student)
            save_data(STUDENTS_FILE, students)
            result = new_student

        print(f"✅ Создан студент: {result['name']}")
        return jsonify(result), 201

    except Exception as e:
        print(f"❌ Ошибка создания студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    """Обновить данные студента"""
    try:
        if 'user_id' not in session:
            return jsonify({"error": "Требуется авторизация"}), 401

        data = request.get_json()
        if not data:
            return jsonify({"error": "Нет данных"}), 400

        # Проверяем права (только свой профиль или админ)
        if session.get('role') != 'admin':
            # Получаем студента чтобы проверить user_id
            if USE_POSTGRESQL:
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('SELECT user_id FROM students WHERE id = %s', (student_id,))
                student = cursor.fetchone()
                cursor.close()
                conn.close()

                if not student or student['user_id'] != session['user_id']:
                    return jsonify({"error": "Недостаточно прав"}), 403
            else:
                students = load_data(STUDENTS_FILE, [])
                student = next((s for s in students if s.get('id') == student_id), None)
                if not student or student.get('userId') != session['user_id']:
                    return jsonify({"error": "Недостаточно прав"}), 403

        if USE_POSTGRESQL:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute('''
                UPDATE students 
                SET name = %s, course = %s, status = %s, description = %s, 
                    full_info = %s, institution = %s, skills = %s, links = %s, 
                    photo = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING *
            ''', (
                data.get('name', '').strip(),
                int(data.get('course', 1)),
                data.get('status', 'studying'),
                data.get('description', '').strip(),
                data.get('fullInfo', '').strip(),
                data.get('institution', '').strip(),
                json.dumps(data.get('skills', [])),
                json.dumps(data.get('links', {})),
                data.get('photo', '/images/default.jpg'),
                student_id
            ))

            updated_student = cursor.fetchone()
            conn.commit()

            if not updated_student:
                cursor.close()
                conn.close()
                return jsonify({"error": "Студент не найден"}), 404

            result = {
                "id": updated_student['id'],
                "name": updated_student['name'],
                "course": updated_student['course'],
                "status": updated_student['status'],
                "description": updated_student['description'],
                "fullInfo": updated_student['full_info'],
                "institution": updated_student['institution'],
                "skills": updated_student['skills'] if updated_student['skills'] else [],
                "links": updated_student['links'] if updated_student['links'] else {},
                "photo": updated_student['photo'],
                "createdAt": updated_student['created_at'].isoformat(),
                "updatedAt": updated_student['updated_at'].isoformat(),
                "userId": updated_student['user_id']
            }

            cursor.close()
            conn.close()

        else:
            students = load_data(STUDENTS_FILE, [])
            student_index = next((i for i, s in enumerate(students) if s.get('id') == student_id), None)

            if student_index is None:
                return jsonify({"error": "Студент не найден"}), 404

            students[student_index].update({
                "name": data.get('name', students[student_index]['name']).strip(),
                "course": int(data.get('course', students[student_index]['course'])),
                "status": data.get('status', students[student_index]['status']),
                "description": data.get('description', students[student_index]['description']).strip(),
                "fullInfo": data.get('fullInfo', students[student_index].get('fullInfo', '')).strip(),
                "institution": data.get('institution', students[student_index]['institution']).strip(),
                "skills": data.get('skills', students[student_index].get('skills', [])),
                "links": data.get('links', students[student_index].get('links', {})),
                "photo": data.get('photo', students[student_index].get('photo', '/images/default.jpg')),
                "updatedAt": datetime.now().isoformat()
            })

            save_data(STUDENTS_FILE, students)
            result = students[student_index]

        print(f"✅ Обновлен студент: {result['name']}")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Ошибка обновления студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Удалить студента"""
    try:
        if 'user_id' not in session:
            return jsonify({"error": "Требуется авторизация"}), 401

        # Проверяем права (только свой профиль или админ)
        if session.get('role') != 'admin':
            if USE_POSTGRESQL:
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)
                cursor.execute('SELECT user_id FROM students WHERE id = %s', (student_id,))
                student = cursor.fetchone()
                cursor.close()
                conn.close()

                if not student or student['user_id'] != session['user_id']:
                    return jsonify({"error": "Недостаточно прав"}), 403
            else:
                students = load_data(STUDENTS_FILE, [])
                student = next((s for s in students if s.get('id') == student_id), None)
                if not student or student.get('userId') != session['user_id']:
                    return jsonify({"error": "Недостаточно прав"}), 403

        if USE_POSTGRESQL:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM students WHERE id = %s', (student_id,))
            deleted_count = cursor.rowcount
            conn.commit()

            cursor.close()
            conn.close()

            if deleted_count == 0:
                return jsonify({"error": "Студент не найден"}), 404

        else:
            students = load_data(STUDENTS_FILE, [])
            initial_length = len(students)
            students = [s for s in students if s.get('id') != student_id]

            if len(students) == initial_length:
                return jsonify({"error": "Студент не найден"}), 404

            save_data(STUDENTS_FILE, students)

        print(f"✅ Удален студент ID: {student_id}")
        return jsonify({"message": "Студент успешно удален"})

    except Exception as e:
        print(f"❌ Ошибка удаления студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/statistics', methods=['GET'])
def get_statistics():
    """Получить статистику студентов"""
    try:
        if USE_POSTGRESQL:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) as total FROM students")
            total = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) as studying FROM students 
                WHERE status = 'studying'
            """)
            studying = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) as graduated FROM students 
                WHERE status = 'graduated'
            """)
            graduated = cursor.fetchone()[0]

            cursor.execute("""
                SELECT course, COUNT(*) as count 
                FROM students 
                GROUP BY course 
                ORDER BY course
            """)
            course_stats = {row[0]: row[1] for row in cursor.fetchall()}

            # Получаем уникальные учебные заведения
            cursor.execute("""
                SELECT DISTINCT institution 
                FROM students 
                WHERE institution IS NOT NULL AND institution != ''
                ORDER BY institution
            """)
            institutions = [row[0] for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            return jsonify({
                "total": total,
                "studying": studying,
                "graduated": graduated,
                "courseStats": course_stats,
                "institutions": institutions
            })

        else:
            students = load_data(STUDENTS_FILE, [])

            total = len(students)
            studying = sum(1 for s in students if s.get('status') == 'studying')
            graduated = sum(1 for s in students if s.get('status') == 'graduated')

            course_stats = {}
            for student in students:
                course = student.get('course', 1)
                course_stats[course] = course_stats.get(course, 0) + 1

            institutions = list(set(
                s.get('institution', '') for s in students
                if s.get('institution')
            ))

            return jsonify({
                "total": total,
                "studying": studying,
                "graduated": graduated,
                "courseStats": course_stats,
                "institutions": institutions
            })

    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return jsonify({"error": str(e)}), 500


# ========== AUTH API ==========

@app.route('/api/login', methods=['POST'])
def login():
    """Вход в систему"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Нет данных"}), 400

        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({"error": "Логин и пароль обязательны"}), 400

        if USE_POSTGRESQL:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if user['password'] == password_hash:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']

                    user_data = {
                        "id": user['id'],
                        "username": user['username'],
                        "role": user['role'],
                        "email": user.get('email')
                    }

                    print(f"✅ Успешный вход: {username}")
                    return jsonify(user_data)
                else:
                    return jsonify({"error": "Неверный логин или пароль"}), 401
            else:
                return jsonify({"error": "Неверный логин или пароль"}), 401

        else:
            users = load_data(USERS_FILE, [])
            user = next((u for u in users if u.get('username') == username), None)

            if user:
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                if user.get('password') == password_hash:
                    session['user_id'] = user['id']
                    session['username'] = user['username']
                    session['role'] = user['role']

                    user_data = {
                        "id": user['id'],
                        "username": user['username'],
                        "role": user['role'],
                        "email": user.get('email')
                    }

                    print(f"✅ Успешный вход: {username}")
                    return jsonify(user_data)
                else:
                    return jsonify({"error": "Неверный логин или пароль"}), 401
            else:
                return jsonify({"error": "Неверный логин или пароль"}), 401

    except Exception as e:
        print(f"❌ Ошибка входа: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/current-user', methods=['GET'])
def get_current_user():
    """Получить текущего пользователя"""
    if 'user_id' in session:
        if USE_POSTGRESQL:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(cursor_factory=RealDictCursor)

                # Сначала проверяем существование таблицы
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    );
                """)

                table_exists = cursor.fetchone()['exists']

                if not table_exists:
                    print("⚠️ Таблица 'users' еще не создана")
                    # Возвращаем минимальные данные из сессии
                    return jsonify({
                        "id": session['user_id'],
                        "username": session.get('username', 'unknown'),
                        "role": session.get('role', 'student')
                    })

                cursor.execute('SELECT * FROM users WHERE id = %s', (session['user_id'],))
                user = cursor.fetchone()

                cursor.close()
                conn.close()

                if user:
                    return jsonify({
                        "id": user['id'],
                        "username": user['username'],
                        "role": user['role'],
                        "email": user.get('email')
                    })
                else:
                    # Пользователь удален из БД, но сессия еще жива
                    session.clear()
                    return jsonify({"error": "Сессия устарела"}), 401

            except Exception as e:
                print(f"❌ Ошибка получения пользователя из PostgreSQL: {e}")
                # Если PostgreSQL падает, пытаемся из JSON
                pass

        # Пробуем JSON или fallback
        users = load_data(USERS_FILE, [])
        user = next((u for u in users if u.get('id') == session['user_id']), None)

        if user:
            return jsonify({
                "id": user['id'],
                "username": user['username'],
                "role": user['role'],
                "email": user.get('email')
            })

    return jsonify({"error": "Не авторизован"}), 401


# ========== ДОПОЛНИТЕЛЬНЫЕ ЭНДПОИНТЫ ==========

@app.route('/api/logout', methods=['POST'])
def logout():
    """Выход из системы"""
    session.clear()
    return jsonify({"message": "Успешный выход"})


@app.route('/api/register', methods=['POST'])
def register():
    """Регистрация нового пользователя"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Нет данных"}), 400

        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        role = data.get('role', 'student')

        if not username or not password:
            return jsonify({"error": "Логин и пароль обязательны"}), 400

        if len(username) < 3:
            return jsonify({"error": "Логин должен содержать минимум 3 символа"}), 400

        if len(password) < 6:
            return jsonify({"error": "Пароль должен содержать минимум 6 символов"}), 400

        if USE_POSTGRESQL:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Проверяем, существует ли пользователь
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
            if cursor.fetchone()[0] > 0:
                cursor.close()
                conn.close()
                return jsonify({"error": "Пользователь с таким логином уже существует"}), 400

            # Хэшируем пароль
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # Создаем пользователя
            cursor.execute('''
                INSERT INTO users (username, password, role, email)
                VALUES (%s, %s, %s, %s)
                RETURNING id, username, role, email
            ''', (username, password_hash, role, email))

            new_user = cursor.fetchone()
            conn.commit()

            cursor.close()
            conn.close()

            print(f"✅ Зарегистрирован пользователь: {username}")
            return jsonify({
                "id": new_user[0],
                "username": new_user[1],
                "role": new_user[2],
                "email": new_user[3]
            }), 201

        else:
            users = load_data(USERS_FILE, [])

            # Проверяем, существует ли пользователь
            if any(u.get('username') == username for u in users):
                return jsonify({"error": "Пользователь с таким логином уже существует"}), 400

            # Генерируем новый ID
            new_id = max([u.get('id', 0) for u in users], default=0) + 1

            # Хэшируем пароль
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            new_user = {
                "id": new_id,
                "username": username,
                "password": password_hash,
                "role": role,
                "email": email,
                "createdAt": datetime.now().isoformat()
            }

            users.append(new_user)
            save_data(USERS_FILE, users)

            print(f"✅ Зарегистрирован пользователь: {username}")
            return jsonify({
                "id": new_user['id'],
                "username": new_user['username'],
                "role": new_user['role'],
                "email": new_user['email']
            }), 201

    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    try:
        if USE_POSTGRESQL:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()

                # Проверяем существование таблиц
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'users'
                    ) as users_exists,
                    EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'students'
                    ) as students_exists;
                """)

                exists = cursor.fetchone()
                users_exists = exists[0]
                students_exists = exists[1]

                if users_exists and students_exists:
                    cursor.execute("SELECT COUNT(*) FROM users")
                    user_count = cursor.fetchone()[0]
                    cursor.execute("SELECT COUNT(*) FROM students")
                    student_count = cursor.fetchone()[0]
                else:
                    user_count = 0
                    student_count = 0

                cursor.close()
                conn.close()

                return jsonify({
                    "status": "ok",
                    "mode": "postgresql",
                    "tables": {
                        "users": users_exists,
                        "students": students_exists
                    },
                    "timestamp": datetime.now().isoformat(),
                    "data_counts": {
                        "users": user_count,
                        "students": student_count
                    }
                })
            except Exception as db_error:
                return jsonify({
                    "status": "error",
                    "mode": "postgresql",
                    "error": str(db_error),
                    "timestamp": datetime.now().isoformat()
                }), 500
        else:
            users = load_data(USERS_FILE, [])
            students = load_data(STUDENTS_FILE, [])

            return jsonify({
                "status": "ok",
                "mode": "json",
                "timestamp": datetime.now().isoformat(),
                "data_counts": {
                    "users": len(users),
                    "students": len(students)
                }
            })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500


@app.route('/api/check-card', methods=['GET'])
def check_user_card():
    """Проверить, есть ли у пользователя карточка студента"""
    try:
        if 'user_id' not in session:
            return jsonify({"error": "Требуется авторизация"}), 401

        user_id = session['user_id']

        if USE_POSTGRESQL:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute('SELECT id, name FROM students WHERE user_id = %s', (user_id,))
            student = cursor.fetchone()

            cursor.close()
            conn.close()

            if student:
                return jsonify({
                    "hasCard": True,
                    "studentId": student['id'],
                    "studentName": student['name']
                })
            else:
                return jsonify({"hasCard": False})
        else:
            students = load_data(STUDENTS_FILE, [])
            student = next((s for s in students if s.get('userId') == user_id), None)

            if student:
                return jsonify({
                    "hasCard": True,
                    "studentId": student.get('id'),
                    "studentName": student.get('name')
                })
            else:
                return jsonify({"hasCard": False})

    except Exception as e:
        print(f"❌ Ошибка проверки карточки: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/init-db', methods=['POST'])
def init_database():
    """Ручная инициализация базы данных"""
    try:
        if not USE_POSTGRESQL:
            return jsonify({"error": "Только для PostgreSQL режима"}), 400

        init_postgresql()

        return jsonify({
            "success": True,
            "message": "База данных инициализирована"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/debug', methods=['GET'])
def debug_info():
    """Информация для отладки"""
    info = {
        "mode": "PostgreSQL" if USE_POSTGRESQL else "JSON",
        "database_url_exists": bool(os.environ.get('DATABASE_URL')),
        "session_user_id": session.get('user_id'),
        "session_username": session.get('username'),
        "session_role": session.get('role'),
        "current_time": datetime.now().isoformat(),
        "render": True
    }

    if USE_POSTGRESQL:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Проверяем таблицы
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = cursor.fetchall()
            info["tables_in_db"] = [table[0] for table in tables]

            if 'users' in info["tables_in_db"]:
                cursor.execute("SELECT COUNT(*) FROM users")
                info["user_count"] = cursor.fetchone()[0]

            if 'students' in info["tables_in_db"]:
                cursor.execute("SELECT COUNT(*) FROM students")
                info["student_count"] = cursor.fetchone()[0]

            cursor.close()
            conn.close()
        except Exception as e:
            info["db_error"] = str(e)

    return jsonify(info)


# ========== ФОТО ЗАГРУЗКА ==========

@app.route('/api/upload-photo', methods=['POST'])
def upload_photo():
    """Загрузить фото для студента"""
    try:
        if 'photo' not in request.files:
            return jsonify({"error": "Нет файла фото"}), 400

        file = request.files['photo']

        if file.filename == '':
            return jsonify({"error": "Не выбран файл"}), 400

        if file and allowed_file(file.filename):
            # Создаем уникальное имя файла
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

            # Сохраняем файл
            file.save(filepath)

            # Опционально: изменяем размер фото
            try:
                img = Image.open(filepath)
                # Максимальный размер 800x800
                img.thumbnail((800, 800))
                img.save(filepath, optimize=True, quality=85)
            except Exception as img_error:
                print(f"⚠️ Не удалось обработать изображение: {img_error}")

            photo_url = f"/images/uploads/{unique_filename}"
            return jsonify({"photoUrl": photo_url})
        else:
            return jsonify({"error": "Неподдерживаемый формат файла"}), 400

    except Exception as e:
        print(f"❌ Ошибка загрузки фото: {e}")
        return jsonify({"error": str(e)}), 500


# ========== ЗАПУСК ==========

if __name__ == '__main__':
    # УБЕДИТЕЛЬНАЯ ИНИЦИАЛИЗАЦИЯ ПЕРЕД ЗАПУСКОМ
    print("\n" + "=" * 60)
    print("🚀 ЗАПУСК СЕРВЕРА НА RENDER")
    print("=" * 60)

    # Принудительно инициализируем данные
    init_data()

    print("\n" + "=" * 60)
    print("✅ СЕРВЕР ГОТОВ К РАБОТЕ!")
    print("=" * 60)
    print(f"📊 Режим работы: {'PostgreSQL' if USE_POSTGRESQL else 'JSON'}")

    if USE_POSTGRESQL:
        print("📍 Для проверки БД откройте: /api/debug")
        print("📍 Для принудительной инициализации: POST /api/init-db")

    print("📍 Основная страница: /")
    print("📍 Добавить студента: /add-student")
    print("📍 Админ-панель:      /admin")
    print("\n👤 ТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ:")
    print("   Админ:    логин: admin    пароль: admin123")
    print("   Студент:  логин: student1 пароль: student123")
    print("=" * 60 + "\n")

    # На Render используем порт из переменной окружения
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
