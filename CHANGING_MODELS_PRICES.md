# Как поменять тарифы (цены) на модели

Справочная заметка о том, где и как считаются/хранятся цены на модели в стеке
Hermes WebUI + Hermes Agent.

## Главное

**Сам WebUI цены по токенам НЕ считает.** Прайс (цена за 1M входных/выходных/кэш-токенов
на модель) живёт в движке **Hermes Agent**. WebUI берёт у агента уже готовую оценку
стоимости `session_estimated_cost_usd` и дальше её только хранит, суммирует и показывает.

Цепочка:

```
Hermes Agent считает session_estimated_cost_usd
  → api/streaming.py читает его и считает дельту за ход
  → api/state_sync.py + индекс сессий сохраняют estimated_cost / estimated_cost_usd
  → api/routes.py агрегирует для дашбордов (Activity/инсайты)
```

## Где лежит таблица тарифов

Единственный источник расчёта стоимости — файл движка Hermes Agent:

```
agent/usage_pricing.py
```

Внутри — словарь `_OFFICIAL_DOCS_PRICING`, ключ `(provider, model)`, значение `PricingEntry`.
Цены в **USD за 1 млн токенов**:

```python
PricingEntry(
    input_cost_per_million=Decimal("3.00"),      # вход
    output_cost_per_million=Decimal("15.00"),    # выход
    cache_read_cost_per_million=Decimal("0.30"), # чтение кэша
    cache_write_cost_per_million=Decimal("3.75"),# запись кэша
    request_cost=None,                           # фикс. плата за запрос (если есть)
    source="official_docs_snapshot",
    ...
)
```

Алиасы/варианты (напр. `-pro`, preview-ID) регистрируются в alias-блоках внизу файла
(циклы по `_OFFICIAL_DOCS_PRICING[...] = _OFFICIAL_DOCS_PRICING[...]`), а не дублированием записи.

## Точные пути на машине (dev-песочница)

Файл существует в **двух одинаковых по содержимому, но разных** копиях:

| Путь | Что это |
|---|---|
| `/home/hermeswebui/.hermes/hermes-agent/agent/usage_pricing.py` | **грузит WebUI** — `_discover_agent_dir()` резолвит сюда (`HERMES_HOME/hermes-agent`) |
| `/app/hermes-agent-src/agent/usage_pricing.py` | вторая копия (staged-исходники, кладёт `docker_init.bash:474`) |

Проверено запуском кода обнаружения:

```
resolved _AGENT_DIR = /home/hermeswebui/.hermes/hermes-agent
```

Менять надо ту, что в `~/.hermes/hermes-agent`. Правка одной копии **не** затрагивает другую.

Оба каталога на этой машине — **не git-репозитории** (обычные копии; `.hermes/hermes-agent`
принадлежит `root`). Поэтому правильный способ — вносить правку в исходники `hermes-agent`
и пересобирать/передеплоить, а не править копию на сервере вручную (иначе потеряется при
следующем редеплое).

## Как резолвится цена (зависит от провайдера)

Порядок в `get_pricing_entry()` / `resolve_billing_route()`:

| Маршрут | Откуда берётся цена |
|---|---|
| `openai-codex`, subscription-маршруты | `$0` |
| **OpenRouter** | живой запрос к OpenRouter `/models` |
| **Nous** / кастомный `base_url` | живой запрос `/models` у этого endpoint |
| прямые **OpenAI / Anthropic / Google / MiniMax / Fireworks** | **хардкод-таблица `_OFFICIAL_DOCS_PRICING`** |
| `custom` / `local` / неизвестный | `$0` (прайс неизвестен) |

→ Правка таблицы действует **только на прямых провайдеров**. OpenRouter / Nous /
custom-эндпоинты тянут цену живьём и таблицу не смотрят.

## Как поменять тариф

**Прямой провайдер** — отредактировать запись в `_OFFICIAL_DOCS_PRICING` (изменить `Decimal`-поля).

**Новая модель** — добавить новый ключ `(provider, model)` в тот же словарь.

**Варианты/алиасы** — alias-блоки внизу файла.

После правки **перезапустить процесс** WebUI/агента — таблица читается при импорте модуля.

## Ограничения

1. **Конфиг-переопределения нет.** В коде объявлены enum-значения `user_override` /
   `custom_contract`, но они ни к какому файлу/ключу не подключены — отдельного
   «кастомного прайса» в `config.yaml` или JSON сейчас нет.
2. **OpenRouter / Nous / custom-endpoint не затронуты** правкой таблицы. Чтобы зафиксировать
   для них свою цену, придётся менять логику резолва (`get_pricing_entry`) — отдельная правка кода.
3. **Пикер моделей показывает другую цену**, чем биллинг: `hermes_cli/models.py`
   (`input_token_price_per_m` / `output_token_price_per_m`) и `inventory.py` берут
   рекламируемую цену провайдера для отображения — это отдельно от `usage_pricing.py`,
   который реально считает стоимость. После ручной правки тарифа цена в пикере может
   расходиться со счётчиком стоимости.

## Как определить живой путь на боевом сервере

На проде (Docker/Coolify) путь зависит от окружения контейнера. Порядок поиска
`api/config.py::_discover_agent_dir()`:

1. `HERMES_WEBUI_AGENT_DIR` (env) — если задан, всегда побеждает;
2. `HERMES_HOME/hermes-agent`;
3. соседний/родительский `hermes-agent` относительно репо;
4. `~/.hermes/hermes-agent`, `~/hermes-agent`, XDG, `/opt`, `/usr/local`, `/usr/local/share`.

Точный путь на проде — в контейнере WebUI:

```bash
python3 -c "import api.config as c; print(c._AGENT_DIR)"
```

→ это и есть каталог, внутри которого лежит `agent/usage_pricing.py` для правки.

## Смежный механизм (не путать с тарифами)

- `api/providers.py` + `api/config.py` — **бюджет и история расходов по провайдеру**
  (лимит `provider_cost_budget`, снапшоты, OpenRouter `/auth/key`). Это алертинг по лимитам,
  а не расчёт цены.
- `api/config.py` (загрузка каталога OpenRouter) смотрит `pricing.prompt`/`pricing.completion`
  **только чтобы пометить бесплатные модели** (`:free`), сами цены не хранит.
