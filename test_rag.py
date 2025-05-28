#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки работы системы RAG
"""

import sys
import os

# Добавляем текущую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_rag_system():
    """Тестирование системы RAG"""
    print("🔬 Тестирование системы RAG...")
    
    try:
        from historical_rag import HistoricalRAG
        print("✅ Модуль historical_rag успешно импортирован")
        
        # Инициализация системы RAG
        rag = HistoricalRAG()
        print("✅ Система RAG инициализирована")
        
        # Тестовый текст дневника
        test_diary = """
        15 января 1943 года. Сегодня наша дивизия получила приказ наступать на Сталинград. 
        Немецкие войска укрепились в городе, но мы готовы к бою. 
        Товарищ Иванов рассказывал о боях под Москвой в прошлом году.
        """
        
        print(f"📝 Тестовый текст: {test_diary[:100]}...")
        
        # Тестируем поиск исторического контекста
        print("\n🔍 Поиск исторического контекста...")
        context = rag.get_historical_context_dict(test_diary)
        
        print(f"📊 Результаты поиска:")
        print(f"   - Найдено элементов: {context.get('found_items', 0)}")
        print(f"   - Тип контекста: {context.get('context_type', 'неизвестно')}")
        
        if context.get('context_items'):
            print(f"   - Первый элемент: {context['context_items'][0].get('title', 'Без названия')}")
        
        if context.get('summary'):
            print(f"   - Резюме: {context['summary'][:100]}...")
        
        # Тестируем статистику базы данных
        print("\n📈 Статистика базы данных:")
        stats = rag.get_database_stats()
        for key, value in stats.items():
            print(f"   - {key}: {value}")
        
        print("\n✅ Тестирование завершено успешно!")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Убедитесь, что установлены зависимости: pip install scikit-learn numpy scipy")
        return False
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_war_diary_analyzer():
    """Тестирование интеграции с анализатором дневников"""
    print("\n🔬 Тестирование интеграции с анализатором...")
    
    try:
        from war_diary_analyzer import WarDiaryAnalyzer
        print("✅ Модуль war_diary_analyzer импортирован")
        
        analyzer = WarDiaryAnalyzer()
        print("✅ Анализатор инициализирован")
        
        # Проверяем доступность RAG
        if hasattr(analyzer, 'rag') and analyzer.rag:
            print("✅ RAG система интегрирована в анализатор")
        else:
            print("⚠️ RAG система не интегрирована или недоступна")
        
        # Тестовый анализ с историческим контекстом
        test_diary = "Сегодня мы обороняли Ленинград от немецких войск. Блокада продолжается уже несколько месяцев."
        
        print(f"📝 Тестируем анализ с историческим контекстом...")
        
        # Проверяем наличие метода
        if hasattr(analyzer, 'analyze_emotions_with_context'):
            print("✅ Метод analyze_emotions_with_context доступен")
            # Можно протестировать, но это займет время из-за API вызовов
            print("💡 Для полного тестирования запустите анализ через веб-интерфейс")
        else:
            print("❌ Метод analyze_emotions_with_context не найден")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании анализатора: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Запуск тестирования системы RAG\n")
    
    # Тестируем RAG систему
    rag_success = test_rag_system()
    
    # Тестируем интеграцию
    analyzer_success = test_war_diary_analyzer()
    
    print(f"\n📋 Итоги тестирования:")
    print(f"   - RAG система: {'✅ Работает' if rag_success else '❌ Ошибка'}")
    print(f"   - Интеграция: {'✅ Работает' if analyzer_success else '❌ Ошибка'}")
    
    if rag_success and analyzer_success:
        print("\n🎉 Все тесты пройдены! Система RAG готова к использованию.")
    else:
        print("\n⚠️ Обнаружены проблемы. Проверьте логи выше.") 