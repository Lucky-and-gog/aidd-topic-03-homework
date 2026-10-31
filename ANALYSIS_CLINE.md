# Анализ проекта Investing Demo

## 1. Назначение приложения и технологический стек

**Investing Demo** — веб-приложение для учета и мониторинга биржевых инструментов (акций). Пользователь может просматривать список акций, открывать карточку инструмента с историческим графиком цен и текущей ценой, а авторизованный пользователь — добавлять, редактировать и удалять инструменты. Приложение интегрируется с **Tinkoff Invest API** для загрузки справочника акций, получения последних цен и исторических свечей. Фоновый процесс (Celery) периодически обновляет текущие цены и вычисляет направление тренда. Также предоставляется REST API (Django REST Framework) для CRUD-операций над акциями.

**Технологический стек:**

- Язык: Python.
- Веб-фреймворк: Django 4.1.7 (`requirements.txt`).
- REST API: Django REST Framework 3.14.0, django-filter 22.1.
- Формы/UI: django-crispy-forms 2.0 + crispy-bootstrap3, Bootstrap 3/4 (статические CSS).
- База данных: PostgreSQL (настройка в `config/settings.py`, `DATABASES`), драйвер `psycopg2-binary`.
- Очередь/фоновые задачи: Celery 5.2.7, брокер Redis (`redis://127.0.0.1:6379/0`), beat-расписание в `config/celery.py`.
- Внешний API: Tinkoff Invest API (`tinkoff-investments==0.2.0b50`), пакет `tinkoff`.
- Графики: Plotly 5.13.1 (`plotly.graph_objs.Scatter`, `plotly.offline.plot`).
- Вспомогательные библиотеки: `python-dateutil`, `pytz`, `tenacity`, `cachetools`, `pydantic`, `grpcio`/`protobuf` (зависимости Tinkoff API), `amqp`/`kombu` (транспорт Celery).
- Сервер приложений: WSGI/ASGI (`config/wsgi.py`, `config/asgi.py`).

## 2. Структура проекта и основные компоненты

Корневые файлы: `manage.py`, `requirements.txt`, `docker-compose.yml` (PostgreSQL + Redis), `README.md`, `HOMEWORK.md`.

Пакеты:

- `config/` — настройки проекта (`settings.py`), корневая маршрутизация (`urls.py`), конфигурация Celery (`celery.py`), WSGI/ASGI.
- `dashboard/` — приложение «акции»: модель `Share`, представления, формы, админка, сервисы внешнего API, фоновая задача, REST API, шаблоны, миграции.
- `user/` — приложение «пользователи»: регистрация, вход, выход на основе стандартной модели `django.contrib.auth.User`.

Ключевые файлы dashboard:

- `dashboard/models.py` — модель `Share`.
- `dashboard/views.py` — CBV: `ShareListView`, `ShareDetailView`, `ShareCreateView`, `ShareUpdateView`, `ShareDeleteView`, `IsUserAuthenticatedMixin`.
- `dashboard/urls.py` — маршруты веб-интерфейса и подключение API.
- `dashboard/forms.py` — `ShareModelForm` (`fields = "__all__"`).
- `dashboard/admin.py` — `ShareAdmin`.
- `dashboard/tasks.py` — Celery-задача `update_last_price`.
- `dashboard/services/market_data.py` — `get_last_data(share)`.
- `dashboard/services/graph.py` — `get_graph(share)`.
- `dashboard/management/commands/add_shares.py` — команда `add_shares`.
- `dashboard/migrations/0001..0007` — эволюция схемы `Share`.
- `dashboard/api/v1/*` — `router`, `views`, `serializer`, `urls`.

Ключевые файлы user:

- `user/models.py` — `User = get_user_model()`.
- `user/views.py` — `AuthView`, `RegistrationView`, `LogoutView`.
- `user/forms.py` — `AuthForm`, `RegistrationForm`.
- `user/urls.py` — маршруты `login/`, `registration/`, `logout/`.

