"""
Mock fixtures and test data for MCP responses
Provides consistent test data for MCP integration testing
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import json


class MCPResponseFixtures:
    """Collection of mock MCP server responses for testing"""
    
    @staticmethod
    def successful_task_creation() -> Dict[str, Any]:
        """Mock successful task creation response"""
        return {
            "result": {
                "content": {
                    "id": "cu_3kj5h2l",
                    "name": "Test Task Creation",
                    "description": "This is a test task created via MCP",
                    "status": "open",
                    "priority": 2,
                    "assignees": ["test@example.com"],
                    "tags": ["testing", "mcp"],
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "url": "https://app.clickup.com/t/cu_3kj5h2l",
                    "folder": {
                        "id": "fl_123456",
                        "name": "Test Folder"
                    },
                    "list": {
                        "id": "li_789012",
                        "name": "Test List"
                    }
                }
            }
        }
    
    @staticmethod
    def task_retrieval(task_id: str = "cu_3kj5h2l") -> Dict[str, Any]:
        """Mock task retrieval response"""
        return {
            "result": {
                "content": {
                    "id": task_id,
                    "name": "Retrieved Task",
                    "description": "Task retrieved from ClickUp",
                    "status": "in progress",
                    "priority": 1,
                    "assignees": ["john@example.com", "jane@example.com"],
                    "tags": ["urgent", "client-work"],
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=3)).isoformat(),
                    "created_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "time_estimate": 7200000,  # 2 hours in milliseconds
                    "time_spent": 3600000,     # 1 hour in milliseconds
                    "custom_fields": [
                        {
                            "id": "cf_123",
                            "name": "Client",
                            "value": "Acme Corp"
                        },
                        {
                            "id": "cf_456", 
                            "name": "Effort Level",
                            "value": "Medium"
                        }
                    ]
                }
            }
        }
    
    @staticmethod
    def task_update(task_id: str = "cu_3kj5h2l") -> Dict[str, Any]:
        """Mock task update response"""
        return {
            "result": {
                "content": {
                    "id": task_id,
                    "name": "Updated Task Title",
                    "description": "Updated task description",
                    "status": "review",
                    "priority": 3,
                    "assignees": ["updated@example.com"],
                    "tags": ["updated", "testing"],
                    "due_date": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            }
        }
    
    @staticmethod
    def task_list() -> Dict[str, Any]:
        """Mock task list response"""
        base_time = datetime.now(timezone.utc)
        tasks = []
        
        for i in range(5):
            task = {
                "id": f"cu_task_{i}",
                "name": f"Task {i + 1}",
                "description": f"Description for task {i + 1}",
                "status": ["open", "in progress", "review", "done"][i % 4],
                "priority": (i % 4) + 1,
                "assignees": [f"user{i}@example.com"],
                "tags": [f"tag{i}", "batch"],
                "due_date": (base_time + timedelta(days=i + 1)).isoformat(),
                "created_at": (base_time - timedelta(hours=i)).isoformat(),
                "updated_at": base_time.isoformat()
            }
            tasks.append(task)
        
        return {
            "result": {
                "content": {
                    "tasks": tasks,
                    "last_page": True,
                    "page": 0
                }
            }
        }
    
    @staticmethod
    def search_results(query: str = "urgent") -> Dict[str, Any]:
        """Mock search results response"""
        relevant_tasks = [
            {
                "id": "cu_urgent_1",
                "name": "Urgent Client Request",
                "description": "High priority client request that needs immediate attention",
                "status": "open",
                "priority": 1,
                "assignees": ["urgent@example.com"],
                "tags": ["urgent", "client"],
                "due_date": (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat(),
                "relevance_score": 0.95
            },
            {
                "id": "cu_urgent_2", 
                "name": "Critical Bug Fix",
                "description": "Production bug that needs urgent resolution",
                "status": "in progress",
                "priority": 1,
                "assignees": ["dev@example.com"],
                "tags": ["urgent", "bug", "production"],
                "due_date": (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat(),
                "relevance_score": 0.87
            }
        ]
        
        return {
            "result": {
                "content": relevant_tasks
            }
        }
    
    @staticmethod
    def task_comments(task_id: str = "cu_3kj5h2l") -> Dict[str, Any]:
        """Mock task comments response"""
        base_time = datetime.now(timezone.utc)
        
        comments = [
            {
                "id": "comment_1",
                "comment_text": "Started working on this task",
                "user": {
                    "id": "user_1",
                    "username": "john.doe",
                    "email": "john@example.com"
                },
                "date": (base_time - timedelta(hours=2)).isoformat(),
                "resolved": False
            },
            {
                "id": "comment_2",
                "comment_text": "Found an issue with the requirements, need clarification",
                "user": {
                    "id": "user_2", 
                    "username": "jane.smith",
                    "email": "jane@example.com"
                },
                "date": (base_time - timedelta(hours=1)).isoformat(),
                "resolved": False
            },
            {
                "id": "comment_3",
                "comment_text": "Requirements clarified, proceeding with implementation",
                "user": {
                    "id": "user_1",
                    "username": "john.doe", 
                    "email": "john@example.com"
                },
                "date": (base_time - timedelta(minutes=30)).isoformat(),
                "resolved": True
            }
        ]
        
        return {
            "result": {
                "content": {
                    "comments": comments
                }
            }
        }
    
    @staticmethod
    def time_tracking(task_id: str = "cu_3kj5h2l") -> Dict[str, Any]:
        """Mock time tracking response"""
        base_time = datetime.now(timezone.utc)
        
        return {
            "result": {
                "content": {
                    "total_time": 9000000,  # 2.5 hours in milliseconds
                    "time_entries": [
                        {
                            "id": "time_1",
                            "start": (base_time - timedelta(hours=3)).isoformat(),
                            "end": (base_time - timedelta(hours=2)).isoformat(),
                            "time": 3600000,  # 1 hour
                            "description": "Initial setup and research",
                            "user": {
                                "id": "user_1",
                                "username": "john.doe"
                            }
                        },
                        {
                            "id": "time_2",
                            "start": (base_time - timedelta(hours=1, minutes=30)).isoformat(),
                            "end": (base_time - timedelta(minutes=30)).isoformat(),
                            "time": 3600000,  # 1 hour
                            "description": "Implementation work",
                            "user": {
                                "id": "user_1", 
                                "username": "john.doe"
                            }
                        },
                        {
                            "id": "time_3",
                            "start": (base_time - timedelta(minutes=30)).isoformat(),
                            "end": base_time.isoformat(),
                            "time": 1800000,  # 30 minutes
                            "description": "Testing and bug fixes",
                            "user": {
                                "id": "user_2",
                                "username": "jane.smith"
                            }
                        }
                    ]
                }
            }
        }
    
    @staticmethod
    def workspace_members() -> Dict[str, Any]:
        """Mock workspace members response"""
        return {
            "result": {
                "content": {
                    "members": [
                        {
                            "user": {
                                "id": "user_1",
                                "username": "john.doe",
                                "email": "john@example.com",
                                "color": "#ff6b6b",
                                "profilePicture": "https://attachments.clickup.com/user_1.jpg"
                            },
                            "invited_by": {
                                "id": "user_admin",
                                "username": "admin"
                            }
                        },
                        {
                            "user": {
                                "id": "user_2",
                                "username": "jane.smith", 
                                "email": "jane@example.com",
                                "color": "#4ecdc4",
                                "profilePicture": "https://attachments.clickup.com/user_2.jpg"
                            },
                            "invited_by": {
                                "id": "user_admin",
                                "username": "admin"
                            }
                        }
                    ]
                }
            }
        }
    
    @staticmethod
    def error_response(error_code: int = 400, error_message: str = "Bad Request") -> Dict[str, Any]:
        """Mock error response"""
        return {
            "error": {
                "code": error_code,
                "message": error_message,
                "details": f"Mock error response for testing: {error_message}"
            }
        }
    
    @staticmethod
    def rate_limit_response() -> Dict[str, Any]:
        """Mock rate limit response"""
        return {
            "error": {
                "code": 429,
                "message": "Rate limit exceeded",
                "details": "Too many requests. Please wait before making additional requests.",
                "retry_after": 60
            }
        }
    
    @staticmethod
    def server_error_response() -> Dict[str, Any]:
        """Mock server error response"""
        return {
            "error": {
                "code": 500,
                "message": "Internal Server Error",
                "details": "The server encountered an unexpected condition"
            }
        }


class MCPTestDataBuilder:
    """Builder class for creating custom test data"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to initial state"""
        self._task_data = {
            "id": "cu_custom",
            "name": "Custom Task",
            "description": "Custom task description",
            "status": "open",
            "priority": 3,
            "assignees": [],
            "tags": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        return self
    
    def with_id(self, task_id: str):
        """Set task ID"""
        self._task_data["id"] = task_id
        return self
    
    def with_title(self, title: str):
        """Set task title"""
        self._task_data["name"] = title
        return self
    
    def with_description(self, description: str):
        """Set task description"""
        self._task_data["description"] = description
        return self
    
    def with_status(self, status: str):
        """Set task status"""
        self._task_data["status"] = status
        return self
    
    def with_priority(self, priority: int):
        """Set task priority (1-4)"""
        self._task_data["priority"] = max(1, min(4, priority))
        return self
    
    def with_assignees(self, assignees: List[str]):
        """Set task assignees"""
        self._task_data["assignees"] = assignees
        return self
    
    def with_tags(self, tags: List[str]):
        """Set task tags"""
        self._task_data["tags"] = tags
        return self
    
    def with_due_date(self, due_date: datetime):
        """Set task due date"""
        self._task_data["due_date"] = due_date.isoformat()
        return self
    
    def with_custom_field(self, field_id: str, field_name: str, value: Any):
        """Add custom field"""
        if "custom_fields" not in self._task_data:
            self._task_data["custom_fields"] = []
        
        self._task_data["custom_fields"].append({
            "id": field_id,
            "name": field_name,
            "value": value
        })
        return self
    
    def build_task(self) -> Dict[str, Any]:
        """Build task data"""
        return {
            "result": {
                "content": self._task_data.copy()
            }
        }
    
    def build_task_list(self, count: int = 1) -> Dict[str, Any]:
        """Build task list with multiple variations"""
        tasks = []
        
        for i in range(count):
            task = self._task_data.copy()
            task["id"] = f"{task['id']}_{i}"
            task["name"] = f"{task['name']} {i + 1}"
            tasks.append(task)
        
        return {
            "result": {
                "content": {
                    "tasks": tasks,
                    "last_page": True,
                    "page": 0
                }
            }
        }


class MCPErrorScenarios:
    """Collection of error scenarios for testing"""
    
    @staticmethod
    def network_timeout():
        """Simulate network timeout"""
        import httpx
        raise httpx.TimeoutException("Request timed out")
    
    @staticmethod
    def connection_error():
        """Simulate connection error"""
        import httpx
        raise httpx.ConnectError("Connection failed")
    
    @staticmethod
    def rate_limit_error():
        """Simulate rate limiting"""
        from app.utils.retry import RateLimitError
        raise RateLimitError(retry_after=60)
    
    @staticmethod
    def server_error():
        """Simulate server error"""
        from app.utils.retry import ServerError
        raise ServerError(500, "Internal Server Error")
    
    @staticmethod
    def invalid_json_response():
        """Simulate invalid JSON response"""
        return "invalid json response"
    
    @staticmethod
    def missing_content_response():
        """Simulate response with missing content"""
        return {"result": {}}
    
    @staticmethod
    def malformed_task_response():
        """Simulate malformed task data"""
        return {
            "result": {
                "content": {
                    "id": None,  # Invalid ID
                    "name": "",  # Empty name
                    "invalid_field": "should_not_exist"
                }
            }
        }


# Convenience functions for quick access to fixtures

def get_sample_task_creation():
    """Get sample task creation response"""
    return MCPResponseFixtures.successful_task_creation()

def get_sample_task_list(count: int = 5):
    """Get sample task list response"""
    return MCPResponseFixtures.task_list()

def get_custom_task(title: str = "Custom Task", priority: int = 3):
    """Get custom task with specified parameters"""
    return (MCPTestDataBuilder()
            .with_title(title)
            .with_priority(priority)
            .build_task())

def get_error_response(error_code: int = 400, message: str = "Bad Request"):
    """Get error response"""
    return MCPResponseFixtures.error_response(error_code, message)

# Export commonly used fixtures
__all__ = [
    'MCPResponseFixtures',
    'MCPTestDataBuilder', 
    'MCPErrorScenarios',
    'get_sample_task_creation',
    'get_sample_task_list',
    'get_custom_task',
    'get_error_response'
]