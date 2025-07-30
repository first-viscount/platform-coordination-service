# Platform Coordination Service API Documentation

## Overview

The Platform Coordination Service provides a RESTful API for managing and coordinating various platform services. This document provides comprehensive information about the API endpoints, request/response formats, and usage examples.

## Base URL

- Development: `http://localhost:8000`
- Docker: `http://platform-coordination-service:8000`

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI Schema: `/openapi.json`

## API Versioning

The API uses URL-based versioning. The current version is `v1`.

- Version prefix: `/api/v1`
- Example: `/api/v1/examples/items`

## Authentication

Currently, the API does not require authentication. Authentication will be added in future versions.

## Common Headers

### Request Headers
```
Content-Type: application/json
Accept: application/json
```

### Response Headers
```
Content-Type: application/json
X-Request-ID: <unique-request-id>
```

## Error Handling

All errors follow a consistent format:

```json
{
  "error": {
    "type": "ErrorType",
    "message": "Human-readable error message",
    "code": "ERROR_CODE",
    "details": [],
    "timestamp": "2025-01-29T12:00:00Z",
    "path": "/api/path",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Types

| Error Type | HTTP Status | Description |
|------------|-------------|-------------|
| ValidationError | 400 | Invalid request data |
| BadRequestError | 400 | Malformed request |
| NotFoundError | 404 | Resource not found |
| ConflictError | 409 | Resource conflict |
| InternalServerError | 500 | Server error |

## Endpoints

### Service Information

#### GET /
Get basic service information.

**Response Example:**
```json
{
  "service": "platform-coordination-service",
  "version": "0.1.0"
}
```

### Health Check

#### GET /health
Check service health status.

**Response Example:**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-29T12:00:00Z",
  "service": "platform-coordination-service",
  "version": "0.1.0"
}
```

**Usage:**
```bash
curl http://localhost:8000/health
```

### Example Items API

The example items API demonstrates CRUD operations with proper error handling.

#### List Items
**GET** `/api/v1/examples/items`

List all items with pagination support.

**Query Parameters:**
- `limit` (integer, 1-100): Number of items to return (default: 10)
- `offset` (integer, >= 0): Number of items to skip (default: 0)

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/examples/items?limit=20&offset=0"
```

**Response Example:**
```json
[
  {
    "id": "item-001",
    "name": "Example Item",
    "value": 42
  },
  {
    "id": "item-002",
    "name": "Another Item",
    "value": 100
  }
]
```

#### Get Item by ID
**GET** `/api/v1/examples/items/{item_id}`

Retrieve a specific item by its ID.

**Path Parameters:**
- `item_id` (string): The item ID to retrieve

**Example Request:**
```bash
curl http://localhost:8000/api/v1/examples/items/item-001
```

**Success Response (200):**
```json
{
  "id": "item-001",
  "name": "Example Item",
  "value": 42
}
```

**Error Response (404):**
```json
{
  "error": {
    "type": "NotFoundError",
    "message": "item not found: item-999",
    "code": "RESOURCE_NOT_FOUND",
    "details": [],
    "timestamp": "2025-01-29T12:00:00Z",
    "path": "/api/v1/examples/items/item-999"
  }
}
```

#### Create Item
**POST** `/api/v1/examples/items`

Create a new item.

**Request Body:**
```json
{
  "id": "item-003",
  "name": "New Item",
  "value": 150
}
```

**Validation Rules:**
- `id`: Required, must be unique
- `name`: Required, 1-100 characters
- `value`: Required, >= 0, <= 1000

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/v1/examples/items \
  -H "Content-Type: application/json" \
  -d '{
    "id": "item-003",
    "name": "New Item",
    "value": 150
  }'
```

**Success Response (201):**
```json
{
  "id": "item-003",
  "name": "New Item",
  "value": 150
}
```

