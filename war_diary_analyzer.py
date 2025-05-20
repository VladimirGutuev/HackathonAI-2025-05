import os
from dotenv import load_dotenv
from openai import OpenAI       # Импортируем только новую библиотеку
import json
import base64  # Добавляем для работы с изображениями
import requests  # Добавляем для работы с API
import io  # Добавляем для работы с файлами
from datetime import datetime  # Добавляем для работы с датами

# Загрузка переменных окружения
load_dotenv()

class WarDiaryAnalyzer:
    def __init__(self):
        """
        Инициализация анализатора дневников.
        Получает API ключ из переменных окружения.
        """
        self.api_key = os.getenv('OPENAI_API_KEY')
        print(f"Инициализация WarDiaryAnalyzer, API ключ {'найден' if self.api_key else 'НЕ НАЙДЕН'}")
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
        
        Верните ответ СТРОГО в следующем формате JSON (без дополнительных пояснений):
        {{
            "primary_emotions": [
                {{"emotion": "название_эмоции", "intensity": число_от_1_до_10}},
                ...
            ],
            "emotional_tone": "описание_общего_тона",
            "hidden_motives": ["мотив1", "мотив2", ...],
            "attitude": "отношение_к_происходящему"
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
            print(f"Генерация изображения с запросом: {prompt[:100]}...")
            
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
                    {"role": "system", "content": "Ты - эксперт по визуальному искусству с глубоким пониманием военной истории. "
                                                "Твоя задача - преобразовать описание сцены военного времени "
                                                "в детальный визуальный образ для художественной иллюстрации."},
                    {"role": "user", "content": f"Мне нужно создать визуальную иллюстрацию военной сцены на основе следующего описания. "
                                              f"Опиши эту сцену в деталях, добавь визуальные элементы, настроение и атмосферу:\n\n{prompt}"}
                ],
                tools=tools,
                tool_choice={"type": "function", "function": {"name": "generate_image"}}
            )
            
            # Извлекаем результат function call
            function_call = response.choices[0].message.tool_calls[0]
            function_args = json.loads(function_call.function.arguments)
            
            # Получаем обогащенный промпт
            enhanced_prompt = function_args.get('detailed_prompt')
            style = function_args.get('style', 'realistic')
            mood = function_args.get('mood', 'dramatic')
            
            # Добавляем стиль и настроение к промпту
            final_prompt = f"{enhanced_prompt} Style: {style}. Mood: {mood}."
            print(f"Обогащенный промпт: {final_prompt[:150]}...")
            
            # Теперь вызываем Image Generation API с улучшенным промптом
            image_response = self.client.images.generate(
                model="gpt-image-1",  # Используем современную модель
                prompt=final_prompt,
                size=size,
                quality="medium",  # Баланс между качеством и стоимостью
                n=1,
            )
            
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
            
            # Формируем запрос для генерации изображения на основе текста и эмоций
            if emotion_analysis and 'primary_emotions' in emotion_analysis:
                # Используем эмоциональный анализ для улучшения запроса
                emotions_text = ', '.join([f"{e['emotion']} ({e['intensity']})" for e in emotion_analysis['primary_emotions'][:3]])
                tone = emotion_analysis.get('emotional_tone', '')
                
                prompt = f"""
                Создайте художественную иллюстрацию военной сцены, основанную на следующем фрагменте дневника:
                
                "{diary_text}"
                
                Основные эмоции: {emotions_text}
                Общий тон: {tone}
                
                Изображение должно передать атмосферу военного времени, эмоциональное состояние автора и исторический контекст.
                """
            else:
                # Если анализа эмоций нет, генерируем запрос только на основе текста
                prompt = f"""
                Создайте художественную иллюстрацию военной сцены, основанную на следующем фрагменте дневника:
                
                "{diary_text}"
                
                Изображение должно передать атмосферу военного времени и исторический контекст.
                """
            
            # Генерируем изображение
            result = self.generate_image(prompt)
            
            return result
        
        except Exception as e:
            print(f"Ошибка при генерации изображения из дневника: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def generate_music(self, text, emotion_analysis=None):
        """
        Генерирует музыкальное произведение на основе текста дневника и эмоционального анализа.
        Использует MusicGen API для создания музыкального фрагмента.
        
        Args:
            text (str): Текст дневника
            emotion_analysis (dict, optional): Результаты эмоционального анализа
            
        Returns:
            dict: Результат генерации музыки
        """
        try:
            print(f"Генерация музыки на основе текста длиной {len(text)} символов")
            
            # Если текст слишком длинный, обрезаем его
            if len(text) > 4000:
                text = text[:4000]
            
            # Формируем музыкальный запрос на основе текста и эмоций
            if emotion_analysis and 'primary_emotions' in emotion_analysis:
                # Определяем основные параметры на основе эмоций
                emotions = [e['emotion'] for e in emotion_analysis['primary_emotions']]
                intensities = [e['intensity'] for e in emotion_analysis['primary_emotions']]
                avg_intensity = sum(intensities) / len(intensities) if intensities else 5
                
                # Определяем жанр и настроение на основе эмоций
                mood = emotion_analysis.get('emotional_tone', 'reflective')
                
                # Создаем более точное описание для музыки
                music_prompt = f"""
                Create emotional music that captures the following mood from a war diary:
                
                Main emotions: {', '.join(emotions[:3])}
                Overall tone: {mood}
                Setting: Military, wartime, {self._determine_music_genre(emotions)}
                
                The music should convey the emotions of {', '.join(emotions[:2])} with 
                intensity level {avg_intensity}/10 and reflect the atmosphere of war experiences.
                
                Make it {self._determine_tempo(emotions, intensities)} with 
                {self._determine_instruments(emotions)} as primary instruments.
                
                Context from the diary: "{text[:500]}..."
                """
            else:
                # Базовое описание, если нет эмоционального анализа
                music_prompt = f"""
                Create emotional music that captures the mood of this war diary:
                
                "{text[:500]}..."
                
                The music should reflect the atmosphere of wartime experiences, 
                emotional and reflective, with a mix of tension and contemplation.
                """
            
            print("Отправка запроса для генерации музыки...")
            
            # Создаем запрос к LLM для получения описания музыки для MusicGen
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert music composer who creates detailed prompts for AI music generation. Focus on emotional qualities, instruments, tempo, and mood."},
                    {"role": "user", "content": music_prompt}
                ],
                temperature=0.7
            )
            
            # Получаем описание музыки
            music_description = response.choices[0].message.content.strip()
            print(f"Получено описание музыки: {music_description[:100]}...")
            
            # Сохраняем описание как MIDI файл (заглушка - реальная интеграция требует MusicGen API)
            # В реальности здесь был бы вызов MusicGen API
            music_filename = f"music_{int(datetime.now().timestamp())}.mp3"
            music_path = os.path.join("static", "generated_music", music_filename)
            
            # Создаем директорию, если не существует
            os.makedirs(os.path.dirname(music_path), exist_ok=True)
            
            # Поскольку у нас нет прямого доступа к MusicGen, создаем файл с описанием
            with open(music_path.replace('.mp3', '.txt'), 'w', encoding='utf-8') as f:
                f.write(music_description)
                
            # URL для эмбеда YouTube с классической военной музыкой (как заглушка)
            # В реальном приложении здесь был бы URL сгенерированной музыки
            demo_music_urls = [
                "https://www.youtube.com/embed/YPn6_YZGQWs",  # The Great Escape
                "https://www.youtube.com/embed/wULy5uEtTyY",  # Band of Brothers Theme
                "https://www.youtube.com/embed/TmIwm5RElRs",  # Saving Private Ryan
                "https://www.youtube.com/embed/e2LLS33eQvk",  # We Were Soldiers
                "https://www.youtube.com/embed/vKa2qtIbU6g"   # 1917 Theme
            ]
            import random
            demo_url = random.choice(demo_music_urls)
                
            return {
                'success': True,
                'music_description': music_description,
                'embed_url': demo_url,
                'local_path': music_path.replace('.mp3', '.txt'),
                'filename': music_filename.replace('.mp3', '.txt')
            }
            
        except Exception as e:
            print(f"Ошибка при генерации музыки: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'error': str(e)
            }
    
    def _determine_music_genre(self, emotions):
        """Определяет жанр музыки на основе эмоций"""
        if any(e in ['страх', 'ужас', 'тревога', 'fear', 'anxiety', 'panic'] for e in emotions):
            return "tense orchestral"
        elif any(e in ['грусть', 'печаль', 'скорбь', 'sadness', 'grief', 'sorrow'] for e in emotions):
            return "melancholic orchestral"
        elif any(e in ['надежда', 'решимость', 'hope', 'determination', 'courage'] for e in emotions):
            return "triumphant orchestral"
        else:
            return "dramatic orchestral"
    
    def _determine_tempo(self, emotions, intensities):
        """Определяет темп музыки на основе эмоций и их интенсивности"""
        avg_intensity = sum(intensities) / len(intensities) if intensities else 5
        
        if any(e in ['страх', 'fear', 'anxiety', 'panic'] for e in emotions) and avg_intensity > 7:
            return "fast-paced and intense"
        elif any(e in ['грусть', 'sadness', 'grief'] for e in emotions):
            return "slow and contemplative"
        elif avg_intensity > 7:
            return "dynamic with building tension"
        else:
            return "moderate with emotional depth"
    
    def _determine_instruments(self, emotions):
        """Определяет инструменты на основе эмоций"""
        if any(e in ['страх', 'ужас', 'fear', 'anxiety', 'panic'] for e in emotions):
            return "low strings and percussion"
        elif any(e in ['грусть', 'печаль', 'скорбь', 'sadness', 'grief'] for e in emotions):
            return "cello and piano"
        elif any(e in ['надежда', 'решимость', 'hope', 'determination'] for e in emotions):
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