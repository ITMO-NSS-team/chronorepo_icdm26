# ChronoRepo GUI: план веб-приложения для демо (ICDM 2026)

Документ описывает замену `demo/index.html` (статический прототип) на
полноценное веб-приложение: реальный движок `experiments/chrono.py` в
сервинг-режиме + фронтенд. Внутренний планировочный документ, статью не
меняет (см. §10 «Соответствие статье»).

---

## 1. Что не так с текущим demo/

`demo/index.html` — 34 КБ одного файла, в который `build_demo.py` регэкспом
инлайнит `demo_data.json`. Как макет он свою роль отыграл, но как демо
системы он не работает:

- **Индексация нарисована.** `runIndex()` (`index.html:301`) — это
  `setTimeout` по массиву `LOG` со строками «mining git history … 5,127
  commits» и чипы «312 files / 2.4 s», зашитые в HTML (`index.html:132-139`).
  Выбор «any GitHub URL — live indexing» стоит `disabled`.
- **Алгоритм в браузере — не наш алгоритм.** `buildAdj/propagate`
  (`index.html:266-290`) — плотная матрица 14×14, два шага, затухание
  `DECAY=0.55` по *годам*. В движке: `chrono.ppr` с `damping=0.5`,
  10 итераций по разреженным строкам, затухание `LAM=1/90` по *дням*,
  смешение слоёв `alpha=0.25`. Цифры на экране и цифры в статье считаются
  разным кодом.
- **Данных ровно на скриншот.** 14 файлов flask, 31 import-ребро,
  18 co-change-рёбер, 4 инстанса SWE-bench Lite. Ни одного репозитория
  кроме flask, ни одного issue кроме четырёх зашитых.
- **LLM-вызова нет.** Колонка «+ one 7B call» — предзаписанный `final`
  из `results/rerank_qwen_final_lite.jsonl`; «<$0.001» — текст, не счётчик.
- **Impact set не считается по-настоящему** и не показывает ROSE, хотя
  в статье ROSE — намеренно выделенный негативный результат (R@10 0.629
  против 0.577 у нашей пропагации).

Главное: абстракт обещает «The demo lets users index any GitHub repository
live in seconds and get ranked, evidence-annotated answers in milliseconds».
Сейчас это обещание не подкреплено ничем исполняемым. Цель работы — сделать
так, чтобы каждая цифра на экране приходила из того же кода, что и цифры
в таблицах.

---

## 2. Целевая архитектура

```
браузер (SPA)  ──HTTP/JSON + SSE──▶  uvicorn/FastAPI  ──▶  engine (serving)
                                                            └─▶ chrono.py
                                                            └─▶ night_lab.rrf_final
                                                            └─▶ git plumbing (bare clone)
                                                            └─▶ OpenRouter (опционально)
```

Один процесс, без БД и без брокера: индексы живут в памяти (LRU) и
сериализуются на диск в снапшоты. Фронтенд собирается Vite в статику и
отдаётся тем же uvicorn — на стенде запускается одна команда.

### 2.1 Стек и обоснование

| Слой | Выбор | Почему |
|---|---|---|
| Backend | Python 3.12 + FastAPI + uvicorn | движок уже на Python; нужен SSE для прогресса индексации, схемы ответов и один процесс на всё |
| Движок | `experiments/chrono.py` как есть + новый `engine/serving.py` | нулевой риск расхождения с экспериментами; `chrono` остаётся stdlib-only |
| Frontend | Vite + TypeScript + React | три-четыре экрана со связанным состоянием (выбранный репозиторий, файл, время) — на ванильном DOM это уже больно |
| Граф | graphology + sigma.js (WebGL), ForceAtlas2 в Web Worker | нужно держать до ~1500 узлов / 6000 рёбер (django-масштаб); d3-force на SVG умирает после ~500 |
| Стили | CSS-переменные, перенести палитру из текущего `index.html` | визуальный язык прототипа уже согласован со статьёй |
| Тесты | pytest (parity + API), Playwright (smoke трёх экранов) | parity-тест — ключевой, см. §5 |

