# Text-to-SQL API

A powerful API service that translates natural language questions into SQL queries and returns database results, built with Python, Flask, and Google's Gemini AI.

## 🌟 Overview

This project provides a service that allows users to query a Microsoft SQL Server database using natural language. The application:

1. Extracts the database schema
2. Sends the schema and user question to Google's Gemini AI
3. Executes the generated SQL query on the database
4. Returns both the SQL query and the query results

The service is containerized using Docker and includes a ready-to-use AdventureWorks sample database.

## 🏗️ Architecture

```
┌──────────────┐       ┌───────────────┐      ┌─────────────────┐
│              │       │               │      │                 │
│   Client     ├──────►│  Flask App    ├─────►│  Google Gemini  │
│              │       │  (Backend)    │      │     API         │
└──────────────┘       └───────┬───────┘      └─────────────────┘
                               │
                               ▼
                       ┌───────────────┐
                       │               │
                       │ MS SQL Server │
                       │ (Database)    │
                       └───────────────┘
```

### Components:

1. **Flask API** (`app_mssql.py`): Handles HTTP requests, processes natural language queries, and manages the flow between components
   
2. **Database Connection Layer**: Uses pyodbc to connect to and extract schema from the MS SQL Server

3. **AI Integration**: Leverages Google's Gemini AI to translate natural language to SQL queries

4. **Docker Containers**:
   - Backend container running the Flask application
   - MS SQL Server container with pre-loaded AdventureWorks database

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Google Gemini API key

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/benzine12/text-to-sql
   cd text-to-sql
   ```

2. Add a Gemini API key to `.env` file:
   ```bash
   API_KEY=your_google_gemini_api_key
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. The API will be accessible at `http://localhost:8000`

## 📝 API Usage

### Endpoint: `/ask_sql`

**Request**:
```http
POST /ask_sql
Content-Type: application/json

{
  "user_text": "Show me the top 5 products by sales"
}
```

**Response**:
```json
{
  "query": "```sql\nSELECT TOP 5 p.Name AS ProductName, SUM(sod.LineTotal) AS TotalSales\nFROM Production.Product p\nJOIN Sales.SalesOrderDetail sod ON p.ProductID = sod.ProductID\nGROUP BY p.Name\nORDER BY TotalSales DESC\n```",
  "db_result": {
    "status": "success",
    "rows": [
      {
        "ProductName": "Mountain-100 Black, 42",
        "TotalSales": 3399.9900000000000
      },
      ...
    ]
  }
}
```

## 🛠️ Design Decisions & Trade-offs

### Architecture Decisions

1. **Containerization**
   - **Decision**: Using Docker for deployment
   - **Benefit**: Ensures consistent environment across development and production
   - **Trade-off**: Adds complexity for simple deployments

2. **Pre-loaded Database**
   - **Decision**: Using a pre-built AdventureWorks database image
   - **Benefit**: Immediate usability without complex setup
   - **Trade-off**: Increased container size

3. **Schema Extraction**
   - **Decision**: Dynamic schema extraction rather than hardcoded schema
   - **Benefit**: Works with any MS SQL database without modification
   - **Trade-off**: Adds slight overhead to request processing

4. **AI Provider**
   - **Decision**: Using Google's Gemini AI
   - **Benefit**: High-quality SQL generation with good context understanding
   - **Trade-off**: Requires API key and may incur costs