**Validation Error Response (400):**
```json
{
  "error": {
    "type": "ValidationError",
    "message": "Value cannot exceed 1000",
    "code": "VALIDATION_ERROR",
    "details": [
      {
        "field": "value",
        "constraint": "max_value",
        "limit": 1000,
        "actual": 1500
      }
    ],
    "timestamp": "2025-01-29T12:00:00Z",
    "path": "/api/v1/examples/items"
  }
}
```

**Conflict Error Response (409):**
```json
{
  "error": {
    "type": "ConflictError",
    "message": "Item with ID 'item-001' already exists",
    "code": "ITEM_ALREADY_EXISTS",
    "details": [],
    "timestamp": "2025-01-29T12:00:00Z",
    "path": "/api/v1/examples/items"
  }
}
```

#### Delete Item
**DELETE** `/api/v1/examples/items/{item_id}`

Delete an item by ID.

**Example Request:**
```bash
curl -X DELETE http://localhost:8000/api/v1/examples/items/item-001
```

**Success Response (200):**
```json
{
  "message": "Item item-001 deleted successfully"
}
```

### Error Examples

#### GET /api/v1/examples/error-examples/{error_type}

Trigger example errors for testing and understanding error formats.

**Supported Error Types:**
- `validation`: 400 Validation Error
- `not_found`: 404 Not Found Error
- `conflict`: 409 Conflict Error
- `bad_request`: 400 Bad Request Error
- `internal`: 500 Internal Server Error

**Example Request:**
```bash
curl http://localhost:8000/api/v1/examples/error-examples/validation
```

## Best Practices

### 1. Always Handle Errors
Check the HTTP status code and handle errors appropriately:

```python
import requests

response = requests.get("http://localhost:8000/api/v1/examples/items/item-001")
if response.status_code == 200:
    item = response.json()
    print(f"Found item: {item['name']}")
elif response.status_code == 404:
    error = response.json()["error"]
    print(f"Item not found: {error['message']}")
else:
    print(f"Unexpected error: {response.status_code}")
```

### 2. Use Pagination for Lists
When retrieving lists, always consider pagination:

```python
def get_all_items(base_url):
    items = []
    offset = 0
    limit = 50
    
    while True:
        response = requests.get(
            f"{base_url}/api/v1/examples/items",
            params={"limit": limit, "offset": offset}
        )
        batch = response.json()
        
        if not batch:
            break
            
        items.extend(batch)
        offset += limit
    
    return items
```

### 3. Include Request ID for Debugging
When reporting issues, include the request ID from the error response:

```python
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
except requests.HTTPError as e:
    error_data = e.response.json()
    request_id = error_data["error"].get("request_id")
    print(f"Error occurred. Request ID: {request_id}")
```

### 4. Validate Input Before Sending
Validate your data client-side to avoid unnecessary API calls:

```python
def create_item(item_data):
    # Client-side validation
    if item_data.get("value", 0) > 1000:
        raise ValueError("Value cannot exceed 1000")
    
    if not item_data.get("name"):
        raise ValueError("Name is required")
    
    # Send to API
    response = requests.post(
        "http://localhost:8000/api/v1/examples/items",
        json=item_data
    )
    return response.json()
```

## Rate Limiting

Currently, no rate limiting is implemented. This will be added in future versions.

## Monitoring

### Health Check Integration
Configure your monitoring system to check the `/health` endpoint:

```yaml
# Example Kubernetes health check
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Logging
All API requests are logged with structured logging. Important fields include:
- Request ID
- Method and path
- Status code
- Response time
- Error details (if applicable)

## Future Enhancements

1. **Authentication & Authorization**
   - JWT-based authentication
   - Role-based access control
   - API key support

2. **Rate Limiting**
   - Per-IP rate limiting
   - Per-user rate limiting
   - Custom rate limit headers

3. **Additional Features**
   - WebSocket support for real-time updates
   - Batch operations
   - Field filtering and sparse fieldsets
   - Response compression

## Support

For issues or questions:
1. Check the interactive documentation at `/docs`
2. Review error messages and request IDs
3. Contact the platform team with specific error details