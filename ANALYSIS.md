# ANALYSIS.md — Восстановление функциональных требований проекта "Investing Demo"

> Проект 분석 выполнен строго на основе фактического исходного кода. Допуски и догадки не используются. Каждое функциональное требование имеет ссылку на файл и строку (или блок) кода, который его реализует.

---

## 1. Назначение приложения

**Investing Demo** — веб-приложение для отслеживания акций (shares). Пользователь может просматривать список инструментов, смотреть детальную информацию с ценовым графиком (построенным через Plotly на основе данных Tinkoff Invest API), добавлять/редактировать/удалять инструменты (только после аутентификации), а также использовать REST API для полноценного CRUD над акциями. Котировки обновляются автоматически через Celery-задачу.

---

## 2. Технологический стек

| Компонент | Версия / значение | Источник |
|-----------|-------------------|----------|
| Python | Django 4.1.7 | `requirements.txt`, заголовок миграций |
| Веб-фреймворк | Django 4.1.7 | `config/settings.py` |
| REST API | Django REST Framework 3.14.0 | `requirements.txt` |
| Фильтрация API | django-filter 22.1 | `requirements.txt` |
| Формы | django-crispy-forms 2.0, crispy-bootstrap3 | `requirements.txt`, `settings.py` |
| Асинхронные задачи | Celery 5.2.7 | `requirements.txt`, `config/celery.py` |
| Брокер сообщений | Redis (`redis://127.0.0.1:6379/0`) | `settings.py` |
| СУБД | PostgreSQL (`psycopg2-binary` 2.9.5) | `settings.py`, `docker-compose.yml` |
| Внешний API | Tinkoff Invest (`tinkoff-investments` 0.2.0b50, `tinkoff` 0.1.1) | `requirements.txt`, `services/market_data.py`, `services/graph.py` |
| Визуализация | Plotly 5.13.1 | `requirements.txt`, `services/graph.py` |
| Шаблоны | Django Templates, Bootstrap 3 (crispy), Bootstrap 4 (CDN) | `settings.py`, шаблоны |
| Доп. пакеты | tenacity, grpcio, protobuf, pydantic, cachetools, plotly и др. | `requirements.txt` |

---

## 3. Архитектура и взаимодействие компонентов

### 3.1 Структура проекта

```
/config            — конфигурация Django (settings, urls, wsgi, asgi, celery)
/dashboard         — основное бизнес-приложение (акции, графики, API, задачи Celery)
/user              — приложение аутентификации (регистрация, вход, выход)
manage.py          — точка входа Django
docker-compose.yml — Postgres + Redis
requirements.txt   — зависимости
```

### 3.2 Взаимодействие компонентов (схема данных)

```
Tinkoff Invest API
        |
        | (add_shares команда — первичное заполнение)
        v
  Share (модель, PostgreSQL)
        ^
        | (Celery beat -> update_last_price каждые 10 сек)
        |
   Celery + Redis
        |
   (обновляет last_price, is_trend_high)

Пользователь (браузер)
        |
   HTTP-запросы
        |
   Django Views (HTML) <-> Шаблоны (для браузера)
   Django ViewSet (DRF) <-> JSON (для API клиентов)

Аутентификация: Django User (email как username) <-> user app (login/registration/logout)
```

### 3.3 Поток данных

1. Администратор запускает `python manage.py add_shares` — команда загружает список акций из Tinkoff API и создаёт записи в таблице `Share` (`get_or_create` по `figi`).
2. Celery Beat запускает задачу `update_last_price` каждые 10 секунд — для каждой акции запрашивает текущую цену из Tinkoff API и обновляет поля `last_price` и `is_trend_high`.
3. Пользователь (после входа) просматривает список акций, открывает детальную страницу с графиком цен за последние 180 дней, может создавать/редактировать/удалять акции.
4. DRF API предоставляет полный CRUD над акциями с фильтрацией, поиском и сортировкой.

---

## 4. Модель данных

### 4.1 Сущность `Share` (акция)

Расположение: `dashboard/models.py`

