# BharatQuant Web Application

A professional Python web application for BharatQuant stock screener with authentication and Stripe integration.

## Features

- **Authentication System**
  - Email/Password registration and login
  - Google OAuth integration
  - Secure password hashing
  - Session management with Flask-Login

- **Stripe Payment Integration**
  - Multiple subscription tiers (Starter, Pro, Team)
  - Secure checkout with Stripe Checkout
  - Subscription management
  - Invoice generation and tracking
  - Customer portal for billing management
  - Webhook handling for payment events

- **User Dashboard**
  - Portfolio tracking
  - Watchlist management
  - Invoice history
  - Subscription management

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Edit `.env.local` file with your credentials:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here

# Google OAuth (Optional)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Stripe (Required for payments)
STRIPE_PUBLIC_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Stripe Price IDs (Create these in Stripe Dashboard)
STRIPE_PRICE_STARTER=price_...
STRIPE_PRICE_PRO=price_...
STRIPE_PRICE_TEAM=price_...
```

### 3. Set Up Google OAuth (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:5000/auth/callback`
6. Copy Client ID and Client Secret to `.env.local`

### 4. Set Up Stripe

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/)
2. Get your API keys from Developers > API keys
3. Create products and prices for each subscription tier
4. Copy price IDs to `.env.local`
5. Set up webhook endpoint: `http://localhost:5000/subscription/webhook`
6. Copy webhook secret to `.env.local`

### 5. Run the Application

```bash
python -m web.app
```

The application will be available at `http://localhost:5000`

## Project Structure

```
web/
├── __init__.py
├── app.py              # Flask application factory
├── config.py           # Configuration management
├── models.py           # Database models (User, Invoice)
├── routes/
│   ├── __init__.py
│   ├── auth.py         # Authentication routes
│   ├── main.py         # Main application routes
│   └── subscription.py # Stripe integration routes
└── templates/
    ├── base.html
    ├── dashboard_base.html
    ├── index.html
    ├── auth/
    │   ├── login.html
    │   └── signup.html
    ├── dashboard.html
    ├── portfolio.html
    ├── watchlist.html
    ├── invoices.html
    └── subscription.html
```

## Database Models

### User
- Email/password authentication
- Google OAuth integration
- Stripe customer tracking
- Subscription status

### Invoice
- Stripe invoice tracking
- Payment history
- PDF downloads

## API Routes

### Authentication
- `GET/POST /auth/signup` - User registration
- `GET/POST /auth/login` - User login
- `GET /auth/google` - Google OAuth login
- `GET /auth/callback` - OAuth callback
- `GET /auth/logout` - User logout

### Main Application
- `GET /` - Landing page
- `GET /dashboard` - User dashboard
- `GET /portfolio` - Portfolio view
- `GET /watchlist` - Watchlist view
- `GET /invoices` - Invoice history

### Subscription
- `GET /subscription` - Subscription management
- `POST /subscription/create-checkout-session` - Create Stripe checkout
- `GET /subscription/success` - Payment success handler
- `POST /subscription/cancel` - Cancel subscription
- `POST /subscription/portal` - Open customer portal
- `POST /subscription/webhook` - Stripe webhook handler

## Security Features

- Password hashing with Werkzeug
- CSRF protection
- Secure session management
- Environment variable configuration
- Stripe webhook signature verification

## Design System

The application uses the BharatQuant design system:
- **Colors**: Dark mode with green primary (#62df7d)
- **Typography**: Inter for UI, JetBrains Mono for data
- **Framework**: TailwindCSS
- **Icons**: Material Symbols

## Production Deployment

1. Set `FLASK_ENV=production` in `.env.local`
2. Generate a secure `SECRET_KEY`
3. Use production Stripe keys
4. Set up proper database (PostgreSQL recommended)
5. Configure HTTPS
6. Set up proper domain for OAuth redirect URIs
7. Configure Stripe webhook with production URL

## Support

For issues or questions, contact: billing@bharatquant.com