## 3. Архитектура и взаимодействие компонентов

- **Маршрутизация**: `config/urls.py`: `admin/` → Django admin; `''` → `dashboard.urls`; `user` → `user.urls`.
- **Представления**: class-based views (`ListView`, `View`, `CreateView`, `UpdateView`, `DeleteView`).
- **Аутентификация**: сессионная, на базе Django auth. Ограничение доступа к CRUD реализовано через `IsUserAuthenticatedMixin` (`UserPassesTestMixin`), проверяющий `request.user.is_authenticated`.
- **Данные**: PostgreSQL по конфигурации, ORM Django. Таблицы создаются миграциями `dashboard` (7 миграций).
- **Фоновая обработка**: `config/__init__.py` экспортирует `celery_app`; `config/celery.py` настраивает брокер Redis и beat-расписание, вызывающее `dashboard.tasks.update_last_price` каждые 10 секунд. Задача обходит все `Share`, обращается к Tinkoff API и обновляет `last_price`, `is_trend_high`, `updated_at`.
- **Внешние сервисы**: Tinkoff Invest API используется в `add_shares`, `market_data.get_last_data`, `graph.get_graph`. Токен берется из `settings.TINKOFF_TOKEN` (по умолчанию пустая строка).
- **API**: `dashboard/api/urls.py` → `v1/` → DRF `DefaultRouter`, регистрирующий `shares` → `ShareViewSet`. Базовая пагинация/фильтрация задана в `REST_FRAMEWORK`.
- **Шаблоны**: `dashboard/templates/dashboard/*.html` расширяют `base.html`; `user/templates/user/*.html` — отдельный базовый шаблон.
## 4. Используемые библиотеки и внешние зависимости

| Библиотека | Назначение в проекте |
|---|---|
| Django 4.1.7 | ядро веб-приложения, ORM, админка, auth |
| djangorestframework 3.14.0 | REST API для Share |
| django-filter 22.1 | фильтрация в API |
| django-crispy-forms 2.0, crispy-bootstrap3 | рендеринг форм |
| Celery 5.2.7 | фоновые задачи |
| redis 4.5.1 | брокер Celery |
| psycopg2-binary 2.9.5 | драйвер PostgreSQL |
| tinkoff-investments 0.2.0b50 | данные рынка |
| plotly 5.13.1 | графики |
| python-dateutil, pytz | работа с датами |
| tenacity, cachetools, pydantic | зависимости/утилиты |
| grpcio, protobuf | транспорт Tinkoff API |

## 5. Модель данных

### Сущность `Share` (`dashboard/models.py`)

| Атрибут | Тип | Ограничения/свойства | Назначение |
|---|---|---|---|
| `id` | BigAutoField | PK, auto | идентификатор |
| `figi` | CharField(255) | unique | FIGI инструмента (Tinkoff) |
| `isin` | CharField(255) | — | ISIN |
| `name` | CharField(255) | verbose «Наименование компании» | название компании |
| `ticker` | CharField(10) | unique, verbose «Тикер» | тикер |
| `currency` | CharField(20) | verbose «Валюта» | валюта цены |
| `uid` | CharField(255) | unique | UID инструмента (Tinkoff) |
| `last_price` | FloatField | null/blank, verbose «Текущая цена» | последняя цена |
| `is_trend_high` | BooleanField | null/blank, verbose «Растет цена» | направление тренда |
| `updated_at` | DateTimeField | auto_now, null | время последнего обновления |

`Meta`: verbose_name «Акция», verbose_name_plural «Акции». Связей (ForeignKey) в текущем коде нет.

### Пользователь

Отдельной модели пользователя в проекте нет. Используется стандартная модель `django.contrib.auth.models.User` (`user/models.py`: `User = get_user_model()`). Регистрация создает пользователя через `User.objects.create_user(email, email, password)`, где первый аргумент — username, второй — email.

### Примечание о БД

