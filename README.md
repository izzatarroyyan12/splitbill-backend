# Livin Backend

Backend API for the Livin bill-splitting application.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the development server:
```bash
python app.py
```

## API Endpoints

### Authentication
- POST /api/auth/register - Register a new user
- POST /api/auth/login - Login user
- GET /api/auth/profile - Get user profile

### Bills
- POST /api/bills - Create a new bill
- GET /api/bills - Get all bills
- GET /api/bills/<bill_id> - Get specific bill
- POST /api/bills/<bill_id>/pay - Pay a bill
- POST /api/bills/<bill_id>/participants/<participant_index>/pay - Mark participant as paid

## Deployment

This application is configured for deployment on Render. The `render.yaml` file contains the necessary configuration.

## Environment Variables

- `MONGODB_URI`: MongoDB connection string
- `JWT_SECRET_KEY`: Secret key for JWT token generation
- `PORT`: Port to run the server on (default: 5000) 