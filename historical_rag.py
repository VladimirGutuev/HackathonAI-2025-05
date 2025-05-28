import os
import requests
import json
import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import hashlib

class HistoricalRAG:
    """
    Система RAG (Retrieval-Augmented Generation) для исторических данных.
    Использует открытые API Wikipedia и Historical Events для обогащения анализа военных дневников.
    """
    
    def __init__(self, db_path: str = "historical_rag.db", cache_dir: str = "rag_cache"):
        """
        Инициализация системы RAG
        
        Args:
            db_path: Путь к SQLite базе данных
            cache_dir: Папка для кэширования векторов
        """
        self.db_path = db_path
        self.cache_dir = cache_dir
        
        # Создаём папку для кэша если её нет
        os.makedirs(cache_dir, exist_ok=True)
        
        # Инициализируем базу данных
        self._init_database()
        
        # Векторизатор для semantic search
        self.vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=2
        )
        
        # Кэш для векторов
        self.vector_cache_path = os.path.join(cache_dir, "vectors.pkl")
        self.texts_cache_path = os.path.join(cache_dir, "texts.pkl")
        
        # Загружаем векторы из кэша если есть
        self._load_vectors_cache()
        
        # API эндпоинты
        self.wikipedia_api = "https://ru.wikipedia.org/w/api.php"
        self.historical_events_api = "http://www.vizgr.org/historical-events/search.php"
        
        print("HistoricalRAG инициализирован")

    def _init_database(self):
        """Инициализация SQLite базы данных для хранения исторических фактов"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица для исторических событий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                title TEXT,
                description TEXT,
                source TEXT,
                category TEXT,
                relevance_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hash TEXT UNIQUE
            )
        ''')
        
        # Таблица для Wikipedia статей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wikipedia_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                url TEXT,
                extract TEXT,
                categories TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                hash TEXT UNIQUE
            )
        ''')
        
        # Таблица для RAG результатов (кэш)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rag_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT UNIQUE,
                query_text TEXT,
                results TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_date ON historical_events(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_events_category ON historical_events(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_wiki_title ON wikipedia_articles(title)')
        
        conn.commit()
        conn.close()

    def _load_vectors_cache(self):
        """Загрузка векторов из кэша"""
        self.vectors = None
        self.cached_texts = []
        
        if os.path.exists(self.vector_cache_path) and os.path.exists(self.texts_cache_path):
            try:
                with open(self.vector_cache_path, 'rb') as f:
                    self.vectors = pickle.load(f)
                with open(self.texts_cache_path, 'rb') as f:
                    self.cached_texts = pickle.load(f)
                print(f"Загружено {len(self.cached_texts)} текстов из кэша")
            except Exception as e:
                print(f"Ошибка загрузки кэша: {e}")
                self.vectors = None
                self.cached_texts = []

    def _save_vectors_cache(self):
        """Сохранение векторов в кэш"""
        try:
            with open(self.vector_cache_path, 'wb') as f:
                pickle.dump(self.vectors, f)
            with open(self.texts_cache_path, 'wb') as f:
                pickle.dump(self.cached_texts, f)
            print("Векторы сохранены в кэш")
        except Exception as e:
            print(f"Ошибка сохранения кэша: {e}")

    def extract_dates_from_text(self, text: str) -> List[Tuple[str, str]]:
        """
        Извлечение дат из текста дневника
        
        Args:
            text: Текст для анализа
            
        Returns:
            Список кортежей (найденная_дата, контекст)
        """
        date_patterns = [
            # Русские даты
            r'(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+(\d{4})',
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{4})\s*г\.?',
            # Английские даты
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})',
            r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                date_str = match.group(0)
                # Контекст вокруг даты (50 символов до и после)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                dates.append((date_str, context))
        
        return dates

    def extract_historical_keywords(self, text: str, emotion_analysis: Dict = None) -> List[str]:
        """
        Извлечение исторических ключевых слов из текста
        
        Args:
            text: Текст для анализа
            emotion_analysis: Результаты эмоционального анализа
            
        Returns:
            Список ключевых слов для поиска
        """
        keywords = []
        
        # Военные термины
        military_terms = [
            'война', 'битва', 'сражение', 'фронт', 'атака', 'оборона', 'наступление',
            'танк', 'самолёт', 'артиллерия', 'винтовка', 'траншея', 'блиндаж',
            'командир', 'солдат', 'офицер', 'генерал', 'полк', 'дивизия', 'армия',
            'war', 'battle', 'front', 'attack', 'defense', 'tank', 'aircraft', 'artillery'
        ]
        
        # Географические объекты
        geo_terms = [
            'Москва', 'Ленинград', 'Сталинград', 'Курск', 'Берлин', 'Варшава',
            'Moscow', 'Leningrad', 'Stalingrad', 'Kursk', 'Berlin', 'Warsaw'
        ]
        
        # Исторические периоды
        historical_periods = [
            'Великая Отечественная война', 'Вторая мировая война', 'Первая мировая война',
            'World War II', 'World War I', 'WWII', 'WWI', '1941', '1942', '1943', '1944', '1945'
        ]
        
        all_terms = military_terms + geo_terms + historical_periods
        
        # Ищем термины в тексте
        text_lower = text.lower()
        for term in all_terms:
            if term.lower() in text_lower:
                keywords.append(term)
        
        # Добавляем ключевые слова из эмоционального анализа
        if emotion_analysis and 'thematic_analysis' in emotion_analysis:
            thematic = emotion_analysis['thematic_analysis']
            for category in ['military_characters', 'battle_locations', 'war_equipment', 'historical_events']:
                if category in thematic:
                    keywords.extend(thematic[category])
        
        return list(set(keywords))  # Убираем дубликаты

    def search_wikipedia(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Поиск в Wikipedia API
        
        Args:
            query: Поисковый запрос
            limit: Количество результатов
            
        Returns:
            Список статей Wikipedia
        """
        try:
            # Поиск статей
            search_params = {
                'action': 'opensearch',
                'search': query,
                'limit': limit,
                'namespace': 0,
                'format': 'json'
            }
            
            search_response = requests.get(self.wikipedia_api, params=search_params, timeout=10)
            search_data = search_response.json()
            
            if len(search_data) < 4:
                return []
            
            titles = search_data[1]
            descriptions = search_data[2]
            urls = search_data[3]
            
            articles = []
            
            # Получаем подробную информацию о каждой статье
            for i, title in enumerate(titles):
                article_params = {
                    'action': 'query',
                    'titles': title,
                    'prop': 'extracts|categories',
                    'exintro': True,
                    'explaintext': True,
                    'exsectionformat': 'plain',
                    'format': 'json'
                }
                
                article_response = requests.get(self.wikipedia_api, params=article_params, timeout=10)
                article_data = article_response.json()
                
                if 'query' in article_data and 'pages' in article_data['query']:
                    page_id = list(article_data['query']['pages'].keys())[0]
                    page_data = article_data['query']['pages'][page_id]
                    
                    extract = page_data.get('extract', descriptions[i] if i < len(descriptions) else '')
                    categories = [cat['title'] for cat in page_data.get('categories', [])]
                    
                    article = {
                        'title': title,
                        'extract': extract,
                        'url': urls[i] if i < len(urls) else '',
                        'categories': categories,
                        'source': 'wikipedia'
                    }
                    
                    articles.append(article)
                    
                    # Сохраняем в базу данных
                    self._save_wikipedia_article(article)
            
            return articles
            
        except Exception as e:
            print(f"Ошибка поиска в Wikipedia: {e}")
            return []

    def search_historical_events(self, query: str = None, begin_date: str = None, 
                                end_date: str = None, limit: int = 10) -> List[Dict]:
        """
        Поиск исторических событий
        
        Args:
            query: Поисковый запрос
            begin_date: Начальная дата (YYYYMMDD)
            end_date: Конечная дата (YYYYMMDD)
            limit: Количество результатов
            
        Returns:
            Список исторических событий
        """
        try:
            params = {
                'format': 'json',
                'limit': limit,
                'lang': 'en'  # Используем английский для лучшего покрытия
            }
            
            if query:
                params['query'] = query
            if begin_date:
                params['begin_date'] = begin_date
            if end_date:
                params['end_date'] = end_date
            
            response = requests.get(self.historical_events_api, params=params, timeout=15)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    events = []
                    
                    # Проверяем различные форматы ответа API
                    if isinstance(data, dict) and 'result' in data:
                        for event in data['result']:
                            if isinstance(event, dict):
                                event_data = {
                                    'date': event.get('date', ''),
                                    'title': event.get('title', ''),
                                    'description': event.get('description', ''),
                                    'category': event.get('category', ''),
                                    'source': 'historical_events_api'
                                }
                                events.append(event_data)
                                
                                # Сохраняем в базу данных
                                self._save_historical_event(event_data)
                    elif isinstance(data, list):
                        # Если API возвращает массив напрямую
                        for event in data:
                            if isinstance(event, dict):
                                event_data = {
                                    'date': event.get('date', ''),
                                    'title': event.get('title', ''),
                                    'description': event.get('description', ''),
                                    'category': event.get('category', ''),
                                    'source': 'historical_events_api'
                                }
                                events.append(event_data)
                                
                                # Сохраняем в базу данных
                                self._save_historical_event(event_data)
                    
                    return events
                    
                except json.JSONDecodeError:
                    # API вернул не JSON, возможно XML или HTML
                    print("API исторических событий вернул не JSON формат")
                    return []
            else:
                print(f"Ошибка API исторических событий: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Ошибка поиска исторических событий: {e}")
            return []

    def _save_wikipedia_article(self, article: Dict):
        """Сохранение статьи Wikipedia в базу данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаём хэш для проверки дубликатов
            content_hash = hashlib.md5(
                f"{article['title']}{article['extract']}".encode()
            ).hexdigest()
            
            cursor.execute('''
                INSERT OR IGNORE INTO wikipedia_articles 
                (title, content, url, extract, categories, hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                article['title'],
                article['extract'],
                article['url'],
                article['extract'],
                json.dumps(article['categories']),
                content_hash
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Ошибка сохранения Wikipedia статьи: {e}")

    def _save_historical_event(self, event: Dict):
        """Сохранение исторического события в базу данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Создаём хэш для проверки дубликатов
            content_hash = hashlib.md5(
                f"{event['date']}{event['title']}{event['description']}".encode()
            ).hexdigest()
            
            cursor.execute('''
                INSERT OR IGNORE INTO historical_events 
                (date, title, description, source, category, hash)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                event['date'],
                event['title'],
                event['description'],
                event['source'],
                event['category'],
                content_hash
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Ошибка сохранения исторического события: {e}")

    def get_relevant_historical_context(self, diary_text: str, emotion_analysis: Dict = None, 
                                      top_k: int = 5) -> List[Dict]:
        """
        Получение релевантного исторического контекста для текста дневника
        
        Args:
            diary_text: Текст дневника
            emotion_analysis: Результаты эмоционального анализа
            top_k: Количество наиболее релевантных результатов
            
        Returns:
            Список релевантных исторических фактов
        """
        print("Поиск релевантного исторического контекста...")
        
        # Извлекаем ключевые слова и даты
        keywords = self.extract_historical_keywords(diary_text, emotion_analysis)
        dates = self.extract_dates_from_text(diary_text)
        
        print(f"Найдены ключевые слова: {keywords[:5]}")  # Показываем первые 5
        print(f"Найдены даты: {[d[0] for d in dates[:3]]}")  # Показываем первые 3
        
        all_context = []
        
        # Поиск по ключевым словам
        for keyword in keywords[:3]:  # Ограничиваем количество запросов
            # Wikipedia
            wiki_results = self.search_wikipedia(keyword, limit=2)
            all_context.extend(wiki_results)
            
            # Исторические события
            historical_results = self.search_historical_events(query=keyword, limit=3)
            all_context.extend(historical_results)
        
        # Поиск по датам
        for date_str, context in dates[:2]:  # Ограничиваем количество дат
            try:
                # Пытаемся парсить дату для поиска событий
                year_match = re.search(r'(\d{4})', date_str)
                if year_match:
                    year = year_match.group(1)
                    begin_date = f"{year}0101"
                    end_date = f"{year}1231"
                    
                    date_events = self.search_historical_events(
                        begin_date=begin_date, 
                        end_date=end_date, 
                        limit=3
                    )
                    all_context.extend(date_events)
            except Exception as e:
                print(f"Ошибка обработки даты {date_str}: {e}")
        
        # Ранжируем результаты по релевантности
        if all_context:
            ranked_context = self._rank_context_by_relevance(diary_text, all_context)
            return ranked_context[:top_k]
        
        return []

    def get_historical_context_dict(self, diary_text: str, emotion_analysis: Dict = None, 
                                   top_k: int = 5) -> Dict:
        """
        Получение исторического контекста в формате словаря
        
        Args:
            diary_text: Текст дневника
            emotion_analysis: Результаты эмоционального анализа
            top_k: Количество наиболее релевантных результатов
            
        Returns:
            Словарь с информацией об историческом контексте
        """
        context_items = self.get_relevant_historical_context(diary_text, emotion_analysis, top_k)
        
        if context_items:
            context_type = 'full_context'
            if len(context_items) < 3:
                context_type = 'limited_context'
        else:
            context_type = 'no_context'
        
        return {
            'found_items': len(context_items),
            'context_items': context_items,
            'context_type': context_type,
            'summary': self.generate_historical_summary(context_items) if context_items else "Исторический контекст не найден."
        }

    def _rank_context_by_relevance(self, query_text: str, context_items: List[Dict]) -> List[Dict]:
        """
        Ранжирование контекста по релевантности
        
        Args:
            query_text: Исходный текст дневника
            context_items: Список найденных исторических фактов
            
        Returns:
            Отсортированный по релевантности список
        """
        if not context_items:
            return []
        
        try:
            # Подготавливаем тексты для векторизации
            context_texts = []
            for item in context_items:
                if 'extract' in item:
                    text = f"{item['title']} {item['extract']}"
                elif 'description' in item:
                    text = f"{item['title']} {item['description']}"
                else:
                    text = item.get('title', '')
                context_texts.append(text)
            
            if not context_texts:
                return context_items
            
            # Векторизуем тексты
            all_texts = [query_text] + context_texts
            
            # Если векторизатор не обучен, обучаем его
            if self.vectors is None:
                vectors = self.vectorizer.fit_transform(all_texts)
            else:
                vectors = self.vectorizer.transform(all_texts)
            
            # Вычисляем схожесть
            query_vector = vectors[0:1]
            context_vectors = vectors[1:]
            
            similarities = cosine_similarity(query_vector, context_vectors)[0]
            
            # Сортируем по схожести
            ranked_indices = np.argsort(similarities)[::-1]
            
            ranked_context = []
            for idx in ranked_indices:
                item = context_items[idx].copy()
                item['relevance_score'] = float(similarities[idx])
                ranked_context.append(item)
            
            return ranked_context
            
        except Exception as e:
            print(f"Ошибка ранжирования: {e}")
            return context_items

    def generate_historical_summary(self, context_items: List[Dict]) -> str:
        """
        Генерация краткого исторического резюме на основе найденного контекста
        
        Args:
            context_items: Список исторических фактов
            
        Returns:
            Краткое резюме исторического контекста
        """
        if not context_items:
            return "Исторический контекст не найден."
        
        summary_parts = []
        
        # Группируем по источникам
        wiki_items = [item for item in context_items if item.get('source') == 'wikipedia']
        events_items = [item for item in context_items if item.get('source') == 'historical_events_api']
        
        if wiki_items:
            summary_parts.append("📚 **Историческая справка из Wikipedia:**")
            for item in wiki_items[:2]:  # Берём топ-2
                title = item.get('title', '')
                extract = item.get('extract', '')[:200] + "..." if len(item.get('extract', '')) > 200 else item.get('extract', '')
                summary_parts.append(f"• **{title}**: {extract}")
        
        if events_items:
            summary_parts.append("\n📅 **Исторические события:**")
            for item in events_items[:3]:  # Берём топ-3
                date = item.get('date', '')
                title = item.get('title', '')
                description = item.get('description', '')[:150] + "..." if len(item.get('description', '')) > 150 else item.get('description', '')
                summary_parts.append(f"• **{date}**: {title} - {description}")
        
        return "\n".join(summary_parts)

    def enhance_analysis_with_context(self, analysis_result: Dict, historical_context: List[Dict]) -> Dict:
        """
        Обогащение результатов анализа историческим контекстом
        
        Args:
            analysis_result: Результаты анализа дневника
            historical_context: Найденный исторический контекст
            
        Returns:
            Обогащённые результаты анализа
        """
        enhanced_result = analysis_result.copy()
        
        # Добавляем исторический контекст
        enhanced_result['historical_context'] = {
            'found_items': len(historical_context),
            'context_items': historical_context,
            'summary': self.generate_historical_summary(historical_context)
        }
        
        # Добавляем флаг о наличии исторического обогащения
        enhanced_result['has_historical_enrichment'] = len(historical_context) > 0
        
        return enhanced_result

    def clear_cache(self):
        """Очистка кэша векторов"""
        try:
            if os.path.exists(self.vector_cache_path):
                os.remove(self.vector_cache_path)
            if os.path.exists(self.texts_cache_path):
                os.remove(self.texts_cache_path)
            self.vectors = None
            self.cached_texts = []
            print("Кэш очищен")
        except Exception as e:
            print(f"Ошибка очистки кэша: {e}")

    def get_database_stats(self) -> Dict:
        """Получение статистики базы данных"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM historical_events")
            events_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM wikipedia_articles")
            articles_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM rag_results")
            cache_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'historical_events': events_count,
                'wikipedia_articles': articles_count,
                'cached_results': cache_count,
                'vector_cache_exists': os.path.exists(self.vector_cache_path)
            }
            
        except Exception as e:
            print(f"Ошибка получения статистики: {e}")
            return {} 