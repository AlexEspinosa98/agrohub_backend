from datetime import datetime
from typing import Any

from common.domain import entities, repositories


class TestBaseRepository:
    def test_abstract_methods_exist(self) -> None:
        """
        Test that ensures all required abstract methods are defined
        """
        # Get all abstract methods from the repository class
        abstract_methods: set[str] = repositories.BaseRepository.__abstractmethods__

        # Assert that the required methods are defined as abstract
        assert "save" in abstract_methods
        assert "get_by_id" in abstract_methods
        assert "list_all" in abstract_methods
        assert "delete" in abstract_methods

    def test_implementation_example(self) -> None:
        """
        Test showing how a concrete implementation would work
        This is more of a documentation test, as we can't actually
        use an abstract class directly
        """

        # Create a test entity
        class TestEntity(entities.BaseEntity):
            def __init__(self, id: int) -> None:
                super().__init__(
                    id=id,
                    is_active=True,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    deleted_at=None,
                )

            def to_dict(self) -> dict[str, Any]:
                return {"id": self.id}

        # Create a concrete implementation for testing
        class ConcreteRepository(repositories.BaseRepository[TestEntity]):
            def save(self, entity: TestEntity) -> TestEntity:
                return entity

            def get_by_id(self, entity_id: str) -> TestEntity | None:
                return None

            def list_all(self) -> list[TestEntity]:
                return []

            def delete(self, entity_id: str) -> bool:
                return True

        # Create an instance of the concrete class
        repo = ConcreteRepository()

        # Test the basic functions
        assert repo.list_all() == []
        assert repo.get_by_id("1") is None
        assert repo.delete("1") is True

        # Test save with an entity
        test_entity = TestEntity(id=123)
        assert repo.save(test_entity) == test_entity