| Поле | Тип | Атрибуты | Назначение |
|------|-----|----------|------------|
| `id` | BigAutoField | primary_key (по умолчанию `DEFAULT_AUTO_FIELD`) | Идентификатор |
| `figi` | CharField | max_length=255, unique=True | FIGI-идентификатор инструмента (Tinkoff) |
| `isin` | CharField | max_length=255 | ISIN-код |
| `name` | CharField | max_length=255, verbose_name="Наименование компании" | Название компании |
| `ticker` | CharField | max_length=10, unique=True, verbose_name="Тикер" | Тикер |
| `currency` | CharField | max_length=20, verbose_name="Валюта" | Валюта котировки |
| `uid` | CharField | max_length=255, unique=True | UID инструмента (Tinkoff) |
| `last_price` | FloatField | blank=True, null=True, verbose_name="Текущая цена" | Последняя цена |
| `is_trend_high` | BooleanField | blank=True, null=True, verbose_name="Растет цена" | Флаг растения цены |
| `updated_at` | DateTimeField | auto_now=True, blank=True, null | Дата последнего обновления |

Meta: `verbose_name = "Акция"`, `verbose_name_plural = "Акции"`.

### 4.2 Пользователь

Используется стандартная модель `django.contrib.auth.models.User` (без кастомной модели пользователя). Электронная почта используется как логин (`username`).

### 4.3 Связи

Явных связей (ForeignKey, ManyToMany, OneToOne) между моделями в проекте нет. Связь пользователя с акциями отсутствует — все акции общие для всех пользователей.

### 4.4 Миграции

`dashboard/migrations/`: 7 файлов (от `0001_add_share` до `0007_add_updated_at`). Поле `updated_at` добавлено последним (миграция `0007`). `user/migrations/` содержит только `__init__.py` (используются миграции `django.contrib.auth`).

---

## 5. Механизмы обработки запросов и работы с БД

### 5.1 Маршрутизация URL

`config/urls.py`:
- `admin/` -> Django admin
- `""` -> `dashboard.urls` (корень)
- `"user"` -> `user.urls` (аутентификация)

`dashboard/urls.py` (`app_name = "dashboard"`):
- `""` -> `ShareListView` (имя `index`)
- `"<int:pk>"` -> `ShareDetailView` (имя `detail`)
- `"create"` -> `ShareCreateView` (имя `create`)
- `"update/<int:pk>"` -> `ShareUpdateView` (имя `update`)
- `"delete/<int:pk>"` -> `ShareDeleteView` (имя `delete`)
- `"api/"` -> `dashboard.api.urls`

`dashboard/api/v1/urls.py`: роутер DRF регистрирует `shares` -> `/api/v1/shares/` (list/create) и `/api/v1/shares/{id}/` (retrieve/update/destroy).

`user/urls.py` (`app_name = "user"`):
- `"login/"` -> `AuthView` (имя `auth`)
- `"registration/"` -> `RegistrationView` (имя `registration`)
- `"logout/"` -> `LogoutView` (имя `logout`)

### 5.2 Представления (Views)

#### HTML-представления (`dashboard/views.py`)

- `IsUserAuthenticatedMixin(UserPassesTestMixin)` — проверяет `request.user.is_authenticated`; при отказе перенаправляет на `dashboard:index`.
- `ShareListView(ListView)` — модель `Share`, шаблон `dashboard/list.html`, `paginate_by = 100`, сортировка по `name`.
- `ShareDetailView(View)` — статический метод `get(request, pk)`; `Share.objects.get(id=pk)` (без обработки 404); рендерит `dashboard/detail.html` с `plot_div` и `share`.
- `ShareCreateView(IsUserAuthenticatedMixin, CreateView)` — форма `ShareModelForm`, шаблон `dashboard/create.html`, редирект на `dashboard:index`.
- `ShareUpdateView(IsUserAuthenticatedMixin, UpdateView)` — модель `Share`, форма `ShareModelForm`, шаблон `dashboard/create.html`, редирект на `dashboard:index`.
- `ShareDeleteView(IsUserAuthenticatedMixin, DeleteView)` — модель `Share`, шаблон `dashboard/delete.html`, редирект на `dashboard:index`.

