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
import psycopg2
from psycopg2.extras import RealDictCursor
import urllib.parse

app = Flask(__name__, static_folder='public')
CORS(app, supports_credentials=True, origins=['http://localhost:5000', 'https://your-app.onrender.com'])
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['UPLOAD_FOLDER'] = 'public/images/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Создаем папки если их нет
os.makedirs('data', exist_ok=True)
os.makedirs('public/images/uploads', exist_ok=True)

# URL для Render PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')


def get_db_connection():
    """Создает соединение с базой данных"""
    if DATABASE_URL:
        # Parse the database URL for Render
        parsed_url = urllib.parse.urlparse(DATABASE_URL)
        conn = psycopg2.connect(
            database=parsed_url.path[1:],
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            port=parsed_url.port,
            sslmode='require'
        )
    else:
        # Local SQLite fallback
        conn = psycopg2.connect(
            database='students_db',
            user='postgres',
            password='password',
            host='localhost',
            port='5432'
        )
    return conn


def init_database():
    """Инициализация базы данных"""
    print("\n🔧 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Таблица пользователей
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

        # Таблица студентов
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
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL
            )
        ''')

        conn.commit()

        # Проверяем, есть ли пользователи
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count == 0:
            # Создаем начальных пользователей
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

            print("✅ Добавлены тестовые пользователи")

            # Создаем начальных студентов
            cursor.execute('''
                INSERT INTO students (name, course, status, description, full_info, institution, skills, links, photo, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                'Иван Иванов', 1, 'studying',
                'Backend-разработчик, увлекается Python и SQL',
                'Студент 1 курса, изучает Python и базы данных.',
                'Колледж информационных технологий №1',
                json.dumps(['Python', 'SQL', 'PostgreSQL']),
                json.dumps({"github": "https://github.com/ivanov", "portfolio": "https://ivanov-portfolio.ru"}),
                '/images/default.jpg',
                1
            ))

            cursor.execute('''
                INSERT INTO students (name, course, status, description, full_info, institution, skills, links, photo, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                'Мария Петрова', 3, 'studying',
                'Frontend-разработчик, специалист по React',
                'Студентка 3 курса, создала несколько проектов на React.',
                'Колледж информационных технологий №1',
                json.dumps(['JavaScript', 'React', 'HTML', 'CSS']),
                json.dumps({"github": "https://github.com/maria", "portfolio": "https://maria-dev.ru"}),
                '/images/default.jpg',
                2
            ))

            cursor.execute('''
                INSERT INTO students (name, course, status, description, full_info, institution, skills, links, photo, user_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                'Алексей Сидоров', 2, 'studying',
                'Data Science, интересуется машинным обучением',
                'Студент 2 курса, изучает Python, математику и ML.',
                'Технический колледж',
                json.dumps(['Python', 'Pandas', 'NumPy', 'Scikit-learn']),
                json.dumps({"github": "https://github.com/alexey", "portfolio": "https://alexey-ds.ru"}),
                '/images/default.jpg',
                None
            ))

            print("✅ Добавлены тестовые студенты")

        conn.commit()
        cursor.close()
        conn.close()

        print("✅ База данных готова к работе")

    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# ========== API МАРШРУТЫ ==========

@app.route('/')
def index():
    return send_from_directory('public', 'index.html')


@app.route('/admin')
def admin():
    return send_from_directory('public', 'admin.html')


@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('public', path)


@app.route('/add-student')
def add_student_page():
    return send_from_directory('public', 'add-student.html')