Зависимости фронта фиксируются lock-файлом, `dist/` кладётся в
`demo/web/dist` и коммитится тегом релиза — на стенде node не нужен.

**Отвергнутые альтернативы.**
*Pure-stdlib `http.server` + ванильный ESM*: сохранил бы «zero deps» дух
репозитория, но SSE, роутинг, валидация и состояние фронта пишутся руками —
это тот же объём работы с худшим результатом. FastAPI изолирован в
`demo/`, корневой пайплайн остаётся stdlib.
*Streamlit / Gradio*: полчаса до прототипа, но интерактивный граф со
слайдером времени и три синхронизированные колонки там не делаются;
демо-трек оценивает именно интерфейс.

### 2.2 Ключевой рефакторинг: индекс вместо контекста инстанса

`night_lab.build_context()` заточен под инстанс бенчмарка: он принимает
`inst` с `base_commit` и `problem_statement` и на каждый вызов пересобирает
*всё* — дерево, блобы, BM25, оба слоя (~6 с медиана по статье). Для сервинга
нужно разделить на «дорого и один раз» и «дёшево на каждый запрос»:

```python
# demo/app/engine/serving.py
@dataclass
class RepoIndex:
    repo: str; rev: str; built_at: float
    files: dict[str, str]            # path -> blob sha  (chrono.tree_at)
    py_paths: list[str]; py_idx: dict[str, int]
    bm25: chrono.BM25                # по всем текстовым файлам
    blob_cache: chrono.BlobCache     # idents для grep-затравки
    s_edges: dict[tuple, float]      # chrono.static_edges
    t_dec: dict[tuple, float]        # chrono.temporal_edges(LAM)
    t_raw: dict[tuple, float]        # то же без затухания -> evidence «x47»
    rows_s, rows_t: dict             # chrono.row_normalized
    recency: dict[str, float]; freq: Counter
    buckets: dict[tuple, list[int]]  # co-change по месяцам -> таймлайн
    last_seen: dict[tuple, int]      # unix ts последнего совместного коммита
    stats: IndexStats                # коммиты, файлы, рёбра, тайминги, RSS
```

- `build_index(repo_dir, rev="HEAD", *, progress=cb) -> RepoIndex` —
  повторяет последовательность `build_context`, но без issue-зависимых
  частей и с колбэком прогресса на каждой стадии.
- `localize(index, issue_text, *, depth=100)` — считает на запрос только
  `seed_bm` (BM25), `seed_gr` (`grep_scores`), `seed_path`,
  `explicit_paths`, затем два `hybrid_rank` и `night_lab.rrf_final(ctx,
  k=40, exclude=("gr",))`. `ctx` собирается как тонкий адаптер-словарь над
  `RepoIndex`, то есть **рецепт статьи вызывается буквально тем же кодом**,
  а не переписывается.
- `impact(index, seed_file, k=20)` — четыре ранжирования разом: `rose`
  (сырые co-change счётчики), `temporal_ppr`, `static_ppr`,
  `hybrid_a25` — те же конфиги, что в `run_e3.py:CONFIGS`.
- `explain(index, a, b)` — evidence-чипы; логику берём из
  `prepare_rerank50.evidence_str` (вынести в `engine/evidence.py`, чтобы
  скрипты эксперимента и демо использовали одну функцию): co-change ×N
  + месяц последнего, import-ребро, двухшаговый мост.
- `subgraph(index, *, focus=None, limit=400)` — то, что реально уезжает на
  фронт: либо top-N по co-change-вовлечённости, либо k-hop окрестность
  выбранного файла.

Исторический срез (`ancestor_set` + `base_ts`) остаётся параметром
`build_index`: это нужно и для parity-тестов, и для демо-режима «показать
репозиторий, каким он был до фикса».

### 2.3 Клонирование

