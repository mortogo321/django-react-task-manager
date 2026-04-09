# BaanTask — Тестовое задание (5 дней) / Test Assignment (5 days) / แบบทดสอบ (5 วัน)

---

## О проекте / About the Project / เกี่ยวกับโครงการ

**RU:** BaanTask — AI-платформа для управления домашним персоналом в Таиланде. Приложение помогает экспатам и иностранным резидентам общаться с тайским персоналом (горничные, няни, водители, повара) через AI-перевод в реальном времени и систему управления задачами.

**EN:** BaanTask is an AI-powered household staff management platform for Thailand. The app helps expats and foreign residents communicate with Thai household staff (maids, nannies, drivers, cooks) through real-time AI translation and a task management system.

**TH:** BaanTask คือแพลตฟอร์ม AI สำหรับจัดการพนักงานในบ้านในประเทศไทย แอปช่วยให้ชาวต่างชาติและผู้พำนักอาศัยสื่อสารกับพนักงานในบ้านชาวไทย (แม่บ้าน พี่เลี้ยง คนขับรถ พ่อครัว) ผ่านระบบแปลภาษา AI แบบเรียลไทม์และระบบจัดการงาน

**Стек / Stack:** Python/Django REST Framework (backend), React (web), PostgreSQL, Redis, Docker.

**RU:** Вы можете (и мы рекомендуем) использовать Claude Code или другие AI-инструменты при выполнении заданий. Нас интересует результат и ваше умение эффективно решать задачи.

**EN:** You are welcome (and encouraged) to use Claude Code or other AI tools. We care about the result and your ability to solve problems effectively.

**TH:** คุณสามารถ (และเราแนะนำให้) ใช้ Claude Code หรือเครื่องมือ AI อื่นๆ ในการทำงาน เราสนใจผลลัพธ์และความสามารถในการแก้ปัญหาอย่างมีประสิทธิภาพ

---

## Общие правила / General Rules / กฎทั่วไป

**RU:**
- Каждое задание выдаётся утром, дедлайн — 18:00 (ICT, Bangkok time)
- Ежедневно отправляйте короткий стендап в чат
- Если что-то непонятно — спрашивайте. Отсутствие вопросов при затруднениях — это хуже, чем лишний вопрос
- Коммиты с осмысленными сообщениями, пожалуйста

**EN:**
- Each task is given in the morning, deadline — 18:00 (ICT, Bangkok time)
- Send a short daily standup to the chat
- If something is unclear — ask. Not asking when stuck is worse than asking one extra question
- Meaningful commit messages, please

**TH:**
- แต่ละงานจะมอบหมายในตอนเช้า กำหนดส่ง — 18:00 (เวลาประเทศไทย)
- ส่งรายงานสั้นๆ ประจำวันในแชท
- ถ้าไม่เข้าใจอะไร — ถามได้เลย การไม่ถามเมื่อติดปัญหาแย่กว่าการถามมากเกินไป
- ข้อความ commit ที่มีความหมาย

**Шаблон стендапа / Standup Template / แบบฟอร์มรายงานประจำวัน:**
```
Date / Дата / วันที่: ___
Done yesterday / Что сделал вчера / ทำเสร็จเมื่อวาน: ___
Plan today / Что планирую сегодня / แผนวันนี้: ___
Blockers / Блокеры / ปัญหา: ___
```

---

## День 1 (Пн) / Day 1 (Mon) / วันที่ 1 (จันทร์): Онбординг + Ревью / Onboarding + Code Review / เริ่มต้น + ตรวจสอบโค้ด

**RU:**
1. Поднять проект локально через Docker Compose
2. Убедиться что backend API и frontend работают
3. Изучить структуру проекта и написать краткий документ (1-2 страницы):
   - Описание архитектуры: какие модули есть, как связаны, что делает каждый сервис
   - Какие модели данных используются и как они связаны между собой
4. Провести code review: найти и описать проблемы в коде — логические ошибки, уязвимости безопасности, пропущенную логику, плохие практики
   - Для каждой проблемы: описание, где находится, почему это проблема, как исправить

**EN:**
1. Set up the project locally via Docker Compose
2. Verify that backend API and frontend are running
3. Study the project structure and write a brief document (1-2 pages):
   - Architecture description: what modules exist, how they connect, what each service does
   - What data models are used and how they relate to each other