@app.route('/api/upload-photo', methods=['POST'])
def upload_photo():
    """Загрузка фотографии"""
    try:
        print("📤 Запрос на загрузку фото получен")

        if 'photo' not in request.files:
            print("❌ Файл не найден в запросе")
            return jsonify({"error": "Файл не найден"}), 400

        file = request.files['photo']
        student_id = request.form.get('studentId')

        print(f"📁 Получен файл: {file.filename}, studentId: {student_id}")

        if file.filename == '':
            return jsonify({"error": "Файл не выбран"}), 400

        if file and allowed_file(file.filename):
            # Генерируем уникальное имя файла
            filename = secure_filename(file.filename)
            ext = filename.rsplit('.', 1)[1].lower()

            if student_id and student_id != 'null' and student_id != 'undefined':
                new_filename = f"student_{student_id}.{ext}"
            else:
                new_filename = f"temp_{uuid.uuid4().hex}.{ext}"

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            file.save(file_path)

            # Оптимизируем изображение
            try:
                with Image.open(file_path) as img:
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    img.save(file_path, 'JPEG', quality=85, optimize=True)
            except Exception as e:
                print(f"⚠️ Не удалось оптимизировать изображение: {e}")

            photo_url = f"/images/uploads/{new_filename}"

            print(f"✅ Фотография загружена: {file_path}")
            return jsonify({
                "success": True,
                "photoUrl": photo_url,
                "filename": new_filename
            })
        else:
            return jsonify({"error": "Неподдерживаемый формат файла"}), 400

    except Exception as e:
        print(f"❌ Ошибка загрузки фотографии: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students', methods=['GET'])
def get_students():
    """Получить всех студентов"""
    try:
        print("📊 Получен запрос на список студентов")

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute('''
            SELECT s.*, 
                   u.username as user_username,
                   u.email as user_email
            FROM students s
            LEFT JOIN users u ON s.user_id = u.id
            ORDER BY s.id
        ''')

        students = cursor.fetchall()

        # Преобразуем студентов в формат JSON
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

        print(f"✅ Загружено {len(result)} студентов из базы данных")

        # Если пользователь авторизован, сортируем его карточку первой
        if 'user_id' in session:
            current_user_id = session['user_id']
            result.sort(key=lambda x: (0 if x.get('userId') == current_user_id else 1, x['id']))

        return jsonify(result)

    except Exception as e:
        print(f"❌ Ошибка получения студентов: {e}")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500


@app.route('/api/students/search', methods=['GET'])
def search_students():
    """Поиск студентов"""
    try:
        search = request.args.get('search', '').lower()
        course = request.args.get('course', '')
        status = request.args.get('status', '')
        institution = request.args.get('institution', '').lower()

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Базовый запрос
        query = '''
            SELECT s.*, 
                   u.username as user_username,
                   u.email as user_email
            FROM students s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE 1=1
        '''
        params = []

        # Добавляем условия поиска
        if search:
            if search.isdigit():
                query += " AND s.id = %s"
                params.append(int(search))
            else:
                query += " AND (LOWER(s.name) LIKE %s OR LOWER(s.description) LIKE %s OR LOWER(s.institution) LIKE %s)"
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern, search_pattern])

        if course and course != 'all':
            query += " AND s.course = %s"
            params.append(int(course))

        if status and status != 'all':
            query += " AND s.status = %s"
            params.append(status)

        if institution:
            query += " AND LOWER(s.institution) LIKE %s"
            params.append(f"%{institution}%")

        query += " ORDER BY s.id"

        cursor.execute(query, params)
        students = cursor.fetchall()

        # Преобразуем результат
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

        print(f"🔍 Результаты поиска: найдено {len(result)} студентов")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Ошибка поиска студентов: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Получить студента по ID"""
    try:
        print(f"🔍 Получен запрос на студента ID: {student_id}")

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute('''
            SELECT s.*, 
                   u.username as user_username,
                   u.email as user_email
            FROM students s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.id = %s
        ''', (student_id,))

        student = cursor.fetchone()

        cursor.close()
        conn.close()

        if not student:
            print(f"❌ Студент ID {student_id} не найден")
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

        print(f"✅ Найден студент: {result['name']}")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Ошибка получения студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/statistics', methods=['GET'])
def get_statistics():
    """Получить статистику студентов"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Общее количество студентов
        cursor.execute("SELECT COUNT(*) FROM students")
        total = cursor.fetchone()[0]

        # Статистика по курсам
        cursor.execute('''
            SELECT course, COUNT(*) 
            FROM students 
            GROUP BY course 
            ORDER BY course
        ''')
        by_course = {"1": 0, "2": 0, "3": 0, "4": 0}
        for row in cursor.fetchall():
            course = str(row[0])
            if course in by_course:
                by_course[course] = row[1]

        # Статистика по статусам
        cursor.execute('''
            SELECT status, COUNT(*) 
            FROM students 
            GROUP BY status
        ''')
        by_status = {
            "studying": 0,
            "graduated": 0,
            "expelled": 0,
            "academic_leave": 0
        }
        for row in cursor.fetchall():
            status = row[0]
            if status in by_status:
                by_status[status] = row[1]

        # Список образовательных учреждений
        cursor.execute('''
            SELECT DISTINCT institution 
            FROM students 
            WHERE institution IS NOT NULL AND institution != ''
            ORDER BY institution
        ''')
        institutions = [row[0] for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        return jsonify({
            "total": total,
            "byCourse": by_course,
            "byStatus": by_status,
            "institutions": institutions
        })

    except Exception as e:
        print(f"❌ Ошибка получения статистики: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students', methods=['POST'])
def create_student():
    """Создать нового студента"""
    try:
        print("➕ Получен запрос на создание студента")

        # Проверяем авторизацию
        if 'user_id' not in session:
            return jsonify({"error": "Требуется авторизация"}), 401

        current_user_id = session['user_id']
        current_role = session.get('role', 'student')

        # Проверяем, может ли пользователь создавать карточки
        if current_role != 'admin':
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM students WHERE user_id = %s", (current_user_id,))
            existing_count = cursor.fetchone()[0]
            cursor.close()
            conn.close()

            if existing_count > 0:
                return jsonify({
                    "error": "У вас уже есть карточка. Вы можете редактировать только свою карточку."
                }), 400

        # Получаем данные
        data = request.get_json()
        if not data:
            return jsonify({"error": "Нет данных"}), 400

        # Проверяем обязательные поля
        required_fields = ['name', 'course', 'description', 'institution']
        for field in required_fields:
            if field not in data or not str(data.get(field, '')).strip():
                return jsonify({"error": f"Поле '{field}' обязательно"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Вставляем нового студента
        cursor.execute('''
            INSERT INTO students (
                name, course, status, description, full_info, institution, 
                skills, links, photo, user_id, created_at, updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            current_user_id if current_role != 'admin' else None,
            datetime.now(),
            datetime.now()
        ))

        new_student = cursor.fetchone()
        conn.commit()

        cursor.close()
        conn.close()

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

        print(f"✅ Добавлен студент: {result['name']} (ID: {result['id']})")
        return jsonify(result), 201

    except Exception as e:
        print(f"❌ Ошибка создания студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    """Обновить данные студента"""
    try:
        print(f"✏️ Получен запрос на обновление студента ID: {student_id}")

        # Проверяем авторизацию
        if 'user_id' not in session:
            return jsonify({"error": "Требуется авторизация"}), 401

        current_user_id = session['user_id']
        current_role = session.get('role', 'student')

        # Получаем данные
        data = request.get_json()
        if not data:
            return jsonify({"error": "Нет данных"}), 400

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Получаем текущего студента
        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return jsonify({"error": "Студент не найден"}), 404

        # Проверяем права на редактирование
        if current_role != 'admin':
            if student['user_id'] != current_user_id:
                cursor.close()
                conn.close()
                return jsonify({"error": "Вы можете редактировать только свою карточку"}), 403

        # Обновляем данные
        cursor.execute('''
            UPDATE students 
            SET 
                name = %s,
                course = %s,
                status = %s,
                description = %s,
                full_info = %s,
                institution = %s,
                skills = %s,
                links = %s,
                photo = %s,
                updated_at = %s
            WHERE id = %s
            RETURNING *
        ''', (
            data.get('name', student['name']).strip(),
            int(data.get('course', student['course'])),
            data.get('status', student['status']),
            data.get('description', student['description']).strip(),
            data.get('fullInfo', student['full_info']).strip(),
            data.get('institution', student['institution']).strip(),
            json.dumps(data.get('skills', student['skills'] if student['skills'] else [])),
            json.dumps(data.get('links', student['links'] if student['links'] else {})),
            data.get('photo', student['photo']),
            datetime.now(),
            student_id
        ))

        updated_student = cursor.fetchone()
        conn.commit()

        cursor.close()
        conn.close()

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

        print(f"✅ Обновлен студент: {result['name']} (ID: {student_id})")
        return jsonify(result)

    except Exception as e:
        print(f"❌ Ошибка обновления студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Удалить студента"""
    try:
        # Проверяем авторизацию
        if 'user_id' not in session:
            return jsonify({"error": "Требуется авторизация"}), 401

        current_user_id = session['user_id']
        current_role = session.get('role', 'student')

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Получаем студента
        cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            cursor.close()
            conn.close()
            return jsonify({"error": "Студент не найден"}), 404

        # Проверяем права на удаление
        if current_role != 'admin':
            if student['user_id'] != current_user_id:
                cursor.close()
                conn.close()
                return jsonify({"error": "Вы можете удалять только свою карточку"}), 403

        # Удаляем фотографию если она не дефолтная
        if student['photo'] and not student['photo'].endswith('default.jpg'):
            try:
                photo_path = os.path.join('public', student['photo'].lstrip('/'))
                if os.path.exists(photo_path):
                    os.remove(photo_path)
                    print(f"✅ Удалена фотография: {photo_path}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить фотографию: {e}")

        # Удаляем студента из базы
        cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
        conn.commit()

        cursor.close()
        conn.close()

        print(f"✅ Удален студент ID: {student_id}")
        return jsonify({"success": True, "message": "Студент удален"})

    except Exception as e:
        print(f"❌ Ошибка удаления студента: {e}")
        return jsonify({"error": str(e)}), 500


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

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
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

    except Exception as e:
        print(f"❌ Ошибка входа: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/logout', methods=['POST'])
def logout():
    """Выход из системы"""
    print("🚪 POST /api/logout - выход из системы")
    session.clear()
    return jsonify({"message": "Успешный выход"})


@app.route('/api/current-user', methods=['GET'])
def get_current_user():
    """Получить текущего пользователя"""
    if 'user_id' in session:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT * FROM users WHERE id = %s", (session['user_id'],))
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

    return jsonify({"error": "Не авторизован"}), 401


@app.route('/api/my-student', methods=['GET'])
def get_my_student():
    """Получить карточку текущего пользователя"""
    try:
        if 'user_id' not in session:
            return jsonify({"error": "Требуется авторизация"}), 401

        current_user_id = session['user_id']

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT * FROM students WHERE user_id = %s", (current_user_id,))
        student = cursor.fetchone()

        cursor.close()
        conn.close()

        if not student:
            return jsonify({"error": "У вас еще нет карточки"}), 404

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

        return jsonify(result)

    except Exception as e:
        print(f"❌ Ошибка получения карточки пользователя: {e}")
        return jsonify({"error": str(e)}), 500


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
            RETURNING id
        ''', (username, password_hash, role, email))

        new_id = cursor.fetchone()[0]
        conn.commit()

        cursor.close()
        conn.close()

        print(f"✅ Зарегистрирован пользователь: {username}")
        return jsonify({
            "id": new_id,
            "username": username,
            "role": role,
            "email": email
        }), 201

    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/check-card', methods=['GET'])
def check_user_card():
    """Проверить, есть ли у пользователя карточка"""
    try:
        if 'user_id' not in session:
            return jsonify({"hasCard": False}), 200

        current_user_id = session['user_id']

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM students WHERE user_id = %s", (current_user_id,))
        has_card = cursor.fetchone()[0] > 0

        cursor.close()
        conn.close()

        if has_card:
            return jsonify({"hasCard": True})
        else:
            return jsonify({"hasCard": False})

    except Exception as e:
        print(f"❌ Ошибка проверки карточки: {e}")
        return jsonify({"hasCard": False, "error": str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Проверяем таблицы
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM students")
        student_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "database": "connected",
            "data_counts": {
                "users": user_count,
                "students": student_count
            }
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }), 500


if __name__ == '__main__':
    # Инициализируем базу данных
    init_database()

    print("\n" + "=" * 60)
    print("🚀 СЕРВЕР ЗАПУЩЕН!")
    print("=" * 60)
    print("📍 Основная страница: http://localhost:5000")
    print("📍 Админ-панель:      http://localhost:5000/admin")
    print("\n👤 ТЕСТОВЫЕ ПОЛЬЗОВАТЕЛИ:")
    print("   Админ:    логин: admin    пароль: admin123")
    print("   Студент:  логин: student1 пароль: student123")
    print("=" * 60 + "\n")

    app.run(host='0.0.0.0', port=5000, debug=True)