`git clone --bare --filter=blob:none --no-checkout https://github.com/<o>/<r>`:
`log --numstat` (весь темпоральный слой) блобы не требует, поэтому
скачивается только история; блобы дерева HEAD подтягиваются лениво пачками
через уже существующий `BlobCache.load_missing` (`cat-file --batch` по 400
шт.). Для django это разница между ~300 МБ и несколькими десятками.
Повторный вход в тот же репозиторий — `git fetch` + инкрементальный
`mine_history` (кеш пикла уже есть в `chrono.mine_history`).

### 2.4 Кеш и снапшоты

- Память: LRU по числу индексов и лимиту RSS (по умолчанию 2 индекса /
  1.5 ГБ, конфигурируемо).
- Диск: `demo/snapshots/<owner>__<repo>@<sha12>.pkl` — pickle `RepoIndex`
  без `blob_cache.tokens` (BM25 уже построен). Рестарт сервера — индекс
  поднимается за сотни мс.
- Бандл для стенда: 4–6 предсобранных снапшотов (flask, requests, seaborn,
  sphinx, django — последний как «масштабный»), скачиваются отдельным
  скриптом, чтобы не попасть в git.

---

## 3. HTTP API

Все ответы — JSON, ошибки — `{"error": {"code", "message"}}`.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/api/repos` | список доступных: снапшоты + уже проиндексированные в памяти |
| `POST` | `/api/index` | `{repo_url, rev?}` → `{job_id, repo_id}`; ставит задачу в очередь |
| `GET` | `/api/index/{job_id}/events` | **SSE**: прогресс индексации (см. ниже) |
| `GET` | `/api/repos/{id}` | статистика индекса: файлы, коммиты, рёбра по слоям, тайминги стадий, RSS |
| `GET` | `/api/repos/{id}/graph` | `?focus=&limit=&layers=static,temporal` → узлы/рёбра подграфа + помесячные бакеты |
| `GET` | `/api/repos/{id}/impact` | `?file=&k=` → 4 ранжирования с evidence |
| `POST` | `/api/repos/{id}/localize` | `{issue_text \| issue_url, depth, llm: {enabled, model}}` |
| `GET` | `/api/instances` | бандл-инстансы бенчмарка (issue + gold + предзаписанный rerank) |
| `GET` | `/api/benchmarks` | таблицы и Pareto-точки из `results/` |

**SSE индексации** — реальные стадии движка, не анимация:

```
event: stage  data: {"stage":"clone","status":"start"}
event: stage  data: {"stage":"clone","status":"done","ms":8410,"bytes":42117632}
event: stage  data: {"stage":"history","status":"done","ms":2120,"commits":5127,"dropped_bulk":214}
event: stage  data: {"stage":"tree","status":"done","ms":180,"files":312}
event: stage  data: {"stage":"blobs","status":"progress","done":260,"total":312}
event: stage  data: {"stage":"imports","status":"done","ms":640,"edges":418}
event: stage  data: {"stage":"temporal","status":"done","ms":950,"edges":9127}
event: ready  data: {"repo_id":"pallets__flask@a1b2c3d","total_ms":13100,"rss_mb":186}
```

**Ответ `localize`** — стадии с таймингами, кандидат несёт своё «почему»:

```json
{
  "timings_ms": {"bm25": 41, "grep": 28, "paths": 6, "ppr": 63, "fuse": 4, "llm": 1180},
  "stages": {
    "bm25":       ["docs/intro/tutorial05.txt", "..."],
    "candidates": ["django/db/models/fields/__init__.py", "..."],
    "final":      ["django/db/models/enums.py", "..."]
  },
  "candidates": [
    {"file": "django/db/models/enums.py", "rank": 23, "rrf": 0.0412,
     "sources": [{"list": "ppr_bm", "rank": 11, "contrib": 0.0196},
                 {"list": "rec", "rank": 34, "contrib": 0.0135},
                 {"list": "path", "rank": 8, "contrib": 0.0208}],
     "evidence": [{"kind": "cochange", "with": "fields/__init__.py", "count": 47,
                   "last": "2019-05"},
                  {"kind": "import", "with": "base.py"}]}
  ],
  "cost": {"prompt_tokens": 1832, "completion_tokens": 96, "usd": 0.00041,
           "model": "qwen/qwen3.5-9b"}
}
```

Разложение RRF (`sources`) — то, чего в прототипе нет вовсе, и оно прямо
показывает механику из таблицы абляции: видно, какой из шести списков
поднял файл.

### 3.1 LLM-прокси

Ключ живёт только на сервере (`OPENROUTER_API_KEY` или
`experiments/.openrouter_key`, как в `run_rerank.py`). Промпт и парсер
ответа переиспользуются: `run_rerank.build_prompt` / `call_llm` выносятся
в `engine/rerank.py`, `run_rerank.py` импортирует их оттуда (одна
формулировка промпта в репозитории). Стоимость считается из настоящего
`usage` в ответе OpenRouter × прайс модели из `demo/app/pricing.json` —
счётчик перестаёт быть картинкой. Лимиты: N вызовов в минуту на IP,
жёсткий таймаут, кнопка выключения live-LLM в конфиге.

---

## 4. Экраны

Три вида из §Interface статьи сохраняются как основные вкладки; добавляются
экран индексации (он и так есть по факту) и экран результатов.

### 4.1 Index — «дай URL, получи граф»
Поле GitHub URL + список снапшотов. Во время индексации — живой лог стадий
из SSE с настоящими миллисекундами и настоящим числом коммитов, прогресс-бар
по блобам. По завершении — чипы статистики и разблокировка вкладок.
Показываем «повторная индексация после коммита: N изменённых блобов» —
это иллюстрация инкрементальности из §Indexing.

### 4.2 Graph & timeline
sigma.js, узлы = файлы (размер — co-change-вовлечённость, цвет — каталог),
рёбра двух цветов: import (сплошные) и co-change (пунктир, толщина =
затухающий вес). Управление: переключатели слоёв, поиск файла, фильтр по
каталогу, «показать окрестность файла» (k-hop), лимит узлов.

Слайдер времени: сервер отдаёт помесячные бакеты `buckets[(a,b)]`, клиент
пересчитывает `w = Σ c_i·exp(-λ·Δдней)` с **тем же** `λ=1/90` — 16 мс на
кадр, без обращений к серверу. Кнопка «play» проигрывает историю. Внизу —
подпись живого сюжета: пара файлов, которую не связывает ни один import,
но которая светится в конкретную эпоху рефакторинга (сценарий из статьи,
шаг 2).

### 4.3 Impact set
Выбор файла (клик по узлу или поиск) → таблица top-k с evidence-чипами
(«co-changed ×47, last in May 2019», «imports config.py», «bridge:
helpers.py»). Переключатель метода: ROSE / temporal-PPR / static-PPR /
hybrid — с честной подписью, что на этой задаче двадцатилетний счётчик
ROSE выигрывает (R@10 0.629 vs 0.577), это результат из статьи, а не баг.
Метр латентности показывает реальное время `impact()` (единицы мс).
Плашка: «лексический поиск здесь неприменим по построению».

### 4.4 Issue → files
Ввод: свободный текст, GitHub issue URL (подтягиваем title+body через
публичный API) или выбор бенчмарк-инстанса. Три колонки — BM25 /
кандидаты ChronoRepo / +один вызов модели — с реальными таймингами и
стоимостью. Для бенчмарк-инстансов подсвечиваются gold-файлы и показывается
ранг gold на каждой стадии (23 → 1 у django-11964 — самый убедительный
кадр демо). Клик по кандидату раскрывает панель «почему»: разложение RRF по
шести спискам + evidence-цепочка (какой файл-затравка связан с этим
кандидатом и каким ребром). Тумблер «с LLM / без LLM» и выбор модели.

### 4.5 Benchmarks
Не обязательный для статьи, но дешёвый экран: Pareto Acc@5 × стоимость
(наши точки vs процитированные LocAgent/SweRank/агенты), таблицы LocBench
и абляции. Данные — из `results/summary*.md` и `results/ablation/`,
конвертируются в `snapshots/benchmarks.json` скриптом сборки. Это заменяет
статические цифры в подзаголовке прототипа.

### 4.6 Режимы работы
- `live` — клонирование произвольного репозитория (стенд с сетью);
- `snapshot` — только предсобранные индексы, всё считается по-настоящему,
  сети не требуется;
- `offline/booth` — snapshot + предзаписанные ответы LLM из
  `results/rerank_qwen_final_lite.jsonl` (страховка §Demo Scenario:
  «A bundled snapshot guarantees a smooth session without network»);
- `tour` — поверх любого из них: скриптованный сценарий из 4 шагов статьи
  с подсказками, чтобы демонстрацию мог провести любой из авторов.

---

## 5. Корректность: parity-тесты

Главный риск демо — «в приложении числа другие, чем в статье». Против него:

1. **`test_parity_candidates`** — для 20 инстансов из
   `data/rerank_final_lite.jsonl` строим индекс на их `base_commit` через
   `engine.build_index` и получаем basket через `engine.localize`;
   требуем **посписочного равенства** с сохранённым `hybrid_top`.
   Тест ловит любое расхождение адаптера `ctx` с `night_lab`.
2. **`test_parity_impact`** — на подвыборке из `results/e3.jsonl` сверяем
   R@10 для `rose` и `temporal_ppr` (допуск 0 — те же коммиты, тот же код).
3. **`test_leakage`** — при `rev=base_commit` в графе нет ни одного ребра
   из коммита-потомка (проверка `ancestor_set`, чтобы демо не «подглядывало»
   в будущее на бенчмарк-инстансах).
4. **`test_timeline_decay`** — клиентский пересчёт весов по бакетам
   (портируется в TS) совпадает с серверным `temporal_edges` в пределах 1e-6.
5. Smoke: индексация flask end-to-end < 60 с в CI, три экрана открываются
   (Playwright), SSE отдаёт `ready`.

---

## 6. Производительность: целевые бюджеты

| Операция | Бюджет | Основание |
|---|---|---|
| Индексация flask (холодный клон) | < 20 с | ~5 тыс. коммитов, 312 файлов |
| Индексация django (blobless) | < 3 мин, снапшот — < 5 с | ~30 тыс. коммитов, ~2.7 тыс. .py |
| `localize` без LLM | < 300 мс | BM25 + два PPR по разреженным строкам |
| `impact` | < 50 мс | одна пропагация |
| Кадр слайдера времени | < 16 мс | пересчёт на клиенте по бакетам |
| RSS на индекс | < 400 МБ (django) | §Footprint статьи |

Тяжёлые стадии уходят в `ThreadPoolExecutor` (git — subprocess, GIL не
мешает), одновременных индексаций не больше двух, очередь с отказом.

---

## 7. Безопасность и эксплуатация

Приложение по кнопке запускает `git clone` на URL из браузера, поэтому:
принимаем только `https://github.com/<owner>/<repo>` по строгому regex
(без ssh, без `file://`, без произвольных хостов), `subprocess` без
`shell=True` (уже так в `chrono.git`), таймауты на все git-вызовы, лимит
размера скачанного, отдельный рабочий каталог, rate-limit на
`/api/index` и `/api/repos/*/localize`, `live`-режим выключается одной
настройкой. Ключ OpenRouter никогда не уходит на клиент. CORS закрыт,
кроме локального dev-origin.

