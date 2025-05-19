import os
from dotenv import load_dotenv
import openai
import json

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
        
        # Установка API ключа для старой версии библиотеки
        openai.api_key = self.api_key

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
            
            # Устанавливаем таймаут для запроса
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Вы - опытный военный психолог, специализирующийся на анализе военных дневников и воспоминаний. Всегда возвращайте ответ в формате JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                request_timeout=120  # Увеличиваем таймаут до 120 секунд
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
            response = openai.ChatCompletion.create(
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

    def process_diary(self, diary_text):
        """
        Основной метод для обработки текста дневника.
        
        Args:
            diary_text (str): Текст дневника для анализа
            
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
            
            # Генерация художественного произведения
            print("Начало генерации художественного произведения")
            generated_text = self.generate_literary_work(diary_text, emotions)
            print(f"Генерация завершена, длина текста: {len(generated_text)}")
            
            return {
                'original_text': diary_text,
                'emotion_analysis': emotions,
                'generated_literary_work': generated_text
            }
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
                'generated_literary_work': f"Произошла ошибка при обработке текста: {str(e)}"
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