import os
from dotenv import load_dotenv, find_dotenv, dotenv_values
from openai import OpenAI       # Импортируем только новую библиотеку
import json
import base64  # Добавляем для работы с изображениями
import requests  # Добавляем для работы с API
import io  # Добавляем для работы с файлами
from datetime import datetime  # Добавляем для работы с датами
import time  # Добавляем для работы с временем

# Улучшенная загрузка переменных окружения
env_path = find_dotenv()
if env_path:
    try:
# Загрузка переменных окружения
        load_dotenv(dotenv_path=env_path, override=True)
        
        # Альтернативный способ загрузки
        config = dotenv_values(env_path)
        for key, value in config.items():
            if key not in os.environ:
                os.environ[key] = value
    except Exception as e:
        print(f"Ошибка при загрузке .env файла: {str(e)}")
else:
    print("Файл .env не найден, переменные окружения не загружены")

class WarDiaryAnalyzer:
    def __init__(self):
        """
        Инициализация анализатора военных дневников.
        Загружает API ключи и конфигурирует клиент OpenAI.
        """
        # Загружаем переменные окружения из файла .env
        load_dotenv()
        
        # Улучшенная загрузка переменных окружения
        self.api_key = os.environ.get('OPENAI_API_KEY')
        self.suno_api_key = os.environ.get('SUNOAI_API_KEY')
        
        # Если ключи не найдены в переменных окружения, пробуем получить их через getenv
        if not self.api_key:
            self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.suno_api_key:
            self.suno_api_key = os.getenv('SUNOAI_API_KEY')
        
        print(f"Инициализация WarDiaryAnalyzer, API ключ OpenAI {'найден' if self.api_key else 'НЕ НАЙДЕН'}")
        print(f"API ключ Suno {'найден' if self.suno_api_key else 'НЕ НАЙДЕН'}")
        print(f"Содержимое переменной SUNOAI_API_KEY: '{self.suno_api_key}'")
        print(f"Текущий рабочий каталог: {os.getcwd()}")
        print(f"Проверка, существует ли файл .env: {os.path.exists('.env')}")
        
        if not self.api_key:
            raise ValueError("Пожалуйста, установите OPENAI_API_KEY в файле .env")
        
        # Конфигурируем клиент OpenAI
        self.client = OpenAI(api_key=self.api_key)

    def analyze_emotions(self, text):
        """
        Глубокий анализ эмоций в тексте с помощью GPT.
        
        Args:
            text (str): Входной текст для анализа
            
        Returns:
            dict: Словарь с результатами анализа эмоций
        """
        if len(text) > 8000:
            print(f"ВНИМАНИЕ: Текст слишком длинный ({len(text)} символов), что может вызвать таймаут")
            # Обрезаем текст, если он слишком длинный
            text = text[:8000] + "..."
            
        prompt = f"""
        Проанализируйте эмоциональное состояние автора в следующем отрывке из военного дневника.
        Учитывайте исторический контекст войны и психологическое состояние участника событий.
        
        Текст дневника:
        {text}
        
        Пожалуйста, определите:
        1. Основные эмоции (страх, надежда, отчаяние, решимость и т.д.)
        2. Интенсивность каждой эмоции по шкале от 1 до 10
        3. Общий эмоциональный тон
        4. Скрытые эмоциональные мотивы
        5. Отношение к происходящему
        6. Тематический анализ военных деталей:
           - Военные персонажи и роли (командиры, солдаты, медсестры и т.д.)
           - Места сражений и локации (фронт, траншеи, города и т.д.)
           - Военная техника и оружие (танки, винтовки, артиллерия и т.д.)
           - Аспекты фронтовой жизни (еда, отдых, письма домой и т.д.)
           - Исторические события и операции (наступления, оборона и т.д.)
        
        Верните ответ СТРОГО в следующем формате JSON (без дополнительных пояснений):
        {{
            "primary_emotions": [
                {{"emotion": "название_эмоции", "intensity": число_от_1_до_10}},
                ...
            ],
            "emotional_tone": "описание_общего_тона",
            "hidden_motives": ["мотив1", "мотив2", ...],
            "attitude": "отношение_к_происходящему",
            "thematic_analysis": {{
                "military_characters": ["роль1", "роль2", ...],
                "battle_locations": ["место1", "место2", ...],
                "war_equipment": ["техника1", "техника2", ...],
                "frontline_life": ["аспект1", "аспект2", ...],
                "historical_events": ["событие1", "событие2", ...]
            }}
        }}
        """

        try:
            print("Отправка запроса к OpenAI API для анализа эмоций...")
            import time
            start_time = time.time()
            
            # Отправляем запрос через новый API
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Вы - опытный военный психолог, специализирующийся на анализе военных дневников и воспоминаний. Всегда возвращайте ответ в формате JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                timeout=120  # Увеличиваем таймаут до 120 секунд
            )
            
            elapsed_time = time.time() - start_time
            print(f"Ответ от OpenAI получен за {elapsed_time:.2f} секунд")
            
            # Получаем текст ответа и пытаемся распарсить его как JSON
            response_text = response.choices[0].message.content.strip()
            
            try:
                result = json.loads(response_text)
                print("JSON успешно распарсен")
                return result
            except json.JSONDecodeError as e:
                print(f"Ошибка парсинга JSON: {str(e)}")
                print(f"Полученный текст: {response_text[:100]}...")
                
                # Попытка исправить неправильный JSON
                try:
                    # Иногда OpenAI возвращает JSON с дополнительным текстом до или после
                    import re
                    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    if json_match:
                        fixed_json = json_match.group(0)
                        result = json.loads(fixed_json)
                        print("JSON успешно исправлен и распарсен")
                        return result
                except Exception:
                    pass
                
                return {
                    "error": f"Ошибка при парсинге JSON ответа: {str(e)}",
                    "primary_emotions": [],
                    "emotional_tone": "неизвестно",
                    "hidden_motives": [],
                    "attitude": "неизвестно"
                }
        except json.JSONDecodeError as e:
            print(f"JSONDecodeError: {str(e)}")
            return {
                "error": f"Ошибка при парсинге JSON ответа: {str(e)}",
                "primary_emotions": [],
                "emotional_tone": "неизвестно",
                "hidden_motives": [],
                "attitude": "неизвестно"
            }
        except Exception as e:
            print(f"Ошибка при анализе эмоций: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                "error": f"Ошибка при анализе эмоций: {str(e)}",
                "primary_emotions": [],
                "emotional_tone": "неизвестно",
                "hidden_motives": [],
                "attitude": "неизвестно"
            }

    def generate_literary_work(self, diary_text, emotion_analysis):
        """
        Генерация художественного произведения на основе дневникового текста
        и его эмоционального анализа.
        
        Args:
            diary_text (str): Исходный текст дневника
            emotion_analysis (dict): Результаты анализа эмоций
            
        Returns:
            str: Сгенерированное художественное произведение
        """
        prompt = f"""
        На основе следующего дневникового текста времен войны и его эмоционального анализа создайте художественное произведение.
        
        Исходный текст:
        {diary_text}
        
        Эмоциональный анализ:
        - Основные эмоции: {', '.join([f"{e['emotion']} ({e['intensity']})" for e in emotion_analysis['primary_emotions']])}
        - Общий тон: {emotion_analysis['emotional_tone']}
        - Скрытые мотивы: {', '.join(emotion_analysis['hidden_motives'])}
        - Отношение к происходящему: {emotion_analysis['attitude']}
        
        Создайте небольшое художественное произведение, которое:
        1. Передает те же эмоции и их интенсивность
        2. Сохраняет исторический контекст
        3. Раскрывает внутренний мир автора
        4. Использует художественные приемы для усиления эмоционального воздействия
        5. Сохраняет атмосферу военного времени
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Вы - талантливый писатель, специализирующийся на военной прозе. Ваш стиль сочетает реализм с глубоким психологизмом."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Произошла ошибка при генерации текста: {str(e)}"

    def generate_image(self, prompt, size="1024x1024", model="gpt-4"):
        """
        Генерирует изображение через Chat Completions API с использованием function_call 
        для вызова Image Generation API.
        
        Args:
            prompt (str): Текстовое описание для генерации изображения
            size (str): Размер изображения: "256x256", "512x512", "1024x1024"
            model (str): Модель GPT для обработки запроса
            
        Returns:
            dict: Словарь с URL сгенерированного изображения или информацией об ошибке
        """
        try:
            # Логируем только начало промпта для отладки, но используем полный промпт
            print(f"Генерация изображения с запросом (начало): {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
            
            # Проверяем наличие слов, которые могут вызвать фильтрацию содержимого
            risky_words = ["война", "военный", "битва", "сражение", "атака", "бой", "труп", 
                           "оружие", "убитый", "раненый", "насилие", "кровь", "взрыв", "бомба",
                           "war", "battle", "violence", "dead", "kill", "blood", "weapon", "gun",
                           "attack", "corpse", "victim", "bomb", "explosive", "combat", "fight"]
            
            extremely_violent_words = [
                "кровь", "пытки", "расстрел", "убил", "пули", "труп", "пытка", 
                "изуродован", "оторвало", "blood", "torture", "shot", "killed", "bullets",
                "corpse", "mutilated", "dismembered", "gore", "visceral"
            ]
            
            # Проверяем на наличие очень жестокого содержимого
            if any(word in prompt.lower() for word in extremely_violent_words):
                print("Обнаружены явные описания насилия в промпте, сразу возвращаем ошибку политики содержания")
                raise Exception(f"Запрос содержит описания насилия, которые запрещены политикой содержания OpenAI.")
            
            # Если в промпте есть потенциально рискованные слова, добавляем префикс, но не пытаемся явно обойти фильтры
            if any(word in prompt.lower() for word in risky_words):
                print("Обнаружены потенциально рискованные слова в промпте, добавляем префикс")
                # Используем менее агрессивный префикс
                prompt = f"Create a symbolic historical scene that avoids explicit violence: {prompt}"
            
            # Определяем функцию для генерации изображения
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "generate_image",
                        "description": "Генерирует изображение на основе детального описания",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "detailed_prompt": {
                                    "type": "string",
                                    "description": "Подробное описание изображения для генерации"
                                },
                                "style": {
                                    "type": "string",
                                    "description": "Художественный стиль изображения",
                                    "enum": ["realistic", "artistic", "cinematic", "documentary"]
                                },
                                "mood": {
                                    "type": "string",
                                    "description": "Эмоциональное настроение изображения",
                                    "enum": ["dramatic", "solemn", "tense", "hopeful", "melancholic"]
                                }
                            },
                            "required": ["detailed_prompt"]
                        }
                    }
                }
            ]
            
            # Вызываем Chat Completions API для создания обогащенного промпта
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Ты - эксперт по визуальному искусству с глубоким пониманием истории. "
                                                "Твоя задача - преобразовать описание сцены в детальный визуальный образ "
                                                "для художественной иллюстрации. Избегай любых упоминаний насилия, "
                                                "военных сцен, оружия или боевых действий."},
                    {"role": "user", "content": f"Мне нужно создать визуальную иллюстрацию на основе следующего описания. "
                                              f"Опиши эту сцену, добавь визуальные элементы, настроение и атмосферу "
                                              f"без упоминания войны, оружия или насилия:\n\n{prompt}"}
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "generate_image"}}
            )
            
            # Извлекаем результат function call
            function_call = response.choices[0].message.tool_calls[0]
            arguments_text = function_call.function.arguments
            
            # Расширенный метод очистки аргументов от недопустимых символов
            try:
                # Сначала пробуем прямой парсинг
                try:
                    function_args = json.loads(arguments_text)
                    print("JSON успешно разобран напрямую")
                except json.JSONDecodeError as e:
                    print(f"Ошибка прямого парсинга JSON: {e}")
                    
                    # Шаг 1: Удаляем все управляющие символы, кроме разрешенных
                    cleaned_args = ''.join(ch for ch in arguments_text if 
                                        (ord(ch) >= 32 or ch in ['\n', '\r', '\t']))
                    
                    # Шаг 2: Заменяем экранированные кавычки и другие проблемные последовательности
                    cleaned_args = cleaned_args.replace('\\"', '"')
                    cleaned_args = cleaned_args.replace('\\\\', '\\')
                    
                    # Шаг 3: Удаляем невидимые символы Unicode, которые могут вызывать проблемы
                    import re
                    cleaned_args = re.sub(r'[\u0000-\u001F\u007F-\u009F]', '', cleaned_args)
                    
                    # Шаг 4: Проверяем, что JSON имеет правильную структуру
                    if not (cleaned_args.strip().startswith('{') and cleaned_args.strip().endswith('}')):
                        # Если нет, пытаемся найти JSON-объект с помощью регулярного выражения
                        json_match = re.search(r'\{.*\}', cleaned_args, re.DOTALL)
                        if json_match:
                            cleaned_args = json_match.group(0)
                    
                    print(f"Очищенные аргументы (начало): {cleaned_args[:100]}{'...' if len(cleaned_args) > 100 else ''}")
                    
                    # Пробуем парсить очищенные аргументы
                    try:
                        function_args = json.loads(cleaned_args)
                        print("JSON успешно разобран после очистки")
                    except json.JSONDecodeError as e2:
                        print(f"Ошибка парсинга JSON после очистки: {e2}")
                        
                        # Пробуем восстановить промпт напрямую из ответа
                        try:
                            # Ищем часть с описанием изображения
                            prompt_match = re.search(r'"detailed_prompt"\s*:\s*"([^"]*)"', cleaned_args)
                            if prompt_match:
                                detailed_prompt = prompt_match.group(1)
                                print(f"Найден промпт с помощью regex (начало): {detailed_prompt[:50]}{'...' if len(detailed_prompt) > 50 else ''}")
                                function_args = {
                                    "detailed_prompt": detailed_prompt,
                                    "style": "realistic",
                                    "mood": "dramatic"
                                }
                            else:
                                # Если не удалось найти по regex, используем оригинальный промпт
                                print("Не удалось извлечь промпт из JSON, используем оригинальный промпт")
                                function_args = {
                                    "detailed_prompt": f"Create a realistic illustration inspired by historical context: {prompt}",
                                    "style": "realistic",
                                    "mood": "dramatic"
                                }
                        except Exception as e3:
                            print(f"Ошибка при извлечении промпта: {e3}")
                            raise e2  # Пробрасываем исходную ошибку JSON для обработки ниже
            except json.JSONDecodeError as e:
                print(f"Критическая ошибка при парсинге JSON аргументов: {e}")
                print(f"Начало аргументов: {arguments_text[:100]}{'...' if len(arguments_text) > 100 else ''}")
                
                # Создаем безопасные аргументы
                function_args = {
                    "detailed_prompt": f"Create a detailed artistic illustration of a historical scene",
                    "style": "realistic",
                    "mood": "dramatic"
                }
                print("Используем безопасные аргументы")
            except Exception as e:
                print(f"Неожиданная ошибка при обработке аргументов: {e}")
                function_args = {
                    "detailed_prompt": f"Create an artistic historical illustration",
                    "style": "realistic",
                    "mood": "atmospheric"
                }
            
            # Получаем обогащенный промпт
            enhanced_prompt = function_args.get('detailed_prompt')
            style = function_args.get('style', 'realistic')
            mood = function_args.get('mood', 'dramatic')
            
            # Проверяем детальный промпт на наличие крайне жестоких слов
            if any(word in enhanced_prompt.lower() for word in extremely_violent_words):
                print("Обнаружены экстремально жестокие слова в обогащенном промпте, прерываем генерацию")
                raise Exception("Запрос содержит описания насилия, которые запрещены политикой содержания OpenAI.")
            
            # Если в обогащенном промпте есть рискованные слова, мягко корректируем его
            if any(word in enhanced_prompt.lower() for word in risky_words):
                print("Обнаружены рискованные слова в обогащенном промпте, делаем промпт более абстрактным")
                
                # Делаем промпт более абстрактным и символическим
                enhanced_prompt = (enhanced_prompt.replace("war", "historical period")
                                  .replace("battle", "event")
                                  .replace("weapon", "object")
                                  .replace("combat", "scene")
                                  .replace("violent", "emotional")
                                  .replace("военный", "исторический")
                                  .replace("война", "история")
                                  .replace("оружие", "предмет")
                                  .replace("бой", "эпизод"))
                
                # Добавляем направление для символической интерпретации
                enhanced_prompt = "Create a symbolic, metaphorical image of historical context: " + enhanced_prompt
            
            # Добавляем стиль и настроение к промпту
            final_prompt = f"{enhanced_prompt} Style: {style}. Mood: {mood}."
            # Логируем только начало для отладки, но передаем полный промпт
            print(f"Обогащенный промпт (начало): {final_prompt[:150]}{'...' if len(final_prompt) > 150 else ''}")
            
            # Теперь вызываем Image Generation API с улучшенным промптом и таймаутом
            try:
                image_response = self.client.images.generate(
                    model="dall-e-3",  # Используем современную модель
                    prompt=final_prompt,
                    size=size,
                    quality="standard",  # Баланс между качеством и стоимостью
                    n=1,
                    timeout=60  # Добавляем таймаут 60 секунд
                )
            except Exception as dalle_error:
                error_message = str(dalle_error)
                print(f"Ошибка DALL-E API: {error_message}")
                
                # Проверяем ошибки, связанные с политикой контента
                if "content_policy_violation" in error_message or "image_generation_user_error" in error_message or "violates" in error_message.lower():
                    print("Обнаружено нарушение политики содержания при вызове DALL-E API")
                    raise Exception(f"Запрос отклонен политикой содержания OpenAI: {error_message}")
                else:
                    # Другие ошибки пробрасываем дальше
                    raise dalle_error
            
            # Получаем URL сгенерированного изображения
            image_url = image_response.data[0].url
            print(f"Изображение успешно сгенерировано, URL: {image_url[:60]}...")
            
            # Скачиваем изображение и сохраняем его локально
            img_filename = f"image_{int(datetime.now().timestamp())}.png"
            img_path = os.path.join("static", "generated_images", img_filename)
            
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            
            try:
                # Скачиваем изображение
                print(f"Скачивание изображения с URL: {image_url}")
                img_data = requests.get(image_url).content
                
                # Проверяем, что данные получены
                if not img_data:
                    print("Предупреждение: получены пустые данные изображения")
                    return {
                        'success': True,
                        'image_url': image_url,  # Возвращаем только внешний URL
                        'local_path': "",
                        'filename': ""
                    }
                
                # Сохраняем изображение
                with open(img_path, 'wb') as img_file:
                    img_file.write(img_data)
                
                # Проверяем, что файл создан и имеет размер
                if os.path.exists(img_path) and os.path.getsize(img_path) > 0:
                    print(f"Изображение успешно сохранено: {img_path}")
                    
                    # Формируем URL-путь для веб-сервера (всегда используем прямые слеши для web)
                    web_path = img_path.replace("\\", "/")
                    
                    return {
                        'success': True,
                        'image_url': image_url,
                        'local_path': web_path,
                        'filename': img_filename
                    }
                else:
                    print(f"Предупреждение: файл не создан или пустой: {img_path}")
                    return {
                        'success': True,
                        'image_url': image_url,  # Возвращаем только внешний URL
                        'local_path': "",
                        'filename': ""
                    }
            except Exception as img_error:
                print(f"Ошибка при сохранении изображения: {str(img_error)}")
                import traceback
                traceback.print_exc()
                
                # Возвращаем только внешний URL, если не удалось сохранить локально
                return {
                    'success': True,
                    'image_url': image_url,
                    'local_path': "",
                    'filename': ""
                }
            
        except Exception as e:
            print(f"Ошибка при генерации изображения: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_message = str(e)
            
            # Проверяем ошибки, связанные с политикой контента
            if any(term in error_message.lower() for term in 
                  ["content_policy_violation", "policy", "violates", "content policy", "image_generation_user_error"]):
                return {
                    'success': False,
                    'error': "Запрос отклонен политикой контента OpenAI",
                    'type': 'content_policy_violation',
                    'can_regenerate_safe': True,
                    'technical_error': error_message
                }
            else:
                return {
                    'success': False,
                    'error': str(e)
                }

    def generate_image_from_diary(self, diary_text, emotion_analysis=None):
        """
        Генерирует изображение на основе текста дневника и его эмоционального анализа.
        
        Args:
            diary_text (str): Текст дневника
            emotion_analysis (dict, optional): Результаты эмоционального анализа
            
        Returns:
            dict: Результат генерации изображения
        """
        try:
            # Если текст слишком длинный, обрезаем его
            if len(diary_text) > 4000:
                diary_text = diary_text[:4000]
            
            # Сначала проверяем текст на очень жестокое содержимое, чтобы не пытаться генерировать изображение
            extremely_violent_words = [
                "кровь", "пытки", "расстреляли", "убили", "пули", "трупы", "пытка", 
                "изуродованы", "оторвало", "blood", "torture", "shot", "killed", "bullets",
                "corpses", "mutilated", "dismembered", "gore", "visceral"
            ]
            
            # Проверяем наличие очень жестокого содержимого
            contains_extreme_violence = any(word in diary_text.lower() for word in extremely_violent_words)
            
            # Если обнаружен очень жестокий контент, сразу возвращаем ошибку политики содержания
            if contains_extreme_violence:
                print("Обнаружены явные описания насилия, сразу возвращаем ошибку политики содержания")
                return {
                    'success': False,
                    'error': "Текст содержит описания, которые невозможно визуализировать согласно политике OpenAI.",
                    'type': 'content_policy_violation',
                    'can_regenerate_safe': True,
                    'original_prompt_failed': True,
                    'technical_error': "Текст содержит явные описания насилия, что запрещено политикой OpenAI."
                }
            
            # Минимально фильтруем текст для предотвращения очевидных нарушений
            filtered_text = (diary_text.replace("трупы", "павшие")
                            .replace("убитых", "пострадавших")
                            .replace("мертвых", "павших"))
            
            # Создаем промпт на основе дневникового текста и эмоционального анализа
            if emotion_analysis and 'primary_emotions' in emotion_analysis:
                # Используем эмоциональный анализ для улучшения запроса
                emotions_text = ', '.join([f"{e['emotion']} ({e['intensity']})" for e in emotion_analysis['primary_emotions'][:3]])
                tone = emotion_analysis.get('emotional_tone', '')
                
                # Создаем промпт, который включает прямое цитирование дневника
                direct_prompt = f"""
                Создайте художественную иллюстрацию, основанную на этом фрагменте военного дневника:
                
                "{filtered_text}"
                
                Основные эмоции: {emotions_text}
                Общий тон: {tone}
                
                Изображение должно передать атмосферу и эмоциональное состояние автора дневника. 
                Стиль: реалистичная масляная живопись с драматическим освещением.
                """
            else:
                # Если анализа эмоций нет, используем только текст дневника
                direct_prompt = f"""
                Создайте художественную иллюстрацию, основанную на этом фрагменте военного дневника:
                
                "{filtered_text}"
                
                Изображение должно передать атмосферу и исторический контекст, описанный в дневнике.
                Стиль: реалистичная масляная живопись с драматическим освещением.
                """
            
            # Убедимся, что директория для изображений существует
            os.makedirs(os.path.join('static', 'generated_images'), exist_ok=True)
            
            print(f"Начинаем запрос к API для генерации изображения...")
            
            # Пытаемся сгенерировать изображение
            try:
                result = self.generate_image(direct_prompt)
                print(f"Ответ от API получен для изображения: {result}")
                return result
            except Exception as direct_image_error:
                error_message = str(direct_image_error)
                print(f"Ошибка при генерации изображения: {error_message}")
                
                # Проверяем, связана ли ошибка с модерацией контента
                is_content_policy_error = (
                    "image_generation_user_error" in error_message or
                    "content policy" in error_message.lower() or
                    "violates" in error_message.lower() or
                    "policy violation" in error_message.lower()
                )
                
                if is_content_policy_error:
                    # ВАЖНО: В данном случае мы ВСЕГДА возвращаем ошибку нарушения политики контента,
                    # чтобы фронтенд мог показать пользователю предупреждение и предложить
                    # генерацию безопасной версии изображения
                    return {
                        'success': False,
                        'error': "Текст содержит описания, которые невозможно визуализировать согласно политике OpenAI.",
                        'type': 'content_policy_violation',
                        'can_regenerate_safe': True,
                        'original_prompt_failed': True,  # Новый флаг, указывающий что исходный промпт не прошел
                        'technical_error': error_message
                    }
                else:
                    # Для других технических ошибок возвращаем общее сообщение
                    return {
                        'success': False,
                        'error': f"Техническая ошибка при генерации изображения: {error_message}",
                        'technical_error': error_message
                    }
        
        except Exception as e:
            print(f"Ошибка при генерации изображения из дневника: {str(e)}")
            error_message = str(e)
            
            # Очищаем сообщение об ошибке для пользователя
            if "image_generation_user_error" in error_message:
                user_error = "Содержимое дневника не подходит для генерации изображения. Попробуйте другой текст или используйте более нейтральные формулировки."
            else:
                user_error = "Произошла техническая ошибка при генерации изображения. Пожалуйста, попробуйте позже."
                
            return {
                'success': False,
                'error': user_error,
                'technical_error': error_message  # Сохраняем оригинальную ошибку для логов
            }

    def generate_safe_image_from_diary(self, diary_text, emotion_analysis=None):
        """
        Генерирует безопасную изображение на основе текста дневника и эмоционального анализа,
        используя символический и метафорический подход без прямых отсылок к сценам насилия.
        
        Args:
            diary_text (str): Текст дневника
            emotion_analysis (dict, optional): Результаты эмоционального анализа
            
        Returns:
            dict: Результат генерации изображения
        """
        try:
            # Подготавливаем данные для безопасного промпта
            emotions_text = ''
            tone = 'reflective'
            
            if emotion_analysis and 'primary_emotions' in emotion_analysis:
                emotions_text = ', '.join([f"{e['emotion']}" for e in emotion_analysis['primary_emotions'][:3]])
                tone = emotion_analysis.get('emotional_tone', 'reflective')
            
            # Создаем безопасный промпт, который все же остается тематически связанным с военными дневниками
            prompt = f"""
            I NEED to create a meaningful symbolic illustration that captures the essence of historical diary entries:
            
            Create a poignant artistic illustration that symbolically represents memories from the Great Patriotic War (1941-1945).
            The scene should evoke a {tone} mood and convey {emotions_text} emotions without showing any violence.
            
            Include these symbolic elements:
            - A worn leather diary or journal with handwritten pages in Russian/Cyrillic
            - Soviet military personal mementos from 1941-1945 (old photographs, medals, compass, pocket watch)
            - A window looking out on an Eastern Front landscape with weather that reflects the emotional tone
            - A chair with a Soviet military uniform or greatcoat hung over it (no weapons or violent imagery)
            - Subtle period elements that suggest the 1941-1945 Soviet wartime historical context
            
            Style: Realistic oil painting with dramatic lighting and rich textures.
            Focus on creating an emotionally resonant scene that tells a story through objects and atmosphere.
            The image should feel authentic to the Soviet World War II period but avoid any depictions of conflict, weapons, injuries or violence.
            """
            
            print("Генерация безопасного изображения с символическим подходом...")
            
            # Генерируем изображение с таймаутом
            try:
                result = self.generate_image(prompt)
                print(f"Ответ от API получен для безопасного изображения: {result}")
                
                # Добавляем метку, что это альтернативная/безопасная версия
                if result.get('success'):
                    result['is_safe_alternative'] = True
                
                return result
            except Exception as image_error:
                print(f"Ошибка при генерации безопасного изображения: {str(image_error)}")
                
                # Если даже этот безопасный промпт не прошел, пробуем супер-безопасный вариант
                try:
                    print("Пробуем ультра-безопасный вариант генерации...")
                    super_safe_prompt = """
                    Create a symbolic artistic painting showing an old Russian/Soviet journal and personal items from 1941-1945 Great Patriotic War 
                    on a wooden desk next to a window. The window shows a peaceful Eastern European landscape at sunset. 
                    Include subtle elements that suggest Soviet wartime context - medals, propaganda poster on wall, etc.
                    Style: detailed oil painting with warm lighting.
                    """
                    
                    super_safe_result = self.generate_image(super_safe_prompt)
                    print(f"Ответ от API получен для ультра-безопасного изображения: {super_safe_result}")
                    
                    if super_safe_result.get('success'):
                        super_safe_result['is_safe_alternative'] = True
                        return super_safe_result
                except Exception as super_safe_error:
                    print(f"Ошибка при ультра-безопасной генерации: {str(super_safe_error)}")
                
                # Если все попытки провалились
                return {
                    'success': False,
                    'error': f"Не удалось создать даже безопасную версию изображения: {str(image_error)}",
                    'is_safe_alternative': True
                }
                
        except Exception as e:
            print(f"Ошибка при подготовке безопасного изображения: {str(e)}")
            return {
                'success': False,
                'error': "Произошла ошибка при создании безопасной версии изображения",
                'is_safe_alternative': True
            }
    
    def _create_music_title(self, tone, style, prefix="War Diary"):
        """
        Создает заголовок музыкального трека с учетом ограничения в 80 символов.
        
        Args:
            tone (str): Эмоциональный тон
            style (str): Стиль музыки
            prefix (str, optional): Префикс заголовка. По умолчанию "War Diary"
            
        Returns:
            str: Заголовок, не превышающий 80 символов
        """
        # Ограничиваем длину тона и стиля для предотвращения слишком длинных заголовков
        max_tone_len = 20
        max_style_len = 30
        
        # Обрезаем длинные значения
        short_tone = tone.capitalize()
        if len(short_tone) > max_tone_len:
            short_tone = short_tone[:max_tone_len-3] + "..."
            
        short_style = style
        if len(short_style) > max_style_len:
            short_style = short_style[:max_style_len-3] + "..."
            
        # Формируем заголовок
        title = f"{prefix}: {short_tone} {short_style}"
        
        # Проверяем общую длину и обрезаем при необходимости
        if len(title) > 80:
            title = title[:77] + "..."
            
        print(f"Сформирован заголовок музыки: '{title}' ({len(title)} символов)")
        return title

    def _validate_music_style(self, style, model="V4_5"):
        """
        Проверяет и при необходимости обрезает стиль музыки согласно ограничениям Suno API.
        
        Args:
            style (str): Стиль музыки
            model (str): Используемая модель (влияет на ограничения)
            
        Returns:
            str: Проверенный и при необходимости сокращенный стиль
        """
        # Ограничения по модели
        if model in ["V3_5", "V4"]:
            max_length = 200
        else:  # V4_5
            max_length = 1000
            
        # Проверяем длину стиля
        if len(style) > max_length:
            short_style = style[:max_length-3] + "..."
            print(f"Стиль музыки обрезан с {len(style)} до {len(short_style)} символов")
            return short_style
        
        return style
        
    def _validate_music_prompt(self, prompt, model="V4_5"):
        """
        Проверяет и при необходимости обрезает промпт для генерации музыки согласно ограничениям Suno API.
        
        Args:
            prompt (str): Промпт для генерации музыки
            model (str): Используемая модель (влияет на ограничения)
            
        Returns:
            str: Проверенный и при необходимости сокращенный промпт
        """
        # Ограничения по модели
        if model in ["V3_5", "V4"]:
            max_length = 3000
        else:  # V4_5
            max_length = 5000
            
        # Проверяем длину промпта
        if len(prompt) > max_length:
            short_prompt = prompt[:max_length-3] + "..."
            print(f"Промпт для генерации музыки обрезан с {len(prompt)} до {len(short_prompt)} символов")
            return short_prompt
        
        return prompt

    def generate_music(self, text, emotion_analysis=None, base_url=None, wait_for_result=False):
        """
        Генерирует музыкальное произведение на основе текста дневника и эмоционального анализа.
        Если wait_for_result=False, только отправляет запрос и возвращает task_id.
        """
        try:
            print(f"Генерация музыки на основе текста длиной {len(text)} символов")
            if not self.suno_api_key:
                print("API ключ Suno не найден. Используем запасной метод.")
                return self._fallback_music_generation(text, emotion_analysis, base_url=base_url)
            if len(text) > 4000:
                text = text[:4000]
            model = "V4_5"
            style, mood, tempo, instruments = self._determine_music_params(emotion_analysis)
            style = self._validate_music_style(style, model)
            if emotion_analysis and 'primary_emotions' in emotion_analysis:
                emotions = [e['emotion'] for e in emotion_analysis['primary_emotions']]
                tone = emotion_analysis.get('emotional_tone', 'reflective')
                music_title = self._create_music_title(tone, style, "War Diary")
                music_prompt = f"Create high-quality {mood} {style} music that captures the following emotions: {', '.join(emotions[:3])}. "
                music_prompt += f"The music should reflect a {tone} tone of wartime experiences. "
                music_prompt += f"{tempo} rhythm with {instruments} as primary instruments. "
                music_prompt += f"Based on a war diary that describes: {text[:300]}..."
                music_prompt = self._validate_music_prompt(music_prompt, model)
                negative_tags = "lyrics, vocals, singing, spoken words, voice"
            else:
                music_title = "War Diary Reflection"
                music_prompt = f"Create high-quality emotional {style} music that captures the mood of a war diary. "
                music_prompt += f"The music should be {mood} and reflect the atmosphere of wartime experiences. "
                music_prompt += f"{tempo} with {instruments} as primary instruments. "
                music_prompt += f"Context from the diary: {text[:300]}..."
                music_prompt = self._validate_music_prompt(music_prompt, model)
                negative_tags = "lyrics, vocals, singing, spoken words, voice"
            print(f"Формирование запроса к Suno API: {music_prompt[:150]}...")
            if base_url:
                base_url = base_url.rstrip('/')
                callback_url = f"{base_url}/music_callback"
            else:
                callback_url = None
            request_data = {
                "prompt": music_prompt,
                "style": style,
                "title": music_title,
                "customMode": True,
                "instrumental": True,
                "model": model,
                "negativeTags": negative_tags,
                "callBackUrl": callback_url  # только здесь ссылка!
            }
            if callback_url:
                request_data["callBackUrl"] = callback_url
            headers = {
                "Authorization": f"Bearer {self.suno_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            print(f"Отправка запроса к Suno API с данными: {json.dumps(request_data, ensure_ascii=False)[:200]}...")
            response = requests.post(
                "https://apibox.erweima.ai/api/v1/generate",
                json=request_data,
                headers=headers
            )
            print(f"Получен ответ от Suno API, код: {response.status_code}")
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print(f"Ответ API: {json.dumps(response_data, ensure_ascii=False)[:500]}")
                except Exception as e:
                    print(f"Ошибка при разборе JSON ответа: {str(e)}")
                    return self._fallback_music_generation(text, emotion_analysis, error=f"Ошибка разбора ответа: {str(e)}", base_url=base_url)
                if response_data.get('code') != 200:
                    error_msg = f"API вернул ошибку: {response_data.get('msg', 'Неизвестная ошибка')}"
                    print(error_msg)
                    return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)
                if 'data' not in response_data:
                    error_msg = "В ответе API отсутствует поле 'data'"
                    print(error_msg)
                    return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)
                data = response_data.get('data')
                if not isinstance(data, dict):
                    error_msg = f"Поле 'data' не является словарем: {type(data)}"
                    print(error_msg)
                    return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)
                task_id = data.get('taskId')
                if not task_id:
                    error_msg = "Не удалось получить task_id от Suno API"
                    print(error_msg)
                    return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)
                print(f"Запрос к Suno API успешно отправлен, task_id: {task_id}")
                # Сохраняем метаданные о задаче в файл
                music_metadata = {
                    'task_id': task_id,
                    'title': music_title,
                    'prompt': music_prompt,
                    'style': style,
                    'mood': mood,
                    'tempo': tempo,
                    'instruments': instruments,
                    'emotions': [e['emotion'] for e in emotion_analysis['primary_emotions']][:3] if emotion_analysis and 'primary_emotions' in emotion_analysis else [],
                    'emotional_tone': emotion_analysis.get('emotional_tone', '') if emotion_analysis else '',
                    'status': 'processing',
                    'created_at': datetime.now().isoformat(),
                    'callback_url': callback_url,
                }
                os.makedirs(os.path.join('static', 'generated_music'), exist_ok=True)
                metadata_filename = f"music_metadata_{task_id}.json"
                metadata_path = os.path.join('static', 'generated_music', metadata_filename)
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(music_metadata, f, ensure_ascii=False, indent=2)
                music_description = f"Сгенерирована {mood} {style} музыка, отражающая "
                music_description += f"{', '.join(music_metadata['emotions'] if music_metadata['emotions'] else ['различные'])} эмоции. "
                music_description += f"Использует {instruments}."
                return {
                    'success': True,
                    'status': 'processing',
                    'task_id': task_id,
                    'music_description': music_description,
                    'audio_url': None,
                    'metadata': music_metadata,
                    'metadata_path': metadata_path
                }
            else:
                error_msg = f"Ошибка Suno API: {response.status_code}"
                try:
                    error_msg += f" - {response.text}"
                except:
                    pass
                print(error_msg)
                return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)
        except Exception as e:
            print(f"Ошибка при генерации музыки: {str(e)}")
            import traceback
            traceback.print_exc()
            return self._fallback_music_generation(text, emotion_analysis, error=str(e), base_url=base_url)
    
    def _check_music_status_via_api(self, task_id):
        """
        Выполняет прямой запрос к Suno API для проверки статуса задачи.
        Добавляет задержку перед первой проверкой и пробует альтернативные endpoint'ы.
        """
        if not self.suno_api_key or not task_id:
            return {
                'success': False,
                'error': 'Отсутствует API ключ или ID задачи',
                'api_status': 'error'
            }
        
        try:
            headers = {
                "Authorization": f"Bearer {self.suno_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Задержка перед первой проверкой (важно для Suno)
            print(f"Жду 10 секунд перед первой проверкой статуса задачи {task_id}...")
            time.sleep(10)
            
            # Список endpoint'ов для проверки статуса
            endpoints = [
                f"https://apibox.erweima.ai/api/v1/tasks/{task_id}",
                f"https://apibox.erweima.ai/api/v1/get?taskId={task_id}",
                f"https://apibox.erweima.ai/api/v1/music/{task_id}"
            ]
            
            delays = [0, 5, 10, 15, 20, 30]  # Интервалы между попытками
            last_error = None
            for attempt in range(len(delays)):
                if attempt > 0:
                    print(f"Повторная попытка проверки статуса через {delays[attempt]} секунд...")
                    time.sleep(delays[attempt])
                for url in endpoints:
                    print(f"Проверяю статус задачи через endpoint: {url}")
                    try:
                        response = requests.get(url, headers=headers, timeout=30)
                        print(f"Ответ [{response.status_code}] от {url}: {response.text[:300]}")
                        if response.status_code == 200:
                            try:
                                result = response.json()
                                print(f"JSON-ответ: {json.dumps(result, ensure_ascii=False)[:300]}")
                                api_code = result.get('code')
                                if api_code == 200:
                                    data = result.get('data', {})
                                    status = data.get('status', 'unknown')
                                    is_complete = status == 'complete' or data.get('isFinish', False)
                                    tracks = data.get('tracks', [])
                                    audio_url = ""
                                    stream_url = ""
                                    if tracks and isinstance(tracks, list) and len(tracks) > 0:
                                        first_track = tracks[0]
                                        audio_url = (first_track.get('audio_url') or 
                                                     first_track.get('audioUrl') or 
                                                     first_track.get('url') or 
                                                     '')
                                        stream_url = (first_track.get('stream_audio_url') or 
                                                     first_track.get('streamAudioUrl') or 
                                                     first_track.get('streamUrl') or 
                                                     first_track.get('stream_url') or 
                                                     '')
                                    else:
                                        audio_url = (data.get('audio_url') or 
                                                    data.get('audioUrl') or 
                                                    data.get('url') or 
                                                    '')
                                        stream_url = (data.get('stream_audio_url') or 
                                                     data.get('streamAudioUrl') or 
                                                     data.get('streamUrl') or 
                                                     data.get('stream_url') or 
                                                     '')
                                    # Пробуем получить дополнительные данные
                                    results = data.get('results', {})
                                    if results and isinstance(results, dict):
                                        if not audio_url:
                                            audio_url = (results.get('audio_url') or 
                                                        results.get('audioUrl') or 
                                                        results.get('url') or 
                                                        '')
                                        if not stream_url:
                                            stream_url = (results.get('stream_audio_url') or 
                                                         results.get('streamAudioUrl') or 
                                                         results.get('streamUrl') or 
                                                         results.get('stream_url') or 
                                                         '')
                                    if is_complete and not audio_url and not stream_url:
                                        print("Внимание: Задача отмечена как завершенная, но нет URL аудио")
                                        is_complete = False
                                    return {
                                        'success': True,
                                        'api_status': status,
                                        'is_complete': is_complete,
                                        'audio_url': audio_url,
                                        'stream_url': stream_url,
                                        'data': data
                                    }
                                else:
                                    error_msg = result.get('msg', f"Код ошибки API: {api_code}")
                                    print(f"API вернул ошибку {api_code}: {error_msg}")
                                    last_error = error_msg
                                    continue
                            except Exception as e:
                                print(f"Ошибка при обработке ответа API: {str(e)}")
                                last_error = str(e)
                                continue
                        elif response.status_code == 404:
                            print(f"Endpoint {url} вернул 404 (не найдено) — задача, возможно, ещё в очереди")
                            # Возвращаем статус 'processing', если не истёк таймаут
                            return {
                                'success': True,
                                'api_status': 'processing',
                                'is_complete': False,
                                'audio_url': '',
                                'stream_url': '',
                                'data': {},
                                'message': 'Задача ещё в очереди на генерацию (Suno API вернул 404)'
                            }
                        else:
                            error_msg = f"Ошибка запроса к API: {response.status_code} - {response.text}"
                            print(error_msg)
                            last_error = error_msg
                            continue
                    except Exception as e:
                        print(f"Ошибка при запросе к {url}: {str(e)}")
                        last_error = str(e)
                        continue
            # Если все попытки не увенчались успехом
            return {
                'success': False,
                'error': last_error or 'Не удалось получить статус задачи Suno',
                'api_status': 'error'
            }
        except Exception as e:
            print(f"Ошибка подключения к API: {str(e)}")
            return {
                'success': False,
                'error': f"Ошибка подключения к API: {str(e)}",
                'api_status': 'error'
            }
    
    def _check_music_generation_status(self, task_id):
        """
        Проверяет статус задачи генерации музыки по task_id.
        Сначала проверяет через API, затем проверяет локальные метаданные.
        
        Args:
            task_id (str): Идентификатор задачи
            
        Returns:
            dict: Информация о статусе задачи и результаты, если задача завершена
        """
        try:
            # Проверка наличия task_id
            if not task_id:
                return {
                    'success': False,
                    'status': 'error',
                    'message': "Отсутствует идентификатор задачи (task_id)"
                }
            
            # Сначала проверяем статус через API
            api_status = self._check_music_status_via_api(task_id)
            
            # Проверяем, что api_status не None
            if api_status is None:
                print(f"API вернул None для задачи {task_id}")
                api_status = {
                    'success': False,
                    'error': 'API вернул пустой ответ',
                    'api_status': 'error'
                }
            
            # Если API вернул статус "error", считаем задачу неуспешной
            if api_status.get('api_status') == 'error' or (not api_status.get('success') and api_status.get('error')):
                print(f"API вернул статус 'error' для задачи {task_id}")
                
                # Обновляем метаданные
                metadata_path = os.path.join('static', 'generated_music', f"music_metadata_{task_id}.json")
                
                # Пытаемся загрузить существующие метаданные
                metadata = {}
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except Exception as e:
                        print(f"Ошибка при чтении метаданных: {str(e)}")
                
                # Обновляем метаданные с данными из API
                metadata['status'] = 'error'
                metadata['last_update'] = datetime.now().isoformat()
                metadata['error_message'] = api_status.get('error', "Ошибка API Suno при генерации музыки")
                metadata['api_status'] = 'error'
                metadata['api_data'] = api_status.get('data', {})
                
                # Сохраняем обновленные метаданные
                try:
                    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata, f, ensure_ascii=False, indent=2)
                    print(f"Метаданные обновлены с ошибкой: {metadata_path}")
                except Exception as e:
                    print(f"Ошибка при сохранении метаданных: {str(e)}")
                
                return {
                    'success': False,
                    'status': 'error',
                    'message': api_status.get('error', "API вернул ошибку при генерации музыки. Попробуйте снова."),
                    'task_id': task_id
                }
            
            # Если получили статус через API и он указывает на завершение задачи
            if api_status.get('success') and api_status.get('is_complete') and api_status.get('audio_url'):
                print(f"Задача {task_id} завершена по данным API")
                
                # Обновляем метаданные
                metadata_path = os.path.join('static', 'generated_music', f"music_metadata_{task_id}.json")
                
                # Пытаемся загрузить существующие метаданные
                metadata = {}
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except Exception as e:
                        print(f"Ошибка при чтении метаданных: {str(e)}")
                
                # Получаем URL аудио и другие данные
                audio_url = api_status.get('audio_url', '')
                stream_url = api_status.get('stream_url', '')
                
                # Скачиваем MP3 файл, если есть URL и файл еще не скачан
                local_audio_path = metadata.get('local_audio_path', '')
                local_audio_url = metadata.get('local_audio_url', '')
                
                # Если локальный аудиофайл указан, но не существует, очищаем путь
                if local_audio_path and not os.path.exists(local_audio_path):
                    print(f"Предупреждение: локальный аудиофайл {local_audio_path} не найден")
                    local_audio_path = ''
                    local_audio_url = ''
                
                # Формируем описание музыки
                music_description = f"Сгенерирована музыка в стиле {metadata.get('style', 'инструментальный')}."
                if 'mood' in metadata:
                    music_description += f" Настроение: {metadata.get('mood')}."
                if 'emotions' in metadata and metadata['emotions']:
                    music_description += f" Отражает эмоции: {', '.join(metadata['emotions'])}."
                
                return {
                    'success': True,
                    'status': 'complete',
                    'audio_url': audio_url,
                    'stream_url': stream_url,
                    'image_url': metadata.get('image_url', ''),
                    'local_audio_path': local_audio_path,
                    'local_audio_url': local_audio_url,
                    'local_image_path': metadata.get('local_image_path', ''),
                    'local_image_url': metadata.get('local_image_url', ''),
                    'title': metadata.get('title', ''),
                    'task_id': task_id,
                    'music_description': music_description,
                    'style': metadata.get('style', ''),
                    'mood': metadata.get('mood', ''),
                    'emotions': metadata.get('emotions', []),
                    'emotional_tone': metadata.get('emotional_tone', ''),
                    'is_music_ready': True if local_audio_path or audio_url else False
                }
            
            # Если API вернул ошибку, но не завершил задачу, используем локальные метаданные
            if not api_status.get('success') and api_status.get('error'):
                print(f"Ошибка API при проверке статуса задачи {task_id}: {api_status.get('error')}")
            
            # Если API не подтвердил завершение, проверяем локальные метаданные
            metadata_path = os.path.join('static', 'generated_music', f"music_metadata_{task_id}.json")
            if not os.path.exists(metadata_path):
                return {
                    'success': False,
                    'status': 'error',
                    'message': f"Метаданные для задачи {task_id} не найдены. Возможно, задача была удалена."
                }
            
            # Загружаем метаданные
            try:
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                    
                print(f"Загружены метаданные для задачи {task_id}: {json.dumps(metadata, ensure_ascii=False)[:500]}...")
            except Exception as e:
                print(f"Ошибка при чтении метаданных: {str(e)}")
                return {
                    'success': False,
                    'status': 'error',
                    'message': f"Ошибка при чтении метаданных: {str(e)}"
                }
            
            # Если в метаданных уже отмечено завершение, возвращаем результат
            if metadata.get('status') == 'complete' and (metadata.get('audio_url') or metadata.get('stream_url') or metadata.get('local_audio_path')):
                print(f"Задача {task_id} завершена по локальным метаданным")
                
                music_description = f"Сгенерирована музыка в стиле {metadata.get('style', 'инструментальный')}."
                if 'mood' in metadata:
                    music_description += f" Настроение: {metadata.get('mood')}."
                if 'emotions' in metadata and metadata['emotions']:
                    music_description += f" Отражает эмоции: {', '.join(metadata['emotions'])}."
                
                # Проверяем наличие локальных файлов
                local_audio_path = metadata.get('local_audio_path', '')
                local_audio_url = metadata.get('local_audio_url', '')
                
                # Если локальный аудиофайл указан, но не существует, очищаем путь
                if local_audio_path and not os.path.exists(local_audio_path):
                    print(f"Предупреждение: локальный аудиофайл {local_audio_path} не найден")
                    local_audio_path = ''
                    local_audio_url = ''
                
                return {
                    'success': True,
                    'status': 'complete',
                    'audio_url': metadata.get('audio_url', ''),
                    'stream_url': metadata.get('stream_url', ''),
                    'image_url': metadata.get('image_url', ''),
                    'embed_url': metadata.get('embed_url', ''),
                    'local_audio_path': local_audio_path,
                    'local_image_path': metadata.get('local_image_path', ''),
                    'local_audio_url': local_audio_url,
                    'local_image_url': metadata.get('local_image_url', ''),
                    'proxy_url': metadata.get('proxy_url', ''),
                    'title': metadata.get('title', ''),
                    'task_id': task_id,
                    'music_description': music_description,
                    'is_music_ready': True if local_audio_path or audio_url else False
                }
            
            # Если в метаданных статус ошибки, возвращаем ошибку
            if metadata.get('status') == 'error':
                print(f"Задача {task_id} завершилась с ошибкой по локальным метаданным")
                
                return {
                    'success': False,
                    'status': 'error',
                    'message': metadata.get('error_message', 'Произошла ошибка при генерации музыки'),
                    'task_id': task_id
                }
            
            # Проверяем сколько времени прошло с момента создания задачи
            current_time = datetime.now()
            created_at = datetime.fromisoformat(metadata.get('created_at', current_time.isoformat()))
            elapsed_seconds = (current_time - created_at).total_seconds()
            
            # Определяем максимальное время ожидания (15 минут)
            max_wait_time = 15 * 60  # секунд
            
            # Получаем текущий статус из метаданных
            status = metadata.get('status', 'processing')
            
            # Если превышено максимальное время ожидания, меняем статус на "timeout"
            if elapsed_seconds > max_wait_time and status == 'processing':
                print(f"Превышено время ожидания для задачи {task_id}: {elapsed_seconds:.2f} сек.")
                
                # Обновляем метаданные
                metadata['status'] = 'timeout'
                metadata['last_update'] = current_time.isoformat()
                
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                return {
                    'success': False,
                    'status': 'timeout',
                    'message': f"Превышено время ожидания ({max_wait_time//60} мин). Музыка не была сгенерирована.",
                    'task_id': task_id,
                    'music_description': metadata.get('music_description', 'Музыка не была сгенерирована.')
                }
            
            # Если задача в процессе, возвращаем статус
            print(f"Задача {task_id} в процессе выполнения, прошло {elapsed_seconds:.2f} сек.")
            
            # Оценка прогресса на основе времени выполнения (очень примерно)
            progress = min(95, int(elapsed_seconds / max_wait_time * 100))
            
            # Проверяем, показывает ли API статус ошибки (но задача все еще обрабатывается)
            api_status_value = "unknown"
            if api_status is not None:
                api_status_value = api_status.get('api_status', 'unknown') if api_status.get('success') else 'error'
            
            # Если API статус показывает ошибку, но мы до сих пор считаем задачу в процессе, 
            # устанавливаем флаг ошибки
            if api_status_value == 'error':
                return {
                    'success': False,
                    'status': 'error',
                    'message': 'API вернул ошибку. Генерация музыки не может быть завершена.',
                    'task_id': task_id,
                    'music_description': metadata.get('music_description', 'Музыка не была сгенерирована из-за ошибки API.')
                }
            
            # Если ни одно из условий не сработало, возвращаем статус "в процессе"
            return {
                'success': True,
                'status': 'processing',
                'message': f"Задача в процессе ({progress}% выполнено). Прошло {elapsed_seconds:.1f} сек.",
                'progress': progress,
                'task_id': task_id,
                'elapsed_seconds': elapsed_seconds,
                'music_description': metadata.get('music_description', 'Музыка генерируется...')
            }
            
        except Exception as e:
            print(f"Ошибка при проверке статуса генерации музыки: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'status': 'error',
                'message': str(e),
                'task_id': task_id
            }
    
    def _fallback_music_generation(self, text, emotion_analysis, error=None, base_url=None):
        """
        Запасной метод генерации музыки (например, если нет ключа или ошибка API)
        """
        print("Использование запасного метода генерации музыки через SUNA...")
        
        # Проверка параметров на None
        if emotion_analysis is None:
            emotion_analysis = {}
        
        # Выбираем модель
        model = "V4_5"  # Лучшая модель из доступных
        
        # Определяем параметры музыки на основе эмоционального анализа
        try:
            style, mood, tempo, instruments = self._determine_music_params(emotion_analysis)
        except Exception as e:
            print(f"Ошибка при определении параметров музыки: {str(e)}")
            # Установка значений по умолчанию при ошибке
            style = "Instrumental"
            mood = "reflective"
            tempo = "moderate"
            instruments = "piano and strings"
        
        # Проверяем длину стиля согласно ограничениям API
        style = self._validate_music_style(style, model)
        
        if not self.suno_api_key:
            print("\n\n====== ВНИМАНИЕ: SUNO API ключ не найден ======")
            print("Вы можете ввести ключ вручную для текущей сессии.")
            print("Либо добавьте SUNOAI_API_KEY=ваш_ключ в файл .env в корне проекта")
            temp_key = input("Введите SUNO API ключ (оставьте пустым, чтобы пропустить): ")
            if temp_key and temp_key.strip():
                self.suno_api_key = temp_key.strip()
                print("Ключ временно установлен для текущей сессии")
            else:
                print("Ключ не введен. Генерация музыки будет пропущена.")
                return {
                    'success': False,
                    'error': "API ключ SUNO не найден. Пожалуйста, добавьте SUNOAI_API_KEY в файл .env для генерации музыки."
                }
            
        try:
            # Формируем подходящий музыкальный запрос на основе эмоционального анализа
            emotions = []
            tone = "reflective"
            
            if emotion_analysis and isinstance(emotion_analysis, dict) and 'primary_emotions' in emotion_analysis:
                # Безопасное получение списка эмоций
                if isinstance(emotion_analysis['primary_emotions'], list):
                    emotions = [e.get('emotion', 'emotion') for e in emotion_analysis['primary_emotions'] if isinstance(e, dict)]
                tone = emotion_analysis.get('emotional_tone', 'reflective')
                
            # Используем вспомогательный метод для создания заголовка
            music_title = self._create_music_title(tone, style, "Diary Emotion")
            
            # Формируем детальный запрос для SUNA с учетом эмоций
            emotions_str = ', '.join(emotions[:3]) if emotions else 'varied emotions'
            
            # Подробное описание для лучшей музыкальной генерации
            music_prompt = f"Create high-quality {mood} {style} music that conveys {emotions_str}. "
            music_prompt += f"The piece should have a {tempo} rhythm with {instruments}. "
            music_prompt += f"The music should reflect emotions from a war diary with a {tone} tone. "
            music_prompt += f"No lyrics, just instrumental music that captures the emotional essence of a diary entry."
                
            # Проверяем длину промпта согласно ограничениям API
            music_prompt = self._validate_music_prompt(music_prompt, model)
                
            print(f"Формирование запроса к SUNA API: {music_prompt[:150]}...")
            
            # Подготовка параметров для SUNA API
            headers = {
                "Authorization": f"Bearer {self.suno_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Получаем текущий хост для callback URL
            base_url = "http://localhost:5000"  # Используем локальный URL по умолчанию
            
            # Создаем URL для обратного вызова
            callback_url = f"{base_url}/music_callback"
            
            # Формируем запрос к SUNA API с использованием лучшей модели
            request_data = {
                "prompt": music_prompt,
                "style": style,
                "title": music_title,
                "customMode": True,
                "instrumental": True,
                "model": model,
                "negativeTags": "lyrics, vocals, singing, spoken words, voice",
                # Оставляем callBackUrl пустым, так как для работы в локальной сети API не сможет отправить колбэк на localhost
                # Будем проверять статус через регулярные запросы
            }
            
            print(f"Отправка запроса к SUNA API с данными: {json.dumps(request_data, ensure_ascii=False)[:200]}...")
            
            # Отправляем запрос на генерацию музыки
            response = requests.post(
                "https://apibox.erweima.ai/api/v1/generate",
                json=request_data,
                headers=headers
            )
            
            print(f"Получен ответ от SUNA API, код: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Ответ API: {json.dumps(result, ensure_ascii=False)[:500]}")
                except Exception as e:
                    print(f"Ошибка при разборе JSON ответа: {str(e)}")
                    raise ValueError(f"Не удалось разобрать ответ от API: {str(e)}")
                
                # Проверяем, что result - это словарь
                if not isinstance(result, dict):
                    raise ValueError(f"Неверный формат ответа от API: {type(result)}")
                
                # Проверяем код ответа от API
                if result.get('code') != 200:
                    raise ValueError(f"API вернул ошибку: {result.get('msg', 'Неизвестная ошибка')}")
                
                # Проверяем наличие data
                if 'data' not in result:
                    raise ValueError("В ответе API отсутствует поле 'data'")
                
                # Получаем data и проверяем его тип
                data = result.get('data')
                if not isinstance(data, dict):
                    raise ValueError(f"Поле 'data' не является словарем: {type(data)}")
                
                # Получаем task_id
                task_id = data.get('taskId')
                if not task_id:
                    raise ValueError("Не удалось получить task_id от SUNA API")
                    
                print(f"Запрос на генерацию музыки отправлен, task_id: {task_id}")
                
                # Создаем директорию для сохранения метаданных
                os.makedirs(os.path.join('static', 'generated_music'), exist_ok=True)
                
                # Безопасное получение эмоций для метаданных
                emotion_list = []
                if emotion_analysis and isinstance(emotion_analysis, dict) and 'primary_emotions' in emotion_analysis:
                    if isinstance(emotion_analysis['primary_emotions'], list):
                        emotion_list = [e.get('emotion') for e in emotion_analysis['primary_emotions'][:3] 
                                        if isinstance(e, dict) and 'emotion' in e]
                
                # Получаем текущее время для отслеживания создания задачи
                current_time = datetime.now()
                
                # Метаданные музыки
                music_metadata = {
                    'title': music_title,
                    'style': style,
                    'mood': mood,
                    'tempo': tempo,
                    'instruments': instruments,
                    'emotions': emotion_list,
                    'emotional_tone': emotion_analysis.get('emotional_tone', '') if isinstance(emotion_analysis, dict) else '',
                    'status': 'processing',
                    'created_at': current_time.isoformat(),
                    'last_update': current_time.isoformat(),
                    'task_id': task_id,
                    'prompt': music_prompt,
                    'callback_url': callback_url,
                    'request': request_data,
                    'response': {
                        'code': result.get('code'),
                        'msg': result.get('msg'),
                        'taskId': task_id
                    }
                }
                
                # Сохраняем метаданные в файл
                metadata_filename = f"music_metadata_{task_id}.json"
                metadata_path = os.path.join('static', 'generated_music', metadata_filename)
                
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(music_metadata, f, ensure_ascii=False, indent=2)
                
                # Формируем описание музыки
                music_description = f"Генерируется {mood} {style} музыка"
                if emotions:
                    music_description += f", отражающая {', '.join(emotions[:3])}. "
                music_description += f"Используются инструменты: {instruments}."
                
                return {
                    'success': True,
                    'status': 'processing',
                    'task_id': task_id,
                    'music_description': music_description,
                    'metadata': music_metadata,
                    'metadata_path': metadata_path
                }
            else:
                # Обработка ошибок API
                error_msg = f"Ошибка API: {response.status_code}"
                try:
                    error_msg += f" - {response.text}"
                except:
                    pass
                
                print(error_msg)
                return {
                    'success': False,
                    'error': error_msg
                }
        except Exception as e:
            print(f"Ошибка при генерации музыки через запасной метод: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'error': f"Ошибка запасного метода: {str(e)}"
            }
    
    def _determine_music_params(self, emotion_analysis):
        """
        Определяет музыкальные параметры на основе эмоционального анализа.
        
        Args:
            emotion_analysis (dict): Эмоциональный анализ
            
        Returns:
            tuple: (стиль, настроение, темп, инструменты)
        """
        # Если нет анализа эмоций, возвращаем базовые параметры
        if not emotion_analysis or not isinstance(emotion_analysis, dict) or 'primary_emotions' not in emotion_analysis:
            return "Orchestral", "dramatic", "moderate", "orchestra and piano"
        
        # Безопасно получаем эмоции и их интенсивность
        emotions = []
        intensities = []
        
        try:
            primary_emotions = emotion_analysis.get('primary_emotions', [])
            if isinstance(primary_emotions, list) and primary_emotions:
                for e in primary_emotions:
                    if isinstance(e, dict):
                        if 'emotion' in e:
                            emotions.append(e['emotion'])
                        if 'intensity' in e and isinstance(e['intensity'], (int, float)):
                            intensities.append(e['intensity'])
        except Exception as e:
            print(f"Ошибка при извлечении эмоций: {str(e)}")
        
        if not emotions:
            # Если не удалось получить эмоции, используем значения по умолчанию
            return "Orchestral", "dramatic", "moderate", "orchestra and piano"
        
        avg_intensity = sum(intensities) / len(intensities) if intensities else 5
        
        try:
            # Определяем стиль музыки на основе эмоций
            style = self._determine_music_genre(emotions)
            
            # Определяем настроение
            if any(e.lower() in ['страх', 'ужас', 'тревога', 'fear', 'anxiety', 'panic', 'terror'] for e in emotions):
                mood = "tense"
            elif any(e.lower() in ['грусть', 'печаль', 'скорбь', 'sadness', 'grief', 'sorrow', 'melancholy'] for e in emotions):
                mood = "melancholic"
            elif any(e.lower() in ['надежда', 'радость', 'счастье', 'hope', 'joy', 'happiness'] for e in emotions):
                mood = "hopeful"
            elif any(e.lower() in ['гордость', 'отвага', 'мужество', 'courage', 'bravery', 'valor'] for e in emotions):
                mood = "heroic"
            else:
                mood = "dramatic"
            
            # Определяем темп
            tempo = self._determine_tempo(emotions, intensities)
            
            # Определяем инструменты
            instruments = self._determine_instruments(emotions)
            
            return style, mood, tempo, instruments
        except Exception as e:
            print(f"Ошибка при определении музыкальных параметров: {str(e)}")
            return "Orchestral", "dramatic", "moderate", "orchestra and piano"

    def _determine_music_genre(self, emotions):
        """Определяет жанр музыки на основе эмоций"""
        if any(e.lower() in ['страх', 'ужас', 'тревога', 'fear', 'anxiety', 'panic', 'terror'] for e in emotions):
            return "Cinematic Suspense"
        elif any(e.lower() in ['грусть', 'печаль', 'скорбь', 'sadness', 'grief', 'sorrow', 'melancholy'] for e in emotions):
            return "Neoclassical Piano"
        elif any(e.lower() in ['надежда', 'радость', 'hope', 'joy', 'happiness'] for e in emotions):
            return "Uplifting Orchestral"
        elif any(e.lower() in ['гордость', 'отвага', 'мужество', 'courage', 'bravery', 'valor'] for e in emotions):
            return "Epic Orchestral" 
        elif any(e.lower() in ['решимость', 'determination', 'resolve', 'conviction'] for e in emotions):
            return "Dramatic Orchestral"
        else:
            return "Dramatic Film Score"
    
    def _determine_tempo(self, emotions, intensities):
        """Определяет темп музыки на основе эмоций и их интенсивности"""
        avg_intensity = sum(intensities) / len(intensities) if intensities else 5
        
        if any(e.lower() in ['страх', 'fear', 'anxiety', 'panic', 'terror'] for e in emotions) and avg_intensity > 7:
            return "fast-paced and intense"
        elif any(e.lower() in ['грусть', 'печаль', 'sadness', 'grief', 'sorrow'] for e in emotions):
            return "slow and contemplative"
        elif any(e.lower() in ['гордость', 'отвага', 'courage', 'valor'] for e in emotions):
            return "steady and powerful"
        elif avg_intensity > 7:
            return "dynamic with building tension"
        else:
            return "moderate with emotional depth"
    
    def _determine_instruments(self, emotions):
        """Определяет инструменты на основе эмоций"""
        if any(e.lower() in ['страх', 'ужас', 'тревога', 'fear', 'anxiety', 'panic', 'terror'] for e in emotions):
            return "low strings and percussion"
        elif any(e.lower() in ['грусть', 'печаль', 'скорбь', 'sadness', 'grief', 'sorrow'] for e in emotions):
            return "cello and piano"
        elif any(e.lower() in ['надежда', 'hope', 'joy', 'happiness'] for e in emotions):
            return "strings and woodwinds"
        elif any(e.lower() in ['гордость', 'мужество', 'отвага', 'courage', 'bravery', 'heroism'] for e in emotions):
            return "brass and timpani"
        elif any(e.lower() in ['решимость', 'determination', 'resolve'] for e in emotions):
            return "brass and strings"
        else:
            return "full orchestra with piano accents"

    def process_diary(self, diary_text, generation_type='text'):
        """
        Основной метод для обработки текста дневника.
        
        Args:
            diary_text (str): Текст дневника для анализа
            generation_type (str): Тип генерации: 'text', 'image', 'music' или 'all'
            
        Returns:
            dict: Результаты анализа и генерации
        """
        try:
            print(f"Начало обработки дневника длиной {len(diary_text)} символов")
            
            # Анализ эмоций с помощью GPT
            emotions = self.analyze_emotions(diary_text)
            print(f"Эмоциональный анализ завершен: {emotions.keys()}")
            
            # Проверка наличия ошибок в анализе эмоций
            if 'error' in emotions and emotions['error']:
                print(f"Ошибка при анализе эмоций: {emotions['error']}")
                return {
                    'error': emotions['error'],
                    'status': 'failed',
                    'emotion_analysis': emotions,
                    'generated_literary_work': "Не удалось сгенерировать произведение из-за ошибки анализа эмоций."
                }
            
            # Результаты всегда включают оригинальный текст и эмоциональный анализ
            result = {
                'original_text': diary_text,
                'emotion_analysis': emotions,
            }
            
            # Генерация выбранного типа контента
            if generation_type in ['text', 'all']:
                # Генерация художественного произведения
                print("Начало генерации художественного произведения")
                generated_text = self.generate_literary_work(diary_text, emotions)
                print(f"Генерация завершена, длина текста: {len(generated_text)}")
                result['generated_literary_work'] = generated_text
            
            if generation_type in ['image', 'all']:
                # Генерация изображения
                print("Начало генерации изображения")
                image_result = self.generate_image_from_diary(diary_text, emotions)
                print(f"Генерация изображения завершена: {image_result['success']}")
                result['generated_image'] = image_result
            
            if generation_type in ['music', 'all']:
                # Генерация музыки
                print("Начало генерации музыки")
                music_result = self.generate_music(diary_text, emotions)
                print(f"Генерация музыки завершена: {music_result['success']}")
                result['generated_music'] = music_result
            
            return result
            
        except Exception as e:
            print(f"Критическая ошибка в process_diary: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'error': str(e),
                'status': 'failed',
                'emotion_analysis': {
                    'primary_emotions': [],
                    'emotional_tone': 'не определено',
                    'hidden_motives': [],
                    'attitude': 'не определено'
                },
                'generated_literary_work': f"Произошла ошибка при обработке текста: {str(e)}",
                'generated_image': {
                    'success': False,
                    'error': str(e)
                },
                'generated_music': {
                    'success': False,
                    'error': str(e)
                }
            }

    def _process_callback_data(self, callback_data):
        """
        Обрабатывает данные из callback от Suno API.
        Сохраняет метаданные и аудиофайл.
        """
        try:
            task_id = callback_data.get('task_id')
            data_items = callback_data.get('data', [])
            
            if not data_items or not isinstance(data_items, list) or len(data_items) == 0:
                return {
                    'success': False,
                    'error': 'Отсутствуют данные о сгенерированной музыке в callback',
                    'task_id': task_id
                }
            
            # Берем первый элемент из списка (обычно генерируется только один трек)
            item = data_items[0]
            
            audio_url = item.get('audio_url', '')
            original_audio_url = item.get('source_audio_url', '') 
            stream_url = item.get('stream_audio_url', '')
            original_stream_url = item.get('source_stream_audio_url', '')
            
            # Создаем метаданные
            metadata = {
                'success': True,
                'task_id': task_id,
                'audio_url': audio_url,
                'original_audio_url': original_audio_url,
                'stream_url': stream_url,
                'original_stream_url': original_stream_url,
                'title': item.get('title', 'Untitled'),
                'prompt': item.get('prompt', ''),
                'duration': item.get('duration', 0),
                'model': item.get('model_name', '')
            }
            
            # Сохраняем метаданные
            metadata_path = os.path.join('static', 'generated_music', f'music_metadata_{task_id}.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            return {
                'success': True,
                'task_id': task_id,
                'metadata_path': metadata_path
            }
        except Exception as e:
            print(f"Ошибка при обработке данных из callback от Suno API: {str(e)}")
            return {
                'success': False,
                'error': f"Ошибка при обработке данных из callback от Suno API: {str(e)}",
                'task_id': task_id
            }

def main():
    """
    Пример использования анализатора дневников
    """
    # Пример текста дневника
    sample_diary = """
    15 августа 1943 года.
    Сегодня был тяжелый бой. Мы потеряли троих товарищей, но сумели удержать позицию.
    Каждый день я пишу письма домой, хотя не знаю, дойдут ли они когда-нибудь до адресата.
    В окопах холодно и сыро, но мы держимся. Вера в победу придает сил.
    """
    
    try:
        analyzer = WarDiaryAnalyzer()
        results = analyzer.process_diary(sample_diary)
        
        # Сохранение только сгенерированного произведения
        with open('output.txt', 'w', encoding='utf-8') as f:
            f.write(results['generated_literary_work'])
            
        print("Анализ успешно завершен. Сгенерированное произведение сохранено в файл 'output.txt'")
        
        # # Расширенный вывод (закомментирован)
        # with open('full_output.txt', 'w', encoding='utf-8') as f:
        #     f.write("=== Оригинальный текст ===\n\n")
        #     f.write(results['original_text'])
        #     f.write("\n\n=== Анализ эмоций ===\n\n")
        #     f.write(json.dumps(results['emotion_analysis'], ensure_ascii=False, indent=2))
        #     f.write("\n\n=== Сгенерированное произведение ===\n\n")
        #     f.write(results['generated_literary_work'])
        #     
        # print("Полный анализ сохранен в файл 'full_output.txt'")
        
    except Exception as e:
        print(f"Произошла ошибка: {str(e)}")

if __name__ == "__main__":
    main() 