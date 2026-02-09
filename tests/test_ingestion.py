"""
Phase 8: Content Ingestion & Material Linking Tests

Comprehensive unit tests for Material model, MaterialRegistry, 
provenance tracking, manual ingestion APIs, and CSV importer.
"""

from datetime import datetime
from pathlib import Path
import tempfile
import pytest

from backend.app.domain import (
    # Material
    Material,
    MaterialType,
    MaterialRegistry,
    # Ingestion
    create_node_from_material,
    create_question_from_material,
    CSVQuestionImporter,
    # Core
    Node,
    Graph,
    Edge,
    EdgeType,
    QuestionBank,
    QuestionType,
    KnowledgeType,
)


# ============================================================
# TEST HELPERS
# ============================================================


def create_test_material(
    material_id: str = "mat1",
    title: str = "Test Material",
    material_type: MaterialType = MaterialType.TEXT,
) -> Material:
    """Helper to create a test material."""
    return Material(
        id=material_id,
        project_id="test_project_1",
        title=title,
        material_type=material_type,
        source="https://example.com/test",
        created_at=datetime.now(),
        metadata={"author": "test_author"}
    )


# ============================================================
# MATERIAL MODEL TESTS
# ============================================================


class TestMaterialModel:
    """Tests for Material model."""
    
    def test_create_valid_material(self):
        """Should create material with all fields."""
        now = datetime.now()
        material = Material(
            id="mat1",
            project_id="test_project_1",
            title="Python Tutorial",
            material_type=MaterialType.VIDEO,
            source="https://youtube.com/watch?v=abc",
            created_at=now,
            metadata={"duration": "30min", "language": "en"}
        )
        
        assert material.id == "mat1"
        assert material.title == "Python Tutorial"
        assert material.material_type == MaterialType.VIDEO
        assert material.source == "https://youtube.com/watch?v=abc"
        assert material.created_at == now
        assert material.metadata["duration"] == "30min"
        assert material.metadata["language"] == "en"
    
    def test_material_with_empty_metadata(self):
        """Should allow empty metadata dict."""
        material = Material(
            id="mat1",
            project_id="test_project_1",
            title="Test",
            material_type=MaterialType.PDF,
            source="/path/to/file.pdf",
            created_at=datetime.now()
        )
        
        assert material.metadata == {}
    
    def test_material_id_cannot_be_empty(self):
        """Should reject empty material ID."""
        with pytest.raises(ValueError):
            Material(
                id="",
                project_id="test_project_1",
                title="Test",
                material_type=MaterialType.TEXT,
                source="test.txt",
                created_at=datetime.now()
            )
    
    def test_material_title_cannot_be_empty(self):
        """Should reject empty title."""
        with pytest.raises(ValueError):
            Material(
                id="mat1",
                project_id="test_project_1",
                title="",
                material_type=MaterialType.TEXT,
                source="test.txt",
                created_at=datetime.now()
            )
    
    def test_material_source_cannot_be_empty(self):
        """Should reject empty source."""
        with pytest.raises(ValueError):
            Material(
                id="mat1",
                project_id="test_project_1",
                title="Test",
                material_type=MaterialType.TEXT,
                source="",
                created_at=datetime.now()
            )
    
    def test_all_material_types(self):
        """Should support all material types."""
        types = [MaterialType.TEXT, MaterialType.PDF, MaterialType.VIDEO, 
                MaterialType.WEB, MaterialType.CSV]
        
        for mat_type in types:
            material = Material(
                id=f"mat_{mat_type.value}",
                project_id="test_project_1",
                title="Test",
                material_type=mat_type,
                source="test",
                created_at=datetime.now()
            )
            assert material.material_type == mat_type


# ============================================================
# MATERIAL REGISTRY TESTS
# ============================================================


