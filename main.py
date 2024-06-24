
import joblib
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List


# Путь к файлу модели
model_path = os.path.join(os.path.dirname(__file__), 'model', 'market_prediction_model.pkl')

# Загрузка модели
model = joblib.load(model_path)

# Определение FastAPI приложения
app = FastAPI()

# Модель данных для запроса
class NewsRequest(BaseModel):
    news: List[str]

# Эндпоинт для предсказания
@app.post("/predict")
def predict(news_request: NewsRequest):
    predictions = []
    for news in news_request.news:
        # Ваш код для предсказания на основе загруженной модели
        prediction = "рост"  # Пример
        predictions.append({"news": news, "prediction": prediction})
    return {"predictions": predictions}
