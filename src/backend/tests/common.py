import asyncio
from datetime import datetime
import json
import logging
import os
from typing import AsyncGenerator, List, Sequence, AsyncContextManager, Optional, Generator

import aiofiles
from fastapi import status, Depends # noqa: F401  # used by test files importing common
import freezegun
from freezegun import freeze_time # noqa: F401  # used by test files importing common
from httpx import Response, AsyncClient, ASGITransport
from pydantic import BaseModel
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection
from sqlalchemy.orm import Mapped
from sqlmodel import SQLModel, select, func, col
from sqlmodel.ext.asyncio.session import AsyncSession
import sqlparse
from testcontainers.postgres import PostgresContainer

# avoid any authentication requirements
os.environ['OPENID_URL'] = ''

from tero.agents.api import AGENT_TOOLS_PATH, AGENT_TOOL_FILES_PATH
from tero.agents.domain import AgentListItem, Agent
from tero.agents.test_cases.domain import TestSuiteRun, TestCaseResult
from tero.api import app
from tero.core import repos as repos_module, auth
from tero.core.env import env # noqa: F401  # used by test files importing common
from tero.core.api import BASE_PATH # noqa: F401  # used by test files importing common
from tero.core.assets import solve_asset_path
from tero.core.env import env # noqa: F401  # used by test files importing common
from tero.core.repos import get_db
from tero.files.domain import FileStatus
from tero.teams.domain import Role, Team, TeamRole, TeamRoleStatus
from tero.threads.api import THREAD_MESSAGES_PATH, THREADS_PATH, ThreadCreateApi
from tero.threads.domain import Thread, ThreadMessage
from tero.tools.docs import DOCS_TOOL_ID
from tero.users.domain import User, UserListItem


def parse_date(value: str) -> datetime:
    return datetime.fromisoformat(value)


logger = logging.getLogger(__name__)
pytestmark = pytest.mark.asyncio
PAST_TIME = parse_date("2025-02-21T12:00:00")
CURRENT_TIME = parse_date("2025-02-22T12:00:00")
USER_ID = 1
OTHER_USER_ID = 2
AGENT_ID = 1
NON_EDITABLE_AGENT_ID = 3
NON_VISIBLE_AGENT_ID = 4
THREAD_ID = 1
OTHER_THREAD_ID = 2
OTHER_USER_THREAD_ID = 3
GLOBAL_TEAM_ID = 1
TEST_ICON = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAA1JREFUGFdjWCMg9B8ABAgBzkPo1OYAAAAASUVORK5CYII="

# avoid transformers module giving erros when using freeze_time due to torch not being installed (torch gives problems when installed on x86_64 macos)
freezegun.configure(extend_ignore_list=["transformers"])

# Fix for pydantic datetime schema generation with freezegun
# Based on: https://github.com/pydantic/pydantic/discussions/9343
from pydantic._internal._generate_schema import GenerateSchema
from pydantic_core import core_schema

initial_match_type = GenerateSchema.match_type

def patched_match_type(self, obj):
    if getattr(obj, "__name__", None) == "datetime":
        return core_schema.datetime_schema()
    return initial_match_type(self, obj)

GenerateSchema.match_type = patched_match_type


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer("pgvector/pgvector:pg17", driver="psycopg") as postgres:
        yield postgres


@pytest_asyncio.fixture(name="session")
async def session_fixture(postgres_container: PostgresContainer) -> AsyncGenerator[AsyncSession, None]:
    test_engine = create_async_engine(postgres_container.get_connection_url())
    original_engine = repos_module.engine
    repos_module.engine = test_engine
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)
            await _init_db_data(conn)
        async with AsyncSession(test_engine, expire_on_commit=False) as ret:
            yield ret
    finally:
        repos_module.engine = original_engine


async def _init_db_data(conn: AsyncConnection) -> None:
    sql_script = await find_asset_text('init_db.sql')
    statements = sqlparse.split(sql_script)
    for statement in statements:
        if statement.strip():
            await conn.exec_driver_sql(statement)