#### Аутентификация (`user/views.py`)

- `AuthView(View)` — GET рендерит `user/auth.html` с классом `AuthForm` (без инстанцирования); POST аутентифицирует по `email.lower()` и `password`, при успехе логинит и редиректит на `dashboard:index`, при неудаче показывает ошибку.
- `RegistrationView(View)` — GET рендерит `user/registration.html` с классом `RegistrationForm`; POST сохраняет пользователя, логинит, редиректит на `dashboard:index`.
- `LogoutView(View)` — GET разлогинивает, редиректит на `dashboard:index`.

#### API (`dashboard/api/v1/views.py`)

- `ShareFilter(filters.FilterSet)` — поля `name`, `ticker`.
- `ShareViewSet(viewsets.ModelViewSet)` — `queryset = Share.objects.all()`, фильтрация по `name`/`ticker`, поиск по `$name`, сортировка по `name`/`ticker`.

### 5.3 Формы

- `ShareModelForm(forms.ModelForm)` — `fields = "__all__"` для `Share`.
- `RegistrationForm(forms.Form)` — `email`, `password1`, `password2`; валидация совпадения паролей и уникальности email; `save()` создаёт пользователя через `create_user`.
- `AuthForm(forms.Form)` — `email`, `password`.

### 5.4 Сервисы и внешние API

- `dashboard/services/market_data.py` — `get_last_data(share)`: вызывает `client.market_data.get_last_prices(figi=[share.figi])`, возвращает `[resp.price.units, resp.time]`.
- `dashboard/services/graph.py` — `get_graph(share)`: загружает свечи за 180 дней (`Client(TINKOFF_TOKEN)`), строит Plotly-график (линия, красная, opacity 0.8), возвращает HTML-блок `div`.

### 5.5 Фоновые задачи (Celery)

`dashboard/tasks.py` — `update_last_price()`:
- загружает все `Share`;
- для каждой вызывает `get_last_data(share)`;
- сравнивает `share.last_price > last_price` для определения `is_trend_high` (при ошибке — `True`);
- обновляет через `Share.objects.filter(id=share.id).update(...)`.

`config/celery.py` — beat schedule: задача `dashboard.tasks.update_last_price` каждые 10.0 секунд (имя `"add-every-5-min"`).

### 5.6 Management-команда

`dashboard/management/commands/add_shares.py` — `Command(BaseCommand)`: загружает инструменты через `client.instruments.shares()` и создаёт `Share.objects.get_or_create(...)`.

---

## 6. Функциональные требования

Ниже приведён восстановленный список функциональных требований. Каждое требование опирается на конкретный участок исходного кода.

### Требования к данным и модели

1. **Система должна хранить информацию об акциях (Share) с полями:** `figi` (уникальный), `isin`, `name`, `ticker` (уникальный), `currency`, `uid` (уникальный), `last_price`, `is_trend_high`, `updated_at`.
   *Подтверждение:* `dashboard/models.py` — модель `Share`, поля с `unique=True` на `figi`, `ticker`, `uid`; `verbose_name` на русском языке.

2. **Поля `last_price` и `is_trend_high` должны быть опциональными (могут быть NULL).**
   *Подтверждение:* `dashboard/models.py` — `blank=True, null=True` для `last_price` и `is_trend_high`.

3. **Дата последнего обновления акции должна устанавливаться автоматически при каждом сохранении.**
   *Подтверждение:* `dashboard/models.py` — `updated_at = DateTimeField(auto_now=True)`.

4. **Уникальность FIGI, тикера и UID должна гарантироваться на уровне БД.**
   *Подтверждение:* `dashboard/models.py` — `unique=True` на полях `figi`, `ticker`, `uid`; миграции `0002_update_share.py` и `0003_add_uuid.py`.

### Требования к пользовательскому интерфейсу (HTML)

