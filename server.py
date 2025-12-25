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
CORS(app, supports_credentials=True, origins=['http://localhost:5000'])
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['UPLOAD_FOLDER'] = 'public/images/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Создаем папки если их нет
os.makedirs('data', exist_ok=True)
os.makedirs('public/images/uploads', exist_ok=True)

# Пути к файлам данных
STUDENTS_FILE = os.path.join('data', 'students.json')
USERS_FILE = os.path.join('data', 'users.json')


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def load_data(filename):
    """Загрузка данных из файла"""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"❌ Ошибка загрузки {filename}: {e}")
        return []


def save_data(filename, data):
    """Сохранение данных в файл"""
    try:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения {filename}: {e}")
        return False


def init_data():
    """Инициализация начальных данных"""
    print("\n🔧 ИНИЦИАЛИЗАЦИЯ ДАННЫХ")

    # Проверяем и создаем файл пользователей
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
        print(f"✅ Создан файл пользователей с {len(initial_users)} записями")

    # Проверяем и создаем файл студентов
    if not os.path.exists(STUDENTS_FILE):
        initial_students = [
            {
                "id": 1,
                "name": "Иван Иванов",
                "course": 1,
                "status": "studying",
                "description": "Backend-разработчик, увлекается Python и SQL",
                "fullInfo": "Студент 1 курса, изучает Python и базы данных.",
                "skills": ["Python", "SQL", "PostgreSQL"],
                "links": {
                    "github": "https://github.com/ivanov",
                    "portfolio": "https://ivanov-portfolio.ru"
                },
                "photo": "/images/default.jpg",
                "createdAt": datetime.now().isoformat(),
                "updatedAt": datetime.now().isoformat(),
                "userId": 1
            },
            {
                "id": 2,
                "name": "Мария Петрова",
                "course": 3,
                "status": "studying",
                "description": "Frontend-разработчик, специалист по React",
                "fullInfo": "Студентка 3 курса, создала несколько проектов на React.",
                "skills": ["JavaScript", "React", "HTML", "CSS"],
                "links": {
                    "github": "https://github.com/maria",
                    "portfolio": "https://maria-dev.ru"
                },
                "photo": "/images/default.jpg",
                "createdAt": datetime.now().isoformat(),
                "updatedAt": datetime.now().isoformat(),
                "userId": 2
            },
            {
                "id": 3,
                "name": "Алексей Сидоров",
                "course": 2,
                "status": "studying",
                "description": "Data Science, интересуется машинным обучением",
                "fullInfo": "Студент 2 курса, изучает Python, математику и ML.",
                "skills": ["Python", "Pandas", "NumPy", "Scikit-learn"],
                "links": {
                    "github": "https://github.com/alexey",
                    "portfolio": "https://alexey-ds.ru"
                },
                "photo": "/images/default.jpg",
                "createdAt": datetime.now().isoformat(),
                "updatedAt": datetime.now().isoformat(),
                "userId": None
            }
        ]
        save_data(STUDENTS_FILE, initial_students)
        print(f"✅ Создан файл студентов с {len(initial_students)} записями")

    # Создаем папку для загрузок если ее нет
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    print("=" * 50 + "\n")


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
                # Для существующего студента сохраняем с его ID
                new_filename = f"student_{student_id}.{ext}"
            else:
                # Для нового студента временное имя
                new_filename = f"temp_{uuid.uuid4().hex}.{ext}"

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)

            # Сохраняем файл
            file.save(file_path)

            # Оптимизируем изображение
            try:
                with Image.open(file_path) as img:
                    # Конвертируем в RGB если нужно
                    if img.mode in ('RGBA', 'P'):
                        img = img.convert('RGB')
                    # Сохраняем с оптимизацией
                    img.save(file_path, 'JPEG', quality=85, optimize=True)
            except Exception as e:
                print(f"⚠️ Не удалось оптимизировать изображение: {e}")

            # URL для доступа к файлу
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
        students = load_data(STUDENTS_FILE)

        print(f"📁 Загружено {len(students)} студентов из файла")

        # Если пользователь авторизован, его карточка будет первой
        if 'user_id' in session:
            current_user_id = session['user_id']
            print(f"👤 Текущий пользователь ID: {current_user_id}")
            # Сортируем: сначала карточка пользователя, затем остальные
            students.sort(key=lambda x: (0 if x.get('userId') == current_user_id else 1, x['id']))

        print(f"✅ Отправляю {len(students)} студентов")
        return jsonify(students)
    except Exception as e:
        print(f"❌ Ошибка в get_students: {e}")
        return jsonify({"error": "Внутренняя ошибка сервера"}), 500


