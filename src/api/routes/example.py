"""Example API routes demonstrating error handling."""

from fastapi import APIRouter, Path, Query
from pydantic import BaseModel, Field

from src.core.error_utils import raise_not_found, raise_validation_error
from src.core.exceptions import (
    BadRequestError,
    ConflictError,
    ValidationError,
)

router = APIRouter(prefix="/examples", tags=["examples"])


class ExampleItem(BaseModel):
    """Example item model."""

    id: str = Field(..., description="Item ID")
    name: str = Field(..., min_length=1, max_length=100, description="Item name")
    value: int = Field(..., ge=0, description="Item value")


# In-memory storage for examples
items_db: dict[str, ExampleItem] = {}


@router.get(
    "/items",
    response_model=list[ExampleItem],
    summary="List Items",
    description="""
Retrieve a paginated list of items.

This endpoint demonstrates:
- Pagination with limit/offset
- Query parameter validation
- Response model serialization
    """,
    responses={
        200: {
            "description": "List of items",
            "content": {
                "application/json": {
                    "example": [
                        {"id": "item-001", "name": "Example Item", "value": 42},
                        {"id": "item-002", "name": "Another Item", "value": 100},
                    ]
                }
            },
        }
    },
)
async def list_items(
    limit: int = Query(
        10, ge=1, le=100, description="Number of items to return", examples=[10]
    ),
    offset: int = Query(0, ge=0, description="Number of items to skip", examples=[0]),
) -> list[ExampleItem]:
    """List all items with pagination."""
    items = list(items_db.values())
    return items[offset : offset + limit]


@router.get(
    "/items/{item_id}",
    response_model=ExampleItem,
    summary="Get Item by ID",
    description="""
Retrieve a specific item by its ID.

This endpoint demonstrates:
- Path parameter handling
- 404 error response for missing items
- Consistent error formatting
    """,
    responses={
        200: {
            "description": "Item found",
            "content": {
                "application/json": {
                    "example": {"id": "item-001", "name": "Example Item", "value": 42}
                }
            },
        },
        404: {
            "description": "Item not found",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "type": "NotFoundError",
                            "message": "item not found: item-999",
                            "code": "RESOURCE_NOT_FOUND",
                            "details": [],
                            "timestamp": "2025-01-29T12:00:00Z",
                            "path": "/api/v1/examples/items/item-999",
                        }
                    }
                }
            },
        },
    },
)
async def get_item(
    item_id: str = Path(..., description="Item ID to retrieve", examples=["item-001"]),
) -> ExampleItem:
    """Get a specific item by ID."""
    if item_id not in items_db:
        raise_not_found("item", item_id)

    return items_db[item_id]


@router.post(
    "/items",
    response_model=ExampleItem,
    status_code=201,
    summary="Create Item",
    description="""
Create a new item.

This endpoint demonstrates:
- Request body validation
- Business rule validation (value <= 1000)
- Conflict detection for duplicate IDs
- 201 Created status code
    """,
    responses={
        201: {
            "description": "Item created successfully",
            "content": {
                "application/json": {
                    "example": {"id": "item-003", "name": "New Item", "value": 150}
                }
            },
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "type": "ValidationError",
                            "message": "Value cannot exceed 1000",
                            "code": "VALIDATION_ERROR",
                            "details": [
                                {
                                    "field": "value",
                                    "constraint": "max_value",
                                    "limit": 1000,
                                    "actual": 1500,
                                }
                            ],
                            "timestamp": "2025-01-29T12:00:00Z",
                            "path": "/api/v1/examples/items",
                        }
                    }
                }
            },
        },
        409: {
            "description": "Item already exists",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "type": "ConflictError",
                            "message": "Item with ID 'item-001' already exists",
                            "code": "ITEM_ALREADY_EXISTS",
                            "details": [],
                            "timestamp": "2025-01-29T12:00:00Z",
                            "path": "/api/v1/examples/items",
                        }
                    }
                }
            },
        },
    },
)
async def create_item(item: ExampleItem) -> ExampleItem:
    """Create a new item."""
    # Check for duplicate
    if item.id in items_db:
        raise ConflictError(
            f"Item with ID '{item.id}' already exists",
            error_code="ITEM_ALREADY_EXISTS",
            context={"item_id": item.id},
        )

    # Validate business rules
    if item.value > 1000:
        raise_validation_error(
            "Value cannot exceed 1000",
            field="value",
            details=[{"constraint": "max_value", "limit": 1000, "actual": item.value}],
        )

    # Store item
    items_db[item.id] = item
    return item


@router.delete("/items/{item_id}")
async def delete_item(
    item_id: str = Path(..., description="Item ID to delete"),
) -> dict:
    """Delete an item."""
    if item_id not in items_db:
        raise_not_found("item", item_id)

    del items_db[item_id]
    return {"message": f"Item {item_id} deleted successfully"}