class TestMaterialRegistry:
    """Tests for MaterialRegistry."""
    
    def test_create_empty_registry(self):
        """Should create empty registry."""
        registry = MaterialRegistry()
        assert registry.get_all_materials() == []
    
    def test_add_material(self):
        """Should add material to registry."""
        registry = MaterialRegistry()
        material = create_test_material()
        
        registry.add_material(material)
        
        assert registry.has_material("mat1")
        retrieved = registry.get_material("mat1")
        assert retrieved.id == "mat1"
        assert retrieved.title == "Test Material"
    
    def test_add_duplicate_material_raises_error(self):
        """Should reject duplicate material IDs."""
        registry = MaterialRegistry()
        material1 = create_test_material("mat1", "First")
        material2 = create_test_material("mat1", "Second")
        
        registry.add_material(material1)
        
        with pytest.raises(ValueError, match="already exists"):
            registry.add_material(material2)
    
    def test_get_nonexistent_material_raises_error(self):
        """Should raise KeyError for nonexistent material."""
        registry = MaterialRegistry()
        
        with pytest.raises(KeyError, match="not found"):
            registry.get_material("nonexistent")
    
    def test_has_material(self):
        """Should check material existence."""
        registry = MaterialRegistry()
        material = create_test_material()
        
        assert not registry.has_material("mat1")
        
        registry.add_material(material)
        
        assert registry.has_material("mat1")
        assert not registry.has_material("mat2")
    
    def test_get_all_materials(self):
        """Should retrieve all materials."""
        registry = MaterialRegistry()
        mat1 = create_test_material("mat1", "First")
        mat2 = create_test_material("mat2", "Second")
        mat3 = create_test_material("mat3", "Third")
        
        registry.add_material(mat1)
        registry.add_material(mat2)
        registry.add_material(mat3)
        
        all_materials = registry.get_all_materials()
        assert len(all_materials) == 3
        assert mat1 in all_materials
        assert mat2 in all_materials
        assert mat3 in all_materials
    
    def test_remove_material(self):
        """Should remove material from registry."""
        registry = MaterialRegistry()
        material = create_test_material()
        
        registry.add_material(material)
        assert registry.has_material("mat1")
        
        registry.remove_material("mat1")
        assert not registry.has_material("mat1")
    
    def test_remove_nonexistent_material_raises_error(self):
        """Should raise KeyError when removing nonexistent material."""
        registry = MaterialRegistry()
        
        with pytest.raises(KeyError, match="not found"):
            registry.remove_material("nonexistent")


# ============================================================
# NODE PROVENANCE TESTS
# ============================================================


class TestNodeProvenance:
    """Tests for Node provenance tracking."""
    
    def test_node_with_empty_source_materials(self):
        """Should create node with empty source_material_ids by default."""
        node = Node(id="n1", project_id="test_project_1", topic_name="Test")
        
        assert node.source_material_ids == set()
    
    def test_node_with_source_materials(self):
        """Should create node with source material IDs."""
        node = Node(
            id="n1",
            project_id="test_project_1",
            topic_name="Test",
            source_material_ids={"mat1", "mat2"}
        )
        
        assert node.source_material_ids == {"mat1", "mat2"}
    
    def test_node_source_materials_mutable(self):
        """Should allow adding source materials after creation."""
        node = Node(id="n1", project_id="test_project_1", topic_name="Test")
        
        node.source_material_ids.add("mat1")
        node.source_material_ids.add("mat2")
        
        assert "mat1" in node.source_material_ids
        assert "mat2" in node.source_material_ids


# ============================================================
# QUESTION PROVENANCE TESTS
# ============================================================


class TestQuestionProvenance:
    """Tests for Question provenance tracking."""
    
    def test_question_with_empty_source_materials(self):
        """Should create question with empty source_material_ids by default."""
        from backend.app.domain import Question, QuestionMetadata
        
        metadata = QuestionMetadata(
            created_by="test",
            created_at=datetime.now()
        )
        
        question = Question(
            id="q1",
            project_id="test_project_1",
            text="What is X?",
            answer="X is Y",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["n1"],
            metadata=metadata
        )
        
        assert question.source_material_ids == set()
    
    def test_question_with_source_materials(self):
        """Should create question with source material IDs."""
        from backend.app.domain import Question, QuestionMetadata
        
        metadata = QuestionMetadata(
            created_by="test",
            created_at=datetime.now()
        )
        
        question = Question(
            id="q1",
            project_id="test_project_1",
            text="What is X?",
            answer="X is Y",
            question_type=QuestionType.FLASHCARD,
            knowledge_type=KnowledgeType.CONCEPT,
            covered_node_ids=["n1"],
            metadata=metadata,
            source_material_ids={"mat1"}
        )
        
        assert question.source_material_ids == {"mat1"}


# ============================================================
# MANUAL INGESTION API TESTS
# ============================================================


