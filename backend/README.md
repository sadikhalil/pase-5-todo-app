# Todo Application Backend

## Architecture Overview

This application follows a simplified microservice architecture with a stateless main API server that handles all task operations through a shared service layer.

### Components

1. **Main API Server** (Port 8000)
   - Handles REST API requests for tasks
   - Provides chat endpoint that processes requests using shared TaskService
   - Statelessly processes chat requests directly in the database
   - Stores conversation history in the database

2. **MCP Server** (Port 8001) - Optional Component
   - HTTP-based tool server that exposes task operations
   - Provides alternative interface to task operations
   - Secured with internal token authentication
   - Persists all data to the same database

3. **Database**
   - PostgreSQL or SQLite database
   - Stores user data, tasks, conversations, and messages
   - Uses SQLModel for ORM operations

## Project Structure

```
backend/
├── main.py                 # Main application entry point
├── app/
│   ├── api/
│   │   └── main.py         # API routes and chat endpoint
│   │   └── tasks.py        # Task API endpoints
│   ├── auth.py             # Authentication endpoints
│   ├── models/
│   │   └── chat_models.py  # SQLModel database models
│   │   └── user.py         # User model
│   ├── services/
│   │   └── task_service.py # Shared task service layer
│   ├── db/
│   │   └── database.py     # Database connection and session management
│   └── config.py           # Configuration settings
├── mcp/
│   └── mcp_server.py       # MCP tool server
├── requirements.txt        # Python dependencies
├── run_main_server.py      # Script to run main server
└── run_mcp_server.py       # Script to run MCP server
```

## Database Schema

### Tables

- `users`
  - id: string (primary key, UUID)
  - email: string (unique)
  - password_hash: string
  - created_at: timestamp
  - updated_at: timestamp
  - is_active: boolean

- `tasks`
  - id: integer (primary key)
  - user_id: string (foreign key -> users.id)
  - title: string (not null)
  - description: text (nullable)
  - completed: boolean (default false)
  - created_at: timestamp
  - updated_at: timestamp
  - due_date: timestamp (nullable)
  - reminder_date: timestamp (nullable)
  - priority: string (default "medium")

- `conversations`
  - id: string (primary key, UUID)
  - user_id: string (index)
  - title: string
  - created_at: timestamp
  - updated_at: timestamp

- `messages`
  - id: string (primary key, UUID)
  - conversation_id: string (foreign key -> conversations.id, index)
  - user_id: string (index)
  - role: string ("user" or "assistant")
  - content: string
  - timestamp: timestamp

## Running the Application

### Prerequisites
- Python 3.11
- PostgreSQL (optional, SQLite is used by default)

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**

   ```bash
   cp ../.env.production ../.env
   # Edit .env and fill in your own values
   ```

3. **Run main API server:**
   ```bash
   python run_main_server.py
   # Server runs on http://localhost:8000
   ```

4. **(Optional) Run MCP server:**
   ```bash
   python run_mcp_server.py
   # Server runs on http://localhost:8001
   ```

## API Endpoints

### Authentication Endpoints
- `POST /auth/signup` - Register new user
- `POST /auth/login` - Login user

### Task Endpoints
- `GET /tasks/` - Get all tasks for authenticated user
- `POST /tasks/` - Create a new task
- `PUT /tasks/{id}` - Update a task
- `DELETE /tasks/{id}` - Delete a task
- `PATCH /tasks/{id}/status` - Toggle task completion status
- `GET /tasks/stats` - Get task statistics

### Chat Endpoint
- `POST /api/{user_id}/chat` - Process chat message and perform task operations

### Health Check
- `GET /health` - General health check

## Chat Operations

The chat endpoint supports natural language processing for task operations:

- **Add task**: "Add a task to buy groceries" or "Create task wash car"
- **List tasks**: "Show my tasks" or "List all tasks"
- **Complete task**: "Complete task 1" or "Finish task 2"
- **Delete task**: "Delete task 1" or "Remove task 2"
- **Update task**: "Update task 1 title to new title"

## Database Configuration

- **Development**: SQLite (default when `DATABASE_URL` is not set)
- **Production**: PostgreSQL (set `DATABASE_URL` in `.env`)

## Deployment

```bash
cp ../.env.production ../.env
# Edit .env with strong passwords and secrets
docker compose up --build -d
```

See `.env.production` for the list of required environment variables.

## Security

- JWT-based authentication with configurable expiration
- User ID validation to prevent unauthorized access
- Input validation for all endpoints
- SQL injection protection through SQLModel ORM

## Health Checks

- `GET /health` - Returns application health status
- `GET /` - Returns basic application info

## Troubleshooting

### Common Issues
1. **Database connection errors**: Check DATABASE_URL in .env file
2. **Authentication errors**: Ensure proper JWT tokens are being sent
3. **Chat endpoint errors**: Verify user authentication and proper request format
4. **Task operations not reflecting in UI**: Check that refreshTodos is being called after chat operations