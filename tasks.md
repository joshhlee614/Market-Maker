Here is a granular, step-by-step build plan for your MVP market-making project — designed exactly for LLM-driven iterative building:
	•	Each task is small and testable
	•	Each task has a clear start + end
	•	Each task is focused on one concern
	•	The tasks build naturally toward the architecture you just defined

⸻

🗂️ Granular Build Plan — Market-Making MVP

⸻

Phase 0 — Scaffolding

⸻

Task 0.1

Initialize empty git repo + basic folder structure
	•	Create mm_project/
	•	Add .gitignore, README.md, Makefile, requirements.txt, src/ tree with empty subfolders
	•	Add tests/unit/ and tests/integration/

✅ Test: tree command shows clean initial structure

⸻

Task 0.2

Set up automated test runner
	•	Add pytest to requirements.txt
	•	Add one dummy unit test in tests/unit/test_dummy.py
	•	Add GitHub Actions CI pipeline (basic)

✅ Test: pytest passes; GitHub Actions CI runs on push

⸻

Phase 1 — Data Ingestion

⸻

Task 1.1

Connect to Binance L2 WS API
	•	Implement binance_ws.py to connect and receive depthUpdate messages
	•	Log 10 messages to stdout

✅ Test: stdout shows valid depth updates

⸻

Task 1.2

Write Binance WS messages to Redis stream
	•	Implement recorder.py to:
	•	Receive WS messages
	•	Normalize schema
	•	Write each message to Redis stream stream:lob:<symbol>

✅ Test: Redis XRANGE shows recent messages

⸻

Task 1.3

Persist raw messages to Parquet
	•	Implement parquet_writer.py
	•	On each WS message, also append to daily Parquet file in data/raw/

✅ Test: Parquet file contains valid tick messages

⸻

Phase 2 — Limit Order Book Engine

⸻

Task 2.1

Implement basic OrderBook class
	•	Implement order_book.py
	•	insert(order)
	•	cancel(order_id)
	•	match(order) → fills

✅ Test: Unit test basic insert/cancel/match

⸻

Task 2.2

Implement C++ match engine (Phase 1)
	•	Implement basic match_engine.cpp with insert/match logic
	•	Wrap with pybind11 or Cython

✅ Test: Call C++ engine from Python; matches correctly

⸻

Task 2.3

Integrate LOB replay with Parquet
	•	Implement simulator.py to replay Parquet tick data into OrderBook

✅ Test: Backtest replay produces deterministic order book state

⸻

Phase 3 — Feature Generation

⸻

Task 3.1

Implement order book imbalance feature
	•	features/imbalance.py → compute imbalance at top 1/2/5 levels

✅ Test: Unit test imbalance computation

⸻

Task 3.2

Implement short-term volatility feature
	•	features/volatility.py → rolling window volatility of mid price

✅ Test: Unit test volatility computation on synthetic data

⸻

Task 3.3

Implement microprice feature
	•	features/micro_price.py → weighted average of best bid/ask prices

✅ Test: Unit test microprice calculation

⸻

Phase 4 — Simple Strategy (Naive Maker)

⸻

Task 4.1

Implement naive fixed-spread quoting logic
	•	naive_maker.py → given current mid price, quote bid/ask at fixed spread

✅ Test: Returns correct quote prices given mid price

⸻

Task 4.2

Integrate naive maker with backtest engine
	•	In simulator.py, run naive maker logic on each LOB snapshot
	•	Track fills and P&L

✅ Test: Backtest run produces basic P&L CSV

⸻

Phase 5 — Fill Probability Model

⸻

Task 5.1

Implement simple fill probability model
	•	fill_prob.py → logistic regression or simple classifier
	•	Trained on backtest fill data

✅ Test: Model trains and achieves non-trivial AUC on holdout

⸻

Task 5.2

Integrate fill probability model into quoting
	•	ev_maker.py → adjust quote distance to maximize expected value using fill prob model

✅ Test: Backtest run with EV maker outperforms naive maker baseline

⸻

Phase 6 — Inventory & Risk Management

⸻

Task 6.1

Implement inventory skew logic
	•	inventory_skew.py → adjust quoting bias based on current inventory level

✅ Test: Skew increases as inventory moves away from 0

⸻

Task 6.2

Integrate inventory skew into EV maker
	•	ev_maker.py → adjust both price level and side size based on inventory skew

✅ Test: P&L curve vs. inventory stays within expected risk bands

⸻

Phase 7 — Live Engine MVP

⸻

Task 7.1

Implement basic live engine loop
	•	engine.py:
	•	Sub to Redis tick stream
	•	Compute quote
	•	Print quote to stdout

✅ Test: Live engine prints quote each time new tick arrives

⸻

Task 7.2

Connect engine to Binance REST API
	•	binance_gateway.py → implement post/cancel REST endpoints
	•	Engine places actual paper-testnet orders

✅ Test: Binance testnet shows live orders

⸻

Task 7.3

Implement fill listener
	•	Listen for fill events via Binance WS or REST poll
	•	Update Redis position and pnl

✅ Test: Redis position and pnl keys update on fill

⸻

Phase 8 — Observability & Health

⸻

Task 8.1

Implement Prometheus metrics endpoint
	•	healthcheck.py → expose:
	•	Engine loop latency
	•	Outstanding orders
	•	Current inventory / P&L

✅ Test: Prometheus can scrape /metrics

⸻

Task 8.2

Implement Grafana dashboard
	•	Add basic Grafana panel:
	•	Current P&L
	•	Engine latency
	•	Order counts

✅ Test: Grafana shows live dashboard during live trading

⸻

Final Phase — Polish

⸻

Task 9.1

Add CLI for backtest and live
	•	Implement cli.py:
	•	python -m mm_project backtest
	•	python -m mm_project live

✅ Test: CLI launches correct mode

⸻

Task 9.2

Write architecture.md
	•	Finalize docs/architecture.md with actual build result

✅ Test: Matches implemented code structure

⸻

🚀 Summary Milestones

Milestone	Expected Result
Phase 2 complete	Fast offline backtest on real data
Phase 4 complete	MVP naive market-making strategy
Phase 6 complete	Inventory-aware EV-maximizing strategy
Phase 7 complete	Live paper-trading with testnet orders
Phase 8 complete	Live dashboard & observability
Phase 9 complete (polish)	Ready-to-demo MVP repo

