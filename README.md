# Реализация

В проекте реализованы два микросервиса:

- `auth_service` на порту `8000`: регистрация и аутентификация пользователей.
- `posts_service` на порту `8001`: создание сообщений по валидному JWT.

PostgreSQL запускается отдельным контейнером и содержит таблицы `users` и `messages`.

## Запуск

```bash
docker compose up --build
```

## Запросы для Postman

### Регистрация

`POST http://localhost:8000/register`

```json
{
  "email": "user@example.com",
  "password": "StrongPass1"
}
```

При успешной регистрации возвращается пустой ответ с кодом `201`.

### Аутентификация

`POST http://localhost:8000/login`

```json
{
  "email": "user@example.com",
  "password": "StrongPass1"
}
```

При успешной аутентификации возвращается код `200` и JWT:

```json
{
  "token": "<jwt>"
}
```

### Создание сообщения

`POST http://localhost:8001/messages`

Заголовок:

```text
Authorization: Bearer <jwt>
```

Тело:

```json
{
  "message": "Hello from authenticated user"
}
```

При успешном сохранении сообщения возвращается пустой ответ с кодом `201`.