class TestCreateNodeFromMaterial:
    """Tests for create_node_from_material API."""
    
    def test_create_node_with_valid_material(self):
        """Should create node linked to material."""
        registry = MaterialRegistry()
        material = create_test_material("mat1")
        registry.add_material(material)
        
        node = create_node_from_material(
            node_id="n1",
            project_id="test_project_1",
            topic_name="Python Basics",
            material_id="mat1",
            material_registry=registry,
            importance=5.0,
            relevance=3.0
        )
        
        assert node.id == "n1"
        assert node.topic_name == "Python Basics"
        assert node.importance == 5.0
        assert node.relevance == 3.0
        assert "mat1" in node.source_material_ids
    
    def test_create_node_with_defaults(self):
        """Should use default values for optional fields."""
        registry = MaterialRegistry()
        material = create_test_material()
        registry.add_material(material)
        
        node = create_node_from_material(
            node_id="n1",
            project_id="test_project_1",
            topic_name="Test",
            material_id="mat1",
            material_registry=registry
        )
        
        assert node.importance == 0.0
        assert node.relevance == 0.0
    
    def test_create_node_with_nonexistent_material_raises_error(self):
        """Should raise KeyError if material doesn't exist."""
        registry = MaterialRegistry()
        
        with pytest.raises(KeyError, match="not found"):
            create_node_from_material(
                node_id="n1",
                project_id="test_project_1",
                topic_name="Test",
                material_id="nonexistent",
                material_registry=registry
            )


class TestCreateQuestionFromMaterial:
    """Tests for create_question_from_material API."""
    
    def test_create_question_with_valid_material(self):
        """Should create question linked to material."""
        registry = MaterialRegistry()
        material = create_test_material()
        registry.add_material(material)
        
        question = create_question_from_material(
            question_id="q1",
            project_id="test_project_1",
            text="What is Python?",
            answer="A programming language",
            covered_node_ids=["n1", "n2"],
            material_id="mat1",
            material_registry=registry,
            question_type=QuestionType.MCQ,
            knowledge_type=KnowledgeType.FACT,
            difficulty=4,
            tags={"python", "basics"},
            importance=2.0
        )
        
        assert question.id == "q1"
        assert question.text == "What is Python?"
        assert question.answer == "A programming language"
        assert question.covered_node_ids == ["n1", "n2"]
        assert question.question_type == QuestionType.MCQ
        assert question.knowledge_type == KnowledgeType.FACT
        assert question.difficulty == 4
        assert question.tags == {"python", "basics"}
        assert question.metadata.importance == 2.0
        assert "mat1" in question.source_material_ids
    
    def test_create_question_with_defaults(self):
        """Should use default values for optional fields."""
        registry = MaterialRegistry()
        material = create_test_material()
        registry.add_material(material)
        
        question = create_question_from_material(
            question_id="q1",
            project_id="test_project_1",
            text="Test question?",
            answer="Test answer",
            covered_node_ids=["n1"],
            material_id="mat1",
            material_registry=registry
        )
        
        assert question.question_type == QuestionType.FLASHCARD
        assert question.knowledge_type == KnowledgeType.CONCEPT
        assert question.difficulty == 3
        assert question.tags == set()
        assert question.metadata.importance == 0.0
        assert question.metadata.created_by == "system"
    
    def test_create_question_with_nonexistent_material_raises_error(self):
        """Should raise KeyError if material doesn't exist."""
        registry = MaterialRegistry()
        
        with pytest.raises(KeyError, match="not found"):
            create_question_from_material(
                question_id="q1",
                project_id="test_project_1",
                text="Test?",
                answer="Answer",
                covered_node_ids=["n1"],
                material_id="nonexistent",
                material_registry=registry
            )


# ============================================================
# CSV IMPORTER TESTS
# ============================================================


