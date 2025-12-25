// ========== СИСТЕМА СТУДЕНТОВ ==========

class StudentSystem {
    constructor() {
        this.students = [];
        this.currentUser = null;
        this.myStudentCard = null;
        this.currentFilter = 'all';
        this.init();
    }

    async init() {
        console.log('🚀 Инициализация системы студентов...');
        this.initEvents();
        await this.checkAuth();
        await this.loadStudents();
    }

    async loadStudents() {
        try {
            console.log('📥 Загружаю студентов...');
            const cardsContainer = document.getElementById('cards-container');
            cardsContainer.innerHTML = `
                <div class="loading">
                    <i class="fas fa-spinner fa-spin"></i> Загрузка студентов...
                </div>
            `;

            const response = await fetch('/api/students');

            if (!response.ok) {
                throw new Error(`Ошибка ${response.status}: ${response.statusText}`);
            }

            this.students = await response.json();

            console.log(`✅ Загружено ${this.students.length} студентов`);

            // Находим карточку текущего пользователя
            if (this.currentUser) {
                this.myStudentCard = this.students.find(student =>
                    student.userId === this.currentUser.id
                );
                if (this.myStudentCard) {
                    console.log(`🎯 Найдена ваша карточка: ${this.myStudentCard.name}`);
                }
            }

            this.renderStudents();
            this.updateStats();
            this.updateMyCardInfo();

        } catch (error) {
            console.error('❌ Ошибка загрузки студентов:', error);
            this.showError('Не удалось загрузить студентов. Проверьте соединение с сервером.');
        }
    }