В поставляемом `db.sqlite3` присутствуют таблицы `dashboard_portfolio`, `dashboard_position`, `dashboard_portfoliotransaction` со связями к `auth_user` и `dashboard_share` (включая уникальные ограничения `unique_user_portfolio_name`, `unique_portfolio_share`). Эти таблицы **не отражены** в `dashboard/models.py` и миграциях, то есть являются артефактом предыдущих экспериментов/незавершенной функциональности и не соответствуют текущему исходному коду.

## 6. Механизмы обработки запросов и работы с БД

- **Список акций**: `ShareListView(ListView)` — `model=Share`, `template_name=dashboard/list.html`, `paginate_by=100`, `ordering=["name"]`.
- **Детали**: `ShareDetailView(View).get` получает `Share.objects.get(id=pk)` и рендерит `dashboard/detail.html` с `plot_div=get_graph(share)`.
- **Создание**: `ShareCreateView(IsUserAuthenticatedMixin, CreateView)` — `form_class=ShareModelForm`, `success_url=reverse_lazy("dashboard:index")`.
- **Редактирование**: `ShareUpdateView(IsUserAuthenticatedMixin, UpdateView)` — `model=Share`, тот же шаблон/форма.
- **Удаление**: `ShareDeleteView(IsUserAuthenticatedMixin, DeleteView)` — `model=Share`, шаблон `dashboard/delete.html`.
- **Ограничение доступа**: `IsUserAuthenticatedMixin.test_func` возвращает `self.request.user.is_authenticated`; `handle_no_permission` (staticmethod) возвращает redirect на `dashboard:index`.
- **Регистрация**: `RegistrationView` использует `RegistrationForm`; при `is_valid()` вызывает `form.save()`, `login()`, redirect на главную; иначе рендерит шаблон с `form.errors["__all__"]`.
- **Вход**: `AuthView` аутентифицирует по `username=form.data["email"].lower()`, `password=form.data["password"]`; при успехе `login()` и redirect; иначе сообщение об ошибке.
- **Выход**: `LogoutView.get` вызывает `logout()` и redirect на главную.
- **БД**: Django ORM (`Share.objects.all/get/filter/update/create/get_or_create`), миграции 0001–0007. Пользователи — стандартная модель `auth.User` (миграций в `user` нет).
- **Админка**: `ShareAdmin` с `list_display`, `search_fields`, `fields`.
- **REST API**: `ShareViewSet(ModelViewSet)` — queryset `Share.objects.all()`, `serializer_class=ShareSerializer`, filter backends: `OrderingFilter`, `DjangoFilterBackend`, `SearchFilter`; `filterset_class=ShareFilter` (`name`, `ticker`); `ordering_fields=["name","ticker"]`; `search_fields=["$name"]`. Пагинация `LimitOffsetPagination`, `PAGE_SIZE=100` (из `REST_FRAMEWORK`).
- **Сериализация**: `ShareSerializer` поля: `id, figi, isin, name, ticker, currency, last_price, is_trend_high, updated_at` (поле `uid` не включено).
- **Фоновая задача**: `update_last_price()` обходит все `Share`, вызывает `get_last_data`, вычисляет тренд, обновляет запись через `Share.objects.filter(id=share.id).update(...)`.
- **Внешние данные**: `get_last_data` использует `Client(TINKOFF_TOKEN).market_data.get_last_prices(figi=[share.figi])`, возвращает `[price.units, time]`.
- **График**: `get_graph` получает дневные свечи за 180 дней (`CandleInterval.CANDLE_INTERVAL_DAY`), строит `Scatter` по датам и `close.units`, возвращает HTML-`div` через `plotly.offline.plot`.
- **Первичная загрузка**: команда `add_shares` вызывает `client.instruments.shares()` и `Share.objects.get_or_create(...)` по всем полям.
" 
## 7. Восстановленные функциональные требования

