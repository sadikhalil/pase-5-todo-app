# Hackathon Todo Application

## Overview

A modern todo application featuring a chatbot that can manage tasks through natural language processing. The application follows a simplified microservice architecture with a stateless main API server that handles all task operations through a shared service layer.

## Architecture

### Backend Services
- **Main API Server** (Port 8000): Handles chat requests and task operations using shared service layer
- **PostgreSQL/SQLite Database**: Persistent storage for tasks and conversations
- **MCP Server** (Port 8001): Optional HTTP-based tool server for task management

### Tech Stack
- **Backend**: Python 3.11, FastAPI, SQLModel
- **Database**: PostgreSQL or SQLite
- **Frontend**: Next.js 14, React 18, Framer Motion 12

## Project Structure

```
hackathon-todo/
├── backend/                 # Python FastAPI backend
│   ├── main.py              # Main server entry point
│   ├── app/                 # Application modules
│   │   ├── api/             # API routes
│   │   ├── auth.py          # Authentication endpoints
│   │   ├── models/          # Database models
│   │   ├── services/        # Business logic services
│   │   └── db/              # Database configuration
│   ├── mcp/                 # MCP tool server (optional)
│   ├── requirements.txt     # Python dependencies
│   ├── run_main_server.py   # Start main server
│   └── run_mcp_server.py    # Start MCP server
├── frontend/                # Next.js frontend
├── specs/                   # Specification documents
├── docker-compose.yml       # Docker orchestration
├── README.md               # This file
└── .env.example            # Environment variables example
```

## Running the Application

### Prerequisites
- Python 3.11
- Node.js 18+
- PostgreSQL (optional, SQLite is used by default)
- Git

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**

   ```bash
   cp .env.production .env
   # Edit .env and fill in your own values
   ```

4. **Start the main server:**
   ```bash
   python run_main_server.py
   # Main API server runs on http://localhost:8000
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   # Frontend runs on http://localhost:3000
   ```

## API Documentation

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
- `POST /api/{user_id}/chat` - Send a chat message and receive task-based responses

The chat endpoint supports natural language commands:
- Add tasks: "Add a task to buy groceries"
- List tasks: "Show my tasks"
- Complete tasks: "Complete task 1"
- Delete tasks: "Delete task 2"
- Update tasks: "Update task 1 title to new title"

### Health Checks
- `GET /health` - Health check endpoint

## Deployment

### Docker Deployment
```bash
cp .env.production .env
# Edit .env with strong passwords and secrets
docker compose up --build -d
```

See `.env.production` for the list of required environment variables.

## Features

- **JWT-based Authentication**: Secure user authentication with token-based sessions
- **Natural Language Chatbot**: Add, update, delete, and manage tasks using natural language
- **Real-time Updates**: Dashboard automatically refreshes after chat operations
- **Persistent Storage**: All data stored in database with proper relationships
- **Responsive UI**: Modern, mobile-friendly interface built with Next.js

## Security

- JWT-based authentication with configurable expiration
- User ID validation to prevent unauthorized access
- Input validation for all endpoints
- SQL injection protection through SQLModel ORM

## Development

This project was built for a hackathon with a focus on:
- Clean, modular architecture
- Statelessness for scalability
- Secure inter-service communication
- Modern tech stack compliance

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details.

## Phase 5: Kubernetes & Helm Deployment

### Objective

Phase 5 focuses on deploying the todo application using Kubernetes orchestration and Helm-based deployment. This phase transforms the containerized services into a production-ready, scalable architecture that can run consistently across different environments.

### Architecture Overview

In the Kubernetes deployment, the application consists of separate services that communicate through network endpoints rather than localhost:
- **Frontend Service**: Next.js application running in Kubernetes pods, exposed via ingress/load balancer
- **Backend Service**: FastAPI application with embedded MCP logic for chatbot-driven task execution
- **PostgreSQL Service**: Database service with persistent storage for data durability

All services communicate using Kubernetes DNS names rather than localhost, ensuring proper inter-service communication within the cluster. The backend contains the MCP logic internally and executes MCP operations within the backend process, eliminating the need for a separate MCP service or network communication.

### Kubernetes Components

The deployment includes the following Kubernetes resources:

- **Deployments**: Manage the desired state of application pods, ensuring specified number of replicas are running
- **Services**: Enable network connectivity between services and external access through ClusterIP, NodePort, or LoadBalancer types
- **ConfigMaps**: Store non-sensitive configuration data such as application settings and feature flags
- **PersistentVolumeClaims**: Provide persistent storage for PostgreSQL data, ensuring data durability across pod restarts
- **Secrets**: Store sensitive information like database passwords and JWT secrets securely

### Helm Chart Structure

The application is deployed using a single Helm chart named `todo-chatbot` which manages all application components:

```
charts/todo-chatbot/
├── templates/
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── postgresql-statefulset.yaml
│   ├── postgresql-service.yaml
│   └── ingress.yaml
├── Chart.yaml
└── values.yaml
```

The `values.yaml` file contains configurable parameters for all services, allowing customization of resource allocations, replica counts, environment variables, and service configurations.

### Deployment Steps

1. **Prepare the cluster**: Ensure Kubernetes cluster is accessible and kubectl is configured

2. **Add Helm repository** (if using external charts):
   ```bash
   helm repo add bitnami https://charts.bitnami.com/bitnami
   helm repo update
   ```

3. **Install the todo-chatbot application**:
   ```bash
   helm install todo-chatbot ./charts/todo-chatbot -f ./charts/todo-chatbot/values.yaml
   ```

4. **Upgrade the deployment** (when updating):
   ```bash
   helm upgrade todo-chatbot ./charts/todo-chatbot -f ./charts/todo-chatbot/values.yaml
   ```

### Environment Configuration

Key environment variables required for Kubernetes deployment are configured through ConfigMaps and Secrets. See `.env.production` for the full list of required variables.

### Validation Checklist

- [ ] All pods are running and in Ready state (`kubectl get pods`)
- [ ] Services are accessible within the cluster (`kubectl get svc`)
- [ ] Frontend service is reachable from external clients
- [ ] Backend service can connect to PostgreSQL database
- [ ] End-to-end functionality verified through the deployed application
- [ ] Persistent volumes properly attached to PostgreSQL pods
- [ ] Horizontal Pod Autoscaler (if configured) responds to load
- [ ] Health checks passing for all services
- [ ] Configuration and secrets properly mounted in pods
- [ ] Chatbot context-aware task resolution working correctly
- [ ] Confirmation for destructive actions implemented
- [ ] Metadata-aware task management operational
- [ ] Persistent, stateless operations maintained
- [ ] Fully MCP-backed execution verified