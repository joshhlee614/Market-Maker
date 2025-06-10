# Market Maker MVP

A high-frequency market making system for cryptocurrency markets, focusing on Binance BTCUSDT pair.

## Features

- Real-time market data ingestion from Binance WebSocket API
- Fast limit order book (LOB) engine with C++ matching core
- Advanced microstructure feature generation
- Expected value (EV) based quoting with fill probability modeling
- Inventory-aware risk management
- Live trading engine with paper trading support
- Comprehensive backtesting framework

## Project Structure

```
mm_project/
├── src/                      # Source code
│   ├── common/              # Utilities and constants
│   ├── data_feed/           # Market data ingestion
│   ├── storage/             # State and persistence
│   ├── lob/                 # Limit Order Book engine
│   ├── features/            # Feature generation
│   ├── models/              # ML models
│   ├── strategy/            # Trading strategies
│   ├── backtest/            # Backtesting engine
│   ├── live/                # Live trading
│   └── api/                 # REST API
├── tests/                   # Test suite
├── data/                    # Data storage
├── configs/                 # Configuration files
├── notebooks/              # Analysis notebooks
└── docker/                 # Deployment configs
```

## Setup

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
- Copy `configs/env.dev.yaml.example` to `configs/env.dev.yaml`
- Add your Binance API keys

4. Run tests:
```bash
make test
```

## Usage

### Backtesting
```bash
make backtest
```

### Live Trading
```bash
make live
```

## Development

- Follow PEP 8 style guide
- Write unit tests for new features
- Run `make lint` before committing

## License

MIT 