1. Система отображает список всех акций на главной странице с пагинацией по 100 записей и сортировкой по наименованию компании. Подтверждение: `dashboard/views.py` (`ShareListView`: `model=Share`, `paginate_by=100`, `ordering=["name"]`), шаблон `dashboard/templates/dashboard/list.html`.

2. Система предоставляет детальную страницу акции по её идентификатору, отображающую название, текущую цену, валюту и время последнего обновления. Подтверждение: `dashboard/urls.py` (`path("<int:pk>", ...)`), `ShareDetailView`, `dashboard/templates/dashboard/detail.html`.

3. На детальной странице система строит и отображает график исторических цен акции за последние 180 дней (дневные свечи, цены закрытия). Подтверждение: `dashboard/services/graph.py` (`get_graph`: `from_=now()-timedelta(days=180)`, `CandleInterval.CANDLE_INTERVAL_DAY`, `candle.close.units`), `detail.html` (`{{ plot_div }}`).

4. Неаутентифицированный пользователь может просматривать список и детали акций, но не видит элементы управления (добавление, редактирование, удаление). Подтверждение: `list.html` (`{% if user.is_authenticated %}` вокруг кнопок/столбца «Управление» и ссылки «Добавить»).

5. Аутентифицированный пользователь может добавить новую акцию через форму, содержащую все поля модели `Share`. Подтверждение: `dashboard/views.py` (`ShareCreateView(IsUserAuthenticatedMixin, CreateView)`, `form_class=ShareModelForm`), `dashboard/forms.py` (`fields="__all__"`), `dashboard/templates/dashboard/create.html`.

6. Аутентифицированный пользователь может редактировать существующую акцию. Подтверждение: `ShareUpdateView`, маршрут `update/<int:pk>`, форма `ShareModelForm`.

7. Аутентифицированный пользователь может удалить акцию после подтверждения. Подтверждение: `ShareDeleteView`, маршрут `delete/<int:pk>`, шаблон `dashboard/templates/dashboard/delete.html`.

8. Пользователь может зарегистрироваться, указав email и пароль дважды. Система проверяет совпадение паролей и отсутствие ранее зарегистрированного email, создает пользователя и выполняет вход. Подтверждение: `user/forms.py` (`RegistrationForm.clean`, `save`), `user/views.py` (`RegistrationView.post`).

9. Пользователь может войти в систему по email и паролю; при успехе перенаправляется на главную, при ошибке видит сообщение «Неверный логин или пароль!». Подтверждение: `user/views.py` (`AuthView.post`), `user/templates/user/auth.html`.

10. Пользователь может выйти из системы по адресу `/user/logout/`, после чего перенаправляется на главную. Подтверждение: `user/views.py` (`LogoutView`), `user/urls.py` (`path("logout/", ...)`).

11. Приложение предоставляет REST API для CRUD-операций над акциями по префиксу `/api/v1/shares/`. Подтверждение: `dashboard/api/v1/router.py` (`router.register(r"shares", ShareViewSet)`), `dashboard/api/v1/views.py`, `dashboard/api/urls.py`, `dashboard/urls.py`.

12. API поддерживает пагинацию `LimitOffset` с размером страницы 100. Подтверждение: `config/settings.py` (`REST_FRAMEWORK`), `dashboard/tests.py` (`response.data["results"]`).

13. API поддерживает фильтрацию по полям `name` и `ticker`, сортировку по `name`/`ticker`, поиск по `name`. Подтверждение: `dashboard/api/v1/views.py` (`ShareFilter`, `ordering_fields`, `search_fields`).

14. API сериализует поля `id, figi, isin, name, ticker, currency, last_price, is_trend_high, updated_at`. Подтверждение: `dashboard/api/v1/serializer.py` (`ShareSerializer.Meta.fields`).

15. Система периодически (Celery beat) обновляет текущую цену и направление тренда для всех акций, обращаясь к Tinkoff Invest API. Подтверждение: `config/celery.py` (`beat_schedule` → `dashboard.tasks.update_last_price`, `schedule: 10.0`), `dashboard/tasks.py`, `dashboard/services/market_data.py`.

