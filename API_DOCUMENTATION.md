# 📚 API Documentation - ARGO Ocean Intelligence Platform

## Base URLs

- **Development**: `http://localhost:8001`
- **Production**: `https://api.yourdomain.com`

## Authentication

All protected endpoints require a JWT token in the Authorization header:

```http
Authorization: Bearer <your-jwt-token>
```

---

## Table of Contents

1. [Authentication Endpoints](#authentication-endpoints)
2. [Chat Endpoints](#chat-endpoints)
3. [Data Endpoints](#data-endpoints)
4. [Visualization Endpoints](#visualization-endpoints)
5. [Error Codes](#error-codes)
6. [Rate Limits](#rate-limits)

---

## Authentication Endpoints

### Register New User

**POST** `/auth/register`

Create a new user account.

#### Request Body
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "full_name": "John Doe"
}
```

#### Response (201 Created)
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2026-01-31T10:30:00Z"
}
```

#### Errors
- **400**: Email already registered
- **422**: Invalid email format or weak password

---

### Login

**POST** `/auth/login`

Authenticate user and receive JWT token.

#### Request Body (Form Data)
```
username=user@example.com
password=securePassword123
```

#### Response (200 OK)
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### Errors
- **401**: Invalid credentials
- **422**: Missing username or password

---

### Get Current User

**GET** `/auth/me`

Get authenticated user information.

#### Headers
```
Authorization: Bearer <token>
```

#### Response (200 OK)
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "created_at": "2026-01-31T10:30:00Z"
}
```

#### Errors
- **401**: Invalid or expired token

---

## Chat Endpoints

### Send Chat Query

**POST** `/chat/query`

Send a question to the AI chatbot using RAG pipeline.

#### Headers
```
Authorization: Bearer <token>
Content-Type: application/json
```

#### Request Body
```json
{
  "query": "What's the average temperature in the Arctic region?"
}
```

#### Response (200 OK)
```json
{
  "query": "What's the average temperature in the Arctic region?",
  "response": "Based on the ARGO oceanographic data, here's what I found:\n\n🌡️ Temperature: 2.45°C (range: -1.8°C to 5.2°C, σ=1.23)\n\nThe Arctic measurements show temperatures between -1.8°C and 5.2°C, with an average of 2.45°C. This indicates typical cold Arctic ocean conditions.",
  "timestamp": "2026-01-31T10:35:00Z",
  "retrieved_context": [
    "ARGO profile from float 4902528 measured temperature of 2.3°C at depth 10.0m...",
    "ARGO profile from float 4902529 measured temperature of -1.2°C at depth 50.0m..."
  ]
}
```

#### Errors
- **401**: Not authenticated
- **422**: Empty query string
- **500**: RAG pipeline error

---

### Get Chat History

**GET** `/chat/history`

Retrieve conversation history for authenticated user.

#### Headers
```
Authorization: Bearer <token>
```

#### Query Parameters
- `limit` (optional, default=50): Number of messages to return
- `offset` (optional, default=0): Pagination offset

#### Response (200 OK)
```json
[
  {
    "id": 123,
    "query": "Show me temperature distribution",
    "response": "Based on 115 profiles...",
    "timestamp": "2026-01-31T10:30:00Z"
  },
  {
    "id": 122,
    "query": "What's the salinity range?",
    "response": "Salinity ranges from 31.5 to 35.2 PSU...",
    "timestamp": "2026-01-31T10:25:00Z"
  }
]
```

---

### Delete Chat Message

**DELETE** `/chat/history/{message_id}`

Delete a specific chat message from history.

#### Headers
```
Authorization: Bearer <token>
```

#### Response (200 OK)
```json
{
  "message": "Chat message deleted successfully"
}
```

#### Errors
- **404**: Message not found or not owned by user

---

## Data Endpoints

### Get ARGO Profiles

**GET** `/data/profiles`

Retrieve oceanographic measurement profiles.

#### Query Parameters
- `limit` (optional, default=100): Max number of profiles
- `offset` (optional, default=0): Pagination offset
- `min_temp` (optional): Minimum temperature filter
- `max_temp` (optional): Maximum temperature filter
- `min_depth` (optional): Minimum depth filter
- `max_depth` (optional): Maximum depth filter

#### Response (200 OK)
```json
[
  {
    "id": 1,
    "temperature": 15.5,
    "salinity": 35.2,
    "depth": 100.0,
    "pressure": 101.3,
    "latitude": 45.5,
    "longitude": -125.3,
    "measurement_date": "2026-01-15T08:30:00Z",
    "float_id": "4902528"
  }
]
```

---

### Get Data Summary

**GET** `/data/summary`

Get statistical summary of all oceanographic data.

#### Response (200 OK)
```json
{
  "total_profiles": 115,
  "temperature": {
    "min": -1.8,
    "max": 28.5,
    "avg": 12.4,
    "std": 8.3
  },
  "salinity": {
    "min": 31.2,
    "max": 37.8,
    "avg": 34.5,
    "std": 1.2
  },
  "depth": {
    "min": 0.0,
    "max": 2000.0,
    "avg": 450.5,
    "std": 380.2
  },
  "geographic_coverage": {
    "min_lat": -60.5,
    "max_lat": 75.2,
    "min_lon": -180.0,
    "max_lon": 180.0
  }
}
```

---

### Get Float List

**GET** `/data/floats`

Get list of all ARGO floats with measurement counts.

#### Response (200 OK)
```json
[
  {
    "float_id": "4902528",
    "profile_count": 10,
    "first_measurement": "2026-01-01T00:00:00Z",
    "last_measurement": "2026-01-30T23:59:00Z"
  },
  {
    "float_id": "4902529",
    "profile_count": 5,
    "first_measurement": "2026-01-10T00:00:00Z",
    "last_measurement": "2026-01-30T23:59:00Z"
  }
]
```

---

### Get Float Trajectory

**GET** `/data/floats/{float_id}/trajectory`

Get the geographic path of a specific ARGO float.

#### Response (200 OK)
```json
{
  "float_id": "4902528",
  "coordinates": [
    {
      "latitude": 75.5,
      "longitude": -45.3,
      "timestamp": "2026-01-01T00:00:00Z"
    },
    {
      "latitude": 75.2,
      "longitude": -44.8,
      "timestamp": "2026-01-02T00:00:00Z"
    }
  ]
}
```

---

## Visualization Endpoints

### Get Map Data

**GET** `/visualization/map`

Get data formatted for map visualization with temperature color coding.

#### Query Parameters
- `limit` (optional, default=500): Max number of points

#### Response (200 OK)
```json
[
  {
    "latitude": 45.5,
    "longitude": -125.3,
    "temperature": 15.5,
    "salinity": 35.2,
    "depth": 100.0,
    "float_id": "4902528",
    "measurement_date": "2026-01-15T08:30:00Z"
  }
]
```

---

### Get Chart Data

**GET** `/visualization/chart-data`

Get data for generating various chart types.

#### Query Parameters
- `chart_type` (required): One of `histogram`, `scatter`, `depth_profile`, `heatmap`, `3d_scatter`, `line`, `correlation`
- `variable` (optional): For histogram/line charts: `temperature`, `salinity`, `depth`
- `variable_y` (optional): For scatter plots: second variable name

#### Example: Temperature Histogram
```http
GET /visualization/chart-data?chart_type=histogram&variable=temperature
```

#### Response (200 OK)
```json
{
  "chart_type": "histogram",
  "variable": "temperature",
  "values": [15.5, 16.2, 14.8, 15.9, ...],
  "stats": {
    "mean": 15.6,
    "median": 15.5,
    "std": 0.8,
    "min": 14.2,
    "max": 17.3,
    "count": 115
  },
  "metadata": {
    "title": "Temperature Distribution",
    "xlabel": "Temperature (°C)",
    "ylabel": "Frequency"
  }
}
```

#### Example: Scatter Plot
```http
GET /visualization/chart-data?chart_type=scatter&variable=temperature&variable_y=salinity
```

#### Response (200 OK)
```json
{
  "chart_type": "scatter",
  "variable": "temperature",
  "variable_y": "salinity",
  "x_values": [15.5, 16.2, 14.8, ...],
  "y_values": [35.2, 35.4, 35.1, ...],
  "correlation": 0.87,
  "metadata": {
    "title": "Temperature vs Salinity (r=0.87)",
    "xlabel": "Temperature (°C)",
    "ylabel": "Salinity (PSU)"
  }
}
```

#### Example: Depth Profile
```http
GET /visualization/chart-data?chart_type=depth_profile&variable=temperature
```

#### Response (200 OK)
```json
{
  "chart_type": "depth_profile",
  "variable": "temperature",
  "depths": [0, 10, 20, 50, 100, 200, 500, 1000],
  "values": [18.5, 17.2, 16.8, 14.5, 10.2, 6.8, 4.2, 2.5],
  "metadata": {
    "title": "Temperature Depth Profile",
    "xlabel": "Temperature (°C)",
    "ylabel": "Depth (m)"
  }
}
```

#### Example: 3D Scatter
```http
GET /visualization/chart-data?chart_type=3d_scatter
```

#### Response (200 OK)
```json
{
  "chart_type": "3d_scatter",
  "temperature": [15.5, 16.2, 14.8, ...],
  "salinity": [35.2, 35.4, 35.1, ...],
  "depth": [100, 150, 200, ...],
  "metadata": {
    "title": "3D Ocean Data Visualization",
    "xlabel": "Temperature (°C)",
    "ylabel": "Salinity (PSU)",
    "zlabel": "Depth (m)"
  }
}
```

#### Example: Correlation Matrix
```http
GET /visualization/chart-data?chart_type=correlation
```

#### Response (200 OK)
```json
{
  "chart_type": "correlation",
  "variables": ["temperature", "salinity", "depth", "pressure"],
  "correlation_matrix": [
    [1.00, 0.87, -0.65, 0.98],
    [0.87, 1.00, -0.72, 0.89],
    [-0.65, -0.72, 1.00, -0.68],
    [0.98, 0.89, -0.68, 1.00]
  ],
  "metadata": {
    "title": "Variable Correlation Matrix",
    "description": "Pearson correlation coefficients"
  }
}
```

---

## Error Codes

### Standard HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 401 | Unauthorized | Authentication required or invalid token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Server temporarily unavailable |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong",
  "error_code": "SPECIFIC_ERROR_CODE",
  "timestamp": "2026-01-31T10:30:00Z"
}
```

### Common Error Examples

#### Invalid Token
```json
{
  "detail": "Could not validate credentials",
  "status_code": 401
}
```

#### Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "value is not a valid email address",
      "type": "value_error.email"
    }
  ],
  "status_code": 422
}
```

---

## Rate Limits

### Current Limits (Development)
- **Authentication**: 10 requests/minute per IP
- **Chat Queries**: 60 requests/minute per user
- **Data Endpoints**: 120 requests/minute per user
- **Visualization**: 120 requests/minute per user

### Rate Limit Headers

All responses include rate limit information:

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1706701200
```

### Rate Limit Exceeded Response

```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds.",
  "retry_after": 30
}
```

---

## Pagination

Endpoints that return lists support pagination:

### Parameters
- `limit`: Number of items per page (default: 100, max: 1000)
- `offset`: Number of items to skip (default: 0)

### Example
```http
GET /data/profiles?limit=50&offset=100
```

### Response Headers
```http
X-Total-Count: 115
X-Pagination-Limit: 50
X-Pagination-Offset: 100
```

---

## Webhooks (Future Feature)

### Register Webhook

**POST** `/webhooks/register`

Register a webhook URL to receive real-time notifications.

#### Request Body
```json
{
  "url": "https://your-domain.com/webhook",
  "events": ["new_profile", "data_update"],
  "secret": "your-webhook-secret"
}
```

---

## API Versioning

Current version: **v1**

All endpoints are prefixed with the version:
```
/api/v1/chat/query
/api/v1/data/profiles
```

---

## SDKs & Libraries

### Python Client Example

```python
import requests

class ArgoClient:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.token = None
        
    def login(self, email, password):
        response = requests.post(
            f"{self.base_url}/auth/login",
            data={"username": email, "password": password}
        )
        self.token = response.json()["access_token"]
        
    def query(self, question):
        response = requests.post(
            f"{self.base_url}/chat/query",
            json={"query": question},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()
        
    def get_profiles(self, limit=100):
        response = requests.get(
            f"{self.base_url}/data/profiles",
            params={"limit": limit},
            headers={"Authorization": f"Bearer {self.token}"}
        )
        return response.json()

# Usage
client = ArgoClient("http://localhost:8001")
client.login("demo@argo.com", "demo123")
result = client.query("What's the average temperature?")
print(result["response"])
```

### JavaScript/TypeScript Client Example

```typescript
class ArgoClient {
  private baseUrl: string;
  private token: string | null = null;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }
  
  async login(email: string, password: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ username: email, password })
    });
    const data = await response.json();
    this.token = data.access_token;
  }
  
  async query(question: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/chat/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify({ query: question })
    });
    return response.json();
  }
}

// Usage
const client = new ArgoClient('http://localhost:8001');
await client.login('demo@argo.com', 'demo123');
const result = await client.query('Show me temperature distribution');
console.log(result.response);
```

---

## Interactive API Documentation

Visit these URLs when the backend is running:

- **Swagger UI**: `http://localhost:8001/docs`
- **ReDoc**: `http://localhost:8001/redoc`
- **OpenAPI JSON**: `http://localhost:8001/openapi.json`

---

## Support

For API questions or issues:
- Check the interactive docs at `/docs`
- Review error messages in response
- Enable debug logging in development
- Contact: support@yourdomain.com

**Happy coding with ARGO Ocean Intelligence!** 🌊