    renderStudents() {
        const container = document.getElementById('cards-container');
        const filter = this.currentFilter;

        let filteredStudents = this.students;
        if (filter !== 'all') {
            filteredStudents = this.students.filter(student =>
                student.course.toString() === filter
            );
        }

        if (filteredStudents.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-users-slash"></i>
                    <h3>Нет студентов</h3>
                    <p>${filter === 'all' ? 'Добавьте первого студента' : 'Нет студентов на этом курсе'}</p>
                    ${filter !== 'all' ?
                        '<button class="retry-btn" onclick="window.studentSystem.clearFilter()">Показать всех</button>' :
                        ''
                    }
                </div>
            `;
            return;
        }

        container.innerHTML = filteredStudents.map(student => {
            const isMyCard = this.currentUser && student.userId === this.currentUser.id;

            const getStatusText = (status) => {
                const statuses = {
                    'studying': '🎓 Обучается',
                    'graduated': '🎉 Выпустился',
                    'expelled': '🚫 Отчислен',
                    'academic_leave': '⏸️ Академотпуск'
                };
                return statuses[status] || status;
            };

            const formatDate = (dateString) => {
                if (!dateString) return 'Неизвестно';
                const date = new Date(dateString);
                return date.toLocaleDateString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric'
                });
            };

            const getPhotoUrl = (photo) => {
                if (!photo) return '/images/default.jpg';
                if (photo.startsWith('http') || photo.startsWith('/')) {
                    return photo;
                }
                return `/images/uploads/${photo}`;
            };

            return `
                <div class="card ${isMyCard ? 'my-card' : ''}" data-id="${student.id}">
                    ${isMyCard ?
                        '<div class="my-card-badge"><i class="fas fa-user"></i> Моя карточка</div>' :
                        ''
                    }

                    <div class="card-img-container">
                        <img src="${getPhotoUrl(student.photo)}"
                             alt="${student.name}"
                             class="card-img loaded"
                             onerror="this.src='/images/default.jpg'">
                        <div class="img-placeholder">
                            <i class="fas fa-user-graduate"></i>
                        </div>
                    </div>

                    <div class="card-content">
                        <div class="card-header">
                            <h3 class="card-name">${student.name}</h3>
                            <span class="card-course">${student.course} курс</span>
                        </div>

                        <div class="card-status">
                            <span class="status-badge status-${student.status || 'studying'}">
                                ${getStatusText(student.status || 'studying')}
                            </span>
                        </div>

                        <p class="card-description">${student.description}</p>

                        ${student.skills && student.skills.length > 0 ? `
                            <div class="card-skills">
                                ${student.skills.slice(0, 3).map(skill =>
                                    `<span class="skill">${skill}</span>`
                                ).join('')}
                                ${student.skills.length > 3 ?
                                    `<span class="skill">+${student.skills.length - 3}</span>` :
                                    ''
                                }
                            </div>
                        ` : ''}

                        <div class="card-footer">
                            <div class="card-id">
                                <i class="fas fa-hashtag"></i> ID: ${student.id}
                            </div>
                            <div class="card-date">
                                <i class="far fa-clock"></i> ${formatDate(student.updatedAt)}
                            </div>
                        </div>

                        <div class="card-actions">
                            ${isMyCard ? `
                                <button class="card-edit-btn" onclick="event.stopPropagation(); window.studentSystem.openEditModal(${student.id})">
                                    <i class="fas fa-edit"></i> Редактировать
                                </button>
                            ` : this.currentUser && this.currentUser.role === 'admin' ? `
                                <button class="card-edit-btn" onclick="event.stopPropagation(); window.studentSystem.openEditModal(${student.id})">
                                    <i class="fas fa-edit"></i> Редактировать
                                </button>
                            ` : ''}
                            <button class="card-view-btn" onclick="event.stopPropagation(); window.studentSystem.openViewModal(${student.id})">
                                <i class="fas fa-eye"></i> Подробнее
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    // ========== МОДАЛЬНОЕ ОКНО РЕДАКТИРОВАНИЯ ==========

    openEditModal(studentId) {
        const student = this.students.find(s => s.id === studentId);
        if (!student) {
            this.showNotification('Студент не найден', 'error');
            return;
        }

        if (this.currentUser) {
            if (this.currentUser.role !== 'admin' && student.userId !== this.currentUser.id) {
                this.showNotification('Вы можете редактировать только свою карточку', 'error');
                return;
            }
        } else {
            this.showNotification('Требуется авторизация', 'error');
            return;
        }

        this.closeAllModals();

        const modalHTML = `
            <div class="modal-overlay active" id="edit-modal">
                <div class="modal-content edit-modal">
                    <div class="modal-header">
                        <h3><i class="fas fa-edit"></i> Редактирование карточки</h3>
                        <button class="modal-close" onclick="window.studentSystem.closeModal('edit-modal')">&times;</button>
                    </div>

                    <div class="modal-body">
                        <div class="edit-info">
                            <div class="current-info">
                                <div class="profile-photo-container" style="width: 80px; height: 80px;">
                                    <img src="${student.photo || '/images/default.jpg'}"
                                         alt="${student.name}"
                                         class="current-photo"
                                         id="current-photo-preview"
                                         onerror="this.src='/images/default.jpg'">
                                    <div class="photo-placeholder">
                                        <i class="fas fa-user-graduate"></i>
                                    </div>
                                </div>
                                <div>
                                    <h4>${student.name}</h4>
                                    <p class="student-id">ID: ${student.id}</p>
                                    ${student.userId === this.currentUser?.id ?
                                        '<p><small><i class="fas fa-user"></i> Ваша карточка</small></p>' :
                                        ''
                                    }
                                </div>
                            </div>
                        </div>

                        <form id="edit-student-form">
                            <div class="form-grid">
                                <div class="form-group">
                                    <label>Имя и фамилия *</label>
                                    <input type="text" id="modal-edit-name" value="${student.name}" required>
                                </div>

                                <div class="form-group">
                                    <label>Курс *</label>
                                    <select id="modal-edit-course" required>
                                        ${[1,2,3,4].map(num => `
                                            <option value="${num}" ${student.course == num ? 'selected' : ''}>${num} курс</option>
                                        `).join('')}
                                    </select>
                                </div>

                                <div class="form-group">
                                    <label>Статус</label>
                                    <select id="modal-edit-status">
                                        <option value="studying" ${student.status === 'studying' ? 'selected' : ''}>Обучается</option>
                                        <option value="graduated" ${student.status === 'graduated' ? 'selected' : ''}>Выпустился</option>
                                        <option value="expelled" ${student.status === 'expelled' ? 'selected' : ''}>Отчислен</option>
                                        <option value="academic_leave" ${student.status === 'academic_leave' ? 'selected' : ''}>Академотпуск</option>
                                    </select>
                                </div>

                                <div class="form-group full-width">
                                    <label>Краткое описание *</label>
                                    <input type="text" id="modal-edit-description" value="${student.description}" required>
                                </div>

                                <div class="form-group full-width">
                                    <label>Подробная информация</label>
                                    <textarea id="modal-edit-full-info" rows="3">${student.fullInfo || ''}</textarea>
                                </div>

                                <div class="form-group full-width">
                                    <label>Навыки (через запятую)</label>
                                    <input type="text" id="modal-edit-skills" value="${student.skills ? student.skills.join(', ') : ''}" placeholder="Python, JavaScript, React">
                                </div>

                                <div class="form-group">
                                    <label>GitHub</label>
                                    <input type="url" id="modal-edit-github" value="${student.links?.github || ''}" placeholder="https://github.com/username">
                                </div>

                                <div class="form-group">
                                    <label>Портфолио</label>
                                    <input type="url" id="modal-edit-portfolio" value="${student.links?.portfolio || ''}" placeholder="https://myportfolio.com">
                                </div>
                            </div>

                            <div class="form-actions">
                                ${this.currentUser.role === 'admin' ? `
                                    <button type="button" class="btn btn-danger" onclick="window.studentSystem.confirmDeleteStudent(${student.id})">
                                        <i class="fas fa-trash"></i> Удалить карточку
                                    </button>
                                ` : student.userId === this.currentUser.id ? `
                                    <button type="button" class="btn btn-danger" onclick="window.studentSystem.confirmDeleteStudent(${student.id})">
                                        <i class="fas fa-trash"></i> Удалить мою карточку
                                    </button>
                                ` : ''}
                                <button type="button" class="btn btn-secondary" onclick="window.studentSystem.closeModal('edit-modal')">
                                    Отмена
                                </button>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-save"></i> Сохранить изменения
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.body.style.overflow = 'hidden';

        const editForm = document.getElementById('edit-student-form');
        if (editForm) {
            editForm.addEventListener('submit', (e) => this.saveStudentEdit(e, student.id));
        }
    }

    async saveStudentEdit(event, studentId) {
        event.preventDefault();

        const studentData = {
            name: document.getElementById('modal-edit-name').value.trim(),
            course: parseInt(document.getElementById('modal-edit-course').value),
            status: document.getElementById('modal-edit-status').value,
            description: document.getElementById('modal-edit-description').value.trim(),
            fullInfo: document.getElementById('modal-edit-full-info').value.trim(),
            skills: document.getElementById('modal-edit-skills').value
                .split(',')
                .map(s => s.trim())
                .filter(s => s.length > 0),
            links: {
                github: document.getElementById('modal-edit-github').value.trim() || null,
                portfolio: document.getElementById('modal-edit-portfolio').value.trim() || null
            }
        };

        try {
            const response = await fetch(`/api/students/${studentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(studentData)
            });

            if (response.ok) {
                const updatedStudent = await response.json();
                this.showNotification('Карточка успешно обновлена!', 'success');
                this.closeModal('edit-modal');
                await this.loadStudents();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка обновления карточки');
            }
        } catch (error) {
            console.error('Ошибка обновления карточки:', error);
            this.showNotification(error.message, 'error');
        }
    }