@router.get(
    "/error-examples/{error_type}",
    summary="Trigger Example Errors",
    description="""
Demonstrate different error types for testing and documentation.

Supported error types:
- `validation`: Returns a 400 validation error with field details
- `not_found`: Returns a 404 not found error
- `conflict`: Returns a 409 conflict error
- `bad_request`: Returns a 400 bad request error
- `internal`: Triggers a 500 internal server error

This endpoint is useful for:
- Testing error handling in clients
- Understanding error response formats
- Debugging error scenarios
    """,
    responses={
        200: {
            "description": "Unknown error type message",
            "content": {
                "application/json": {
                    "example": {"message": "Unknown error type: unknown"}
                }
            },
        },
        400: {
            "description": "Bad request or validation error",
            "content": {
                "application/json": {
                    "examples": {
                        "validation": {
                            "summary": "Validation Error",
                            "value": {
                                "error": {
                                    "type": "ValidationError",
                                    "message": "This is a validation error example",
                                    "code": "VALIDATION_ERROR",
                                    "details": [
                                        {
                                            "field": "email",
                                            "message": "Invalid email format",
                                        },
                                        {
                                            "field": "age",
                                            "message": "Must be at least 18",
                                        },
                                    ],
                                    "timestamp": "2025-01-29T12:00:00Z",
                                    "path": "/api/v1/examples/error-examples/validation",
                                }
                            },
                        },
                        "bad_request": {
                            "summary": "Bad Request Error",
                            "value": {
                                "error": {
                                    "type": "BadRequestError",
                                    "message": "Invalid request format",
                                    "code": "BAD_REQUEST",
                                    "details": [
                                        {
                                            "message": "Missing required header: X-Request-ID"
                                        }
                                    ],
                                    "timestamp": "2025-01-29T12:00:00Z",
                                    "path": "/api/v1/examples/error-examples/bad_request",
                                }
                            },
                        },
                    }
                }
            },
        },
        404: {
            "description": "Not found error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "type": "NotFoundError",
                            "message": "example not found: test-123",
                            "code": "RESOURCE_NOT_FOUND",
                            "details": [],
                            "context": {"searched_in": "examples_db"},
                            "timestamp": "2025-01-29T12:00:00Z",
                            "path": "/api/v1/examples/error-examples/not_found",
                        }
                    }
                }
            },
        },
        409: {
            "description": "Conflict error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "type": "ConflictError",
                            "message": "Resource already exists",
                            "code": "DUPLICATE_RESOURCE",
                            "details": [],
                            "context": {"existing_id": "test-123"},
                            "timestamp": "2025-01-29T12:00:00Z",
                            "path": "/api/v1/examples/error-examples/conflict",
                        }
                    }
                }
            },
        },
        500: {
            "description": "Internal server error",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "type": "InternalServerError",
                            "message": "An unexpected error occurred",
                            "code": "INTERNAL_ERROR",
                            "details": [],
                            "timestamp": "2025-01-29T12:00:00Z",
                            "path": "/api/v1/examples/error-examples/internal",
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        }
                    }
                }
            },
        },
    },
)
async def trigger_error_example(
    error_type: str = Path(
        ...,
        description="Type of error to trigger",
        examples=["validation"],
        pattern="^(validation|not_found|conflict|bad_request|internal)$",
    ),
) -> dict:
    """Endpoint to demonstrate different error types."""

    if error_type == "validation":
        raise ValidationError(
            "This is a validation error example",
            details=[
                {"field": "email", "message": "Invalid email format"},
                {"field": "age", "message": "Must be at least 18"},
            ],
        )
    elif error_type == "not_found":
        raise_not_found("example", "test-123", {"searched_in": "examples_db"})
    elif error_type == "conflict":
        raise ConflictError(
            "Resource already exists",
            error_code="DUPLICATE_RESOURCE",
            context={"existing_id": "test-123"},
        )
    elif error_type == "bad_request":
        raise BadRequestError(
            "Invalid request format",
            details=[{"message": "Missing required header: X-Request-ID"}],
        )
    elif error_type == "internal":
        # This will trigger an unhandled exception
        raise RuntimeError("Simulated internal error")

    # This should never be reached due to the regex pattern constraint
    return {"message": f"Unknown error type: {error_type}"}


@router.get("/divide/{a}/{b}")
async def divide_numbers(
    a: int = Path(..., description="Dividend"),
    b: int = Path(..., description="Divisor"),
) -> dict:
    """Example endpoint that might raise unexpected errors."""
    # This will raise ZeroDivisionError if b=0
    result = a / b
    return {"result": result}