---

## 8. Структура каталогов

```
demo/
  README.md                  запуск в трёх режимах
  pyproject.toml             requires-python >=3.12, fastapi, uvicorn
  app/
    main.py                  FastAPI, роуты, отдача web/dist
    config.py                режимы, лимиты, пути
    jobs.py                  очередь индексаций + SSE-шина
    pricing.json             цены моделей для счётчика стоимости
    engine/
      serving.py             RepoIndex, build_index, localize, impact, subgraph
      evidence.py            evidence_str (общий с prepare_rerank*.py)
      rerank.py              промпт + вызов OpenRouter (общий с run_rerank.py)
      clone.py               blobless clone / fetch / валидация URL
      snapshots.py           pickle-снапшоты, LRU
    schemas.py               pydantic-модели ответов
  web/
    src/{App.tsx,api.ts,state.ts,views/{Index,Graph,Impact,Issue,Bench}.tsx,
         components/{GraphCanvas,Timeline,RankColumn,EvidenceChips,Meters}.tsx}
    dist/                    собранная статика (коммитится к релизу)
  scripts/
    build_snapshots.py       предсобранные индексы для стенда
    build_benchmarks.py      results/summary*.md -> benchmarks.json
  tests/                     parity, api, e2e
  legacy/index.html          текущий прототип, до приёмки нового
```