4. Conduct a code review: find and describe issues — logic errors, security vulnerabilities, missing logic, bad practices
   - For each issue: description, location, why it's a problem, how to fix it

**TH:**
1. ตั้งค่าโปรเจกต์ในเครื่องผ่าน Docker Compose
2. ตรวจสอบว่า backend API และ frontend ทำงานได้
3. ศึกษาโครงสร้างโปรเจกต์และเขียนเอกสารสั้นๆ (1-2 หน้า):
   - คำอธิบายสถาปัตยกรรม: มีโมดูลอะไรบ้าง เชื่อมต่อกันอย่างไร แต่ละบริการทำอะไร
   - มีโมเดลข้อมูลอะไรบ้างและเชื่อมโยงกันอย่างไร
4. ทำ code review: ค้นหาและอธิบายปัญหาในโค้ด — ข้อผิดพลาดทางตรรกะ ช่องโหว่ด้านความปลอดภัย ตรรกะที่ขาดหาย แนวปฏิบัติที่ไม่ดี
   - สำหรับแต่ละปัญหา: คำอธิบาย ตำแหน่ง ทำไมเป็นปัญหา วิธีแก้ไข

**Результат / Deliverable / ผลลัพธ์:** документ + описание проблем / document + issue descriptions / เอกสาร + รายละเอียดปัญหา

---

## День 2 (Вт) / Day 2 (Tue) / วันที่ 2 (อังคาร): Расширение API / API Extension / ขยาย API

**RU:**
1. Исправить найденные в День 1 проблемы
2. Добавить недостающую бизнес-логику (подумайте, что может потребоваться)
3. Покрыть unit-тестами (минимум 5 тестов, больше — лучше)
4. Добавить документацию API (Swagger/OpenAPI или README)
5. В конце дня написать краткий отчёт (5-10 предложений): как использовали AI-инструменты, что помогло, что пришлось дорабатывать вручную

**EN:**
1. Fix the issues found on Day 1
2. Add missing business logic (think about what might be needed)
3. Cover with unit tests (minimum 5 tests, more is better)
4. Add API documentation (Swagger/OpenAPI or README)
5. At the end of the day, write a short report (5-10 sentences): how you used AI tools, what helped, what required manual work

**TH:**
1. แก้ไขปัญหาที่พบในวันที่ 1
2. เพิ่ม business logic ที่ขาดหาย (คิดว่าอะไรอาจจำเป็น)
3. เขียน unit test (อย่างน้อย 5 test ยิ่งมากยิ่งดี)
4. เพิ่มเอกสาร API (Swagger/OpenAPI หรือ README)
5. ตอนท้ายวัน เขียนรายงานสั้นๆ (5-10 ประโยค): ใช้เครื่องมือ AI อย่างไร อะไรช่วยได้ อะไรต้องทำเอง

**Результат / Deliverable / ผลลัพธ์:** рабочий API + тесты + отчёт / working API + tests + report / API ที่ทำงานได้ + test + รายงาน

---

## День 3 (Ср) / Day 3 (Wed) / วันที่ 3 (พุธ): Frontend + Интеграция / Frontend + Integration / Frontend + การเชื่อมต่อ

**RU:**
1. Добавить форму создания новой задачи
2. Реализовать изменение статуса задачи (кнопки или drag & drop)
3. Адаптивный дизайн (мобильная версия)
4. Обработка ошибок (нет сети, сервер не отвечает, невалидные данные)

**EN:**
1. Add a form to create a new task
2. Implement task status change (buttons or drag & drop)
3. Responsive design (mobile version)
4. Error handling (no network, server down, invalid data)

**TH:**
1. เพิ่มฟอร์มสร้างงานใหม่
2. ใช้การเปลี่ยนสถานะงาน (ปุ่มหรือ drag & drop)
3. การออกแบบที่ตอบสนอง (เวอร์ชันมือถือ)
4. การจัดการข้อผิดพลาด (ไม่มีเครือข่าย เซิร์ฟเวอร์ไม่ตอบ ข้อมูลไม่ถูกต้อง)

**Бонус / Bonus / โบนัส:** real-time обновления через WebSocket / real-time updates via WebSocket / อัปเดตแบบเรียลไทม์ผ่าน WebSocket

**Результат / Deliverable / ผลลัพธ์:** рабочий UI с backend / working UI integrated with backend / UI ที่เชื่อมต่อกับ backend

