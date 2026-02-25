"""Question management API endpoints."""

from datetime import datetime
import base64
import csv
import io
import json
import logging
import mimetypes
import os
import re
import sqlite3
import tempfile
import uuid
import zipfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models import Question as QuestionModel, AppUser as AppUserModel, Node as NodeModel
from app.services.node_suggestions.embedding_service import EmbeddingService
from app.services.node_suggestions.keyword_extraction_service import KeywordExtractionService
from app.services.node_suggestions.node_suggestion_service import NodeSuggestionService
from app.services.node_suggestions.postgres_repository import PostgresNodeSuggestionRepository

router = APIRouter()
logger = logging.getLogger(__name__)

ANKI_PACKAGE_EXTENSIONS = {".apkg", ".colpkg"}
PERFORMANCE_LEVELS = {"bad", "ok", "good", "great"}


def _serialize_question(question: QuestionModel) -> dict:
    return {
        "id": question.id,
        "project_id": question.project_id,
        "created_by": question.created_by,
        "text": question.text,
        "answer": question.answer,
        "options": question.options,
        "option_explanations": question.option_explanations,
        "question_type": question.question_type,
        "knowledge_type": question.knowledge_type,
        "covered_node_ids": question.covered_node_ids,
        "difficulty": question.difficulty,
        "tags": question.tags,
        "question_metadata": question.question_metadata,
        "last_attempted_at": question.last_attempted_at.isoformat()
        if question.last_attempted_at
        else None,
        "source_material_ids": question.source_material_ids,
    }


async def _get_default_user(db: AsyncSession) -> AppUserModel | None:
    result = await db.execute(select(AppUserModel).order_by(AppUserModel.id))
    return result.scalar_one_or_none()


def _normalize_title(value: str) -> str:
    return " ".join(value.lower().strip().split())


async def _update_node_search_vector(db: AsyncSession, node_id: str) -> None:
    if db.bind.dialect.name != "postgresql":
        return
    await db.execute(
        text(
            "UPDATE nodes "
            "SET search_vector = to_tsvector('english', COALESCE(topic_name, '')) "
            "WHERE id = :node_id"
        ),
        {"node_id": node_id},
    )


def _question_text(question: QuestionModel) -> str:
    parts = [question.text or "", question.answer or ""]
    return "\n\n".join([part for part in parts if part.strip()])


def _normalize_import_row(row: dict, default_type: str = "OPEN") -> dict | None:
    question_text = (
        row.get("question")
        or row.get("text")
        or row.get("front")
        or row.get("prompt")
        or ""
    ).strip()
    answer_text = (
        row.get("answer")
        or row.get("back")
        or row.get("response")
        or ""
    ).strip()

    if not question_text or not answer_text:
        return None

    question_type = (row.get("question_type") or row.get("type") or default_type or "OPEN").upper()
    if question_type not in {"OPEN", "FLASHCARD", "CLOZE", "MCQ"}:
        question_type = default_type

    tags_raw = row.get("tags") or []
    if isinstance(tags_raw, str):
        tags = [tag.strip() for tag in re.split(r"[,;]", tags_raw) if tag.strip()]
    elif isinstance(tags_raw, list):
        tags = [str(tag).strip() for tag in tags_raw if str(tag).strip()]
    else:
        tags = []

    options = row.get("options") if isinstance(row.get("options"), list) else None

    difficulty = row.get("difficulty", 1)
    try:
        difficulty = int(difficulty)
    except (TypeError, ValueError):
        difficulty = 1
    difficulty = max(1, min(5, difficulty))

    source_material_ids = row.get("source_material_ids") if isinstance(row.get("source_material_ids"), list) else []

    return {
        "text": question_text,
        "answer": answer_text,
        "question_type": question_type,
        "knowledge_type": (row.get("knowledge_type") or "CONCEPT").upper(),
        "difficulty": difficulty,
        "tags": tags,
        "options": options,
        "source_material_ids": source_material_ids,
    }