Удаляются после приёмки: `demo/build_demo.py`, `demo/demo_data.json`
(их роль берут `scripts/build_snapshots.py` и снапшоты).
`experiments/export_demo_data.py` остаётся только как экспортёр
бенчмарк-инстансов для `/api/instances`.

---

## 9. Этапы

| Этап | Содержание | Оценка |
|---|---|---|
| M0 | `engine/serving.py`: `RepoIndex`, `build_index`, `localize` + parity-тест №1 | 1.5 дня |
| M1 | FastAPI-скелет, SSE-индексация, `impact`, `graph`, снапшоты | 1.5 дня |
| M2 | Фронт: каркас, экран Index, Graph & timeline на sigma.js | 2 дня |
| M3 | Impact set и Issue → files (три колонки, «почему», метры) | 2 дня |
| M4 | LLM-прокси со счётчиком стоимости, offline/booth-режим, tour | 1 день |
| M5 | Benchmarks-экран, e2e-тесты, README, сборка снапшотов для стенда | 1 день |

M0–M3 дают демонстрируемую систему; M4–M5 — то, что делает её пригодной
для стенда конференции. Точка невозврата — parity-тест на M0: пока
кандидаты не воспроизводятся байт в байт, дальше идти нельзя.

---

## 10. Соответствие статье

