# Используем базовый образ Python
FROM python:3.9-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем зависимости приложения (файлы requirements.txt)
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем всё содержимое текущей директории внутрь контейнера в /app
COPY . .

# Путь к файлу модели внутри контейнера
ENV MODEL_PATH /app/model/market_prediction_model.pkl

# Установка параметров Python для UTF-8 и буферизации
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Экспонируем порт 8000, на который будет доступен FastAPI
EXPOSE 8000

# Команда для запуска FastAPI приложения
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