@pytest_asyncio.fixture(name="client")
async def client_fixture(session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def get_db_override() -> AsyncGenerator[AsyncSession, None]:
        yield session

    async def get_current_user_override(db: AsyncSession = Depends(get_db)):
        from tero.users.repos import UserRepository
        user = await UserRepository(db).find_by_id(USER_ID)
        if user is None:
            raise ValueError(f"User with ID {USER_ID} not found")
        return user

    app.dependency_overrides[get_db] = get_db_override
    app.dependency_overrides[auth.get_current_user] = get_current_user_override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def assert_response(resp: Response, expected: Sequence[BaseModel] | BaseModel):
    resp.raise_for_status()
    assert resp.json() == (
        [json.loads(e.model_dump_json(by_alias=True)) for e in expected] if isinstance(expected, Sequence) else json.loads(
            expected.model_dump_json(by_alias=True)))


@pytest.fixture(name="users")
def users_fixture() -> List[UserListItem]:
    return [UserListItem(id=USER_ID, username="test", name="John Doe"),
            UserListItem(id=OTHER_USER_ID, username="test2", name="Jane Doe"),
            UserListItem(id=3, username="test3", name="John Doe 3"),
            UserListItem(id=5, username="test5", name="John Doe 5")]


@pytest.fixture(name="teams")
def teams_fixture() -> List[Team]:
    return [Team(id=GLOBAL_TEAM_ID, name="Test Team"),
            Team(id=2, name="Another Team"),
            Team(id=4, name="Fourth Team")]


@pytest.fixture(name="agents")
def agents_fixture(users: dict[int, UserListItem], teams: List[Team]) -> List[AgentListItem]:
    return [
        AgentListItem(id=AGENT_ID, name="Agent 1", description="This is the first agent",
                      last_update=parse_date("2025-02-21T12:00"), team=None,
                      user=users[0], active_users=1, can_edit=True),
        AgentListItem(id=2, name="Agent 2", description="This is the second agent",
                      last_update=parse_date("2025-02-21T12:01"), team=teams[0],
                      user=users[0], active_users=2, can_edit=True),
        AgentListItem(id=NON_EDITABLE_AGENT_ID, name="Agent 3", description="This is the third agent",
                      last_update=parse_date("2025-02-21T12:02"), team=teams[2],
                      user=users[1], active_users=1, can_edit=False),
        AgentListItem(id=5, name="Agent 5", description="This is the fifth agent",
                      last_update=parse_date("2025-02-21T12:04"), team=teams[1],
                      user=users[1], active_users=1, can_edit=True)]


async def configure_agent_tool(agent_id: int, tool_id: str, config: dict, client: AsyncClient) -> Response:
    resp = await try_configure_agent_tool(agent_id, tool_id, config, client)
    resp.raise_for_status()
    return resp


async def try_configure_agent_tool(agent_id: int, tool_id: str, config: dict, client: AsyncClient) -> Response:
    return await client.post(AGENT_TOOLS_PATH.format(agent_id=agent_id), json={"toolId": tool_id, "config": config})


async def upload_agent_tool_config_file(agent_id: int, tool_id: str, client: AsyncClient, filename: str = "test.txt",
        content: bytes = b"Hello") -> int:
    resp = await try_upload_agent_tool_config_file(agent_id, tool_id, client, filename, content)
    resp.raise_for_status()
    return resp.json()["id"]


async def try_upload_agent_tool_config_file(agent_id: int, tool_id: str, client: AsyncClient, filename: str = "test.txt",
        content: bytes = b"Hello") -> Response:
    return await client.post(AGENT_TOOL_FILES_PATH.format(agent_id=agent_id, tool_id=tool_id),
                            files={"file": (filename, content)})


async def await_files_processed(agent_id: int, tool_id: str, file_id: int, client: AsyncClient) -> Response:
    timeout_seconds = 10
    start_time = asyncio.get_event_loop().time()
    while True:
        resp = await find_agent_tool_config_files(agent_id, tool_id, client)
        resp.raise_for_status()
        files = resp.json()
        if all(file["status"] != FileStatus.PENDING.value for file in files):
            return resp
        if asyncio.get_event_loop().time() - start_time >= timeout_seconds:
            raise TimeoutError(f"File {file_id} processing timed out after {timeout_seconds} seconds")
        await asyncio.sleep(1)


async def find_agent_tool_config_files(agent_id: int, tool_id: str, client: AsyncClient) -> Response:
    return await client.get(AGENT_TOOL_FILES_PATH.format(agent_id=agent_id, tool_id=tool_id))


async def create_thread(agent_id: int, client: AsyncClient) -> Response:
    return await client.post(THREADS_PATH, json=ThreadCreateApi(agent_id=agent_id).model_dump())


def add_message_to_thread(client: AsyncClient, thread_id: int, message: str, parent_message_id:Optional[int] = None, files:List[str] = [], file_ids:List[int] = [], isInAgentEdition:Optional[bool] = False) -> AsyncContextManager[Response]:
    form_data = {"text": message, "origin": "USER"}
    if parent_message_id is not None:
        form_data["parentMessageId"] = str(parent_message_id)
    if isInAgentEdition is not None:
        form_data["isInAgentEdition"] = str(isInAgentEdition)
    if file_ids:
        form_data["fileIds"] = ",".join(str(file_id) for file_id in file_ids)
    file_data = []
    if files:
        for file_path in files:
            with open(file_path, 'rb') as f:
                file_data.append(("files", (os.path.basename(file_path), f.read())))

    return client.stream("POST", THREAD_MESSAGES_PATH.format(thread_id=thread_id), data=form_data, files=file_data)


class SafeEventLoopPolicy(asyncio.DefaultEventLoopPolicy):
    def new_event_loop(self):
        loop = super().new_event_loop()
        _orig_call_soon = loop.call_soon

        def safe_call_soon(callback, *args, **kwargs):
            # drop any callbacks scheduled after the loop is closed
            if loop.is_closed():
                return
            return _orig_call_soon(callback, *args, **kwargs)

        loop.call_soon = safe_call_soon # type: ignore
        return loop


@pytest.fixture(scope="session")
def event_loop_policy():
    # Avoid "Event loop is closed" error log generated aclose in httpx
    return SafeEventLoopPolicy()


@pytest.fixture
def override_user_role():
    def _override(role: Role):
        async def _fake_get_current_user():
            return _build_mock_user_with_role(role)
        app.dependency_overrides[auth.get_current_user] = _fake_get_current_user
    yield _override
    app.dependency_overrides.clear()


def _build_mock_user_with_role(role: Role) -> User:
    user = User(id=USER_ID, username='test', name="John Doe", monthly_usd_limit=env.monthly_usd_limit_default)
    team = Team(id=1, name="Test Team")
    team_role = TeamRole(team_id=team.id, user_id=user.id, role=role, status=TeamRoleStatus.ACCEPTED)
    team_role.team = team
    user.team_roles = [team_role]
    return user


@pytest.fixture
def override_user():
    def _override(user_id: int):
        async def _fake_get_current_user(db: AsyncSession = Depends(get_db)):
            from tero.users.repos import UserRepository
            user = await UserRepository(db).find_by_id(user_id)
            if user is None:
                raise ValueError(f"User with ID {user_id} not found")
            return user
        app.dependency_overrides[auth.get_current_user] = _fake_get_current_user
    yield _override
    app.dependency_overrides.clear()


async def find_asset_text(filename: str) -> str:
    async with aiofiles.open(solve_asset_path(filename, __file__), 'r') as file:
        return await file.read()


async def find_asset_bytes(filename: str) -> bytes:
    async with aiofiles.open(solve_asset_path(filename, __file__), 'rb') as file:
        return await file.read()


async def find_last_id(column: Mapped[int], db: AsyncSession) -> int:
    result = await db.exec(select(func.max(column)))
    return result.one()


@pytest.fixture(name="last_agent_id")
async def last_agent_id_fixture(session: AsyncSession) -> int:
    return await find_last_id(col(Agent.id), session)


@pytest.fixture(name="last_thread_id")
async def fixture_last_thread_id(session: AsyncSession) -> int:
    return await find_last_id(col(Thread.id), session)


@pytest.fixture(name="last_message_id")
async def fixture_last_message_id(session: AsyncSession) -> int:
    return await find_last_id(col(ThreadMessage.id), session)


@pytest.fixture(name="last_suite_run_id")
async def fixture_last_suite_run_id(session: AsyncSession) -> int:
    return await find_last_id(col(TestSuiteRun.id), session)


@pytest.fixture(name="last_result_id")
async def fixture_last_result_id(session: AsyncSession) -> int:
    return await find_last_id(col(TestCaseResult.id), session)