5. **Неавторизованный пользователь может просматривать список акций с пагинацией (100 на страницу), отсортированный по названию.**
   *Подтверждение:* `dashboard/views.py` — `ShareListView` (`paginate_by = 100`, `ordering = ["name"]`), шаблон `dashboard/templates/dashboard/list.html` с `page_obj`.

6. **Список акций должен отображать для каждой акции: тикер, название, ISIN, текущую цену и валюту, а также индикатор тренда (цвет фона в зависимости от `is_trend_high`).**
   *Подтверждение:* `dashboard/templates/dashboard/list.html` — таблица с колонками Ticker, Name, ISIN, цена; зелёный фон при `is_trend_high`, красный/палевый в противном случае.

7. **Неавторизованный пользователь может просматривать детальную страницу акции с названием, текущей ценой, валютой, датой обновления и ценовым графиком за последние 180 дней.**
   *Подтверждение:* `dashboard/views.py` — `ShareDetailView.get()`; `dashboard/services/graph.py` — `get_graph()` загружает свечи за `now() - timedelta(days=180)`; шаблон `dashboard/templates/dashboard/detail.html` с `{% autoescape off %}{{ plot_div }}`.

8. **Кнопки редактирования и удаления в списке акций должны отображаться только авторизованным пользователям.**
   *Подтверждение:* `dashboard/templates/dashboard/list.html` — кнопки Edit/Delete обёрнуты в `{% if user.is_authenticated %}`; кнопка "Добавить" также под условием авторизации.

9. **Авторизованный пользователь может создать новую акцию через форму со всеми полями модели.**
   *Подтверждение:* `dashboard/views.py` — `ShareCreateView` с `ShareModelForm` (`fields = "__all__"`), шаблон `dashboard/templates/dashboard/create.html`.

10. **Авторизованный пользователь может редактировать существующую акцию через ту же форму.**
    *Подтверждение:* `dashboard/views.py` — `ShareUpdateView` с `ShareModelForm`, шаблон `dashboard/templates/dashboard/create.html`.

11. **Авторизованный пользователь может удалить акцию после подтверждения.**
    *Подтверждение:* `dashboard/views.py` — `ShareDeleteView`, шаблон `dashboard/templates/dashboard/delete.html` с текстом подтверждения.

12. **После успешного создания, обновления или удаления акции пользователь должен перенаправляться на список акций.**
    *Подтверждение:* `dashboard/views.py` — `success_url = reverse_lazy("dashboard:index")` во всех трёх представлениях.

### Требования к аутентификации

13. **Пользователь должен иметь возможность зарегистрироваться, указав email, пароль и подтверждение пароля.**
    *Подтверждение:* `user/views.py` — `RegistrationView`; `user/forms.py` — `RegistrationForm` с полями `email`, `password1`, `password2`.

14. **Пароли при регистрации должны совпадать; email должен быть уникальным.**
    *Подтверждение:* `user/forms.py` — `RegistrationForm.clean()` проверяет `password1 == password2` и `User.objects.filter(email=email)`.

15. **Пользователь должен иметь возможность войти, указав email и пароль.**
    *Подтверждение:* `user/views.py` — `AuthView.post()` вызывает `authenticate(username=email.lower(), password=...)`.

16. **Пользователь должен иметь возможность выйти из системы.**
    *Подтверждение:* `user/views.py` — `LogoutView.get()` вызывает `logout(request)`.

17. **После успешного входа или регистрации пользователь перенаправляется на список акций.**
    *Подтверждение:* `user/views.py` — `AuthView` и `RegistrationView` редиректят на `reverse("dashboard:index")`.

18. **Электронная почта используется в качестве логина (username) при аутентификации.**
    *Подтверждение:* `user/views.py` — `username=form.data["email"].lower()`; `user/forms.py` — `create_user(email, email, password)`.

### Требования к REST API

19. **Система должна предоставлять REST API для полного CRUD над акциями (список, создание, чтение, обновление, удаление).**
    *Подтверждение:* `dashboard/api/v1/views.py` — `ShareViewSet(viewsets.ModelViewSet)`; `dashboard/api/v1/urls.py` — роутер регистрирует `shares`.