---

## День 4 (Чт) / Day 4 (Thu) / วันที่ 4 (พฤหัสบดี): AI-перевод / AI Translation / การแปลภาษา AI

**RU:**
1. Сервис-обёртка для Claude API (предоставим тестовый ключ)
2. Автоматический перевод текста задачи на тайский при создании
3. Отображение задачи на языке пользователя
4. Кэширование переводов (Redis или in-memory)
5. Обработка ошибок API (timeout, rate limit, fallback)
6. Написать архитектурный документ: как масштабировать сервис перевода при 10,000 запросов/мин?

**EN:**
1. Wrapper service for Claude API (we'll provide a test key)
2. Automatic translation of task text to Thai when created
3. Display task in the user's language
4. Translation caching (Redis or in-memory)
5. API error handling (timeout, rate limit, fallback)
6. Write an architecture document: how would you scale the translation service to 10,000 requests/min?

**TH:**
1. สร้าง service wrapper สำหรับ Claude API (เราจะให้ test key)
2. แปลข้อความงานเป็นภาษาไทยอัตโนมัติเมื่อสร้าง
3. แสดงงานในภาษาของผู้ใช้
4. แคชการแปล (Redis หรือ in-memory)
5. จัดการข้อผิดพลาด API (timeout, rate limit, fallback)
6. เขียนเอกสารสถาปัตยกรรม: จะขยาย service แปลภาษาเป็น 10,000 request/นาที ได้อย่างไร?

**Результат / Deliverable / ผลลัพธ์:** перевод + кэш + документ / translation + cache + document / การแปล + แคช + เอกสาร

---

## День 5 (Пт) / Day 5 (Fri) / วันที่ 5 (ศุกร์): Свободная фича + Защита / Free Feature + Presentation / ฟีเจอร์อิสระ + นำเสนอ

**Утро (4 часа) / Morning (4 hours) / เช้า (4 ชั่วโมง):**

**RU:** Выбрать и реализовать одну фичу:

**EN:** Choose and implement one feature:

**TH:** เลือกและสร้างฟีเจอร์หนึ่งอย่าง:

- **Вариант A / Option A / ตัวเลือก A:** Система уведомлений / Notification System / ระบบแจ้งเตือน — push при смене статуса задачи, настройки пользователя, лог уведомлений / push on task status change, user preferences, notification log / push เมื่อสถานะงานเปลี่ยน การตั้งค่าผู้ใช้ บันทึกการแจ้งเตือน

- **Вариант B / Option B / ตัวเลือก B:** Дашборд аналитики / Analytics Dashboard / แดชบอร์ดวิเคราะห์ — статистика задач, графики, фильтры по периоду и работнику / task statistics, charts, filters by period and worker / สถิติงาน กราฟ ตัวกรองตามช่วงเวลาและพนักงาน

- **Вариант C / Option C / ตัวเลือก C:** Своя идея / Your own idea / ไอเดียของคุณ — предложите фичу и обоснуйте выбор / propose a feature and justify your choice / เสนอฟีเจอร์และอธิบายเหตุผล

**После обеда (2 часа) / Afternoon (2 hours) / บ่าย (2 ชั่วโมง):**

**RU:** Видеозвонок (10-15 минут):
1. Обзор что сделано за неделю
2. Демо работающего приложения
3. Что было самым сложным и как решили
4. Как использовали AI-инструменты
5. Что бы улучшили, если бы было ещё 2 недели

**EN:** Video call (10-15 minutes):
1. Overview of what was done during the week
2. Demo of the working application
3. What was the most challenging and how you solved it
4. How you used AI tools
5. What you'd improve with 2 more weeks

**TH:** วิดีโอคอล (10-15 นาที):
1. สรุปสิ่งที่ทำตลอดสัปดาห์
2. สาธิตแอปพลิเคชันที่ทำงานได้
3. อะไรยากที่สุดและแก้ไขอย่างไร
4. ใช้เครื่องมือ AI อย่างไร
5. จะปรับปรุงอะไรถ้ามีเวลาอีก 2 สัปดาห์

---

**RU:** Удачи! Если есть вопросы — не стесняйтесь спрашивать.

**EN:** Good luck! If you have questions — don't hesitate to ask.

**TH:** ขอให้โชคดี! ถ้ามีคำถาม — อย่าลังเลที่จะถาม