- §Interface («Three views, shown live») — вкладки 4.2–4.4 сохраняют
  формулировки один в один; текст статьи править не нужно.
- §Demo Scenario, шаги 1–4 — маппятся на `tour`-режим: (1) вставка URL и
  реальная индексация, (2) слайдер истории, (3) клик по файлу → impact set
  с evidence, (4) issue → BM25 vs ChronoRepo со счётчиком стоимости.
- Абстракт «index any GitHub repository live in seconds» — становится
  исполняемым утверждением (§2.3 + §6); имеет смысл после M1 перемерить
  тайминги на демо-машине и, если они разойдутся с §Footprint, обновить
  цифры в статье, а не в интерфейсе.
- §Evaluation, Impact set — экран 4.3 честно показывает превосходство ROSE,
  как и обещано в тексте («We report this negative result prominently»).
- Fig. `walkthrough.pdf` — после M3 можно перерисовать из настоящих
  скриншотов приложения вместо синтетической схемы.

## 11. Открытые вопросы — решено

1. **Стенд с сетью** → `live` режим по умолчанию, `snapshot`/`booth`
   остаются флагом `CHRONO_MODE`.
2. **Бюджет OpenRouter есть** → счётчик стоимости считает настоящие вызовы
   (usage из ответа × цена модели из `/api/v1/models`), предзаписанные
   ответы нужны только в `booth`.
3. **Наружу не публикуем** → rate-limit оставлен базовым (6 индексаций и
   20 LLM-вызовов в минуту на IP), CORS открыт только для локального dev.

---

# Статус реализации (готово)

Реализовано по плану; ниже — что построено, что измерено и в чём пришлось
отойти от документа выше.

## Что построено

