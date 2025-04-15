
setInterval(() => {
    location.reload();
}, 10000); // refresh every 5 seconds

function fetchStockData() {
    fetch('http://localhost:5000/api/stocks')
        .then(response => response.json())
        .then(data => {
            const tbody = document.getElementById('stockData');
            tbody.innerHTML = ''; // Clear existing data
            data.forEach(stock => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${stock.symbol}</td>
                    <td>${stock.open.toFixed(2)}</td>
                    <td>${stock.high.toFixed(2)}</td>
                    <td>${stock.low.toFixed(2)}</td>
                    <td>${stock.close.toFixed(2)}</td>
                    <td>${stock.volume}</td>
                    <td>${stock.timestamp}</td>
                `;
                tbody.appendChild(row);
            });
        })
        .catch(error => console.error('Error fetching stock data:', error));
}

// Fetch data initially and then every 60 seconds
fetchStockData();
setInterval(fetchStockData, 60000);