def _parse_json_questions(file_bytes: bytes) -> list[dict]:
    payload = json.loads(file_bytes.decode("utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("questions") or payload.get("qa_pairs") or []
    if not isinstance(payload, list):
        raise ValueError("JSON import must be a list of questions or include a 'questions' field")

    parsed: list[dict] = []
    for item in payload:
        if isinstance(item, dict):
            normalized = _normalize_import_row(item, default_type="OPEN")
            if normalized:
                parsed.append(normalized)
    return parsed


def _parse_csv_questions(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    parsed: list[dict] = []
    for row in reader:
        normalized = _normalize_import_row({k.lower(): v for k, v in row.items() if k}, default_type="OPEN")
        if normalized:
            parsed.append(normalized)
    return parsed


def _parse_txt_questions(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8", errors="ignore")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    parsed: list[dict] = []

    for line in lines:
        if "\t" in line:
            front, back = line.split("\t", 1)
            normalized = _normalize_import_row({"front": front, "back": back}, default_type="FLASHCARD")
            if normalized:
                parsed.append(normalized)
            continue

        qa_match = re.match(r"^Q\s*:\s*(.+?)\s+A\s*:\s*(.+)$", line, flags=re.IGNORECASE)
        if qa_match:
            normalized = _normalize_import_row(
                {"question": qa_match.group(1), "answer": qa_match.group(2)},
                default_type="OPEN",
            )
            if normalized:
                parsed.append(normalized)
    return parsed


def _media_to_data_uri(filename: str, media_bytes: bytes) -> str:
    mime_type, _ = mimetypes.guess_type(filename)
    mime_type = mime_type or "application/octet-stream"
    b64 = base64.b64encode(media_bytes).decode("ascii")
    return f"data:{mime_type};base64,{b64}"


def _embed_anki_media(html: str, media_lookup: dict[str, bytes]) -> str:
    if not html:
        return html

    def replace_src(match: re.Match) -> str:
        quote = match.group(1)
        raw_src = match.group(2)
        src = raw_src.strip()

        if src.startswith("http://") or src.startswith("https://") or src.startswith("data:"):
            return match.group(0)

        media_bytes = media_lookup.get(src)
        if media_bytes is None:
            return match.group(0)

        data_uri = _media_to_data_uri(src, media_bytes)
        return f'src={quote}{data_uri}{quote}'

    return re.sub(r"src\s*=\s*(['\"])([^'\"]+)\1", replace_src, html, flags=re.IGNORECASE)


def _parse_anki_questions(file_bytes: bytes) -> list[dict]:
    logger.info("Anki import parse started: bytes=%s", len(file_bytes))
    with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as archive:
        names = set(archive.namelist())
        logger.info("Anki archive entries detected: count=%s", len(names))
        collection_name = None
        for candidate in ("collection.anki21", "collection.anki2"):
            if candidate in names:
                collection_name = candidate
                break
        if not collection_name:
            logger.error("Anki package missing collection database. entries=%s", sorted(list(names))[:20])
            raise ValueError("Anki package missing collection database")

        media_map: dict[str, str] = {}
        if "media" in names:
            try:
                media_map = json.loads(archive.read("media").decode("utf-8"))
            except Exception:
                media_map = {}

        media_lookup: dict[str, bytes] = {}
        for key, filename in media_map.items():
            if key in names:
                media_lookup[str(filename)] = archive.read(key)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".anki2") as temp_db:
            temp_db.write(archive.read(collection_name))
            temp_db_path = temp_db.name

    connection = None
    try:
        connection = sqlite3.connect(temp_db_path)
        cursor = connection.cursor()
        model_field_names_by_mid: dict[str, list[str]] = {}
        try:
            cursor.execute("SELECT models FROM col LIMIT 1")
            models_row = cursor.fetchone()
            if models_row and models_row[0]:
                models_payload = json.loads(models_row[0])
                if isinstance(models_payload, dict):
                    for mid_key, model in models_payload.items():
                        if not isinstance(model, dict):
                            continue
                        fields = model.get("flds")
                        if not isinstance(fields, list):
                            continue
                        names: list[str] = []
                        for field in fields:
                            if isinstance(field, dict) and field.get("name"):
                                names.append(str(field["name"]).strip().lower())
                        model_field_names_by_mid[str(mid_key)] = names
        except Exception:
            model_field_names_by_mid = {}

        cursor.execute(
            "SELECT DISTINCT n.id, n.flds, n.tags, n.mid FROM notes n "
            "INNER JOIN cards c ON c.nid = n.id"
        )
        rows = cursor.fetchall()
        logger.info("Anki notes fetched for parsing: rows=%s models=%s", len(rows), len(model_field_names_by_mid))
    finally:
        if connection:
            connection.close()
        try:
            os.remove(temp_db_path)
        except Exception:
            pass

    def select_front_back(raw_fields: list[str], field_names: list[str]) -> tuple[str, str] | None:
        cleaned_fields = [field.strip() for field in raw_fields]
        named_pairs = [
            (field_names[idx] if idx < len(field_names) else "", cleaned_fields[idx])
            for idx in range(len(cleaned_fields))
        ]

        front_priority = {"front", "question", "prompt", "term", "title", "q"}
        back_priority = {"back", "answer", "definition", "explanation", "a"}

        front = ""
        back = ""

        for name, value in named_pairs:
            if name in front_priority and value:
                front = value
                break
        for name, value in named_pairs:
            if name in back_priority and value:
                back = value
                break

        if front and back:
            return front, back

        non_empty = [value for value in cleaned_fields if value]
        if len(non_empty) >= 2:
            return non_empty[0], non_empty[-1]

        if len(non_empty) == 1:
            one = non_empty[0]
            separator_match = re.split(r"<hr\s+id=['\"]?answer['\"]?\s*/?>", one, maxsplit=1, flags=re.IGNORECASE)
            if len(separator_match) == 2:
                lhs = separator_match[0].strip()
                rhs = separator_match[1].strip()
                if lhs and rhs:
                    return lhs, rhs

        return None

    parsed: list[dict] = []
    seen_pairs: set[tuple[str, str]] = set()
    unmatched_rows = 0
    for _note_id, fields_raw, tags_raw, mid_raw in rows:
        fields = (fields_raw or "").split("\x1f")
        field_names = model_field_names_by_mid.get(str(mid_raw), [])
        selected = select_front_back(fields, field_names)
        if not selected:
            unmatched_rows += 1
            continue

        front_raw, back_raw = selected
        front = _embed_anki_media(front_raw, media_lookup)
        back = _embed_anki_media(back_raw, media_lookup)
        pair_key = (front.strip(), back.strip())
        if not pair_key[0] or not pair_key[1] or pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        tags = [tag.strip() for tag in (tags_raw or "").split() if tag.strip()]

        normalized = _normalize_import_row(
            {
                "front": front,
                "back": back,
                "tags": tags,
                "question_type": "FLASHCARD",
            },
            default_type="FLASHCARD",
        )
        if normalized:
            parsed.append(normalized)

    logger.info(
        "Anki parse complete: parsed=%s unmatched=%s deduped=%s",
        len(parsed),
        unmatched_rows,
        max(len(rows) - unmatched_rows - len(parsed), 0),
    )

    return parsed


def _parse_import_file(filename: str, file_bytes: bytes) -> list[dict]:
    extension = os.path.splitext(filename.lower())[1]

    if extension == ".json":
        return _parse_json_questions(file_bytes)
    if extension == ".csv":
        return _parse_csv_questions(file_bytes)
    if extension in {".txt", ".tsv"}:
        return _parse_txt_questions(file_bytes)
    if extension in ANKI_PACKAGE_EXTENSIONS:
        return _parse_anki_questions(file_bytes)

    raise ValueError(f"Unsupported import file type: {extension}")


@router.get("/questions")
async def list_questions(
    project_id: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """List questions for a project."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.project_id == project_id)
    )
    questions = result.scalars().all()
    return [_serialize_question(question) for question in questions]


@router.get("/questions/{question_id}")
async def get_question(question_id: str, db: AsyncSession = Depends(get_db)):
    """Get a specific question by ID."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return _serialize_question(question)


@router.post("/questions")
async def create_question(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new question."""
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    text = data.get("text")
    answer = data.get("answer")
    if not text or not answer:
        raise HTTPException(status_code=400, detail="text and answer are required")

    question_id = data.get("id") or f"question-{uuid.uuid4().hex}"
    existing = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Question already exists")

    default_user = await _get_default_user(db)
    created_by = data.get("created_by") or (default_user.username if default_user else "")

    question = QuestionModel(
        id=question_id,
        project_id=project_id,
        created_by=created_by,
        text=text,
        answer=answer,
        options=data.get("options"),
        option_explanations=data.get("option_explanations"),
        question_type=data.get("question_type", "OPEN"),
        knowledge_type=data.get("knowledge_type", "CONCEPT"),
        covered_node_ids=data.get("covered_node_ids", []),
        difficulty=data.get("difficulty", 1),
        tags=data.get("tags", []),
        question_metadata={
            "created_by": created_by,
            "created_at": datetime.now().isoformat(),
            "importance": data.get("importance", 0.2),
            "hits": 0,
            "misses": 0,
        },
        last_attempted_at=None,
        source_material_ids=data.get("source_material_ids", []),
    )
    db.add(question)
    await db.commit()
    await db.refresh(question)
    return _serialize_question(question)


@router.patch("/questions/{question_id}")
async def update_question(question_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update an existing question."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    for field in (
        "text",
        "answer",
        "options",
        "option_explanations",
        "question_type",
        "knowledge_type",
        "covered_node_ids",
        "difficulty",
        "tags",
        "source_material_ids",
    ):
        if field in data:
            setattr(question, field, data[field])

    if "question_metadata" in data and isinstance(data["question_metadata"], dict):
        question.question_metadata = data["question_metadata"]

    await db.commit()
    await db.refresh(question)
    return _serialize_question(question)


@router.put("/questions/{question_id}/nodes")
async def replace_question_nodes(
    question_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Replace the set of nodes linked to a question."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    node_ids = data.get("node_ids") or []
    new_nodes = data.get("new_nodes") or []
    filtered_node_ids = [node_id for node_id in node_ids if not node_id.startswith("material:")]
    node_ids = filtered_node_ids

    nodes_result = await db.execute(
        select(NodeModel).where(NodeModel.project_id == question.project_id)
    )
    nodes = nodes_result.scalars().all()
    node_map = {node.id: node for node in nodes}
    title_map = {
        _normalize_title(node.topic_name): node.id
        for node in nodes
        if node.topic_name
    }

    desired_ids = {node_id for node_id in node_ids if node_id in node_map}
    missing_ids = sorted(set(node_ids) - set(node_map))
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Nodes not found: {', '.join(missing_ids)}",
        )

    created_nodes: list[NodeModel] = []
    created_node_ids: list[str] = []
    if new_nodes:
        default_user = await _get_default_user(db)
        created_by = default_user.username if default_user else ""
        for entry in new_nodes:
            title = None
            if isinstance(entry, str):
                title = entry
            elif isinstance(entry, dict):
                title = entry.get("title") or entry.get("suggested_title")
            if not title or not title.strip():
                raise HTTPException(status_code=400, detail="new_nodes titles are required")

            normalized = _normalize_title(title)
            existing_id = title_map.get(normalized)
            if existing_id:
                desired_ids.add(existing_id)
                continue

            node_id = f"node_{uuid.uuid4().hex}"
            node = NodeModel(
                id=node_id,
                project_id=question.project_id,
                created_by=created_by,
                topic_name=title.strip(),
                proven_knowledge_rating=0.0,
                user_estimated_knowledge_rating=0.0,
                importance=0.0,
                relevance=0.5,
                view_frequency=0,
                source_material_ids=[],
            )
            db.add(node)
            created_nodes.append(node)
            created_node_ids.append(node_id)
            desired_ids.add(node_id)
            title_map[normalized] = node_id

        if created_nodes:
            await db.flush()
            for node in created_nodes:
                await _update_node_search_vector(db, node.id)

    question.covered_node_ids = sorted(desired_ids)
    await db.commit()

    return {
        "question_id": question_id,
        "node_ids": sorted(desired_ids),
        "created_node_ids": created_node_ids,
    }


@router.post("/questions/{question_id}/suggestions")
async def suggest_nodes_for_question(
    question_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """Suggest nodes for a question by wrapping the raw-text suggestion workflow."""
    threshold = float(data.get("threshold", settings.SUGGESTION_THRESHOLD))
    semantic_weight = float(data.get("semantic_weight", settings.SUGGESTION_SEMANTIC_WEIGHT))
    keyword_weight = float(data.get("keyword_weight", settings.SUGGESTION_KEYWORD_WEIGHT))
    top_k = int(data.get("top_k", settings.SUGGESTION_TOP_K))
    dedup_threshold = float(data.get("dedup_threshold", settings.SUGGESTION_DEDUP_THRESHOLD))
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")

    result = await db.execute(select(QuestionModel).where(QuestionModel.id == question_id))
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    question_text = _question_text(question)
    return await suggest_nodes_for_question_text(
        data={
            "project_id": project_id,
            "text": question_text,
            "threshold": threshold,
            "semantic_weight": semantic_weight,
            "keyword_weight": keyword_weight,
            "top_k": top_k,
            "dedup_threshold": dedup_threshold,
        },
        db=db,
    )


@router.post("/questions/suggestions/raw-text")
async def suggest_nodes_for_question_text(data: dict, db: AsyncSession = Depends(get_db)):
    """Suggest nodes from raw text using the shared hybrid workflow."""
    threshold = float(data.get("threshold", settings.SUGGESTION_THRESHOLD))
    semantic_weight = float(data.get("semantic_weight", settings.SUGGESTION_SEMANTIC_WEIGHT))
    keyword_weight = float(data.get("keyword_weight", settings.SUGGESTION_KEYWORD_WEIGHT))
    top_k = int(data.get("top_k", settings.SUGGESTION_TOP_K))
    dedup_threshold = float(data.get("dedup_threshold", settings.SUGGESTION_DEDUP_THRESHOLD))
    project_id = data.get("project_id")
    text_value = (data.get("text") or "").strip()

    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    if not text_value:
        return {"strong": [], "weak": []}

    hf_token = settings.HF_TOKEN or os.environ.get("HF_TOKEN")
    if not hf_token:
        raise HTTPException(status_code=400, detail="HF_TOKEN is required")

    from huggingface_hub import InferenceClient

    hf_base_url = os.environ.get(
        "HF_INFERENCE_BASE_URL",
        "https://router.huggingface.co/hf-inference",
    )
    client = InferenceClient(token=hf_token, base_url=hf_base_url)
    embedding_service = EmbeddingService(client, expected_dim=768)
    keyword_service = KeywordExtractionService(client)
    repository = PostgresNodeSuggestionRepository(db)
    service = NodeSuggestionService(repository, embedding_service, keyword_service)

    try:
        result = await service.suggest_nodes_for_text(
            project_id=project_id,
            text=text_value,
            threshold=threshold,
            semantic_weight=semantic_weight,
            keyword_weight=keyword_weight,
            top_k=top_k,
            dedup_threshold=dedup_threshold,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Node suggestion failed: {exc}") from exc

    return {
        "strong": [item.__dict__ for item in result.strong],
        "weak": [item.__dict__ for item in result.weak],
    }


@router.delete("/questions/{question_id}")
async def delete_question(question_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a question."""
    result = await db.execute(
        select(QuestionModel).where(QuestionModel.id == question_id)
    )
    question = result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    await db.delete(question)
    await db.commit()
    return {"status": "deleted"}


@router.post("/questions/import")
async def import_questions(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    created_by: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Import questions from JSON/CSV/TXT or Anki package files."""
    if not project_id.strip():
        raise HTTPException(status_code=400, detail="project_id is required")

    if not file.filename:
        raise HTTPException(status_code=400, detail="file is required")

    logger.info("Question import requested: project_id=%s filename=%s", project_id, file.filename)

    try:
        file_bytes = await file.read()
        imported_rows = _parse_import_file(file.filename, file_bytes)
    except ValueError as exc:
        logger.warning("Question import parse validation failed: filename=%s error=%s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except zipfile.BadZipFile as exc:
        logger.warning("Question import invalid zip: filename=%s", file.filename)
        raise HTTPException(status_code=400, detail="Invalid Anki package") from exc
    except Exception as exc:
        logger.exception("Question import failed while parsing: filename=%s", file.filename)
        raise HTTPException(status_code=400, detail=f"Failed to parse import file: {exc}") from exc

    if not imported_rows:
        logger.warning("Question import parsed zero rows: project_id=%s filename=%s", project_id, file.filename)
        raise HTTPException(status_code=400, detail="No valid questions found in import file")

    default_user = await _get_default_user(db)
    actor = created_by or (default_user.username if default_user else "")

    created_ids: list[str] = []
    for row in imported_rows:
        question_id = f"question-{uuid.uuid4().hex[:12]}"
        question = QuestionModel(
            id=question_id,
            project_id=project_id,
            created_by=actor,
            text=row["text"],
            answer=row["answer"],
            options=row.get("options"),
            option_explanations=None,
            question_type=row.get("question_type", "OPEN"),
            knowledge_type=row.get("knowledge_type", "CONCEPT"),
            covered_node_ids=[],
            difficulty=row.get("difficulty", 1),
            tags=row.get("tags", []),
            question_metadata={
                "created_by": actor,
                "created_at": datetime.now().isoformat(),
                "importance": 0.2,
                "hits": 0,
                "misses": 0,
                "flashcard_ratings": {level: 0 for level in PERFORMANCE_LEVELS},
            },
            last_attempted_at=None,
            source_material_ids=row.get("source_material_ids", []),
        )
        db.add(question)
        created_ids.append(question_id)

    await db.commit()

    logger.info(
        "Question import completed: project_id=%s filename=%s imported=%s",
        project_id,
        file.filename,
        len(created_ids),
    )

    return {
        "imported_count": len(created_ids),
        "question_ids": created_ids,
    }


@router.post("/questions/import/preview")
async def preview_import_questions(
    file: UploadFile = File(...),
    offset: int = Form(0),
    limit: int = Form(50),
):
    """Preview parsed questions from import file without persisting them."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="file is required")

    logger.info("Question import preview requested: filename=%s", file.filename)

    try:
        file_bytes = await file.read()
        imported_rows = _parse_import_file(file.filename, file_bytes)
    except ValueError as exc:
        logger.warning("Question preview parse validation failed: filename=%s error=%s", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except zipfile.BadZipFile as exc:
        logger.warning("Question preview invalid zip: filename=%s", file.filename)
        raise HTTPException(status_code=400, detail="Invalid Anki package") from exc
    except Exception as exc:
        logger.exception("Question preview failed while parsing: filename=%s", file.filename)
        raise HTTPException(status_code=400, detail=f"Failed to parse import file: {exc}") from exc

    if not imported_rows:
        logger.warning("Question preview parsed zero rows: filename=%s", file.filename)
        raise HTTPException(status_code=400, detail="No valid questions found in import file")

    safe_offset = max(0, int(offset))
    safe_limit = max(1, min(500, int(limit)))
    paged_rows = imported_rows[safe_offset : safe_offset + safe_limit]

    previews = []
    for row in paged_rows:
        previews.append(
            {
                "text": row["text"],
                "answer": row["answer"],
                "question_type": row.get("question_type", "OPEN"),
                "difficulty": row.get("difficulty", 1),
                "tags": row.get("tags", []),
            }
        )

    logger.info(
        "Question preview completed: filename=%s total=%s preview=%s offset=%s limit=%s",
        file.filename,
        len(imported_rows),
        len(previews),
        safe_offset,
        safe_limit,
    )

    return {
        "total_count": len(imported_rows),
        "preview_count": len(previews),
        "offset": safe_offset,
        "limit": safe_limit,
        "has_more": safe_offset + len(previews) < len(imported_rows),
        "questions": previews,
    }
