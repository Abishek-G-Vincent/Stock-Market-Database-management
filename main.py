import yfinance as yf
import mysql.connector
import time
from flask import Flask, jsonify, send_from_directory
from threading import Thread
from flask_cors import CORS
import traceback
def initialize_historical_data():
    stock_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
    conn = mysql.connector.connect(
        database="stock_market",
        user="root",
        password="3wyyAJ#i*x2GXWR",
        host="localhost",
        port="3306"
    )
    cursor = conn.cursor()

    for symbol in stock_symbols:
        stock = yf.Ticker(symbol)
        # Fetch 7 days with hourly data
        data = stock.history(period="30d", interval="1d")
        print(f"Raw data for {symbol}:\n", data)  # Debug: Print raw data
        if not data.empty:
            for index, row in data.iterrows():
                if not pd.isna(row["Close"]) and row["Close"] > 0:
                    cursor.execute(
                        """
                        INSERT INTO Stock_Price (stock_id, timestamp, open_price, high_price, low_price, close_price, volume)
                        VALUES (
                            (SELECT stock_id FROM Stock WHERE symbol = %s),
                            %s, %s, %s, %s, %s, %s
                        )
                        ON DUPLICATE KEY UPDATE
                            open_price = VALUES(open_price),
                            high_price = VALUES(high_price),
                            low_price = VALUES(low_price),
                            close_price = VALUES(close_price),
                            volume = VALUES(volume)
                        """,
                        (
                            symbol,
                            index.strftime('%Y-%m-%d %H:%M:%S'),
                            row["Open"],
                            row["High"],
                            row["Low"],
                            row["Close"],
                            row["Volume"],
                        ),
                    )
                    print(f"Inserted/Updated {symbol} at {index.strftime('%Y-%m-%d %H:%M:%S')}: Close={row['Close']}")
            conn.commit()
        else:
            print(f"No historical data for {symbol}")

    cursor.close()
    conn.close()

app = Flask(__name__, static_folder='static')
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow all origins for /api/* endpoints

# Global Connection for Flask Routes
conn = mysql.connector.connect(
    database="stock_market", user="root", password="3wyyAJ#i*x2GXWR", host="localhost", port="3306"
)
cursor = conn.cursor()

def get_stock_data(symbol):
    stock = yf.Ticker(symbol)
    data = stock.history(period="1d", interval="1h")
    if not data.empty:
        latest_data = data.iloc[-1]
        return {
            "symbol": symbol,
            "open": latest_data["Open"],
            "high": latest_data["High"],
            "low": latest_data["Low"],
            "close": latest_data["Close"],
            "volume": latest_data["Volume"],
        }
    return None

def fetch_stock_data():
    import mysql.connector  # Re-import inside thread
    stock_symbols = ["AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]

    while True:
        try:
            # Create a new connection and cursor inside the thread
            conn_thread = mysql.connector.connect(
                database="stock_market",
                user="root",
                password="3wyyAJ#i*x2GXWR",
                host="localhost",
                port="3306"
            )
            cursor_thread = conn_thread.cursor()

            for symbol in stock_symbols:
                stock_data = get_stock_data(symbol)
                if stock_data:
                    cursor_thread.execute(
                        """
                        INSERT INTO Stock_Price (stock_id, timestamp, open_price, high_price, low_price, close_price, volume)
                        VALUES (
                            (SELECT stock_id FROM Stock WHERE symbol = %s),
                            NOW(), %s, %s, %s, %s, %s
                        )
                        """,
                        (
                            stock_data["symbol"],
                            stock_data["open"],
                            stock_data["high"],
                            stock_data["low"],
                            stock_data["close"],
                            stock_data["volume"],
                        ),
                    )
                    conn_thread.commit()

            cursor_thread.close()
            conn_thread.close()
            time.sleep(10)

        except Exception as e:
            print("Error in background thread:", e)
            time.sleep(5)  # Prevent crashing loop

@app.route('/api/history/<symbol>', methods=['GET'])
def get_stock_history(symbol):
    try:
        # Create a new connection for this request
        conn = mysql.connector.connect(
            database="stock_market",
            user="root",
            password="3wyyAJ#i*x2GXWR",
            host="localhost",
            port="3306"
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT sp.timestamp, sp.close_price
            FROM Stock_Price sp
            JOIN Stock s ON s.stock_id = sp.stock_id
            WHERE s.symbol = %s
            ORDER BY sp.timestamp ASC
        """, (symbol,))
        rows = cursor.fetchall()
        history = [
            {
                "timestamp": row[0].strftime('%Y-%m-%d %H:%M:%S'),
                "close": float(row[1])
            } for row in rows
        ]
        cursor.close()
        conn.close()
        return jsonify(history)
    except Exception as e:
        print("Error in get_stock_history:", e)
        return jsonify({"error": str(e)}), 500



@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    try:
        # Create a new connection for this request
        conn = mysql.connector.connect(
            database="stock_market",
            user="root",
            password="3wyyAJ#i*x2GXWR",
            host="localhost",
            port="3306"
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.symbol, sp.open_price, sp.high_price, sp.low_price, sp.close_price, sp.volume, sp.timestamp
            FROM Stock_Price sp
            JOIN (
                SELECT stock_id, MAX(timestamp) AS latest_time
                FROM Stock_Price
                GROUP BY stock_id
            ) latest ON sp.stock_id = latest.stock_id AND sp.timestamp = latest.latest_time
            JOIN Stock s ON s.stock_id = sp.stock_id
        """)
        rows = cursor.fetchall()
        stocks = [
            {
                "symbol": row[0],
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": int(row[5]),
                "timestamp": row[6].strftime('%Y-%m-%d %H:%M:%S')
            } for row in rows
        ]
        cursor.close()
        conn.close()
        return jsonify(stocks)
    except Exception as e:
        print("Error in get_stocks:", e)
        return jsonify({"error": str(e)}), 500

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    thread = Thread(target=fetch_stock_data)
    thread.daemon = True
    thread.start()
    app.run(debug=True, use_reloader=False, host='0.0.0.0', port=5000)
