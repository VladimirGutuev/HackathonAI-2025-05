import os
from dotenv import load_dotenv, find_dotenv, dotenv_values
from openai import OpenAI       # Импортируем только новую библиотеку
import json
import base64  # Добавляем для работы с изображениями
import requests  # Добавляем для работы с API
import io  # Добавляем для работы с файлами
from datetime import datetime  # Добавляем для работы с датами
import time  # Добавляем для работы с временем
import uuid # Для генерации уникальных имен файлов
import random  # Добавляем для выбора случайного типа произведения

# Попытка импорта системы RAG
try:
    from historical_rag import HistoricalRAG
    RAG_AVAILABLE = True
    print("Система RAG с исторической базой данных доступна")
except ImportError as e:
    RAG_AVAILABLE = False
    print(f"Система RAG недоступна: {e}")

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
        
        # Инициализируем систему RAG если доступна
        self.historical_rag = None
        if RAG_AVAILABLE:
            try:
                self.historical_rag = HistoricalRAG()
                print("Система RAG инициализирована")
            except Exception as e:
                print(f"Ошибка инициализации RAG: {e}")
                self.historical_rag = None

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

    def generate_literary_work(self, diary_text, emotion_analysis, user_id=None, literary_type='random'):
        """
        Генерация художественного произведения на основе текста дневника и анализа эмоций.
        Также сохраняет произведение и метаданные в папку instance/generated_literary_works/.
        Возвращает словарь с текстом произведения и путями к файлам.
        
        Args:
            diary_text (str): Текст дневника
            emotion_analysis (dict): Результат анализа эмоций
            user_id (int, optional): ID пользователя, если он аутентифицирован.
            literary_type (str): Тип произведения: 'poem', 'story', 'drama', 'random'
            
        Returns:
            dict: Словарь с ключами 'text', 'filepath', 'meta_filepath' или None в случае ошибки.
        """
        if not emotion_analysis or not isinstance(emotion_analysis, dict) or emotion_analysis.get('error'):
            error_msg = emotion_analysis.get('error', 'Нет данных для анализа эмоций') if isinstance(emotion_analysis, dict) else 'Некорректные данные анализа эмоций'
            print(f"Прерывание генерации лит. произведения: {error_msg}")
            return None # Не генерируем, если нет анализа или в нем ошибка

        primary_emotions_str = ", ".join([f"{e['emotion']} ({e['intensity']}/10)" for e in emotion_analysis.get('primary_emotions', [])])
        emotional_tone = emotion_analysis.get('emotional_tone', 'неопределенный')
        
        # Определяем тип произведения
        if literary_type == 'random':
            selected_type = random.choice(['poem', 'story', 'drama'])
        else:
            selected_type = literary_type
        
        # Формируем промпт в зависимости от типа произведения
        type_instructions = {
            'poem': {
                'name': 'стихотворение',
                'instruction': 'Напиши лирическое стихотворение от лица или о герое дневника. Используй образную речь, метафоры и ритм, чтобы передать эмоциональное состояние и атмосферу. Стихи должны быть глубокими и трогательными, отражающими внутренний мир человека на войне.',
                'length': '16-24 строки',
                'style': 'поэтический, образный, лирический'
            },
            'story': {
                'name': 'повесть',
                'instruction': 'Напиши небольшую повесть или развернутый рассказ от третьего лица. Создай полноценный сюжет с развитием характера, диалогами и описанием обстановки. Сосредоточься на психологических переживаниях героя и его внутренней трансформации.',
                'length': '400-600 слов',
                'style': 'повествовательный, психологический, детализированный'
            },
            'drama': {
                'name': 'драматический монолог',
                'instruction': 'Напиши драматический монолог или короткую сцену с диалогами. Используй театральную форму подачи - внутренний монолог героя, его размышления вслух или диалог с невидимым собеседником. Передай драматизм момента и силу переживаний.',
                'length': '300-450 слов',
                'style': 'драматический, эмоциональный, сценический'
            }
        }
        
        type_info = type_instructions[selected_type]
        
        prompt = f"""
        На основе следующего отрывка из военного дневника и его эмоционального анализа, создай {type_info['name']}.
        
        {type_info['instruction']}
        
        Требования:
        - Объем: {type_info['length']}
        - Стиль: {type_info['style']}
        - Избегай чрезмерного натурализма и жестоких сцен
        - Сохраняй уважительное отношение к исторической памяти
        - Передай атмосферу эпохи и внутренний мир персонажа

        Текст дневника:
        {diary_text}
        
        Эмоциональный анализ:
        - Основные эмоции: {primary_emotions_str}
        - Общий тон: {emotional_tone}

        Создай {type_info['name']}, который глубоко передаст переживания и атмосферу того времени.
        """

        try:
            print(f"Отправка запроса на генерацию художественного произведения (тип: {selected_type})...")
            response = self.client.chat.completions.create(
                model="gpt-4o", # Или другая подходящая модель
                messages=[
                    {"role": "system", "content": f"Ты - талантливый писатель, специализирующийся на военной прозе и психологии человеческих переживаний в экстремальных условиях. Ты мастерски создаешь {type_info['name']} в {type_info['style']} стиле."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.75,
                max_tokens=800 
            )
            generated_text = response.choices[0].message.content.strip()
            print(f"Художественное произведение ({selected_type}) сгенерировано, длина: {len(generated_text)} символов.")
            
            # --- Сохранение файла и метаданных ---
            # Создаем директорию, если ее нет
            works_dir = os.path.join('instance', 'generated_literary_works')
            os.makedirs(works_dir, exist_ok=True)
            
            # Генерируем уникальный ID для файла
            file_id = str(uuid.uuid4())
            txt_filename = f"{file_id}.txt"
            meta_filename = f"{file_id}.meta.json"
            
            txt_path = os.path.join(works_dir, txt_filename)
            meta_path = os.path.join(works_dir, meta_filename)
            
            # Сохраняем текст произведения
            with open(txt_path, 'w', encoding='utf-8') as f_txt:
                f_txt.write(generated_text)
            
            # Сохраняем метаданные
            metadata = {
                'file_id': file_id,
                'generation_timestamp': datetime.now().isoformat(),
                'literary_type': selected_type,
                'source_diary_text_snippet': diary_text[:200] + ("..." if len(diary_text) > 200 else ""),
                'emotion_analysis_used': emotion_analysis,
                'model_used': response.model, # Сохраняем модель, если API это возвращает
                'user_id': user_id # Сохраняем ID пользователя, если передан
            }
            with open(meta_path, 'w', encoding='utf-8') as f_meta:
                json.dump(metadata, f_meta, ensure_ascii=False, indent=4)
                
            print(f"Произведение сохранено: {txt_path}, метаданные: {meta_path}")
            
            return {
                'text': generated_text,
                'filepath': txt_filename, # Возвращаем только имя файла, не полный путь
                'meta_filepath': meta_filename,
                'literary_type': selected_type
            }
            
        except Exception as e:
            print(f"Ошибка при генерации или сохранении художественного произведения: {e}")
            import traceback
            traceback.print_exc()
            return None

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
            print(f"[generate_music] Начало генерации музыки. Текст: {len(text)} симв. Base_url: {base_url}")
            if not self.suno_api_key:
                print("[generate_music] API ключ Suno не найден. Используем запасной метод _fallback_music_generation.")
                return self._fallback_music_generation(text, emotion_analysis, base_url=base_url)

            if len(text) > 4000: # Ограничение длины текста для промпта
                text = text[:4000]

            model = "V4_5" # ИСПОЛЬЗУЕМ КОРРЕКТНУЮ МОДЕЛЬ V4_5
            style, mood, tempo, instruments = self._determine_music_params(emotion_analysis)
            style = self._validate_music_style(style, model) # Валидация длины стиля

            if emotion_analysis and 'primary_emotions' in emotion_analysis:
                emotions = [e['emotion'] for e in emotion_analysis['primary_emotions']]
                tone = emotion_analysis.get('emotional_tone', 'reflective')
                music_title = self._create_music_title(tone, style, "War Diary")
                music_prompt = f"Create high-quality {mood} {style} music that captures the following emotions: {', '.join(emotions[:3])}. "
                music_prompt += f"The music should reflect a {tone} tone of wartime experiences. "
                music_prompt += f"{tempo} rhythm with {instruments} as primary instruments. "
                music_prompt += f"Based on a war diary that describes: {text[:300]}..." # Используем часть текста
            else:
                music_title = "War Diary Reflection"
                music_prompt = f"Create high-quality emotional {style} music that captures the mood of a war diary. "
                music_prompt += f"The music should be {mood} and reflect the atmosphere of wartime experiences. "
                music_prompt += f"{tempo} with {instruments} as primary instruments. "
                music_prompt += f"Context from the diary: {text[:300]}..."
            
            music_prompt = self._validate_music_prompt(music_prompt, model) # Валидация длины промпта
            negative_tags = "lyrics, vocals, singing, spoken words, voice"

            print(f"[generate_music] Сформирован промпт (начало): {music_prompt[:150]}... Стиль: {style}, Заголовок: {music_title}")

            # Определение callBackUrl (ОБЯЗАТЕЛЬНЫЙ ПАРАМЕТР)
            # Сначала пытаемся использовать переменную окружения EXTERNAL_URL (для ngrok)
            # Затем переданный base_url (если есть, например, из Flask request)
            # Если ничего нет, то пытаемся сформировать из Flask request (если доступно)
            # В крайнем случае, используем заглушку (но это не сработает для реального коллбэка)
            
            determined_callback_url = None
            if os.environ.get('EXTERNAL_URL'):
                determined_callback_url = f"{os.environ.get('EXTERNAL_URL').rstrip('/')}/music_callback"
                print(f"[generate_music] callBackUrl из EXTERNAL_URL: {determined_callback_url}")
            elif base_url:
                determined_callback_url = f"{base_url.rstrip('/')}/music_callback"
                print(f"[generate_music] callBackUrl из переданного base_url: {determined_callback_url}")
            elif 'request' in globals() and hasattr(request, 'host_url'): # Проверяем, что request доступен (мы в контексте Flask)
                try:
                    from flask import request as flask_request # Импортируем flask.request если доступно
                    determined_callback_url = f"{flask_request.host_url.rstrip('/')}/music_callback"
                    print(f"[generate_music] callBackUrl из flask_request.host_url: {determined_callback_url}")
                except ImportError:
                     print("[generate_music] Flask request не доступен для определения host_url.")
                     # Оставляем determined_callback_url = None, чтобы сработал следующий блок
            
            if not determined_callback_url:
                 # КРАЙНИЙ СЛУЧАЙ: если URL не определен, ставим заглушку, но это не сработает для Suno
                 # Suno API требует callBackUrl. Если он не доступен извне, коллбэк не придет.
                 # Для локальной разработки без туннеля, можно поставить http://localhost:xxxx,
                 # но Suno не сможет его вызвать. Статус придется проверять вручную.
                 determined_callback_url = "http://localhost:5000/music_callback" # Заглушка, коллбэк не придет!
                 print(f"[generate_music] ВНИМАНИЕ: callBackUrl установлен на заглушку: {determined_callback_url}. Коллбэк от Suno не будет получен.")


            request_data = {
                "prompt": music_prompt,
                "style": style,
                "title": music_title,
                "customMode": True,
                "instrumental": True,
                "model": model, # Корректная модель
                "negativeTags": negative_tags,
                "callBackUrl": determined_callback_url # ОБЯЗАТЕЛЬНЫЙ ПАРАМЕТР
            }

            headers = {
                "Authorization": f"Bearer {self.suno_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            print(f"[generate_music] Отправка запроса к Suno API. Данные (часть): {json.dumps(request_data, ensure_ascii=False)[:300]}...")
            response = requests.post(
                "https://apibox.erweima.ai/api/v1/generate",
                json=request_data,
                headers=headers,
                timeout=30 # Таймаут для запроса
            )
            print(f"[generate_music] Ответ от Suno API: Код={response.status_code}, Тело (часть)={response.text[:500]}")

            if response.status_code == 200:
                try:
                    response_data = response.json()
                except json.JSONDecodeError as e:
                    error_msg = f"Ошибка разбора JSON ответа от Suno API: {str(e)}. Ответ: {response.text}"
                    print(f"[generate_music] {error_msg}")
                    # Даже если JSON не разобрался, но код 200, можно попробовать _fallback с этой ошибкой
                    return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)

                if response_data.get('code') != 200:
                    error_msg = f"Suno API вернул ошибку (внутренний код {response_data.get('code')}): {response_data.get('msg', 'Неизвестная ошибка API')}"
                    print(f"[generate_music] {error_msg}")
                    return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)
                
                if 'data' not in response_data or not isinstance(response_data.get('data'), dict):
                    error_msg = "В ответе Suno API отсутствует или некорректно поле 'data'"
                    print(f"[generate_music] {error_msg}. Ответ: {response_data}")
                    return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)

                task_id = response_data['data'].get('taskId')
                if not task_id:
                    error_msg = "Не удалось получить task_id от Suno API из поля 'data'"
                    print(f"[generate_music] {error_msg}. Ответ data: {response_data['data']}")
                    return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)

                print(f"[generate_music] Запрос к Suno API успешно отправлен, task_id: {task_id}")
                
                music_metadata = {
                    'task_id': task_id, 'title': music_title, 'prompt': music_prompt, 'style': style,
                    'mood': mood, 'tempo': tempo, 'instruments': instruments,
                    'emotions': [e['emotion'] for e in emotion_analysis['primary_emotions']][:3] if emotion_analysis and 'primary_emotions' in emotion_analysis else [],
                    'emotional_tone': emotion_analysis.get('emotional_tone', '') if emotion_analysis else '',
                    'status': 'processing', 'created_at': datetime.now().isoformat(),
                    'callback_url_used': determined_callback_url,
                    'model_used': model
                }
                self._save_status_to_metadata(task_id, music_metadata) # Сохраняем начальные метаданные

                music_description = f"Сгенерирована {mood} {style} музыка, отражающая "
                music_description += f"{', '.join(music_metadata['emotions'] if music_metadata['emotions'] else ['различные'])} эмоции. "
                music_description += f"Использует {instruments}."
                
                return {
                    'success': True, 'status': 'processing', 'task_id': task_id,
                    'music_description': music_description, 'audio_url': None,
                    'metadata': music_metadata
                }
            else: # Ошибка HTTP != 200
                error_msg = f"Ошибка HTTP запроса к Suno API: {response.status_code}"
                try:
                    error_msg += f" - {response.text}"
                except: pass # Если тело ответа не текст
                print(f"[generate_music] {error_msg}")
                # Переходим к fallback, передавая информацию об ошибке
                return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)

        except requests.exceptions.Timeout:
            error_msg = "Таймаут при запросе к Suno API (generate_music)"
            print(f"[generate_music] {error_msg}")
            return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)
        except requests.exceptions.RequestException as e:
            error_msg = f"Ошибка соединения с Suno API (generate_music): {str(e)}"
            print(f"[generate_music] {error_msg}")
            return self._fallback_music_generation(text, emotion_analysis, error=error_msg, base_url=base_url)
        except Exception as e:
            print(f"[generate_music] Непредвиденная ошибка при генерации музыки: {str(e)}")
            import traceback
            traceback.print_exc()
            # Переходим к fallback с общей ошибкой
            return self._fallback_music_generation(text, emotion_analysis, error=str(e), base_url=base_url)
    
    def _fallback_music_generation(self, text, emotion_analysis, error=None, base_url=None):
        """
        Запасной метод генерации музыки. Основное отличие от generate_music - явный запрос ключа, если его нет.
        Также используется, если основной метод завершился ошибкой.
        """
        print(f"[_fallback_music_generation] Активирован запасной метод. Переданная ошибка: {error}. Base_url: {base_url}")
        
        if emotion_analysis is None: emotion_analysis = {} # Гарантируем, что это словарь
        
        model = "V4_5"  # ИСПОЛЬЗУЕМ КОРРЕКТНУЮ МОДЕЛЬ V4_5
        style, mood, tempo, instruments = self._determine_music_params(emotion_analysis)
        style = self._validate_music_style(style, model)

        if not self.suno_api_key:
            print("\\n\\n====== [_fallback_music_generation] ВНИМАНИЕ: SUNO API ключ не найден ======")
            # Этот блок с input() не будет работать в серверном окружении Flask.
            # Оставляем для CLI, но для Flask это должно быть обработано иначе.
            # Для Flask - просто возвращаем ошибку, что ключ не настроен.
            return {
                'success': False,
                'error': "API ключ SUNO не найден или недействителен. Пожалуйста, настройте SUNOAI_API_KEY в .env.",
                'status': 'error',
                'reason': 'missing_api_key_in_fallback'
            }
            
        try:
            emotions = []
            tone = "reflective"
            if emotion_analysis and 'primary_emotions' in emotion_analysis and isinstance(emotion_analysis['primary_emotions'], list):
                emotions = [e.get('emotion', 'emotion') for e in emotion_analysis['primary_emotions'] if isinstance(e, dict)]
            tone = emotion_analysis.get('emotional_tone', 'reflective')
                
            music_title = self._create_music_title(tone, style, "Diary Emotion (Fallback)")
            emotions_str = ', '.join(emotions[:3]) if emotions else 'varied emotions'
            
            music_prompt = f"Create high-quality {mood} {style} music that conveys {emotions_str}. "
            music_prompt += f"The piece should have a {tempo} rhythm with {instruments}. "
            music_prompt += f"The music should reflect emotions from a war diary with a {tone} tone. "
            music_prompt += f"No lyrics, just instrumental music that captures the emotional essence of a diary entry."
            music_prompt = self._validate_music_prompt(music_prompt, model)
                
            print(f"[_fallback_music_generation] Формирование запроса к Suno API. Промпт (начало): {music_prompt[:150]}...")
            
            headers = {
                "Authorization": f"Bearer {self.suno_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Определение callBackUrl (ОБЯЗАТЕЛЬНЫЙ ПАРАМЕТР)
            determined_callback_url = None
            if os.environ.get('EXTERNAL_URL'):
                determined_callback_url = f"{os.environ.get('EXTERNAL_URL').rstrip('/')}/music_callback"
                print(f"[_fallback_music_generation] callBackUrl из EXTERNAL_URL: {determined_callback_url}")
            elif base_url:
                determined_callback_url = f"{base_url.rstrip('/')}/music_callback"
                print(f"[_fallback_music_generation] callBackUrl из переданного base_url: {determined_callback_url}")
            elif 'request' in globals() and hasattr(request, 'host_url'):
                try:
                    from flask import request as flask_request
                    determined_callback_url = f"{flask_request.host_url.rstrip('/')}/music_callback"
                    print(f"[_fallback_music_generation] callBackUrl из flask_request.host_url: {determined_callback_url}")
                except ImportError:
                     print("[_fallback_music_generation] Flask request не доступен для определения host_url.")

            if not determined_callback_url:
                 determined_callback_url = "http://localhost:5000/music_callback" 
                 print(f"[_fallback_music_generation] ВНИМАНИЕ: callBackUrl установлен на заглушку: {determined_callback_url}.")

            request_data = {
                "prompt": music_prompt, "style": style, "title": music_title,
                "customMode": True, "instrumental": True, "model": model,
                "negativeTags": "lyrics, vocals, singing, spoken words, voice",
                "callBackUrl": determined_callback_url # ОБЯЗАТЕЛЬНЫЙ
            }
            
            print(f"[_fallback_music_generation] Отправка запроса к Suno API (fallback). Данные (часть): {json.dumps(request_data, ensure_ascii=False)[:300]}...")
            response = requests.post(
                "https://apibox.erweima.ai/api/v1/generate",
                json=request_data, headers=headers, timeout=30
            )
            print(f"[_fallback_music_generation] Ответ от Suno API (fallback): Код={response.status_code}, Тело (часть)={response.text[:500]}")

            if response.status_code == 200:
                try:
                    result_json = response.json()
                except json.JSONDecodeError as e_json:
                    final_error_msg = f"Ошибка разбора JSON от Suno API (fallback): {str(e_json)}. Ответ: {response.text}"
                    print(f"[_fallback_music_generation] {final_error_msg}")
                    return {'success': False, 'error': final_error_msg, 'status': 'error', 'reason': 'fallback_json_decode_error'}

                if result_json.get('code') != 200:
                    final_error_msg = f"Suno API (fallback) вернул ошибку {result_json.get('code')}: {result_json.get('msg', 'Неизвестная ошибка API')}"
                    print(f"[_fallback_music_generation] {final_error_msg}")
                    return {'success': False, 'error': final_error_msg, 'status': 'error', 'reason': 'fallback_api_internal_error'}
                
                if 'data' not in result_json or not isinstance(result_json.get('data'), dict):
                    final_error_msg = "В ответе Suno API (fallback) отсутствует или некорректно поле 'data'"
                    print(f"[_fallback_music_generation] {final_error_msg}. Ответ: {result_json}")
                    return {'success': False, 'error': final_error_msg, 'status': 'error', 'reason': 'fallback_missing_data_field'}

                task_id = result_json['data'].get('taskId')
                if not task_id:
                    final_error_msg = "Не удалось получить task_id от Suno API (fallback) из поля 'data'"
                    print(f"[_fallback_music_generation] {final_error_msg}. Ответ data: {result_json['data']}")
                    return {'success': False, 'error': final_error_msg, 'status': 'error', 'reason': 'fallback_missing_task_id'}
                    
                print(f"[_fallback_music_generation] Запрос на генерацию музыки (fallback) отправлен, task_id: {task_id}")
                
                fallback_metadata = {
                    'task_id': task_id, 'title': music_title, 'prompt': music_prompt, 'style': style,
                    'mood': mood, 'tempo': tempo, 'instruments': instruments,
                    'emotions': emotions[:3], 'emotional_tone': tone,
                    'status': 'processing_fallback', 'created_at': datetime.now().isoformat(),
                    'callback_url_used': determined_callback_url, 'model_used': model,
                    'original_error_triggering_fallback': error, # Сохраняем исходную ошибку
                    'request_data_fallback': request_data # Сохраняем данные запроса для отладки
                }
                self._save_status_to_metadata(task_id, fallback_metadata)
                
                music_description = f"Генерируется (fallback) {mood} {style} музыка"
                if emotions: music_description += f", отражающая {', '.join(emotions[:3])}. "
                music_description += f"Инструменты: {instruments}."
                
                return {
                    'success': True, 'status': 'processing_fallback', 'task_id': task_id,
                    'music_description': music_description, 'metadata': fallback_metadata
                }
            else: # Ошибка HTTP != 200 в fallback
                final_error_msg = f"Ошибка HTTP запроса к Suno API (fallback): {response.status_code}"
                try:
                    final_error_msg += f" - {response.text}"
                except: pass
                print(f"[_fallback_music_generation] {final_error_msg}")
                return {'success': False, 'error': final_error_msg, 'status': 'error', 'reason': 'fallback_http_error'}

        except requests.exceptions.Timeout:
            final_error_msg = "Таймаут при запросе к Suno API (fallback)"
            print(f"[_fallback_music_generation] {final_error_msg}")
            return {'success': False, 'error': final_error_msg, 'status': 'error', 'reason': 'fallback_timeout'}
        except requests.exceptions.RequestException as e_req:
            final_error_msg = f"Ошибка соединения с Suno API (fallback): {str(e_req)}"
            print(f"[_fallback_music_generation] {final_error_msg}")
            return {'success': False, 'error': final_error_msg, 'status': 'error', 'reason': 'fallback_connection_error'}
        except Exception as e_final:
            final_error_msg = f"Непредвиденная ошибка в _fallback_music_generation: {str(e_final)}"
            print(f"[_fallback_music_generation] {final_error_msg}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'error': final_error_msg, 'status': 'error', 'reason': 'fallback_unexpected_error'}

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
    
    def _check_music_generation_status(self, task_id, retries=15, delay=15, timeout_seconds=400):  # Увеличен общий таймаут до 400 секунд
        """Проверяет статус генерации музыки через API Suno, используя локальное кеширование статуса и несколько эндпоинтов."""
        if not self.suno_api_key:
            return {'status': 'error', 'message': 'API ключ Suno не настроен'}

        print(f"[_check_music_generation_status] Начало проверки статуса для Task ID: {task_id}. Попыток: {retries}, Задержка: {delay}s, Таймаут API: {timeout_seconds}s")

        cached_status = self._load_status_from_metadata(task_id)
        if cached_status:
            if cached_status.get('status') == 'complete' and (cached_status.get('audio_url') or cached_status.get('stream_url')):
                print(f"[_check_music_generation_status] Музыка для Task ID: {task_id} найдена локально (завершено).")
                return cached_status
            if cached_status.get('status') == 'error':
                print(f"[_check_music_generation_status] Локальные метаданные для Task ID: {task_id} уже указывают на ошибку: {cached_status.get('message')}")
                # Если ошибка была 'max_retries_reached' или 'timeout', и прошло мало времени, можно попробовать еще раз
                if cached_status.get('error_type') in ['max_retries_reached', 'timeout']:
                     try:
                        last_update_dt = datetime.fromisoformat(cached_status.get('last_update', '1970-01-01T00:00:00'))
                        if (datetime.now() - last_update_dt).total_seconds() < 300: # Если ошибка была менее 5 минут назад
                             print(f"[_check_music_generation_status] Предыдущая ошибка ({cached_status.get('error_type')}) была недавно, продолжаем попытки.")
                        else:
                             return cached_status # Возвращаем старую ошибку, если прошло много времени
                     except: # На случай если last_update некорректен
                        return cached_status
                else:
                    return cached_status # Возвращаем другие типы ошибок сразу


        # Эндпоинты для проверки статуса в порядке предпочтения
        status_check_endpoints = [
            f"https://apibox.erweima.ai/api/v1/tasks/{task_id}",
            f"https://apibox.erweima.ai/api/v1/get?taskId={task_id}",
            f"https://apibox.erweima.ai/api/v1/music/{task_id}" 
        ]

        headers = {
            'Authorization': f'Bearer {self.suno_api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        total_wait_time = 0
        # Увеличим начальную задержку перед первым реальным запросом к API
        initial_api_delay = 20 # секунд
        
        print(f"[_check_music_generation_status] Начальная задержка перед первым API запросом: {initial_api_delay}s для Task ID: {task_id}")
        time.sleep(initial_api_delay)
        total_wait_time += initial_api_delay

        last_known_api_message = cached_status.get('message', "Статус не определен из кеша") if cached_status else "Статус не определен"

        for attempt in range(retries):
            print(f"[_check_music_generation_status] Попытка {attempt + 1}/{retries} для Task ID: {task_id}...")
            
            if attempt > 0 : # Задержка между основными попытками (кроме первой после initial_api_delay)
                time.sleep(delay)
                total_wait_time += delay
            
            if total_wait_time > timeout_seconds:
                print(f"[_check_music_generation_status] Общий таймаут {timeout_seconds}s исчерпан для Task ID: {task_id}.")
                timeout_status_data = {
                    'status': 'timeout',
                    'message': f'Превышено общее время ожидания {timeout_seconds}s. Последнее сообщение от API: {last_known_api_message}',
                    'error_type': 'overall_timeout'
                }
                current_metadata = self._load_status_from_metadata(task_id) or {'task_id': task_id}
                current_metadata.update(timeout_status_data)
                self._save_status_to_metadata(task_id, current_metadata)
                return current_metadata

            success_on_endpoint = False
            for endpoint_url in status_check_endpoints:
                if success_on_endpoint: break # Если успешно на одном эндпоинте, не пробуем другие в этой попытке
                
                print(f"[_check_music_generation_status] Проверка эндпоинта: {endpoint_url}")
                try:
                    response = requests.get(endpoint_url, headers=headers, timeout=30) # Таймаут для HTTP запроса
                    print(f"[_check_music_generation_status] Ответ API (Эндпоинт: {endpoint_url}, Попытка: {attempt + 1}): Код={response.status_code}, Тело={response.text[:500]}")

                    current_metadata = self._load_status_from_metadata(task_id) or {'task_id': task_id}
                    current_metadata.setdefault('api_response_history', []).append({
                        'timestamp': datetime.now().isoformat(),
                        'endpoint': endpoint_url,
                        'status_code': response.status_code,
                        'response_body_snippet': response.text[:1000] # Сохраняем больше для отладки
                    })

                    if response.status_code == 200:
                        data = response.json()
                        api_payload = data.get('data', data if isinstance(data, dict) else {})
                        if not isinstance(api_payload, dict): api_payload = {}

                        api_status = api_payload.get('status', data.get('status', 'unknown'))
                        last_known_api_message = f"Статус API: {api_status}, Сообщение: {api_payload.get('message', data.get('message', 'N/A'))}"
                        
                        success_on_endpoint = True # Успешный ответ 200 OK

                        if api_status == 'complete':
                            audio_url = api_payload.get('audio_url') or api_payload.get('audioUrl')
                            stream_url = api_payload.get('stream_audio_url') or api_payload.get('streamUrl')
                            
                            tracks = api_payload.get('tracks', [])
                            if not audio_url and tracks and isinstance(tracks, list) and len(tracks) > 0:
                                audio_url = tracks[0].get('audio_url', tracks[0].get('audioUrl'))
                                stream_url = tracks[0].get('stream_audio_url', tracks[0].get('streamUrl'))
                            
                            if not audio_url: # Проверяем на верхнем уровне ответа
                                audio_url = data.get('audio_url', data.get('audioUrl'))
                                stream_url = data.get('stream_audio_url', data.get('streamUrl'))

                            print(f"[_check_music_generation_status] Задача {task_id} ЗАВЕРШЕНА. Аудио URL: {audio_url}, Stream URL: {stream_url}")
                            
                            complete_status_data = {
                                'status': 'complete', 'audio_url': audio_url, 'stream_url': stream_url,
                                'message': 'Музыка успешно сгенерирована.'
                            }
                            current_metadata.update(complete_status_data)
                            self._save_status_to_metadata(task_id, current_metadata)
                            return current_metadata

                        elif api_status in ['processing', 'pending', 'submitted', 'generating']:
                            processing_status_data = {
                                'status': api_status,
                                'message': f'Задача в обработке (API статус: {api_status})'
                            }
                            current_metadata.update(processing_status_data)
                            self._save_status_to_metadata(task_id, current_metadata)
                            # Продолжаем цикл попыток, но этот эндпоинт отработал для этой попытки
                        
                        elif api_status == 'error':
                            error_detail_msg = api_payload.get('error_message', api_payload.get('message', data.get('message', 'Неизвестная ошибка API')))
                            print(f"[_check_music_generation_status] Ошибка от API Suno для Task ID {task_id}: {error_detail_msg}")
                            error_status_data = {
                                'status': 'error', 'message': f'Ошибка API Suno: {error_detail_msg}', 'error_type': 'api_reported_error'
                            }
                            current_metadata.update(error_status_data)
                            self._save_status_to_metadata(task_id, current_metadata)
                            return current_metadata # Возвращаем ошибку от API сразу

                        else: # Неизвестный статус
                            print(f"[_check_music_generation_status] Неизвестный статус от API Suno для Task ID {task_id}: {api_status}. Ответ: {data}")
                            unknown_status_data = {
                                'status': 'error', # Трактуем как ошибку
                                'message': f'Неизвестный статус от API Suno: {api_status}',
                                'error_type': 'unknown_api_status'
                            }
                            current_metadata.update(unknown_status_data)
                            self._save_status_to_metadata(task_id, current_metadata)
                            # Продолжаем цикл, может следующий эндпоинт или попытка даст результат

                    elif response.status_code == 404:
                        last_known_api_message = f"Задача {task_id} не найдена на эндпоинте {endpoint_url} (404)."
                        print(f"[_check_music_generation_status] {last_known_api_message}")
                        # Не выходим, пробуем следующий эндпоинт или попытку
                    
                    else: # Другие HTTP ошибки
                        last_known_api_message = f"Ошибка HTTP {response.status_code} от эндпоинта {endpoint_url}: {response.text[:200]}"
                        print(f"[_check_music_generation_status] {last_known_api_message}")
                        current_metadata['message'] = last_known_api_message # Обновляем сообщение в метаданных
                        self._save_status_to_metadata(task_id, current_metadata)
                        # Не выходим, пробуем следующий эндпоинт или попытку
                
                except requests.exceptions.Timeout:
                    last_known_api_message = f"Таймаут HTTP запроса к эндпоинту {endpoint_url} (попытка {attempt + 1})"
                    print(f"[_check_music_generation_status] {last_known_api_message}")
                except requests.exceptions.RequestException as e:
                    last_known_api_message = f"Ошибка соединения с {endpoint_url} (попытка {attempt + 1}): {e}"
                    print(f"[_check_music_generation_status] {last_known_api_message}")
                except json.JSONDecodeError:
                    last_known_api_message = f"Ошибка декодирования JSON от {endpoint_url} (попытка {attempt + 1}). Ответ: {response.text[:200]}"
                    print(f"[_check_music_generation_status] {last_known_api_message}")
                except Exception as e:
                    last_known_api_message = f"Непредвиденная ошибка при обработке {endpoint_url} (попытка {attempt + 1}): {e}"
                    print(f"[_check_music_generation_status] {last_known_api_message}")
                
                # Если успешно на одном эндпоинте, нет смысла проверять другие в этой же попытке
                if success_on_endpoint:
                    break 
            
            # Если ни один эндпоинт не дал успешного ответа 200 со статусом 'complete' или 'processing'
            if not success_on_endpoint and attempt == retries - 1 :
                 print(f"[_check_music_generation_status] Все эндпоинты и все {retries} попыток исчерпаны для Task ID: {task_id}. Музыка не получена.")
                 final_failure_status = {
                'status': 'error',
                    'message': f'Не удалось получить музыку после {retries} попыток ({total_wait_time}s). Последнее сообщение: {last_known_api_message}',
                    'error_type': 'max_retries_no_endpoint_success'
                }
                 current_metadata = self._load_status_from_metadata(task_id) or {'task_id': task_id}
                 current_metadata.update(final_failure_status)
                 self._save_status_to_metadata(task_id, current_metadata)
                 return current_metadata

        print(f"[_check_music_generation_status] Цикл завершен без явного возврата для Task ID: {task_id} (это не должно происходить при нормальной логике)")
        fallback_timeout_status = {
            'status': 'timeout', # Или 'error' в зависимости от last_known_api_message
            'message': f'Превышено время ожидания или все попытки исчерпаны ({total_wait_time}s). Последнее известное сообщение: {last_known_api_message}',
            'error_type': 'loop_ended_unexpectedly'
        }
        current_metadata = self._load_status_from_metadata(task_id) or {'task_id': task_id}
        current_metadata.update(fallback_timeout_status)
        self._save_status_to_metadata(task_id, current_metadata)
        return current_metadata

    def _save_status_to_metadata(self, task_id, status_data):
        """
        Сохраняет данные статуса в файл метаданных.
        
        Args:
            task_id (str): ID задачи
            status_data (dict): Данные статуса для сохранения
        """
        try:
            metadata_path = os.path.join('static', 'generated_music', f'music_metadata_{task_id}.json')
            
            # Загружаем существующие метаданные
            current_metadata = self._load_status_from_metadata(task_id) or {'task_id': task_id}
            
            # Обновляем метаданные новыми данными статуса
            current_metadata.update(status_data)
            current_metadata['last_update'] = datetime.now().isoformat()
            
            # Проверяем наличие audio_url и автоматически обновляем статус
            if current_metadata.get('audio_url') and current_metadata.get('status') != 'complete':
                current_metadata['status'] = 'complete'
                print(f"[_save_status_to_metadata] Автоматически изменен статус на 'complete' для Task ID: {task_id} (найден audio_url)")
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(current_metadata, f, ensure_ascii=False, indent=2)
            print(f"[_save_status_to_metadata] Статус для Task ID: {task_id} сохранен в {metadata_path}")
        except Exception as e:
            print(f"[_save_status_to_metadata] Ошибка сохранения статуса для Task ID: {task_id}: {e}")

    def _load_status_from_metadata(self, task_id):
        """Загружает статус задачи генерации музыки из файла метаданных."""
        try:
            metadata_dir = os.path.join('static', 'generated_music')
            metadata_filename = f"music_metadata_{task_id}.json"
            metadata_path = os.path.join(metadata_dir, metadata_filename)

            if os.path.exists(metadata_path):
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                print(f"[_load_status_from_metadata] Статус для Task ID: {task_id} загружен из {metadata_path}")
                return metadata
            else:
                print(f"[_load_status_from_metadata] Файл метаданных для Task ID: {task_id} не найден.")
                return None
        except Exception as e:
            print(f"[_load_status_from_metadata] Ошибка загрузки статуса для Task ID: {task_id}: {e}")
            return None
    
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

    def analyze_emotions_with_context(self, diary_text):
        """
        Расширенный анализ эмоций с историческим контекстом через RAG.
        
        Args:
            diary_text (str): Текст дневника для анализа
            
        Returns:
            dict: Результаты анализа эмоций с историческим обогащением
        """
        print("Начало расширенного анализа эмоций с историческим контекстом...")
        
        # Сначала проводим стандартный анализ эмоций
        emotion_analysis = self.analyze_emotions(diary_text)
        
        # Если есть ошибки в базовом анализе, возвращаем его без обогащения
        if 'error' in emotion_analysis and emotion_analysis['error']:
            print(f"Ошибка в базовом анализе эмоций: {emotion_analysis['error']}")
            return emotion_analysis
        
        # Если RAG система доступна, обогащаем результат историческим контекстом
        if self.historical_rag is not None:
            try:
                print("Поиск исторического контекста...")
                
                # Получаем релевантный исторический контекст
                historical_context = self.historical_rag.get_relevant_historical_context(
                    diary_text, 
                    emotion_analysis, 
                    top_k=5
                )
                
                if historical_context:
                    print(f"Найдено {len(historical_context)} релевантных исторических источников")
                    
                    # Обогащаем анализ историческим контекстом
                    enhanced_analysis = self.historical_rag.enhance_analysis_with_context(
                        emotion_analysis, 
                        historical_context
                    )
                    
                    # Генерируем историческое резюме для улучшения промптов
                    if enhanced_analysis.get('has_historical_enrichment', False):
                        print("Генерация обогащенного анализа эмоций с историческим контекстом...")
                        
                        # Создаем обогащенный промпт для повторного анализа
                        historical_summary = enhanced_analysis['historical_context']['summary']
                        
                        enhanced_prompt = f"""
                        Проанализируйте эмоциональное состояние автора в следующем отрывке из военного дневника
                        с учетом предоставленного исторического контекста.
                        
                        Текст дневника:
                        {diary_text}
                        
                        Исторический контекст:
                        {historical_summary}
                        
                        Пожалуйста, определите:
                        1. Основные эмоции с учетом исторических реалий
                        2. Интенсивность эмоций по шкале от 1 до 10
                        3. Общий эмоциональный тон в историческом контексте
                        4. Скрытые эмоциональные мотивы с учетом исторических событий
                        5. Отношение к происходящему в контексте эпохи
                        6. Историческая достоверность описанных событий и чувств
                        
                        Верните ответ СТРОГО в следующем формате JSON:
                        {{
                            "primary_emotions": [
                                {{"emotion": "название_эмоции", "intensity": число_от_1_до_10, "historical_context": "как эмоция связана с историческим контекстом"}},
                                ...
                            ],
                            "emotional_tone": "описание_общего_тона_с_историческим_контекстом",
                            "hidden_motives": ["мотив1", "мотив2", ...],
                            "attitude": "отношение_к_происходящему_в_историческом_контексте",
                            "historical_accuracy": "оценка_исторической_достоверности",
                            "historical_insights": ["инсайт1", "инсайт2", ...]
                        }}
                        """
                        
                        try:
                            # Отправляем обогащенный запрос к OpenAI
                            response = self.client.chat.completions.create(
                                model="gpt-4",
                                messages=[
                                    {"role": "system", "content": "Вы - историк и военный психолог, специализирующийся на анализе военных дневников с учетом исторического контекста. Всегда возвращайте ответ в формате JSON."},
                                    {"role": "user", "content": enhanced_prompt}
                                ],
                                temperature=0.7,
                                timeout=120
                            )
                            
                            response_text = response.choices[0].message.content.strip()
                            
                            try:
                                enhanced_emotion_analysis = json.loads(response_text)
                                print("Обогащенный анализ эмоций успешно получен")
                                
                                # Объединяем оба анализа
                                final_analysis = enhanced_analysis.copy()
                                final_analysis['emotion_analysis'] = enhanced_emotion_analysis
                                final_analysis['analysis_type'] = 'enhanced_with_historical_context'
                                
                                return final_analysis
                                
                            except json.JSONDecodeError as e:
                                print(f"Ошибка парсинга обогащенного анализа: {e}")
                                # Возвращаем стандартный обогащенный анализ
                                enhanced_analysis['analysis_type'] = 'standard_with_historical_context'
                                return enhanced_analysis
                        
                        except Exception as e:
                            print(f"Ошибка при получении обогащенного анализа эмоций: {e}")
                            enhanced_analysis['analysis_type'] = 'standard_with_historical_context'
                            return enhanced_analysis
                    
                    else:
                        print("Исторический контекст найден, но обогащение не применено")
                        enhanced_analysis['analysis_type'] = 'standard_with_limited_context'
                        return enhanced_analysis
                
                else:
                    print("Релевантный исторический контекст не найден")
                    emotion_analysis['analysis_type'] = 'standard_only'
                    return emotion_analysis
                    
            except Exception as e:
                print(f"Ошибка при работе с системой RAG: {e}")
                emotion_analysis['analysis_type'] = 'standard_only'
                emotion_analysis['rag_error'] = str(e)
                return emotion_analysis
        
        else:
            print("Система RAG недоступна, возвращаем стандартный анализ")
            emotion_analysis['analysis_type'] = 'standard_only'
            return emotion_analysis

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