@app.route('/api/students/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Получить студента по ID"""
    try:
        print(f"🔍 Получен запрос на студента ID: {student_id}")
        students = load_data(STUDENTS_FILE)
        student = next((s for s in students if s.get('id') == student_id), None)

        if not student:
            print(f"❌ Студент ID {student_id} не найден")
            return jsonify({"error": "Студент не найден"}), 404

        print(f"✅ Найден студент: {student['name']}")
        return jsonify(student)
    except Exception as e:
        print(f"❌ Ошибка получения студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students', methods=['POST'])
def create_student():
    """Создать нового студента"""
    try:
        print("➕ Получен запрос на создание студента")

        # Проверяем Content-Type
        if request.content_type.startswith('multipart/form-data'):
            # Получаем данные из формы
            name = request.form.get('name', '').strip()
            course = request.form.get('course', '1')
            description = request.form.get('description', '').strip()
            photo_url = request.form.get('photo', '/images/default.jpg')

            # Преобразуем строку навыков в список
            skills_str = request.form.get('skills', '')
            skills = [skill.strip() for skill in skills_str.split(',') if skill.strip()]

            # Получаем ссылки
            links = {
                "github": request.form.get('github', '').strip() or None,
                "portfolio": request.form.get('portfolio', '').strip() or None
            }

            data = {
                "name": name,
                "course": course,
                "description": description,
                "fullInfo": request.form.get('fullInfo', description),
                "skills": skills,
                "links": links,
                "photo": photo_url
            }
        else:
            # Получаем JSON данные
            data = request.get_json()
            if not data:
                print("❌ Нет данных в запросе")
                return jsonify({"error": "Нет данных"}), 400

        print(f"📝 Данные для создания: {data}")

        required_fields = ['name', 'course', 'description']
        for field in required_fields:
            if field not in data:
                print(f"❌ Отсутствует обязательное поле: {field}")
                return jsonify({"error": f"Поле {field} обязательно"}), 400

        students = load_data(STUDENTS_FILE)

        # Проверяем, есть ли уже карточка у этого пользователя
        if 'user_id' in session:
            current_user_id = session['user_id']
            print(f"👤 Проверяем карточку для пользователя ID: {current_user_id}")
            if current_user_id != 1:  # Админ может создавать несколько
                user_student = next((s for s in students if s.get('userId') == current_user_id), None)
                if user_student:
                    print(f"⚠️ У пользователя уже есть карточка ID: {user_student['id']}")
                    return jsonify(
                        {"error": "У вас уже есть карточка. Вы можете редактировать только свою карточку."}), 400

        # Генерируем новый ID
        if students:
            new_id = max([s.get('id', 0) for s in students], default=0) + 1
        else:
            new_id = 1

        print(f"🆕 Создаем студента с ID: {new_id}")

        new_student = {
            "id": new_id,
            "name": data.get('name', '').strip(),
            "course": int(data.get('course', 1)),
            "status": data.get('status', 'studying'),
            "description": data.get('description', '').strip(),
            "fullInfo": data.get('fullInfo', data.get('description', '').strip()),
            "skills": data.get('skills', []),
            "links": data.get('links', {}),
            "photo": data.get('photo', '/images/default.jpg'),
            "createdAt": datetime.now().isoformat(),
            "updatedAt": datetime.now().isoformat(),
            "userId": session.get('user_id') if 'user_id' in session else None
        }

        students.append(new_student)

        if save_data(STUDENTS_FILE, students):
            print(f"✅ Добавлен студент: {new_student['name']} (ID: {new_id})")
            return jsonify(new_student), 201
        else:
            print("❌ Ошибка сохранения в файл")
            return jsonify({"error": "Ошибка сохранения"}), 500

    except Exception as e:
        print(f"❌ Ошибка создания студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['PUT'])
def update_student(student_id):
    """Обновить данные студента"""
    try:
        print(f"✏️ Получен запрос на обновление студента ID: {student_id}")

        # Проверяем Content-Type
        if request.content_type.startswith('multipart/form-data'):
            # Получаем данные из формы
            name = request.form.get('name', '').strip()
            course = request.form.get('course', '1')
            description = request.form.get('description', '').strip()
            photo_url = request.form.get('photo', '/images/default.jpg')

            # Преобразуем строку навыков в список
            skills_str = request.form.get('skills', '')
            skills = [skill.strip() for skill in skills_str.split(',') if skill.strip()]

            # Получаем ссылки
            links = {
                "github": request.form.get('github', '').strip() or None,
                "portfolio": request.form.get('portfolio', '').strip() or None
            }

            data = {
                "name": name,
                "course": course,
                "status": request.form.get('status', 'studying'),
                "description": description,
                "fullInfo": request.form.get('fullInfo', description),
                "skills": skills,
                "links": links,
                "photo": photo_url
            }
        else:
            # Получаем JSON данные
            data = request.get_json()

        if not data:
            return jsonify({"error": "Нет данных"}), 400

        students = load_data(STUDENTS_FILE)

        # Находим студента
        student_index = None
        for i, student in enumerate(students):
            if student.get('id') == student_id:
                student_index = i
                break

        if student_index is None:
            return jsonify({"error": "Студент не найден"}), 404

        # Проверяем права на редактирование
        student = students[student_index]
        if 'user_id' in session:
            current_user_id = session['user_id']
            current_role = session.get('role', 'student')

            # Админ может редактировать все карточки
            if current_role != 'admin':
                # Студент может редактировать только свою карточку
                if student.get('userId') != current_user_id:
                    return jsonify({"error": "Вы можете редактировать только свою карточку"}), 403
        else:
            return jsonify({"error": "Требуется авторизация"}), 401

        # Обновляем данные
        updatable_fields = ['name', 'course', 'status', 'description', 'fullInfo', 'skills', 'links', 'photo']
        for field in updatable_fields:
            if field in data:
                if field == 'course':
                    try:
                        student[field] = int(data[field])
                    except:
                        student[field] = 1
                elif field == 'photo' and (data[field] == '' or data[field] is None):
                    # Если фото очищено, ставим дефолтное
                    student[field] = '/images/default.jpg'
                elif field == 'skills':
                    # Обрабатываем навыки
                    if isinstance(data[field], str):
                        student[field] = [skill.strip() for skill in data[field].split(',') if skill.strip()]
                    else:
                        student[field] = data[field]
                elif field == 'links':
                    # Обрабатываем ссылки
                    if isinstance(data[field], dict):
                        student[field] = data[field]
                    else:
                        try:
                            student[field] = json.loads(data[field]) if data[field] else {}
                        except:
                            student[field] = {}
                else:
                    student[field] = data[field]

        student['updatedAt'] = datetime.now().isoformat()

        if save_data(STUDENTS_FILE, students):
            print(f"✅ Обновлен студент: {student['name']} (ID: {student_id})")
            return jsonify(student)
        else:
            return jsonify({"error": "Ошибка сохранения"}), 500

    except Exception as e:
        print(f"❌ Ошибка обновления студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Удалить студента"""
    try:
        students = load_data(STUDENTS_FILE)

        # Находим студента
        student = next((s for s in students if s.get('id') == student_id), None)
        if not student:
            return jsonify({"error": "Студент не найден"}), 404

        # Проверяем права на удаление
        if 'user_id' in session:
            current_user_id = session['user_id']
            current_role = session.get('role', 'student')

            # Админ может удалять все карточки
            if current_role != 'admin':
                # Студент может удалять только свою карточку
                if student.get('userId') != current_user_id:
                    return jsonify({"error": "Вы можете удалять только свою карточку"}), 403
        else:
            return jsonify({"error": "Требуется авторизация"}), 401

        # Удаляем фотографию студента если она не дефолтная
        if student.get('photo') and not student['photo'].endswith('default.jpg'):
            try:
                photo_path = os.path.join('public', student['photo'].lstrip('/'))
                if os.path.exists(photo_path):
                    os.remove(photo_path)
                    print(f"✅ Удалена фотография: {photo_path}")
            except Exception as e:
                print(f"⚠️ Не удалось удалить фотографию: {e}")

        # Удаляем студента
        students = [s for s in students if s.get('id') != student_id]

        if save_data(STUDENTS_FILE, students):
            print(f"✅ Удален студент ID: {student_id}")
            return jsonify({"success": True, "message": "Студент удален"})
        else:
            return jsonify({"error": "Ошибка сохранения"}), 500

    except Exception as e:
        print(f"❌ Ошибка удаления студента: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/delete-photo/<filename>', methods=['DELETE'])
def delete_photo(filename):
    """Удалить загруженную фотографию"""
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"✅ Удалена фотография: {file_path}")
            return jsonify({"success": True, "message": "Фотография удалена"})
        else:
            return jsonify({"error": "Файл не найден"}), 404

    except Exception as e:
        print(f"❌ Ошибка удаления фотографии: {e}")
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

        users = load_data(USERS_FILE)
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
        users = load_data(USERS_FILE)
        user = next((u for u in users if u.get('id') == session['user_id']), None)

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
        students = load_data(STUDENTS_FILE)

        # Ищем карточку пользователя
        student = next((s for s in students if s.get('userId') == current_user_id), None)

        if not student:
            return jsonify({"error": "У вас еще нет карточки"}), 404

        return jsonify(student)
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

        users = load_data(USERS_FILE)

        # Проверяем, существует ли пользователь
        if any(u.get('username') == username for u in users):
            return jsonify({"error": "Пользователь с таким логином уже существует"}), 400

        # Генерируем новый ID
        if users:
            new_id = max([u.get('id', 0) for u in users], default=0) + 1
        else:
            new_id = 1

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

        if save_data(USERS_FILE, users):
            print(f"✅ Зарегистрирован пользователь: {username}")
            return jsonify({
                "id": new_id,
                "username": username,
                "role": role,
                "email": email
            }), 201
        else:
            return jsonify({"error": "Ошибка сохранения"}), 500

    except Exception as e:
        print(f"❌ Ошибка регистрации: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/test', methods=['GET'])
def test_api():
    """Тестовый endpoint"""
    return jsonify({
        "status": "ok",
        "message": "API работает корректно",
        "timestamp": datetime.now().isoformat()
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Проверка работоспособности"""
    students = load_data(STUDENTS_FILE)
    users = load_data(USERS_FILE)

    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "data_files": {
            "students": os.path.exists(STUDENTS_FILE),
            "users": os.path.exists(USERS_FILE)
        },
        "data_counts": {
            "students": len(students),
            "users": len(users)
        }
    })


if __name__ == '__main__':
    init_data()

    # Получаем порт из переменных окружения
    port = int(os.environ.get('PORT', 5000))


    app.run(host='0.0.0.0', port=port, debug=False)