    // ========== УПРАВЛЕНИЕ МОДАЛЬНЫМИ ОКНАМИ ==========

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.remove();
        }

        const remainingModals = document.querySelectorAll('.modal-overlay');
        if (remainingModals.length === 0) {
            document.body.style.overflow = 'auto';
        }
    }

    closeAllModals() {
        document.querySelectorAll('.modal-overlay').forEach(modal => modal.remove());
        document.body.style.overflow = 'auto';
    }

    // ========== АВТОРИЗАЦИЯ И УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЕМ ==========

    async checkAuth() {
        try {
            const response = await fetch('/api/current-user');
            if (response.ok) {
                this.currentUser = await response.json();
                this.updateAuthUI();
            }
        } catch (error) {
            console.log('Пользователь не авторизован');
        }
    }

    updateAuthUI() {
        const userSection = document.getElementById('user-section');
        const guestInfo = document.getElementById('guest-info');
        const editSection = document.getElementById('edit-section');

        if (!userSection) return;

        if (this.currentUser) {
            userSection.innerHTML = `
                <div class="user-info">
                    <i class="fas fa-user-circle"></i>
                    <div class="user-details">
                        <strong>${this.currentUser.username}</strong>
                        <span class="user-role ${this.currentUser.role}">
                            ${this.currentUser.role === 'admin' ? '👑 Админ' : '👨‍🎓 Студент'}
                        </span>
                    </div>
                    <button class="logout-btn" onclick="window.studentSystem.logout()">
                        <i class="fas fa-sign-out-alt"></i>
                    </button>
                </div>
            `;

            if (guestInfo) guestInfo.style.display = 'none';
            if (editSection) editSection.style.display = 'block';
        } else {
            userSection.innerHTML = `
                <div class="auth-buttons">
                    <button class="login-btn" onclick="window.studentSystem.showLoginModal()">
                        <i class="fas fa-sign-in-alt"></i> Войти
                    </button>
                    <button class="register-btn" onclick="window.studentSystem.showRegisterModal()">
                        <i class="fas fa-user-plus"></i> Регистрация
                    </button>
                </div>
            `;

            if (guestInfo) guestInfo.style.display = 'block';
            if (editSection) editSection.style.display = 'none';
        }
    }

    updateMyCardInfo() {
        const myCardInfo = document.getElementById('my-card-info');
        const createCardSection = document.getElementById('create-card-section');
        const adminInfo = document.getElementById('admin-info');

        if (!myCardInfo || !createCardSection) return;

        if (this.currentUser) {
            if (this.currentUser.role === 'admin') {
                myCardInfo.style.display = 'none';
                createCardSection.style.display = 'none';
                if (adminInfo) adminInfo.style.display = 'block';
            } else {
                if (this.myStudentCard) {
                    myCardInfo.style.display = 'block';
                    createCardSection.style.display = 'none';

                    document.getElementById('my-card-name').textContent = this.myStudentCard.name;
                    document.getElementById('my-card-course').textContent = `${this.myStudentCard.course} курс`;

                    const statusText = {
                        'studying': 'Обучается',
                        'graduated': 'Выпустился',
                        'expelled': 'Отчислен',
                        'academic_leave': 'Академ'
                    };
                    const status = this.myStudentCard.status || 'studying';
                    document.getElementById('my-card-status').textContent = statusText[status] || status;
                } else {
                    myCardInfo.style.display = 'none';
                    createCardSection.style.display = 'block';
                }

                if (adminInfo) adminInfo.style.display = 'none';
            }
        } else {
            myCardInfo.style.display = 'none';
            createCardSection.style.display = 'none';
            if (adminInfo) adminInfo.style.display = 'none';
        }
    }

    // ========== ФОРМА ДОБАВЛЕНИЯ СТУДЕНТА С ФОТО ==========

    async addStudent(event) {
        event.preventDefault();

        const form = event.target;

        try {
            // Проверяем, есть ли уже карточка у пользователя
            if (this.currentUser && this.currentUser.role !== 'admin') {
                if (this.myStudentCard) {
                    this.showNotification('У вас уже есть карточка. Вы можете редактировать только свою карточку.', 'error');
                    return;
                }
            }

            // Получаем фото
            let photoUrl = '/images/default.jpg';
            const photoInput = document.getElementById('add-photo-input');
            const photoUrlInput = document.getElementById('add-photo-url');

            if (photoInput && photoInput.files[0]) {
                photoUrl = photoUrlInput.value;
            }

            const studentData = {
                name: form.querySelector('#name').value.trim(),
                course: parseInt(form.querySelector('#course').value),
                status: form.querySelector('#status').value,
                description: form.querySelector('#description').value.trim(),
                fullInfo: form.querySelector('#full-info').value.trim() || form.querySelector('#description').value.trim(),
                skills: form.querySelector('#skills').value.split(',').map(s => s.trim()).filter(s => s),
                links: {
                    github: form.querySelector('#github').value.trim() || null,
                    portfolio: form.querySelector('#portfolio').value.trim() || null
                },
                photo: photoUrl
            };

            const response = await fetch('/api/students', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'include',
                body: JSON.stringify(studentData)
            });

            if (response.ok) {
                const newStudent = await response.json();
                this.showNotification('Студент успешно добавлен!', 'success');

                // Сбрасываем форму
                form.reset();
                if (photoUrlInput) photoUrlInput.value = '/images/default.jpg';
                const previewContainer = document.getElementById('add-photo-preview-container');
                if (previewContainer) previewContainer.innerHTML = '';

                await this.loadStudents();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка добавления студента');
            }
        } catch (error) {
            console.error('Ошибка добавления студента:', error);
            this.showNotification(error.message, 'error');
        }
    }

    initAddPhotoUpload() {
        const uploadArea = document.getElementById('add-photo-upload-area');
        const photoInput = document.getElementById('add-photo-input');

        if (!uploadArea || !photoInput) return;

        uploadArea.addEventListener('click', () => {
            photoInput.click();
        });

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#00b894';
            uploadArea.style.background = 'rgba(0, 184, 148, 0.1)';
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = '#ddd';
            uploadArea.style.background = '#fafafa';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = '#ddd';
            uploadArea.style.background = '#fafafa';

            if (e.dataTransfer.files.length) {
                const file = e.dataTransfer.files[0];
                if (file.type.startsWith('image/')) {
                    photoInput.files = e.dataTransfer.files;
                    this.handleAddPhotoUpload(file);
                } else {
                    this.showNotification('Пожалуйста, выберите файл изображения', 'error');
                }
            }
        });

        photoInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                this.handleAddPhotoUpload(e.target.files[0]);
            }
        });
    }

    async handleAddPhotoUpload(file) {
        try {
            const previewContainer = document.getElementById('add-photo-preview-container');
            const photoUrlInput = document.getElementById('add-photo-url');

            if (file.size > 5 * 1024 * 1024) {
                this.showNotification('Файл слишком большой. Максимальный размер: 5MB', 'error');
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                previewContainer.innerHTML = `
                    <div style="display: flex; align-items: center; gap: 15px; background: #f8f9fa; padding: 15px; border-radius: 10px;">
                        <img src="${e.target.result}" alt="Превью" style="width: 80px; height: 80px; object-fit: cover; border-radius: 10px;">
                        <div style="flex: 1;">
                            <p style="margin: 0 0 5px 0; font-weight: bold;">${file.name}</p>
                            <p style="margin: 0; color: #666; font-size: 0.9em;">${(file.size / 1024).toFixed(1)} KB</p>
                        </div>
                        <button type="button" class="btn btn-danger" onclick="this.parentElement.remove(); document.getElementById('add-photo-url').value = '/images/default.jpg';" style="padding: 5px 10px;">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                `;
            };
            reader.readAsDataURL(file);

            const formData = new FormData();
            formData.append('photo', file);

            const response = await fetch('/api/upload-photo', {
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                const result = await response.json();
                photoUrlInput.value = result.photoUrl;
                this.showNotification('Фото успешно загружено!', 'success');
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка загрузки фото');
            }
        } catch (error) {
            console.error('Ошибка загрузки фото:', error);
            this.showNotification(error.message, 'error');
            document.getElementById('add-photo-input').value = '';
        }
    }

    // ========== ФИЛЬТРЫ И ПОИСК ==========

    initEvents() {
        // Форма добавления студента
        const studentForm = document.getElementById('student-form');
        if (studentForm) {
            studentForm.addEventListener('submit', (e) => this.addStudent(e));
            this.initAddPhotoUpload();
        }

        // Форма поиска для редактирования
        const editByIdForm = document.getElementById('edit-by-id-form');
        if (editByIdForm) {
            editByIdForm.addEventListener('submit', (e) => {
                e.preventDefault();
                this.openEditById();
            });
        }

        // Фильтры
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.filterStudents(e));
        });

        // Кнопка обновления
        const reloadBtn = document.getElementById('reload-btn');
        if (reloadBtn) {
            reloadBtn.addEventListener('click', () => this.loadStudents());
        }

        // Закрытие по ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllModals();
            }
        });

        // Закрытие по клику на оверлей
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal-overlay')) {
                this.closeAllModals();
            }
        });
    }

    async openEditById() {
        const studentId = parseInt(document.getElementById('edit-student-id').value);

        if (!studentId || studentId <= 0) {
            this.showNotification('Введите корректный ID студента', 'error');
            return;
        }

        try {
            const response = await fetch(`/api/students/${studentId}`);

            if (!response.ok) {
                throw new Error('Студент не найден');
            }

            const student = await response.json();

            if (this.currentUser) {
                if (this.currentUser.role === 'admin') {
                    this.openEditModal(student.id);
                } else if (student.userId === this.currentUser.id) {
                    this.openEditModal(student.id);
                } else {
                    this.showNotification('Вы можете редактировать только свою карточку', 'error');
                }
            } else {
                this.showNotification('Требуется авторизация', 'error');
            }

        } catch (error) {
            console.error('Ошибка поиска студента:', error);
            this.showNotification(error.message, 'error');
        }
    }

    filterStudents(event) {
        document.querySelectorAll('.filter-btn').forEach(btn =>
            btn.classList.remove('active'));
        event.currentTarget.classList.add('active');
        this.currentFilter = event.currentTarget.dataset.filter;

        const filterText = document.getElementById('filter-text');
        if (filterText) {
            if (this.currentFilter === 'all') {
                filterText.textContent = 'Показаны все студенты';
            } else {
                const filteredCount = this.students.filter(s => s.course.toString() === this.currentFilter).length;
                filterText.textContent = `Показаны студенты ${this.currentFilter} курса (${filteredCount} чел.)`;
            }
        }

        this.renderStudents();
    }

    clearFilter() {
        this.currentFilter = 'all';
        document.querySelectorAll('.filter-btn').forEach(btn =>
            btn.classList.remove('active'));
        const allBtn = document.querySelector('.filter-btn[data-filter="all"]');
        if (allBtn) allBtn.classList.add('active');

        const filterText = document.getElementById('filter-text');
        if (filterText) filterText.textContent = 'Показаны все студенты';

        this.renderStudents();
    }

    updateStats() {
        const total = this.students.length;
        const totalElement = document.getElementById('total-count');
        const footerElement = document.getElementById('footer-count');

        if (totalElement) totalElement.textContent = total;
        if (footerElement) footerElement.textContent = total;
    }

    // ========== АВТОРИЗАЦИЯ ==========

    showLoginModal() {
        this.closeAllModals();

        const modalHTML = `
            <div class="modal-overlay active" id="login-modal">
                <div class="modal-content" style="max-width: 400px;">
                    <div class="modal-header">
                        <h3><i class="fas fa-sign-in-alt"></i> Вход в систему</h3>
                        <button class="modal-close" onclick="window.studentSystem.closeModal('login-modal')">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom: 20px;">
                            <small style="color: #666; display: block; margin-bottom: 10px;">Тестовые пользователи:</small>
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 8px; font-size: 0.9rem;">
                                <div><strong>Админ:</strong> admin / admin123</div>
                                <div><strong>Студент:</strong> student1 / student123</div>
                            </div>
                        </div>
                        <form id="modal-login-form">
                            <div class="form-group">
                                <label>Логин</label>
                                <input type="text" id="modal-username" required>
                            </div>
                            <div class="form-group">
                                <label>Пароль</label>
                                <input type="password" id="modal-password" required>
                            </div>
                            <div class="form-actions">
                                <button type="button" class="btn btn-secondary" onclick="window.studentSystem.closeModal('login-modal')">
                                    Отмена
                                </button>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-sign-in-alt"></i> Войти
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.body.style.overflow = 'hidden';

        const loginForm = document.getElementById('modal-login-form');
        if (loginForm) {
            loginForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const username = document.getElementById('modal-username').value;
                const password = document.getElementById('modal-password').value;
                this.login(username, password);
            });
        }
    }

    showRegisterModal() {
        this.closeAllModals();

        const modalHTML = `
            <div class="modal-overlay active" id="register-modal">
                <div class="modal-content" style="max-width: 400px;">
                    <div class="modal-header">
                        <h3><i class="fas fa-user-plus"></i> Регистрация</h3>
                        <button class="modal-close" onclick="window.studentSystem.closeModal('register-modal')">&times;</button>
                    </div>
                    <div class="modal-body">
                        <form id="modal-register-form">
                            <div class="form-group">
                                <label>Логин *</label>
                                <input type="text" id="reg-username" required>
                            </div>
                            <div class="form-group">
                                <label>Пароль *</label>
                                <input type="password" id="reg-password" required>
                            </div>
                            <div class="form-group">
                                <label>Email (необязательно)</label>
                                <input type="email" id="reg-email">
                            </div>
                            <div class="form-actions">
                                <button type="button" class="btn btn-secondary" onclick="window.studentSystem.closeModal('register-modal')">
                                    Отмена
                                </button>
                                <button type="submit" class="btn btn-primary">
                                    <i class="fas fa-user-plus"></i> Зарегистрироваться
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.body.style.overflow = 'hidden';

        const registerForm = document.getElementById('modal-register-form');
        if (registerForm) {
            registerForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const username = document.getElementById('reg-username').value;
                const password = document.getElementById('reg-password').value;
                const email = document.getElementById('reg-email').value;
                this.register(username, password, email);
            });
        }
    }

    async login(username, password) {
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ username, password })
            });

            if (response.ok) {
                this.currentUser = await response.json();
                this.updateAuthUI();
                this.showNotification('Успешный вход!', 'success');
                this.closeModal('login-modal');
                await this.loadStudents();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка входа');
            }
        } catch (error) {
            this.showNotification(error.message, 'error');
        }
    }

    async register(username, password, email) {
        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username,
                    password,
                    email,
                    role: 'student'
                })
            });

            if (response.ok) {
                const user = await response.json();
                this.showNotification('Регистрация успешна! Теперь войдите в систему.', 'success');
                this.closeModal('register-modal');
                setTimeout(() => this.login(username, password), 1000);
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка регистрации');
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
            this.myStudentCard = null;
            this.updateAuthUI();
            this.updateMyCardInfo();
            this.showNotification('Вы успешно вышли из системы', 'info');
            await this.loadStudents();

        } catch (error) {
            console.error('Ошибка выхода:', error);
        }
    }

    async confirmDeleteStudent(studentId) {
        const student = this.students.find(s => s.id === studentId);
        if (!student) return;

        const isMyCard = student.userId === this.currentUser?.id;
        const message = isMyCard
            ? 'Вы уверены, что хотите удалить свою карточку? Это действие нельзя отменить.'
            : `Вы уверены, что хотите удалить карточку студента "${student.name}"? Это действие нельзя отменить.`;

        if (!confirm(message)) return;

        try {
            const response = await fetch(`/api/students/${studentId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (response.ok) {
                this.showNotification(isMyCard ? 'Ваша карточка удалена' : 'Карточка студента удалена', 'success');
                this.closeModal('edit-modal');
                await this.loadStudents();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Ошибка удаления');
            }
        } catch (error) {
            console.error('Ошибка удаления карточки:', error);
            this.showNotification(error.message, 'error');
        }
    }

    // ========== МОДАЛЬНОЕ ОКНО ПРОСМОТРА ==========

    openViewModal(studentId) {
        const student = this.students.find(s => s.id === studentId);
        if (!student) {
            this.showNotification('Студент не найден', 'error');
            return;
        }

        this.closeAllModals();

        const getStatusColor = (status) => {
            const colors = {
                'studying': '#00b894',
                'graduated': '#3498db',
                'expelled': '#e74c3c',
                'academic_leave': '#f39c12'
            };
            return colors[status] || '#95a5a6';
        };

        const getStatusText = (status) => {
            const statuses = {
                'studying': '🎓 Обучается',
                'graduated': '🎉 Выпустился',
                'expelled': '🚫 Отчислен',
                'academic_leave': '⏸️ Академотпуск'
            };
            return statuses[status] || status;
        };

        const formatDate = (dateString) => {
            if (!dateString) return 'Неизвестно';
            const date = new Date(dateString);
            return date.toLocaleDateString('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        };

        const getPhotoUrl = (photo) => {
            if (!photo) return '/images/default.jpg';
            if (photo.startsWith('http') || photo.startsWith('/')) {
                return photo;
            }
            return `/images/uploads/${photo}`;
        };

        const modalHTML = `
            <div class="modal-overlay active" id="view-modal">
                <div class="modal-content view-modal">
                    <div class="modal-header">
                        <h3><i class="fas fa-user-graduate"></i> Карточка студента</h3>
                        <button class="modal-close" onclick="window.studentSystem.closeModal('view-modal')">&times;</button>
                    </div>

                    <div class="modal-body">
                        <div class="student-profile">
                            <div class="profile-header">
                                <div class="profile-photo-container">
                                    <img src="${getPhotoUrl(student.photo)}"
                                         alt="${student.name}"
                                         class="profile-photo"
                                         onerror="this.src='/images/default.jpg'">
                                    <div class="photo-placeholder">
                                        <i class="fas fa-user-graduate"></i>
                                    </div>
                                </div>
                                <div class="profile-info">
                                    <h2>${student.name}</h2>
                                    <div class="profile-meta">
                                        <span class="course-badge">${student.course} курс</span>
                                        <span class="status-badge" style="background: ${getStatusColor(student.status)};">
                                            ${getStatusText(student.status)}
                                        </span>
                                        <span class="id-badge">ID: ${student.id}</span>
                                    </div>
                                    ${student.userId === this.currentUser?.id ?
                                        '<div style="margin-top: 10px;"><span class="my-card-badge"><i class="fas fa-user"></i> Моя карточка</span></div>' :
                                        ''
                                    }
                                </div>
                            </div>

                            <div class="info-section">
                                <h4><i class="fas fa-info-circle"></i> Описание</h4>
                                <p class="description-text">${student.description || 'Нет описания'}</p>
                                ${student.fullInfo ? `
                                    <div class="full-info">
                                        <h5>Подробнее:</h5>
                                        <p>${student.fullInfo}</p>
                                    </div>
                                ` : ''}
                            </div>

                            ${student.skills && student.skills.length > 0 ? `
                                <div class="info-section">
                                    <h4><i class="fas fa-code"></i> Навыки</h4>
                                    <div class="skills-container">
                                        ${student.skills.map(skill => `
                                            <span class="skill-tag">${skill}</span>
                                        `).join('')}
                                    </div>
                                </div>
                            ` : ''}

                            ${student.links && (student.links.github || student.links.portfolio) ? `
                                <div class="info-section">
                                    <h4><i class="fas fa-link"></i> Ссылки</h4>
                                    <div class="links-container">
                                        ${student.links.github ? `
                                            <a href="${student.links.github}" target="_blank" class="social-link github">
                                                <i class="fab fa-github"></i>
                                                <span>GitHub</span>
                                            </a>
                                        ` : ''}
                                        ${student.links.portfolio ? `
                                            <a href="${student.links.portfolio}" target="_blank" class="social-link portfolio">
                                                <i class="fas fa-briefcase"></i>
                                                <span>Портфолио</span>
                                            </a>
                                        ` : ''}
                                    </div>
                                </div>
                            ` : ''}

                            <div class="info-section">
                                <h4><i class="fas fa-calendar-alt"></i> Информация</h4>
                                <div class="dates-info">
                                    <div class="date-item">
                                        <span class="date-label">Создано:</span>
                                        <span class="date-value">${formatDate(student.createdAt)}</span>
                                    </div>
                                    <div class="date-item">
                                        <span class="date-label">Обновлено:</span>
                                        <span class="date-value">${formatDate(student.updatedAt)}</span>
                                    </div>
                                </div>
                            </div>

                            <div class="modal-actions">
                                ${(this.currentUser && (student.userId === this.currentUser.id || this.currentUser.role === 'admin')) ? `
                                    <button class="btn btn-edit" onclick="window.studentSystem.openEditModal(${student.id})">
                                        <i class="fas fa-edit"></i> Редактировать
                                    </button>
                                ` : ''}
                                <button class="btn btn-close" onclick="window.studentSystem.closeModal('view-modal')">
                                    <i class="fas fa-times"></i> Закрыть
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHTML);
        document.body.style.overflow = 'hidden';
    }

    // ========== УВЕДОМЛЕНИЯ И ОШИБКИ ==========

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
                <span>${message}</span>
            </div>
            <button onclick="this.parentElement.remove()">&times;</button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    showError(message) {
        const container = document.getElementById('cards-container');
        container.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <h3>Ошибка загрузки</h3>
                <p>${message}</p>
                <button class="retry-btn" onclick="window.studentSystem.loadStudents()">
                    <i class="fas fa-redo"></i> Попробовать снова
                </button>
            </div>
        `;
    }
}

// Запускаем систему
document.addEventListener('DOMContentLoaded', () => {
    window.studentSystem = new StudentSystem();
});