20. **API должен поддерживать фильтрацию акций по названию и тикеру.**
    *Подтверждение:* `dashboard/api/v1/views.py` — `ShareFilter` с полями `("name", "ticker")`, `filterset_class = ShareFilter`.

21. **API должен поддерживать поиск по названию акции.**
    *Подтверждение:* `dashboard/api/v1/views.py` — `search_fields = ["$name"]`, `SearchFilter` в `filter_backends`.

22. **API должен поддерживать сортировку по названию и тикеру.**
    *Подтверждение:* `dashboard/api/v1/views.py` — `ordering_fields = ["name", "ticker"]`, `OrderingFilter` в `filter_backends`.

23. **API должен использовать пагинацию LimitOffset с размером страницы 100.**
    *Подтверждение:* `config/settings.py` — `REST_FRAMEWORK` с `DEFAULT_PAGINATION_CLASS = LimitOffsetPagination`, `PAGE_SIZE = 100`.

24. **Сериализатор API должен включать поля: id, figi, isin, name, ticker, currency, last_price, is_trend_high, updated_at.**
    *Подтверждение:* `dashboard/api/v1/serializer.py` — `ShareSerializer` с указанными полями.

### Требования к обновлению котировок

25. **Система должна периодически обновлять текущие цены акций и флаг роста/падения цены через фоновую задачу Celery.**
    *Подтверждение:* `config/celery.py` — `beat_schedule` с задачей `dashboard.tasks.update_last_price` каждые 10.0 секунд; `dashboard/tasks.py` — `update_last_price()`.

26. **Цена акции должна браться из Tinkoff Invest API (поле `units` из `get_last_prices`).**
    *Подтверждение:* `dashboard/services/market_data.py` — `get_last_data()` вызывает `client.market_data.get_last_prices(figi=[...])`, возвращает `resp.price.units`.

27. **Флаг `is_trend_high` должен устанавливаться в `True`, если новая цена выше старой, и в `False` — если ниже.**
    *Подтверждение:* `dashboard/tasks.py` — сравнение `share.last_price > last_price` для определения `is_trend_high`.

28. **Дата обновления (`updated_at`) должна меняться при обновлении цены через Celery-задачу.**
    *Подтверждение:* `dashboard/tasks.py` — `Share.objects.filter(id=share.id).update(last_price=..., is_trend_high=...)` triggers `auto_now` на `updated_at`.

### Требования к заполнению справочника

29. **Система должна предоставлять команду управления для первичного заполнения справочника акций из Tinkoff Invest API.**
    *Подтверждение:* `dashboard/management/commands/add_shares.py` — `Command` вызывает `client.instruments.shares()` и `Share.objects.get_or_create(...)`.

30. **При заполнении справочника должны создаваться или обновляться записи по полям figi, name, isin, ticker, currency, uid.**
    *Подтверждение:* `dashboard/management/commands/add_shares.py` — `get_or_create(figi=..., name=..., isin=..., ticker=..., currency=..., uid=...)`.

---

## 7. Неоднозначности, противоречия и дефекты реализации

Ниже перечислены проблемы, выявленные при анализе кода. Они **не являются** функциональными требованиями, а являются дефектами или неясностями.

### 7.1 Критические проблемы конфигурации

1. **`SECRET_KEY` пустой** (`config/settings.py`) — угроза безопасности, защита CSRF и подписание куки не работают корректно.
2. **`TINKOFF_TOKEN` пустой** (`config/settings.py`) — все вызовы к Tinkoff API (`add_shares`, `update_last_price`, `get_graph`) будут падать с ошибкой авторизации.
3. **`DEBUG = True` и `ALLOWED_HOSTS = []`** — небезопасно для продакшена; приложение не примет запросы с произвольных хостов.

### 7.2 Дефекты в обработке запросов и представлениях

