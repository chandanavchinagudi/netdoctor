
# NetDoctor

Zero-dependency Network Diagnostics Tool**

NetDoctor is a lightweight, pure-Python network diagnostic dashboard that checks DNS, TCP ports, HTTPS/TLS, HTTP status, and more — then gives you a clear score and actionable advice.



 Features

- 🔍 DNS resolution (IPv4 + IPv6)
- 🌐 TCP port connectivity checks (80, 443, 22, etc.)
- 🔒 HTTPS / TLS certificate validation
- 📡 HTTP status & redirect detection
- 📊 Smart scoring system (0–100) with grade
- 💡 Automatic advice based on results
- 🖤 Clean dark-themed web dashboard
- ⚡ Zero external dependencies (pure Python standard library)



 How to Run

1. Clone the repository
bash
git clone https://github.com/YOUR_USERNAME/netdoctor.git
cd netdoctor


2. Go to the web directory
bash
cd web


### 3. Start the dashboard
bash
python app.py


### 4. Open in your browser

http://localhost:8080


Press `Ctrl + C` to stop the server.



Project Structure


netdoctor/
├── web/
│   ├── app.py              # Main server
│   ├── static/
│   │   └── style.css
│   └── templates/
│       └── dashboard.html
├── diagnosis.py
├── diagnostics.py
├── scoring.py
├── history.py
├── netdoctor.py
├── report_generator.py
└── README.md

---

 Requirements

- Python 3.8 or higher
- No external packages required (uses only the standard library)

---

Example Output

| Check       | Status | Detail                          | Latency  |
|-------------|--------|---------------------------------|----------|
| DNS         | ✅     | IPv4 + IPv6 resolved            | 1.2 ms   |
| TCP/80      | ✅     | Connected                       | 38.1 ms  |
| TCP/443     | ✅     | Connected                       | 29.1 ms  |
| HTTPS/TLS   | ✅     | Valid certificate               | 132.1 ms |
| TCP/22      | ❌     | Timeout (expected)              | -        |
| UDP/53      | ❌     | Timeout (expected)              | -        |

**Score: 97/100 (A – Excellent)**
