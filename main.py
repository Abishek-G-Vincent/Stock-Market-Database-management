from flask import Flask, jsonify, request
import mysql.connector
import yfinance as yf
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
CORS(app)

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="3wyyAJ#i*x2GXWR",
        database="stock_market",
        port=3306
    )


def fetch_historical_data_once():
    stock_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
    conn = get_db_connection()
    cursor = conn.cursor()

    for symbol in stock_symbols:
        data = yf.Ticker(symbol).history(period="30d", interval="1d")
        for index, row in data.iterrows():
            if not pd.isna(row["Close"]) and row["Close"] > 0:
                cursor.execute("""
                    INSERT INTO Stock_Prices (stock_id, timestamp, open_price, high_price, low_price, close_price, volume)
                    VALUES (
                        (SELECT stock_id FROM Stock WHERE symbol = %s),
                        %s, %s, %s, %s, %s, %s
                    )
                    ON DUPLICATE KEY UPDATE
                        close_price = VALUES(close_price),
                        open_price = VALUES(open_price),
                        high_price = VALUES(high_price),
                        low_price = VALUES(low_price),
                        volume = VALUES(volume)
                """, (
                    symbol,
                    index.strftime('%Y-%m-%d %H:%M:%S'),
                    row["Open"],
                    row["High"],
                    row["Low"],
                    row["Close"],
                    row["Volume"]
                ))

    conn.commit()
    cursor.close()
    conn.close()

@app.route("/api/fetch-realtime", methods=["POST"])
def fetch_realtime_data():
    try:
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)


        cursor.execute("SELECT stock_id, symbol FROM Stock")
        stock_map = {r["symbol"]: r["stock_id"] for r in cursor.fetchall()}

        for sym in symbols:
            sid = stock_map.get(sym)
            if not sid:
                continue

            df = yf.Ticker(sym).history(period="1d", interval="1m")
            if df.empty:
                continue

            latest = df.iloc[-1]
            if pd.isna(latest["Open"]) or pd.isna(latest["Close"]):
                continue


            cursor.execute("""
                REPLACE INTO latest_stock_prices
                  (stock_id, timestamp, open_price, high_price, low_price, close_price, volume)
                VALUES
                  (%s, NOW(), %s, %s, %s, %s, %s)
            """, (
                sid,
                float(latest["Open"]),
                float(latest["High"]),
                float(latest["Low"]),
                float(latest["Close"]),
                int(latest["Volume"])
            ))

        conn.commit()
        cursor.close()
        conn.close()
        return jsonify(status="success"), 200

    except Exception as e:
        print("❌", e)
        return jsonify(status="error", message=str(e)), 500


@app.route("/api/stocks")
def get_latest_data():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT s.symbol,
               l.open_price, l.high_price, l.low_price, l.close_price,
               l.volume, l.timestamp
        FROM latest_stock_prices l
        JOIN Stock s ON s.stock_id = l.stock_id
        ORDER BY l.timestamp DESC
    """)
    out = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(out)


@app.route("/api/history/<symbol>")
def get_history(symbol):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT sp.timestamp, sp.close_price
        FROM Stock_Prices sp
        JOIN Stock s ON sp.stock_id = s.stock_id
        WHERE s.symbol = %s
        ORDER BY sp.timestamp ASC
    """, (symbol,))
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return jsonify(data)


# fetch_historical_data_once()

if __name__ == "__main__":
    app.run(debug=True)
