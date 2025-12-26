// ========== АДМИН-ПАНЕЛЬ ==========

class AdminPanel {
    constructor() {
        this.currentUser = null;
        this.currentStudentId = null;
        this.students = [];
        this.users = [];
        this.init();
    }

    async init() {
        console.log('🚀 Инициализация админ-панели...');

        // Проверяем авторизацию
        await this.checkAuth();

        // Инициализируем события
        this.initEvents();

        // Загружаем данные если авторизованы
        if (this.currentUser) {
            await this.loadData();
        }
    }

    async checkAuth() {
        try {
            const response = await fetch('/api/current-user');
            if (response.ok) {
                this.currentUser = await response.json();

                if (this.currentUser.role !== 'admin') {
                    this.showNotification('Требуются права администратора', 'error');
                    setTimeout(() => window.location.href = '/', 2000);
                    return;
                }

                this.showAdminContent();
                this.updateUserInfo();
            } else {
                this.showLoginSection();
            }
        } catch (error) {
            console.error('Ошибка проверки авторизации:', error);
            this.showLoginSection();
        }
    }

    showLoginSection() {
        document.getElementById('login-section').style.display = 'flex';
        document.getElementById('admin-content').style.display = 'none';
    }

    showAdminContent() {
        document.getElementById('login-section').style.display = 'none';
        document.getElementById('admin-content').style.display = 'block';
    }

    updateUserInfo() {
        if (this.currentUser) {
            const header = document.querySelector('.admin-header');
            const userInfo = document.createElement('div');
            userInfo.className = 'user-info';
            userInfo.innerHTML = `
                <small style="opacity: 0.8; display: block; margin-top: 10px;">
                    <i class="fas fa-user"></i> ${this.currentUser.username}
                    <span class="role-badge">${this.currentUser.role}</span>
                </small>
            `;
            header.querySelector('p').after(userInfo);
        }
    }

