# Unlimited Parts

Учебный стенд интернет-магазина автозапчастей Parts Unlimited по дисциплине «Программная инженерия». На материалах магазина можно проследить путь от требования к задаче и связанному тест-кейсу.

| Раздел | Что в нём находится |
| --- | --- |
| [Исходный код магазина](app/) | Приложение Parts Unlimited для ASP.NET и его тестовые проекты |
| [Рабочие элементы](https://github.com/monin-1-lab/Unlimited-Parts/issues?q=is%3Aissue) | 16 эпиков, 22 функции, 18 элементов продуктового бэклога, 29 задач и 2 дефекта |
| [Спринты](https://github.com/monin-1-lab/Unlimited-Parts/milestones) | Шесть итераций. Элементы без назначенной итерации остаются в общем бэклоге |
| [Тест-план](test-plan.md) | 12 наборов, 71 тест-кейс и 154 шага с исходными ожидаемыми результатами, где они заданы |
| [Набор данных](parts-unlimited.json) | Идентификаторы, типы, состояния, приоритеты, итерации и связи из шаблона Microsoft |

В Issues метка `type:` задаёт тип элемента, `state:` сохраняет его исходное состояние. Элементы в состоянии `Done` закрыты. Например, в задаче *Provide tentative duration for shipping* есть ссылка на тест-кейс **12425**, который проверяет вывод расчётной даты доставки.

## Воспроизведение

В разделе [Actions](https://github.com/monin-1-lab/Unlimited-Parts/actions) доступны сборка генератора и подготовка стенда. Генератор собирается из исходников на .NET 8 в конфигурации Release для Windows x64. Артефакт `ADOGenerator-win-x64` включает исполняемый файл и шаблоны. Для заполнения GitHub скрипт `seed.py` сопоставляет спринты с Milestones и создаёт Issues по исходным ID. Повторный запуск распознаёт ранее созданные элементы.

Данные получены из [шаблона Gen-PartsUnlimited](https://github.com/microsoft/AzDevOpsDemoGenerator/tree/f5802c5769c21d29b1fdf48d0f0d8c0ee25be017/src/ADOGenerator/Templates/Gen-PartsUnlimited). Код магазина взят из [архива Microsoft PartsUnlimitedE2E](https://github.com/microsoft/PartsUnlimitedE2E/tree/221fab958efbdf8d05fd5b01466df2a2f46d5231/PartsUnlimited-aspnet45). [Лицензия шаблона](LICENSE-template.txt) · [Лицензия приложения](app/LICENSE)
