# Binance Trading Bot

## Introduction

It is a trading bot for binance futures.  
It is based on the algorithmic trading strategy called Volatility Breakout.

## Development Tools

-   python-binance library for accessing binance API
-   docker and docker-compose for executing environment
-   sqlite3 for the database
-   slack for notifying

## How to start

1. Set the variables in .env file
2. Run Docker with docker-compose

```bash
docker-compose up -d --build
```

Below command to stop the program

```bash
docker-compose down
```