class TestCSVQuestionImporter:
    """Tests for CSV question importer."""
    
    def test_import_valid_csv(self):
        """Should import questions from valid CSV."""
        # Setup
        registry = MaterialRegistry()
        material = Material(
            id="csv1",
            project_id="test_project_1",
            title="Test CSV",
            material_type=MaterialType.CSV,
            source="test.csv",
            created_at=datetime.now()
        )
        registry.add_material(material)
        
        graph = Graph(project_id="test_project_1")
        graph.add_node(Node(id="python", project_id="test_project_1", topic_name="Python"))
        graph.add_node(Node(id="variables", project_id="test_project_1", topic_name="Variables"))
        
        bank = QuestionBank()
        importer = CSVQuestionImporter(project_id="test_project_1", material_registry=registry, question_bank=bank, graph=graph)
        
        # Create temp CSV
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write("question_text,answer,covered_node_ids,difficulty,tags\n")
            f.write("What is Python?,A language,python,3,basics\n")
            f.write("What are variables?,Storage,variables,2,basics|intermediate\n")
            csv_path = f.name
        
        try:
            # Import
            questions, errors = importer.import_from_csv(csv_path, "csv1")
            
            # Verify
            assert len(questions) == 2
            assert len(errors) == 0
            
            q1 = questions[0]
            assert q1.text == "What is Python?"
            assert q1.answer == "A language"
            assert q1.covered_node_ids == ["python"]
            assert q1.difficulty == 3
            assert "basics" in q1.tags
            assert "csv1" in q1.source_material_ids
            
            q2 = questions[1]
            assert q2.text == "What are variables?"
            assert q2.covered_node_ids == ["variables"]
            assert q2.difficulty == 2
        finally:
            Path(csv_path).unlink()
    
    def test_import_with_optional_fields(self):
        """Should handle optional question_type and knowledge_type."""
        registry = MaterialRegistry()
        material = create_test_material("csv1", material_type=MaterialType.CSV)
        registry.add_material(material)
        
        graph = Graph(project_id="test_project_1")
        graph.add_node(Node(id="n1", project_id="test_project_1", topic_name="Test"))
        
        bank = QuestionBank()
        importer = CSVQuestionImporter(project_id="test_project_1", material_registry=registry, question_bank=bank, graph=graph)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write("question_text,answer,covered_node_ids,difficulty,question_type,knowledge_type\n")
            f.write("Test?,Answer,n1,3,MCQ,FACT\n")
            csv_path = f.name
        
        try:
            questions, errors = importer.import_from_csv(csv_path, "csv1")
            
            assert len(questions) == 1
            assert questions[0].question_type == QuestionType.MCQ
            assert questions[0].knowledge_type == KnowledgeType.FACT
        finally:
            Path(csv_path).unlink()
    
    def test_import_rejects_invalid_rows(self):
        """Should skip invalid rows and report errors."""
        registry = MaterialRegistry()
        material = create_test_material("csv1", material_type=MaterialType.CSV)
        registry.add_material(material)
        
        graph = Graph(project_id="test_project_1")
        graph.add_node(Node(id="n1", project_id="test_project_1", topic_name="Test"))
        
        bank = QuestionBank()
        importer = CSVQuestionImporter(project_id="test_project_1", material_registry=registry, question_bank=bank, graph=graph)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write("question_text,answer,covered_node_ids,difficulty\n")
            f.write("Valid?,Answer,n1,3\n")  # Valid
            f.write(",No question,n1,3\n")  # Missing question_text
            f.write("No answer,,n1,3\n")  # Missing answer
            f.write("No nodes,Answer,,3\n")  # Missing covered_node_ids
            f.write("Bad difficulty,Answer,n1,10\n")  # Invalid difficulty
            csv_path = f.name
        
        try:
            questions, errors = importer.import_from_csv(csv_path, "csv1")
            
            assert len(questions) == 1
            assert len(errors) == 4
            
            # Check error messages
            error_rows = [row_num for row_num, _ in errors]
            assert 3 in error_rows  # Missing question_text
            assert 4 in error_rows  # Missing answer
            assert 5 in error_rows  # Missing nodes
            assert 6 in error_rows  # Bad difficulty
        finally:
            Path(csv_path).unlink()
    
    def test_import_with_invalid_coverage_fails(self):
        """Should reject questions with invalid node coverage."""
        registry = MaterialRegistry()
        material = create_test_material("csv1", material_type=MaterialType.CSV)
        registry.add_material(material)
        
        graph = Graph(project_id="test_project_1")
        graph.add_node(Node(id="n1", project_id="test_project_1", topic_name="Test"))
        # n2 doesn't exist, so coverage validation will fail
        
        bank = QuestionBank()
        importer = CSVQuestionImporter(project_id="test_project_1", material_registry=registry, question_bank=bank, graph=graph)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write("question_text,answer,covered_node_ids,difficulty\n")
            f.write("Test?,Answer,n1|n2,3\n")  # n2 doesn't exist
            csv_path = f.name
        
        try:
            questions, errors = importer.import_from_csv(csv_path, "csv1")
            
            assert len(questions) == 0
            assert len(errors) == 1
        finally:
            Path(csv_path).unlink()
    
    def test_import_with_nonexistent_material_raises_error(self):
        """Should raise KeyError if material doesn't exist."""
        registry = MaterialRegistry()
        graph = Graph(project_id="test_project_1")
        bank = QuestionBank()
        importer = CSVQuestionImporter(project_id="test_project_1", material_registry=registry, question_bank=bank, graph=graph)
        
        with pytest.raises(KeyError, match="not found"):
            importer.import_from_csv("test.csv", "nonexistent")
    
    def test_import_with_nonexistent_file_raises_error(self):
        """Should raise FileNotFoundError if CSV doesn't exist."""
        registry = MaterialRegistry()
        material = create_test_material()
        registry.add_material(material)
        
        graph = Graph(project_id="test_project_1")
        bank = QuestionBank()
        importer = CSVQuestionImporter(project_id="test_project_1", material_registry=registry, question_bank=bank, graph=graph)
        
        with pytest.raises(FileNotFoundError):
            importer.import_from_csv("/nonexistent/file.csv", "mat1")