    initEvents() {
        // Вход
        document.getElementById('login-form')?.addEventListener('submit', (e) => this.login(e));

        // Выход
        document.getElementById('logout-btn')?.addEventListener('click', () => this.logout());

        // Навигация
        document.querySelectorAll('.admin-btn[data-section]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                this.switchSection(e.currentTarget.dataset.section);
            });
        });

        // Студенты
        document.getElementById('add-student-btn')?.addEventListener('click', () => this.openStudentModal());
        document.getElementById('search-students')?.addEventListener('input', (e) => this.filterStudents(e.target.value));
        document.getElementById('status-filter')?.addEventListener('change', () => this.filterStudents());
        document.getElementById('course-filter')?.addEventListener('change', () => this.filterStudents());
        document.getElementById('clear-filters')?.addEventListener('click', () => this.clearFilters());

        // Пользователи
        document.getElementById('add-user-btn')?.addEventListener('click', () => this.openUserModal());

        // Модальные окна
        document.querySelectorAll('.close-modal, .cancel-btn').forEach(btn => {
            btn.addEventListener('click', () => this.closeModal());
        });

        document.getElementById('student-modal-form')?.addEventListener('submit', (e) => this.saveStudent(e));
        document.getElementById('user-modal-form')?.addEventListener('submit', (e) => this.saveUser(e));

        // Файловый инпут
        const photoUpload = document.getElementById('photo-upload-area');
        const photoInput = document.getElementById('modal-photo');

        if (photoUpload && photoInput) {
            photoUpload.addEventListener('click', () => photoInput.click());
            photoInput.addEventListener('change', (e) => this.previewPhoto(e, 'modal-photo-preview'));
        }

        // Drag and drop для фото
        photoUpload?.addEventListener('dragover', (e) => {
            e.preventDefault();
            photoUpload.style.borderColor = '#6a11cb';
            photoUpload.style.background = 'rgba(106, 17, 203, 0.1)';
        });

        photoUpload?.addEventListener('dragleave', () => {
            photoUpload.style.borderColor = '#ddd';
            photoUpload.style.background = '#fafafa';
        });

        photoUpload?.addEventListener('drop', (e) => {
            e.preventDefault();
            photoUpload.style.borderColor = '#ddd';
            photoUpload.style.background = '#fafafa';

            if (e.dataTransfer.files.length) {
                photoInput.files = e.dataTransfer.files;
                this.previewPhoto({ target: photoInput }, 'modal-photo-preview');
            }
        });
    }

    async login(event) {
        event.preventDefault();

        const username = document.getElementById('login-username').value;
        const password = document.getElementById('login-password').value;

        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                this.currentUser = await response.json();

                if (this.currentUser.role !== 'admin') {
                    throw new Error('Требуются права администратора');
                }

                this.showAdminContent();
                this.updateUserInfo();
                await this.loadData();

                this.showNotification('Успешный вход в админ-панель!', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка входа');
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    async logout() {
        try {
            await fetch('/api/logout', {
                method: 'POST',
                credentials: 'include'
            });

            this.currentUser = null;
            this.showLoginSection();
            document.getElementById('login-form').reset();

            this.showNotification('Вы успешно вышли из системы', 'info');
        } catch (error) {
            console.error('Ошибка выхода:', error);
        }
    }

    switchSection(section) {
        // Обновляем активную кнопку
        document.querySelectorAll('.admin-btn[data-section]').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.section === section);
        });

        // Показываем выбранную секцию
        document.querySelectorAll('.admin-section').forEach(sec => {
            sec.style.display = sec.id === `${section}-section` ? 'block' : 'none';
        });
    }

    async loadData() {
        try {
            await Promise.all([
                this.loadStudents(),
                this.loadUsers()
            ]);

            this.updateStats();
        } catch (error) {
            this.showNotification('Ошибка загрузки данных', 'error');
        }
    }

    async loadStudents() {
        try {
            const response = await fetch('/api/students');
            this.students = await response.json();
            this.renderStudentsTable(this.students);
        } catch (error) {
            console.error('Ошибка загрузки студентов:', error);
            throw error;
        }
    }

    renderStudentsTable(students) {
        const tbody = document.getElementById('students-table');

        if (!students.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" class="empty-state">
                        <i class="fas fa-users-slash"></i>
                        <h3>Нет студентов</h3>
                        <p>Добавьте первого студента через кнопку "Добавить студента"</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = students.map(student => `
            <tr>
                <td>${student.id}</td>
                <td>
                    <img src="${student.photo || 'https://ui-avatars.com/api/?name=' + encodeURIComponent(student.name) + '&background=6a11cb&color=fff&size=100'}"
                         alt="${student.name}"
                         class="table-photo"
                         onerror="this.src='https://ui-avatars.com/api/?name='+encodeURIComponent('${student.name}')+'&background=6a11cb&color=fff&size=100'">
                </td>
                <td>
                    <strong>${student.name}</strong>
                    <br>
                    <small style="color: #666;">${student.description || ''}</small>
                </td>
                <td>
                    <span class="badge" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 5px 15px; border-radius: 15px;">
                        ${student.course} курс
                    </span>
                </td>
                <td>
                    <span class="status-badge status-${student.status || 'studying'}">
                        ${this.getStatusText(student.status)}
                    </span>
                </td>
                <td>
                    <div style="display: flex; flex-wrap: wrap; gap: 5px; max-width: 200px;">
                        ${(student.skills || []).slice(0, 3).map(skill =>
                            `<span class="skill-tag">${skill}</span>`
                        ).join('')}
                        ${(student.skills || []).length > 3 ?
                            `<span class="skill-tag">+${(student.skills || []).length - 3}</span>` : ''
                        }
                    </div>
                </td>
                <td>
                    ${this.formatDate(student.updatedAt || student.createdAt)}
                </td>
                <td>
                    <div class="action-buttons">
                        <button class="action-btn edit-btn" data-id="${student.id}" title="Редактировать">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="action-btn delete-btn" data-id="${student.id}" title="Удалить">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // Добавляем обработчики для кнопок действий
        tbody.querySelectorAll('.edit-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.editStudent(parseInt(btn.dataset.id));
            });
        });

        tbody.querySelectorAll('.delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.confirmDeleteStudent(parseInt(btn.dataset.id));
            });
        });
    }

    async loadUsers() {
        // В реальном приложении здесь нужно загружать пользователей с сервера
        // Для демо покажем заглушку
        const tbody = document.getElementById('users-table');

        if (this.currentUser) {
            tbody.innerHTML = `
                <tr>
                    <td>${this.currentUser.id}</td>
                    <td>${this.currentUser.username}</td>
                    <td>
                        <span class="badge" style="background: #6a11cb; color: white; padding: 5px 15px; border-radius: 15px;">
                            ${this.currentUser.role}
                        </span>
                    </td>
                    <td>${this.currentUser.email || '—'}</td>
                    <td>Сегодня</td>
                    <td>
                        <span style="color: #666; font-size: 0.9em;">Текущий пользователь</span>
                    </td>
                </tr>
            `;
        } else {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        <i class="fas fa-user-slash"></i>
                        <h3>Нет пользователей</h3>
                    </td>
                </tr>
            `;
        }
    }

    openStudentModal(student = null) {
        this.currentStudentId = student ? student.id : null;
        const modal = document.getElementById('student-modal');
        const form = document.getElementById('student-modal-form');

        document.getElementById('modal-title').textContent =
            student ? 'Редактировать студента' : 'Добавить студента';

        if (student) {
            // Заполняем форму данными студента
            document.getElementById('modal-name').value = student.name;
            document.getElementById('modal-course').value = student.course;
            document.getElementById('modal-status').value = student.status || 'studying';
            document.getElementById('modal-description').value = student.description || '';

            if (student.links) {
                document.getElementById('modal-github').value = student.links.github || '';
                document.getElementById('modal-portfolio').value = student.links.portfolio || '';
                document.getElementById('modal-linkedin').value = student.links.linkedin || '';
            }

            document.getElementById('modal-skills').value = (student.skills || []).join(', ');

            // Показываем текущее фото
            if (student.photo) {
                document.getElementById('modal-photo-preview').innerHTML = `
                    <p><small>Текущее фото:</small></p>
                    <img src="${student.photo}" alt="Текущее фото" style="max-width: 150px; border-radius: 10px;">
                `;
            }
        } else {
            // Очищаем форму
            form.reset();
            document.getElementById('modal-photo-preview').innerHTML = '';
        }

        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    async saveStudent(event) {
        event.preventDefault();

        if (!this.currentUser) {
            this.showNotification('Требуется авторизация', 'error');
            return;
        }

        const formData = new FormData();

        // Собираем данные
        const data = {
            name: document.getElementById('modal-name').value.trim(),
            course: document.getElementById('modal-course').value,
            status: document.getElementById('modal-status').value,
            description: document.getElementById('modal-description').value.trim(),
            skills: document.getElementById('modal-skills').value
                .split(',')
                .map(s => s.trim())
                .filter(s => s.length > 0),
            links: {
                github: document.getElementById('modal-github').value.trim() || null,
                portfolio: document.getElementById('modal-portfolio').value.trim() || null,
                linkedin: document.getElementById('modal-linkedin').value.trim() || null
            }
        };

        // Добавляем текстовые данные
        for (const key in data) {
            if (key === 'skills') {
                formData.append(key, JSON.stringify(data[key]));
            } else if (key === 'links') {
                formData.append(key, JSON.stringify(data[key]));
            } else {
                formData.append(key, data[key]);
            }
        }

        // Добавляем файл фото
        const photoFile = document.getElementById('modal-photo').files[0];
        if (photoFile) {
            formData.append('photo', photoFile);
        }

        try {
            let response;

            if (this.currentStudentId) {
                // Обновление существующего студента
                response = await fetch(`/api/students/${this.currentStudentId}`, {
                    method: 'PUT',
                    body: formData,
                    credentials: 'include'
                });
            } else {
                // Создание нового студента
                response = await fetch('/api/students', {
                    method: 'POST',
                    body: formData,
                    credentials: 'include'
                });
            }

            if (response.ok) {
                const student = await response.json();
                this.closeModal();
                await this.loadStudents();
                this.updateStats();

                this.showNotification(
                    this.currentStudentId ?
                    'Студент успешно обновлен!' :
                    'Студент успешно добавлен!',
                    'success'
                );
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка сохранения');
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    async editStudent(studentId) {
        try {
            const response = await fetch(`/api/students/${studentId}`);
            if (response.ok) {
                const student = await response.json();
                this.openStudentModal(student);
            } else {
                throw new Error('Студент не найден');
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    confirmDeleteStudent(studentId) {
        const student = this.students.find(s => s.id === studentId);
        if (!student) return;

        const modal = document.getElementById('confirm-modal');
        const message = document.getElementById('confirm-message');
        const cancelBtn = document.getElementById('confirm-cancel');
        const deleteBtn = document.getElementById('confirm-delete');

        message.textContent = `Вы уверены, что хотите удалить студента "${student.name}"? Это действие нельзя отменить.`;

        // Очищаем старые обработчики
        const newCancelBtn = cancelBtn.cloneNode(true);
        const newDeleteBtn = deleteBtn.cloneNode(true);

        cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
        deleteBtn.parentNode.replaceChild(newDeleteBtn, deleteBtn);

        // Добавляем новые обработчики
        newCancelBtn.addEventListener('click', () => {
            modal.style.display = 'none';
        });

        newDeleteBtn.addEventListener('click', () => {
            this.deleteStudent(studentId);
            modal.style.display = 'none';
        });

        modal.style.display = 'flex';
    }

    async deleteStudent(studentId) {
        try {
            const response = await fetch(`/api/students/${studentId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (response.ok) {
                await this.loadStudents();
                this.updateStats();
                this.showNotification('Студент успешно удален', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка удаления');
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    openUserModal() {
        document.getElementById('user-modal').style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    async saveUser(event) {
        event.preventDefault();

        const userData = {
            username: document.getElementById('user-username').value.trim(),
            password: document.getElementById('user-password').value,
            email: document.getElementById('user-email').value.trim() || null,
            role: document.getElementById('user-role').value
        };

        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(userData)
            });

            if (response.ok) {
                this.closeModal();
                await this.loadUsers();
                this.showNotification('Пользователь успешно создан', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка создания пользователя');
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    filterStudents(search = null) {
        if (search === null) {
            search = document.getElementById('search-students').value.toLowerCase();
        }

        const status = document.getElementById('status-filter').value;
        const course = document.getElementById('course-filter').value;

        let filtered = this.students;

        // Поиск
        if (search) {
            filtered = filtered.filter(student =>
                student.name.toLowerCase().includes(search) ||
                student.description?.toLowerCase().includes(search) ||
                (student.skills || []).some(skill => skill.toLowerCase().includes(search))
            );
        }

        // Фильтр по статусу
        if (status) {
            filtered = filtered.filter(student => student.status === status);
        }

        // Фильтр по курсу
        if (course) {
            filtered = filtered.filter(student => student.course.toString() === course);
        }

        this.renderStudentsTable(filtered);

        // Обновляем информацию о фильтрах
        const total = this.students.length;
        const shown = filtered.length;

        if (search || status || course) {
            const filterInfo = document.createElement('div');
            filterInfo.className = 'filter-info';
            filterInfo.innerHTML = `
                <small style="color: #666;">
                    Показано ${shown} из ${total} студентов
                    ${search ? ` • Поиск: "${search}"` : ''}
                </small>
            `;

            // Удаляем старую информацию
            const oldInfo = document.querySelector('.filter-info');
            if (oldInfo) oldInfo.remove();

            // Добавляем новую информацию после фильтров
            document.querySelector('.filter-controls')?.after(filterInfo);
        } else {
            const oldInfo = document.querySelector('.filter-info');
            if (oldInfo) oldInfo.remove();
        }
    }

    clearFilters() {
        document.getElementById('search-students').value = '';
        document.getElementById('status-filter').value = '';
        document.getElementById('course-filter').value = '';

        const oldInfo = document.querySelector('.filter-info');
        if (oldInfo) oldInfo.remove();

        this.renderStudentsTable(this.students);
    }

    updateStats() {
        if (!this.students.length) return;

        const total = this.students.length;
        const studying = this.students.filter(s => s.status === 'studying').length;
        const graduated = this.students.filter(s => s.status === 'graduated').length;
        const expelled = this.students.filter(s => s.status === 'expelled').length;

        // Обновляем числа
        document.getElementById('total-students').textContent = total;
        document.getElementById('studying-count').textContent = studying;
        document.getElementById('graduated-count').textContent = graduated;

        // Проценты
        const studyingPercent = total > 0 ? Math.round((studying / total) * 100) : 0;
        const graduatedPercent = total > 0 ? Math.round((graduated / total) * 100) : 0;

        document.querySelector('.stat-percent').textContent = `${studyingPercent}% от общего числа`;
        document.querySelectorAll('.stat-percent')[1].textContent = `${graduatedPercent}% от общего числа`;

        // Активность (последние 7 дней)
        const weekAgo = new Date();
        weekAgo.setDate(weekAgo.getDate() - 7);

        const recentUpdates = this.students.filter(s => {
            const updated = new Date(s.updatedAt || s.createdAt);
            return updated > weekAgo;
        }).length;

        document.getElementById('activity-count').textContent = recentUpdates;
        document.querySelector('.stat-change').textContent = `+${recentUpdates} обновлений за неделю`;

        // График распределения по курсам
        this.renderCourseChart();
    }

    renderCourseChart() {
        const courses = {1: 0, 2: 0, 3: 0, 4: 0};
        this.students.forEach(s => {
            if (courses[s.course] !== undefined) {
                courses[s.course]++;
            }
        });

        const chartElement = document.getElementById('course-chart');
        chartElement.innerHTML = `
            <div style="padding: 20px;">
                <div style="display: flex; justify-content: space-around; align-items: flex-end; height: 200px; margin-top: 30px;">
                    ${[1,2,3,4].map(course => {
                        const count = courses[course] || 0;
                        const max = Math.max(...Object.values(courses));
                        const height = max > 0 ? (count / max) * 150 : 0;

                        return `
                            <div style="text-align: center;">
                                <div style="
                                    width: 40px;
                                    height: ${height}px;
                                    background: linear-gradient(to top, #667eea, #764ba2);
                                    border-radius: 10px 10px 0 0;
                                    margin: 0 auto 10px auto;
                                "></div>
                                <div style="font-weight: bold; color: #333;">${course} курс</div>
                                <div style="color: #666; font-size: 0.9em;">${count} чел.</div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    previewPhoto(event, previewId) {
        const file = event.target.files[0];
        const preview = document.getElementById(previewId);

        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.innerHTML = `
                    <p><small>Предпросмотр:</small></p>
                    <img src="${e.target.result}" alt="Предпросмотр фото"
                         style="max-width: 150px; border-radius: 10px; margin-top: 10px;">
                `;
            };
            reader.readAsDataURL(file);
        }
    }

    closeModal() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.style.display = 'none';
        });
        document.body.style.overflow = 'auto';
        this.currentStudentId = null;
    }

    getStatusText(status) {
        const statuses = {
            'studying': '🎓 Обучается',
            'graduated': '🎉 Выпустился',
            'expelled': '🚫 Отчислен',
            'academic_leave': '⏸️ Академотпуск'
        };
        return statuses[status] || status;
    }

    formatDate(dateString) {
        if (!dateString) return '—';

        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));

        if (days === 0) return 'Сегодня';
        if (days === 1) return 'Вчера';
        if (days < 7) return `${days} дня назад`;

        return date.toLocaleDateString('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric'
        });
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notification-container') || (() => {
            const div = document.createElement('div');
            div.id = 'notification-container';
            document.body.appendChild(div);
            return div;
        })();

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;

        const icons = {
            success: 'fa-check-circle',
            error: 'fa-exclamation-circle',
            info: 'fa-info-circle'
        };

        notification.innerHTML = `
            <i class="fas ${icons[type] || 'fa-info-circle'}"></i>
            <div class="notification-content">
                <h4>${type === 'success' ? 'Успешно!' : type === 'error' ? 'Ошибка!' : 'Информация'}</h4>
                <p>${message}</p>
            </div>
            <button class="notification-close">&times;</button>
        `;

        container.appendChild(notification);

        // Закрытие по кнопке
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.style.animation = 'slideInRight 0.3s ease reverse';
            setTimeout(() => notification.remove(), 300);
        });

        // Автоматическое закрытие через 5 секунд
        setTimeout(() => {
            if (notification.parentElement) {
                notification.style.animation = 'slideInRight 0.3s ease reverse';
                setTimeout(() => notification.remove(), 300);
            }
        }, 5000);
    }
}

// Запуск админ-панели
document.addEventListener('DOMContentLoaded', () => {
    window.adminPanel = new AdminPanel();
});