`demo/app/` — FastAPI-бэкенд поверх `experiments/chrono.py`:
`engine/serving.py` (RepoIndex + localize/impact/subgraph), `engine/clone.py`
(валидация URL + bare-клон с прогрессом), `engine/snapshots.py`,
`engine/rerank.py` (один LLM-вызов), `engine/evidence.py`, `store.py` (LRU),
`jobs.py` (фоновые задачи + SSE), `bench.py`, `main.py` (API + раздача SPA).
`demo/web/` — Vite + React + TS + sigma.js, пять экранов из §4.
`demo/tests/` — 24 теста (16 parity + 8 API). `demo/scripts/build_snapshots.py`.
Прототип перенесён в `demo/legacy/`.

## Парити подтверждён

`demo/tests/test_parity.py` на четырёх реальных инстансах (requests ×2,
flask, seaborn): `_fuse` == `night_lab.rrf_final(k=40, exclude=("gr",))`,
корзина == `data/rerank_final_lite.jsonl`, однопроходный майнер пар ==
`chrono.temporal_edges` (сырой и затухающий), чипы evidence рендерятся в
строки `prepare_rerank50.evidence_str`, в граф не попадает ни один
коммит вне ancestor-множества base_commit, а формула слайдера на клиенте
воспроизводит серверный вес рёбер. Сквозная проверка через HTTP:
django-11964 живьём даёт BM25 — промах, кандидаты — ранг 23, после одного
вызова 7B — ранг 1, то есть ровно записанный прогон.

## Измерено (эта машина, один процесс)

| операция | факт |
|---|---|
| клон django (238 МБ) + индекс | 85 с + 28 с (history 16 с, imports 7.2 с) |
| индекс django из снапшота | 0.3 с |
| индекс flask (клон в кеше) | 0.6 с |
| `localize` без LLM, django (2 576 py) | 294 мс |
| `localize` без LLM, flask | 5–11 мс |
| `impact`, django / flask | 160 мс / 4 мс |
| подграф для визуализации, django | 18–28 мс |
| один вызов Qwen2.5-7B по 50 кандидатам | 0.9 с, $0.00006 |
| RSS с индексом django | 240 МБ |

Бюджеты §6 выдержаны; `localize` на django упирается в две пропагации по
2 576 узлам (137 мс), смешение слоёв закешировано по α.

## Отклонения от плана

1. **Blobless-клон отвергнут по замеру.** `--filter=blob:none` тянет блобы
   лениво, по одному раунд-трипу: 60 блобов psf/requests — 49 с. Полный
   `--bare --no-tags --single-branch` того же репозитория — 5.7 с. Клонируем
   полностью; `--single-branch` безопасен, потому что всё ниже по течению
   и так фильтруется ancestor-множеством ревизии.
2. **`web/dist` не коммитится** (в `.gitignore`), на стенде нужен один
   `npm run build`. Если решим, что node на стенде нежелателен, — снять
   `demo/web/dist/` из `.gitignore` перед выездом.
3. **`build_benchmarks.py` не писался.** Таблицы лидерборда
   (`demo/data/leaderboard.json`) выписаны из таблиц I–V статьи —
   единственного авторитетного источника; генератор из `results/summary*.md`
   дал бы то же самое с риском расхождения парсинга.
4. **Добавлено сверх плана:** кнопка «index the pre-fix revision» на экране
   Issue → files (без индекса на base_commit ранги не совпадают с
   записанным прогоном), поиск файлов, `freq`-базлайн на экране impact set,
   защита от path traversal в раздаче SPA.
5. **Тайминги статьи (§Footprint) не перепроверялись** на демо-машине —
   цифры выше сняты здесь и с методикой статьи (Windows, один core) прямо
   не сопоставимы.

## Что осталось

- Playwright-smoke трёх экранов (в §5 планировался; сейчас UI проверен
  только сборкой и типами — визуально его нужно открыть глазами).
- Перерисовка `figs/walkthrough.pdf` из скриншотов приложения.
- Прогон `build_snapshots.py --instances` на машине стенда.