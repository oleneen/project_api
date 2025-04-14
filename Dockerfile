# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Указываем порт, который будет использоваться
EXPOSE 8001

# Команда для запуска сервера (с указанием порта 8001)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]