16. Тренд определяется сравнением новой цены с предыдущей: если новая цена меньше предыдущей, `is_trend_high=False`, иначе `True`. Подтверждение: `dashboard/tasks.py` (`if share.last_price > last_price: is_trend_high=False else True`).

17. Если предыдущая цена отсутствует (выброшено исключение при сравнении), тренд считается растущим (`is_trend_high=True`). Подтверждение: `dashboard/tasks.py` (внутренний `except` → `is_trend_high=True`).

18. Администратор может управлять акциями через Django admin: просмотр списка, поиск по `figi`, `isin`, `name`, `ticker`. Подтверждение: `dashboard/admin.py` (`ShareAdmin`).

19. Предусмотрена команда `python manage.py add_shares` для первичной загрузки справочника акций из Tinkoff Invest API с дедупликацией по всем полям. Подтверждение: `dashboard/management/commands/add_shares.py` (`get_or_create`).

20. В списке акций цена подсвечивается зеленым при растущем тренде и красноватым при нерастущем. Подтверждение: `dashboard/templates/dashboard/list.html` (условие `share.is_trend_high` и цвета фона).

21. Email пользователя используется как имя пользователя (username) для аутентификации. Подтверждение: `user/forms.py` (`User.objects.create_user(email, email, password)`), `user/views.py` (`authenticate(username=form.data["email"].lower(), ...)`).
" 
## 8. Неоднозначности, противоречия и дефекты реализации

1. **Пустой `SECRET_KEY` и `DEBUG=True`** при `ALLOWED_HOSTS=[]` в `config/settings.py` — приложение небезопасно и не готово к продакшену.

2. **Несоответствие окружения**: `requirements.txt` фиксирует Django 4.1.7, а в `venv` установлен Django 5.2.18 на Python 3.14; проект может не запускаться/вести себя иначе в современной среде.

3. **Пустой `TINKOFF_TOKEN` по умолчанию** (`config/settings.py`: `TINKOFF_TOKEN = ""`) — все обращения к Tinkoff API (загрузка акций, цены, графики) завершатся ошибкой без ручной настройки.

4. **База данных**: `settings.py` настроен на PostgreSQL, но в корне присутствует `db.sqlite3` с таблицами `dashboard_portfolio`, `dashboard_position`, `dashboard_portfoliotransaction`, которых нет в моделях/миграциях. Это артефакт экспериментов и расхождение с исходным кодом.

5. **API доступен без аутентификации**: в `REST_FRAMEWORK` не заданы `DEFAULT_PERMISSION_CLASSES`/`DEFAULT_AUTHENTICATION_CLASSES`, поэтому DRF использует `AllowAny` по умолчанию; CRUD через API открыт для анонимных пользователей, в отличие от веб-интерфейса, где CRUD требует входа.

6. **Форма `ShareModelForm` с `fields="__all__"`** позволяет пользователю вручную задавать `last_price`, `is_trend_high`, `updated_at`, `uid`, обходя логику обновления из Tinkoff API и нарушая целостность данных.

7. **`ShareDetailView` использует `Share.objects.get(id=pk)` без `get_object_or_404`** — при несуществующем id возникает необработанное `DoesNotExist` (HTTP 500 вместо 404).

8. **`RegistrationView` хрупко обрабатывает ошибки**: обращение `form.errors["__all__"].data[0].message` вызовет `KeyError`, если ошибки привязаны к полям, а не к форме в целом. `RegistrationForm.clean` обращается к `self.cleaned_data["email"]` и т.д. до проверки валидности полей — при невалидных данных возможен `KeyError`.

9. **Регистрация не применяет валидаторы паролей Django** (форма обычная `forms.Form`, а не `ModelForm`), пароль не проверяется на сложность.

10. **Несогласованность регистра email**: `User.objects.create_user(email, email, password)` сохраняет username в исходном регистре, а `AuthView` ищет `username=form.data["email"].lower()` — вход может не пройти, если email вводился в верхнем регистре при регистрации.

