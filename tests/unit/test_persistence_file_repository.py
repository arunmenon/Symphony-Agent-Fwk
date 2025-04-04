"""Unit tests for FileSystemRepository."""

import asyncio
import json
import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, mock_open

from symphony.persistence.file_repository import FileSystemRepository
from symphony.core.task import Task


from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

class TestModel(BaseModel):
    """Test model for repository tests."""
    
    model_config = ConfigDict(extra="allow")
    
    id: str = "test_id"
    name: str = "Test"
    value: int = 0


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def repo(temp_dir):
    """Create a file system repository for testing."""
    return FileSystemRepository(TestModel, temp_dir)


@pytest.mark.asyncio
async def test_initialize_repository(temp_dir):
    """Test repository initialization."""
    repo = FileSystemRepository(TestModel, temp_dir)
    
    # Check entity directory was created
    entity_dir = os.path.join(temp_dir, "testmodel")
    assert os.path.exists(entity_dir)
    assert os.path.isdir(entity_dir)


@pytest.mark.asyncio
async def test_save_new_entity(repo, temp_dir):
    """Test saving a new entity."""
    entity = TestModel()
    id = await repo.save(entity)
    
    assert id == "test_id"
    
    # Check file was created
    file_path = os.path.join(temp_dir, "testmodel", f"{id}.json")
    assert os.path.exists(file_path)
    
    # Check file contents
    with open(file_path, "r") as f:
        data = json.load(f)
    
    assert data["id"] == "test_id"
    assert data["name"] == "Test"
    assert data["value"] == 0


@pytest.mark.asyncio
async def test_save_update_entity(repo, temp_dir):
    """Test saving an existing entity (update)."""
    # Save initial entity
    entity = TestModel(name="Initial")
    await repo.save(entity)
    
    # Update entity
    updated_entity = TestModel(name="Updated")
    id = await repo.save(updated_entity)
    
    assert id == "test_id"
    
    # Check file was updated
    file_path = os.path.join(temp_dir, "testmodel", f"{id}.json")
    with open(file_path, "r") as f:
        data = json.load(f)
    
    assert data["name"] == "Updated"


@pytest.mark.asyncio
async def test_find_by_id_existing(repo, temp_dir):
    """Test finding an existing entity by ID."""
    # Save entity
    entity = TestModel()
    await repo.save(entity)
    
    # Find by ID
    found = await repo.find_by_id("test_id")
    
    assert found is not None
    assert found.id == "test_id"
    assert found.name == "Test"


@pytest.mark.asyncio
async def test_find_by_id_nonexistent(repo):
    """Test finding a non-existent entity by ID."""
    found = await repo.find_by_id("nonexistent_id")
    assert found is None


@pytest.mark.asyncio
async def test_find_all(repo):
    """Test finding all entities."""
    # Save multiple entities
    entities = [
        TestModel(id="id1", name="First"),
        TestModel(id="id2", name="Second"),
        TestModel(id="id3", name="Third")
    ]
    
    for entity in entities:
        await repo.save(entity)
    
    # Find all
    all_entities = await repo.find_all()
    
    assert len(all_entities) == 3
    ids = [e.id for e in all_entities]
    assert "id1" in ids
    assert "id2" in ids
    assert "id3" in ids


@pytest.mark.asyncio
async def test_find_all_with_filter(repo):
    """Test finding entities with filter criteria."""
    # Save entities with different values
    entities = [
        TestModel(id="id1", name="Test", value=10),
        TestModel(id="id2", name="Test", value=20),
        TestModel(id="id3", name="Other", value=10)
    ]
    
    for entity in entities:
        await repo.save(entity)
    
    # Find with name filter
    name_filtered = await repo.find_all({"name": "Test"})
    assert len(name_filtered) == 2
    assert all(e.name == "Test" for e in name_filtered)
    
    # Find with value filter
    value_filtered = await repo.find_all({"value": 10})
    assert len(value_filtered) == 2
    assert all(e.value == 10 for e in value_filtered)
    
    # Find with combined filter
    combined_filtered = await repo.find_all({"name": "Test", "value": 10})
    assert len(combined_filtered) == 1
    assert combined_filtered[0].name == "Test"
    assert combined_filtered[0].value == 10


@pytest.mark.asyncio
async def test_update_existing(repo, temp_dir):
    """Test updating an existing entity."""
    # Save initial entity
    entity = TestModel()
    await repo.save(entity)
    
    # Update entity
    entity.name = "Updated"
    entity.value = 100
    result = await repo.update(entity)
    
    assert result is True
    
    # Verify update
    updated = await repo.find_by_id("test_id")
    assert updated.name == "Updated"
    assert updated.value == 100
    
    # Check file was updated
    file_path = os.path.join(temp_dir, "testmodel", f"{entity.id}.json")
    with open(file_path, "r") as f:
        data = json.load(f)
    
    assert data["name"] == "Updated"
    assert data["value"] == 100


@pytest.mark.asyncio
async def test_update_nonexistent(repo):
    """Test updating a non-existent entity."""
    entity = TestModel(id="nonexistent_id")
    result = await repo.update(entity)
    
    assert result is False


@pytest.mark.asyncio
async def test_delete_existing(repo, temp_dir):
    """Test deleting an existing entity."""
    # Save entity
    entity = TestModel()
    await repo.save(entity)
    
    # Verify file exists
    file_path = os.path.join(temp_dir, "testmodel", f"{entity.id}.json")
    assert os.path.exists(file_path)
    
    # Delete entity
    result = await repo.delete("test_id")
    
    assert result is True
    assert not os.path.exists(file_path)


@pytest.mark.asyncio
async def test_delete_nonexistent(repo):
    """Test deleting a non-existent entity."""
    result = await repo.delete("nonexistent_id")
    assert result is False


@pytest.mark.asyncio
async def test_handle_file_error(repo):
    """Test handling of file errors."""
    # Mock open to raise an error
    with patch("builtins.open", side_effect=IOError("Test error")):
        # Try to save
        with pytest.raises(IOError):
            await repo.save(TestModel())


@pytest.mark.asyncio
async def test_handle_json_error(repo):
    """Test handling of JSON errors."""
    # Save entity
    entity = TestModel()
    await repo.save(entity)
    
    # Mock json.load to raise an error
    with patch("json.load", side_effect=json.JSONDecodeError("Test error", "", 0)):
        # Try to find by ID
        result = await repo.find_by_id("test_id")
        assert result is None