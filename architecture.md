Here is a complete architecture document (fully in Markdown) you can use to guide your build of the market-making MVP project.

⸻

Market-Making MVP — Full Architecture

⸻

📂 File & Folder Structure

mm_project/
├── README.md
├── Makefile
├── requirements.txt
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── configs/
│   ├── env.dev.yaml
│   ├── env.prod.yaml
│   └── strategy.yaml
├── data/
│   ├── raw/                     # Raw L2 tick data (parquet)
│   ├── processed/               # Feature-engineered data, fills CSVs
│   └── models/                  # Trained models (.pkl / .pt)
├── notebooks/                   # EDA, modeling experiments
├── src/
│   ├── __init__.py
│   ├── common/                  # Utilities and constants
│   │   ├── logging.py
│   │   └── utils.py
│   ├── data_feed/               # Market data ingestion
│   │   ├── binance_ws.py
│   │   ├── recorder.py
│   │   └── schemas.py
│   ├── storage/                 # State and persistence layer
│   │   ├── parquet_writer.py
│   │   ├── postgres.py
│   │   └── state_store.py
│   ├── lob/                     # Limit Order Book engine
│   │   ├── order_book.py
│   │   ├── match_engine.cpp
│   │   └── match_engine.pyx
│   ├── features/                # Microstructure feature generation
│   │   ├── imbalance.py
│   │   ├── volatility.py
│   │   └── micro_price.py
│   ├── models/                  # Fill probability, inventory models
│   │   ├── fill_prob.py
│   │   ├── inventory_skew.py
│   │   └── model_base.py
│   ├── strategy/                # Quote generation and risk logic
│   │   ├── naive_maker.py
│   │   ├── ev_maker.py
│   │   └── risk_manager.py
│   ├── backtest/                # Offline backtester
│   │   ├── simulator.py
│   │   └── metrics.py
│   ├── live/                    # Live trading loop
│   │   ├── engine.py
│   │   ├── binance_gateway.py
│   │   ├── signal_handler.py
│   │   └── healthcheck.py
│   ├── api/                     # Optional REST API
│   │   └── rest.py
│   └── cli.py                   # CLI runner interface
├── scripts/
│   ├── run_backtest.sh
│   ├── run_live.sh
│   └── deploy_vps.sh
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   └── architecture.md          # This document
└── .github/
    └── workflows/ci.yml         # CI pipeline


⸻

🧱 What Each Part Does

Top-Level
	•	README.md — project overview and quickstart
	•	Makefile — CLI for common tasks (backtest, live, test)
	•	requirements.txt — Python dependencies

docker/
	•	Defines containerized environment for consistent deployment
	•	Compose file can spin up Redis, Postgres, Prometheus + your app

configs/
	•	env.dev.yaml — local dev settings (API keys, logging, endpoints)
	•	strategy.yaml — strategy parameters (spread size, risk bands, model paths)

data/
	•	raw/ — immutable tick data (Binance BTCUSDT L2) in parquet format
	•	processed/ — engineered features, backtest fills/P&L logs
	•	models/ — trained models for quote placement and risk management

notebooks/
	•	Interactive experiments (feature EDA, model tuning, profiling)

src/common/
	•	Logging setup, time utils, global constants

src/data_feed/
	•	binance_ws.py — async websocket listener for Binance L2 stream
	•	recorder.py — writes stream to Redis and raw parquet
	•	schemas.py — defines tick message schemas and validation

src/storage/
	•	state_store.py — thin wrapper over Redis for real-time state
	•	postgres.py — P&L, fills, and config persistence
	•	parquet_writer.py — saves tick data and features offline

src/lob/
	•	order_book.py — maintains in-memory order book
	•	match_engine.cpp / match_engine.pyx — optimized simulator backend for fast backtests

src/features/
	•	Implements real-time microstructure metrics:
	•	order book imbalance
	•	short-term volatility
	•	microprice calculation

src/models/
	•	Predicts fill probabilities and computes inventory-aware adjustments:
	•	logistic regression or tiny NN → fill edge
	•	Kelly-style skew → inventory-aware quoting