11. **`AuthView` не валидирует форму**: прямой доступ `form.data["email"]`/`form.data["password"]` может привести к `KeyError` при отсутствии полей.

12. **`RegistrationForm.save()` вызывает `authenticate` и возвращает его результат**; если аутентификация вернет `None`, `RegistrationView` выполнит `login(request, None)` и упадет.

13. **`market_data.get_last_data`** предполагает, что `resp.last_prices` непуст; при пустом списке `.pop()` вызовет `IndexError`. Также возвращается только `price.units` (дробная часть `nano` игнорируется), что теряет точность; поле `time` получается, но в задаче не используется.

14. **`update_last_price`**: сравнение `share.last_price > last_price` при `last_price=None` (новая акция без цены) вызывает `TypeError`, который перехватывается и тренд принудительно становится `True`; логика тренда для первого обновления неоднозначна. Задача не использует полученное время.

15. **Частота Celery beat**: ключ расписания называется `add-every-5-min`, но `schedule: 10.0` (секунд) — противоречие между названием и фактическим интервалом; задача выполняется каждые 10 секунд, что может быть избыточным.

16. **`graph.get_graph`** использует только `candle.close.units` (игнорирует `nano`), строит график только по ценам закрытия; при отсутствии свечей (пустой результат) график будет пустым; `now()` из Tinkoff может иметь особенности часового пояса.

17. **API `search_fields = ["$name"]`** использует синтаксис полнотекстового поиска PostgreSQL; при работе на SQLite (например, в тестах/другой среде) поиск может не работать. Тесты проекта (`dashboard/tests.py`) используют `APITestCase`, который создает тестовую БД согласно настройкам (PostgreSQL), поэтому без доступного PostgreSQL тесты не запустятся.

18. **Сериализатор исключает `uid`**, но модель требует `uid` (unique, not null). При создании через API без `uid` валидация завершится ошибкой; веб-форма с `fields="__all__"` принуждает вводить `uid` вручную. Неоднозначно, кто должен задавать `uid`.

19. **`IsUserAuthenticatedMixin.handle_no_permission` объявлен как `@staticmethod`**, что нестандартно для Django (ожидается метод экземпляра); хотя в данном случае работает, это хрупкое решение.

20. **Маршрут `path("user", include("user.urls"))` без завершающего слеша** в `config/urls.py` — потенциальная неоднозначность URL (хотя include обычно работает).

21. **Отсутствуют миграции для `user`** (приложение не имеет моделей, кроме алиаса) — нормально, но означает отсутствие профиля пользователя.

22. **Таблицы portfolio в `db.sqlite3` не соответствуют коду** — незавершенная/удаленная функциональность портфелей не реализована в текущем исходном коде.

23. **`Share.isin` не уникален**, возможны дубликаты ISIN при ручном вводе.

24. **`ticker` ограничен 10 символами** — может быть недостаточно для некоторых инструментов (зависит от биржи).

25. **Логирование**: настроен только логгер `main`; ошибки задач пишутся в `app.logs` (игнорируется git), но не централизованно.

26. **Статические файлы**: шаблоны ссылаются на CDN (Bootstrap, jQuery, Plotly) и локальные CSS; не настроены `STATIC_ROOT`/сборка статики для продакшена.

27. **В `dashboard/tests.py` тест `test_share_update_invalid` ожидает 400 при неполных данных**, что корректно для DRF; однако тесты не покрывают веб-представления, аутентификацию, Celery и сервисы.

## 9. Краткое резюме

Проект — Django-приложение для мониторинга акций с интеграцией Tinkoff Invest API, Celery-обновлением цен, Plotly-графиками и DRF API. Основная сущность — `Share`. Выявлены дефекты безопасности, несогласованности окружения, отсутствие аутентификации API, хрупкая обработка ошибок в регистрации/входе, потеря точности цен и расхождение БД с кодом.
" 