4. **`ShareDetailView` использует `Share.objects.get(id=pk)` без обработки `DoesNotExist`** (`dashboard/views.py`) — при несуществующем `pk` вернётся 500 вместо 404. В то же время API корректно возвращает 404 (подтверждено тестом `test_share_detail_invalid`).
5. **`AuthView.get()` и `RegistrationView.get()` передают форму как класс, а не как экземпляр** (`user/views.py`) — в шаблоне `{{ form.as_p }}` или `{% crispy form %}` могут возникнуть ошибки рендеринга.
6. **`RegistrationForm.clean()` обращается к `self.cleaned_data` без предварительной проверки наличия полей** (`user/forms.py`) — при отсутствии одного из полей может возникнуть `KeyError` или валидация пропустит ошибки отдельных полей.
7. **Регистрация через `RegistrationForm` не использует `ModelForm` и не вызывает `is_valid()` корректно во всех путях** — в `RegistrationView.post()` проверяется `form.is_valid()`, но `clean()` возвращает пользователя, а не очищенные данные, что нестандартно для Django.

### 7.3 Дефекты в фоновых задачах и сервисах

8. **В задаче `update_last_price` при `last_price is None` сравнение `share.last_price > last_price` выбросит `TypeError`** (`dashboard/tasks.py`) — широкий `except` перехватывает его и устанавливает `is_trend_high = True`, что искажает данные.
9. **Имя задачи в beat schedule `"add-every-5-min"` contradиктуется интервалом `10.0` секунд** (`config/celery.py`) — описание не соответствует фактическому расписанию.
10. **`get_last_data` возвращает только `resp.price.units`, игнорируя дробную часть (nano)** (`dashboard/services/market_data.py`) — теряется точность цены.
11. **`get_graph` использует только `candle.close.units`, игнорируя nano** (`dashboard/services/graph.py`) — теряется точность графических данных.
12. **В `get_graph` имя серии на графике жёстко задано как `"test"`** (`dashboard/services/graph.py`) — неинформативно.

### 7.4 Дефекты миграций

13. **Миграция `0004_add_last_price.py` содержит опечатки:** `ticker verbose_name="Ти"` (обрезано) и `name verbose_name="Валюта"` (неверно) — исправлены только в последующих миграциях `0005` и `0006`.

### 7.5 Архитектурные и конcepтуальные неясности

14. **Отсутствует связь между пользователем и акциями** — нет модели портфеля, watchlist, или favourites; все акции общие для всех пользователей. Неясно, зачем требуется аутентификация для создания/редактирования акций, если они общие.
15. **Не указано, кто и как должен заполнять справочник акций** — команда `add_shares` требует ручного запуска; нет автоматического первичного импорта при развёртывании.
16. **Отсутствует админка для приложения `user`** — `user/admin.py` не существует.
17. **`TINKOFF_TOKEN` хранится в `settings.py` в открытом виде** — нет использования переменных окружения (`.env` отсутствует, хотя упомянут в `.gitignore`).
18. **Тесты покрывают только API, не покрывают HTML-представления и задачи Celery** — `dashboard/tests.py` содержит 12 тестов, все на `APITestCase`.

### 7.6 Локализация и строки

19. **В `ShareDeleteView` заголовок "Удаление задачи"** (`dashboard/views.py`) — несоответствие предметной области (удаляется акция, а не задача).
20. **В шаблонах используется смесь Bootstrap 3 (crispy_bootstrap3) и Bootstrap 4 (CDN в шаблонах)** — возможны визуальные конфликты стилей.

---

## 8. Итог

Проект "Investing Demo" реализует базовый функционал отслеживания акций с данными от Tinkoff Invest: HTML-интерфейс (список, детальная страница с графиком, CRUD для авторизованных), аутентификация (email как логин), REST API с фильтрацией/поиском/сортировкой, фоновое обновление цен через Celery и команду первичного импорта. Основные дефекты касаются конфигурации безопасности (пустые ключи), обработки исключений (отсутствие 404 в детальном представлении, широкий except в задаче Celery), потери точности цен (игнорирование nano) и отсутствия связи пользователя с акциями.
