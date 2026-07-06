INSERT INTO department (name, full_name) VALUES
('АБ', 'Служба авиационной безопасности'),
('ОТ', 'Отдел охраны труда и техники безопасности'),
('ПЕР', 'Служба организации перевозок');

INSERT INTO position (name) VALUES
('Стажер'),
('Специалист по охране труда'),
('Ведущий специалист по охране труда'),
('Руководитель службы');

INSERT INTO training_type (name) VALUES
('Онлайн-курс'),
('Очный тренинг'),
('Вебинар');

INSERT INTO program (id_type, program_code, name, time_to_complete, is_shown) VALUES
(1, 101, 'Основы охраны труда и техники безопасности', '10:00:00', true),
(1, 102, 'Безопасность на перроне и подъездных путях', '15:30:00', true),
(2, 103, 'Пожарная безопасность и действия при ЧС', '08:00:00', true);

INSERT INTO topic (id_program, name) VALUES
(1, 'Инструктаж по охране труда'),
(1, 'Средства индивидуальной защиты (СИЗ)'),
(2, 'Безопасное поведение на перроне'),
(2, 'Работа вблизи воздушных судов'),
(3, 'Порядок действий при пожаре');

INSERT INTO learning_material (id_topic, file_link) VALUES
(1, 'https://example.com/materials/safety_induction.pdf'),
(2, 'https://example.com/materials/ppe_guide.pdf'),
(3, 'https://example.com/materials/apron_safety.pdf'),
(4, 'https://example.com/materials/aircraft_proximity.pdf'),
(5, 'https://example.com/materials/fire_safety.pdf');

INSERT INTO question (id_topic, question_text, is_verified) VALUES
(1, 'Через какое время после приема на работу сотрудник обязан пройти первичный инструктаж по охране труда?', true),
(1, 'Что относится к обязательным средствам индивидуальной защиты (СИЗ) при работе на перроне?', true),
(2, 'На каком минимальном расстоянии от движущегося воздушного судна запрещено находиться без специального разрешения?', true),
(3, 'Какой сигнал подается при обнаружении возгорания на территории аэропорта?', true),
(5, 'Какое действие является приоритетным при срабатывании пожарной сигнализации?', true);

INSERT INTO answer (id_question, answer_text, is_correct) VALUES
(1, 'В течение первого рабочего дня', true),
(1, 'В течение месяца', false),
(2, 'Сигнальный жилет, каска и защитная обувь', true),
(2, 'Обычная рабочая одежда', false),
(3, '25 метров', true),
(3, '2 метра', false),
(4, 'Три коротких сигнала сирены', true),
(4, 'Один длинный гудок', false),
(5, 'Немедленно покинуть здание по эвакуационному маршруту', true),
(5, 'Продолжить работу до объявления по громкой связи', false);

INSERT INTO employee (id_department, id_position, employee_number, first_name, last_name, middle_name, email, password_hash) VALUES
(1, 2, 1001, 'Иван', 'Иванов', 'Иванович', 'ivanov@example.com', 'pbkdf2_sha256$260000$6707204bb5b22aef235e2f8ba61246ef$db95a36d6bedcea933d7851c10d9895bbb44746794b69be62413ab74e6a70253'),
(1, 3, 1002, 'Петр', 'Петров', 'Петрович', 'petrov@example.com', 'pbkdf2_sha256$260000$6707204bb5b22aef235e2f8ba61246ef$db95a36d6bedcea933d7851c10d9895bbb44746794b69be62413ab74e6a70253'),
(2, 1, 1003, 'Мария', 'Сидорова', 'Александровна', 'sidorova@example.com', 'pbkdf2_sha256$260000$6707204bb5b22aef235e2f8ba61246ef$db95a36d6bedcea933d7851c10d9895bbb44746794b69be62413ab74e6a70253'),
(3, 4, 1004, 'Олег', 'Смирнов', 'Владимирович', 'smirnov@example.com', 'pbkdf2_sha256$260000$6707204bb5b22aef235e2f8ba61246ef$db95a36d6bedcea933d7851c10d9895bbb44746794b69be62413ab74e6a70253');

INSERT INTO notification (id_employee, date, is_viewed) VALUES
(1, '2026-06-01 10:00:00', true),
(2, '2026-06-02 11:00:00', false),
(3, '2026-06-03 12:00:00', true),
(1, '2026-06-05 09:30:00', false);

INSERT INTO complaint (id_question, complaint_text, is_solved) VALUES
(1, 'Вопрос сформулирован некорректно, не указан характер работ.', false),
(4, 'В вопросе не указано, о каком типе сигнала идет речь.', true);

INSERT INTO request (id_employee, id_topic, message_text, ai_response_text, sequence_number) VALUES
(1, 1, 'Как часто нужно проходить повторный инструктаж по охране труда?', 'Повторный инструктаж по охране труда проводится не реже одного раза в 6 месяцев, если иное не установлено локальными нормативными актами.', 1),
(2, 3, 'Можно ли находиться на перроне без сигнального жилета?', 'Нет, нахождение на перроне без сигнального жилета и других средств индивидуальной защиты запрещено правилами техники безопасности.', 1),
(2, 3, 'А если жилет временно отсутствует?', 'В этом случае сотрудник обязан покинуть перрон и сообщить руководителю о необходимости получить СИЗ перед возвращением к работе.', 2);

INSERT INTO program_completion (id_employee, id_program, start_date, end_date) VALUES
(1, 1, '2026-05-01 09:00:00', '2026-05-10 18:00:00'),
(2, 2, '2026-05-05 09:00:00', NULL),
(3, 1, '2026-06-01 09:00:00', NULL),
(4, 3, '2026-06-10 10:00:00', '2026-06-12 16:00:00');

INSERT INTO material_study (id_program_completion, id_learning_material, is_read) VALUES
(1, 1, true),
(1, 2, true),
(2, 3, true),
(2, 4, false),
(3, 1, true),
(3, 2, false);

INSERT INTO test_completion (id_program_completion, id_answer, is_final_test) VALUES
(1, 1, true),
(1, 3, true),
(2, 5, false),
(2, 8, true),
(3, 1, false),
(4, 10, true);