# ============================================================
# INTEGRATION TESTS
# ============================================================


class TestIngestionIntegration:
    """Integration tests for complete ingestion workflow."""
    
    def test_complete_workflow(self):
        """Should handle complete material ingestion workflow."""
        # 1. Setup material registry
        registry = MaterialRegistry()
        
        # 2. Add materials
        video_material = Material(
            id="vid1",
            project_id="test_project_1",
            title="Python Tutorial Video",
            material_type=MaterialType.VIDEO,
            source="https://youtube.com/watch?v=abc",
            created_at=datetime.now(),
            metadata={"duration": "45min"}
        )
        registry.add_material(video_material)
        
        csv_material = Material(
            id="csv1",
            project_id="test_project_1",
            title="Practice Questions CSV",
            material_type=MaterialType.CSV,
            source="/data/questions.csv",
            created_at=datetime.now()
        )
        registry.add_material(csv_material)
        
        # 3. Create graph with nodes from materials
        graph = Graph(project_id="test_project_1")
        
        node1 = create_node_from_material(
            node_id="python",
            project_id="test_project_1",
            topic_name="Python Basics",
            material_id="vid1",
            material_registry=registry,
            importance=5.0
        )
        graph.add_node(node1)
        
        node2 = create_node_from_material(
            node_id="variables",
            project_id="test_project_1",
            topic_name="Variables",
            material_id="vid1",
            material_registry=registry,
            importance=4.0
        )
        graph.add_node(node2)
        
        graph.add_edge(Edge(
            from_node_id="python",
            to_node_id="variables",
            project_id="test_project_1",
            type=EdgeType.PREREQUISITE,
            weight=1.0
        ))
        
        # 4. Create question bank and add manual question
        bank = QuestionBank()
        
        question1 = create_question_from_material(
            question_id="q1",
            project_id="test_project_1",
            text="What is Python used for?",
            answer="General-purpose programming",
            covered_node_ids=["python"],
            material_id="vid1",
            material_registry=registry,
            difficulty=2
        )
        bank.add_question(question1, graph)
        
        # 5. Import questions from CSV
        importer = CSVQuestionImporter(project_id="test_project_1", material_registry=registry, question_bank=bank, graph=graph)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
            f.write("question_text,answer,covered_node_ids,difficulty,tags\n")
            f.write("What are variables?,Storage locations,variables,3,basics\n")
            csv_path = f.name
        
        try:
            questions, errors = importer.import_from_csv(csv_path, "csv1")
            
            # Verify complete workflow
            assert len(errors) == 0
            assert len(questions) == 1
            assert bank.count_questions() == 2  # 1 manual + 1 from CSV
            
            # Verify provenance tracking
            assert "vid1" in node1.source_material_ids
            assert "vid1" in node2.source_material_ids
            assert "vid1" in question1.source_material_ids
            assert "csv1" in questions[0].source_material_ids
            
            # Verify question bank queries work
            python_questions = bank.get_questions_by_node("python")
            assert len(python_questions) == 1
            
            variables_questions = bank.get_questions_by_node("variables")
            assert len(variables_questions) == 1
        finally:
            Path(csv_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
