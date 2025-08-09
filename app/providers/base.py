from typing import List, Dict, Any

class ProviderAdapter:
    name: str

    def create_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def create_subtasks(self, parent_external_id: str, subtasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def add_checklist(self, external_id: str, items: List[str]) -> None:
        raise NotImplementedError

    def update_status(self, external_id: str, status: str) -> None:
        raise NotImplementedError

    def verify_webhook(self, headers: Dict[str, str], raw_body: bytes) -> bool:
        raise NotImplementedError