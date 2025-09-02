# TheoEats Food Ordering Chatbot

![Python](https://img.shields.io/badge/python-3.9-blue) ![Flask](https://img.shields.io/badge/flask-3.x-orange) ![MySQL](https://img.shields.io/badge/mysql-8.0-blue) ![Railway](https://img.shields.io/badge/deployed-railway-purple) ![License](https://img.shields.io/badge/license-Apache%202.0-green)

TheoEats is a modern **food ordering web application** powered by an intelligent **Dialogflow chatbot** for seamless order management. Users can browse the menu, interact with the chatbot to place orders, manage their cart, and track orders - all backed by a robust Flask backend and MySQL database.

🔗 **Live Demo:** [https://foodorderingchatbot-production.up.railway.app](https://foodorderingchatbot-production.up.railway.app)

## ✨ Features

- 🤖 **Smart Dialogflow Integration** - Interactive chatbot (TheoBot) for natural language ordering
- 🍽️ **Dynamic Menu Display** - Browse food items with images and prices
- 🛒 **Persistent Cart Management** - MySQL-backed cart sessions with real-time updates
- 📱 **Responsive Design** - Optimized for both desktop and mobile devices
- 🔄 **Order Tracking** - Real-time order status and session management
- 💾 **Database Persistence** - All orders and cart data stored securely in MySQL
- 🚀 **Cloud Deployment** - Fully deployed on Railway for 24/7 availability

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+) |
| **Backend** | Flask (Python 3.9) |
| **Chatbot** | Google Dialogflow |
| **Database** | MySQL 8.0 |
| **Deployment** | Railway Cloud Platform |
| **Session Management** | Flask-Session with MySQL backend |

## 📁 Project Structure

```
food-ordering_chatbot/
├── backend/
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # Flask application entry point
│   ├── db_handler.py            # Database operations and connection
│   ├── function_handler.py      # Business logic and order processing
│   └── init_db.py              # Database initialization and setup
├── frontend/
│   ├── index.html              # Main landing page
│   ├── cart.html               # Cart management interface
│   └── images/                 # Menu item images
│       ├── fish.jpg
│       ├── rice.jpg
│       └── ...
├── services/
│   └── repair_db.py            # Database maintenance utilities
├── database/
│   └── theo_eat.sql            # Database schema and seed data
├── LICENSE                     # Apache 2.0 License
├── Procfile                    # Railway deployment configuration
├── requirements.txt            # Python dependencies
├── runtime.txt                 # Python runtime version
└── README.md                   # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- MySQL 8.0+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Omeche/food-ordering_chatbot.git
cd food-ordering_chatbot
```

### 2. Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup

#### Option A: Local MySQL Setup
```bash
# Create database
mysql -u root -p -e "CREATE DATABASE theo_eat;"

# Import schema and data
mysql -u root -p theo_eat < database/theo_eat.sql
```

#### Option B: Use Railway MySQL (Recommended)
1. Create a Railway account at [railway.app](https://railway.app)
2. Create a new MySQL service
3. Note your database credentials from Railway dashboard

### 5. Environment Configuration
Create a `.env` file in the root directory:
```env
# Database Configuration
MYSQLHOST=your_mysql_host
MYSQLPORT=3306
MYSQLUSER=your_mysql_user
MYSQLPASSWORD=your_mysql_password
MYSQLDATABASE=theo_eat

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_secret_key_here

# Dialogflow Configuration (optional for local testing)
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
```

### 6. Run Locally
```bash
# Start the Flask development server
python backend/main.py
```

The application will be available at `http://127.0.0.1:5000`

## 🌐 Deployment

### Deploy to Railway

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

2. **Connect Railway**
   - Go to [railway.app](https://railway.app)
   - Click "Deploy from GitHub repo"
   - Select your repository
   - Railway will automatically detect the Flask app

3. **Configure Environment Variables**
   In Railway dashboard, add:
   - `MYSQLHOST`
   - `MYSQLPORT`
   - `MYSQLUSER`
   - `MYSQLPASSWORD`
   - `MYSQLDATABASE`

4. **Update Dialogflow Webhook**
   - Go to Dialogflow Console
   - Navigate to Fulfillment
   - Set webhook URL to: `https://your-railway-app.up.railway.app/api/dialogflow_webhook`

## 📱 Usage

1. **Visit the Application**
   - Open [Live Demo](https://foodorderingchatbot-production.up.railway.app)

2. **Interact with TheoBot**
   - Click on the chat widget
   - Say "Hi" or "I want to order food"
   - Follow the chatbot's prompts to add items

3. **Manage Your Order**
   - View items in your cart
   - Modify quantities or remove items
   - Complete your order through the chat

4. **Track Your Order**
   - Get order confirmation
   - Check order status via chat

## 🤖 Chatbot Commands

TheoBot understands natural language, but here are some example commands:

- `"Hi"` or `"Hello"` - Start conversation
- `"I want to order fish"` - Add specific item
- `"Add 2 rice to my order"` - Add multiple items
- `"What's in my cart?"` - View current order
- `"Remove fish from my order"` - Remove items
- `"Complete my order"` - Finalize order
- `"Track my order"` - Check order status

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main landing page |
| `/cart` | GET | Cart management page |
| `/api/dialogflow_webhook` | POST | Dialogflow webhook handler |
| `/api/get_cart` | GET | Retrieve current cart items |
| `/api/add_to_cart` | POST | Add item to cart |
| `/api/remove_from_cart` | POST | Remove item from cart |


## 🤝 Contributing

I welcome contributions! Here's how to get started:

1. **Fork the Repository**
   ```bash
   git fork https://github.com/Omeche/food-ordering_chatbot.git
   ```

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make Changes**
   - Write clean, documented code
   - Follow PEP 8 style guidelines
   - Add tests for new features

4. **Commit Changes**
   ```bash
   git commit -m "Add amazing feature"
   ```

5. **Push to Branch**
   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open Pull Request**
   - Provide clear description of changes
   - Reference any related issues

### Development Guidelines
- Follow Python PEP 8 style guide
- Write meaningful commit messages
- Add comments for complex logic
- Update documentation for new features
- Test thoroughly before submitting PR

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error**
```
Error: Can't connect to MySQL server
```
- Check database credentials in environment variables
- Ensure MySQL service is running
- Verify network connectivity

**Chatbot Not Responding**
- Check Dialogflow webhook URL
- Verify webhook is accessible externally
- Check Dialogflow console for errors

**Port Already in Use**
```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9
```

## 📄 License

This project is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Google Dialogflow](https://dialogflow.cloud.google.com/)** - Natural language processing and chatbot framework
- **[Railway](https://railway.app/)** - Cloud hosting platform for seamless deployment
- **[Flask](https://flask.palletsprojects.com/)** - Lightweight Python web framework
- **[MySQL](https://www.mysql.com/)** - Reliable database management system

## 📞 Support

Need help? Here's how to get support:

- 📧 **Email**: [omechetochi@gmail.com](omechetochi@gmail.com)
- 🐛 **Issues**: [GitHub Issues](https://github.com/Omeche/food-ordering_chatbot/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/Omeche/food-ordering_chatbot/discussions)

---

**Built with ❤️ by [Omeche](https://github.com/Omeche)**

⭐ **Star this repo if you found it helpful!**