src/strategy/
	•	Implements quoting logic:
	•	naive_maker.py — fixed-spread strategy
	•	ev_maker.py — expected-value-maximizing quoting
	•	risk_manager.py — dynamic spread widening when inventory P&L bands exceeded

src/backtest/
	•	simulator.py — full LOB simulator for historical replay
	•	metrics.py — computes Sharpe, win rate, latency histograms

src/live/
	•	engine.py — async live trading loop:
	•	consumes Redis ticks
	•	recomputes optimal quotes
	•	posts/cancels orders to Binance REST API
	•	logs fills to Redis + Postgres
	•	binance_gateway.py — REST client for live order ops
	•	healthcheck.py — exposes Prometheus /metrics endpoint

src/api/
	•	Optional REST API for:
	•	position overview
	•	cancel all orders
	•	healthcheck / liveness

src/cli.py
	•	CLI entrypoint: backtest or live mode

scripts/
	•	Shell helpers to run tests, deploy to VPS, or start live mode

tests/
	•	unit/ — pure unit tests
	•	integration/ — tests for multi-component interactions
	•	e2e/ — tests full system loop with fake data

⸻

🗃️ Where State Lives

State	Location	Purpose
Current order book snapshot	Redis key lob:<symbol>	Used by live engine to compute quotes
Outstanding orders	Redis hash orders:<order_id>	Track open orders for cancel/replace logic
Current position & P&L	Redis keys position:<symbol> + pnl:<symbol>	Used by risk manager and strategy
Historical ticks	Parquet files in data/raw/	Offline backtesting, model training
Fills	Postgres table fills + Redis stream	Live and historical P&L analysis
Inventory model state	Redis keys + model files in data/models/	Live adaptive quoting
Config & strategy params	Postgres configs + YAML file	Centralized configuration, version controlled


⸻

🔄 How Services Connect

graph TD
    subgraph External
        Binance[Binance WS/REST API]
    end

    subgraph Data Ingestion
        WS(binance_ws.py)
        Recorder(recorder.py)
    end

    subgraph State Storage
        Redis
        Postgres
        Parquet[data/raw/]
    end

    subgraph Live Engine
        Engine(engine.py)
        Gateway(binance_gateway.py)
        Risk(risk_manager.py)
        Model(models/*.py)
    end

    subgraph Observability
        Healthcheck(healthcheck.py)
        Prometheus
        Grafana
    end

    Binance --> WS --> Recorder
    Recorder --> Redis
    Recorder --> Parquet
    Engine --> Redis
    Engine --> Gateway
    Engine --> Postgres
    Engine --> Risk
    Engine --> Model
    Healthcheck --> Prometheus
    Prometheus --> Grafana


⸻

Summary Flow

Data Flow
	1.	Binance WS stream → Recorder → Redis stream + Parquet raw ticks
	2.	Live Engine:
	•	Subscribes to Redis tick stream
	•	Reads latest state from Redis (book, inventory, fills)
	•	Calls Models → computes optimal quotes
	•	Posts/cancels orders via REST API
	•	On fill → updates Redis & Postgres
	3.	Observability:
	•	Healthcheck exposes metrics → Prometheus scrapes → Grafana dashboard

State
	•	Hot path → Redis
	•	Warm path → Postgres
	•	Cold path → Parquet + versioned models

⸻

Scaling Path

Scale Need	Solution
Higher message rate	Shard recorder → Kafka + consumer group
More assets	Run 1 Engine instance per symbol
Faster backtests	Rewrite LOB core in pure Rust or FPGA
Multiple venues	Generalize data_feed and gateway layers
Live monitoring	Extend API + Prometheus metrics coverage


⸻

🚀 Summary

This architecture:
	•	Gets you to a Minimally Viable Market Maker with:
	•	Real L2 data ingestion
	•	Feature-driven quoting
	•	Backtest loop
	•	Live paper trading engine
	•	Mirrors the tech stacks used by actual prop shops at an intern level.
	•	Is scalable to multi-symbol or multi-exchange setups.

⸻