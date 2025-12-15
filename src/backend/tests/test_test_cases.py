from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import re
from typing import List, cast, Optional

from sse_starlette import ServerSentEvent

from .common import *

from tero.agents.test_cases.api import TEST_CASES_PATH, TEST_CASE_PATH, TEST_CASE_CLONE_PATH, TEST_CASE_MESSAGES_PATH, TEST_CASE_MESSAGE_PATH, TEST_SUITE_RUN_RESULTS_PATH, TEST_SUITE_RUN_RESULT_MESSAGE_PATH
from tero.agents.test_cases.domain import TestCaseResult, TestCaseResultStatus, NewTestCaseMessage, UpdateTestCaseMessage, PublicTestCase, TestSuiteRun, TestSuiteRunStatus
from tero.threads.domain import ThreadMessageOrigin, ThreadMessagePublic, Thread
from tero.tools.core import AgentActionEvent, AgentAction


TEST_CASE_1_THREAD_ID = 7
TEST_CASE_2_THREAD_ID = 8
TEST_CASE_3_THREAD_ID = 9
TEST_CASE_4_THREAD_ID = 13
EXECUTION_THREAD_1_ID = 10
EXECUTION_THREAD_2_ID = 11
EXECUTION_THREAD_3_ID = 12


@dataclass
class TestCaseStep:
    input: str
    response_chunks: List[str]
    user_message_id: int
    agent_message_id: int
    execution_statuses: Optional[List[AgentActionEvent]] = None


@dataclass
class TestCaseExpectation:
    test_case_id: int
    result_id: int
    status: TestCaseResultStatus
    steps: List[TestCaseStep]


@pytest.fixture(name="test_cases")
def test_cases_fixture() -> List[PublicTestCase]:
    return [
        PublicTestCase(
            agent_id=AGENT_ID,
            thread=Thread(
                id=TEST_CASE_1_THREAD_ID,
                name="Test Case #1",
                user_id=USER_ID,
                agent_id=AGENT_ID,
                creation=parse_date("2025-02-21T12:10:00"),
                is_test_case=True
            ),
            last_update=parse_date("2025-02-21T12:10:00")
        ),
        PublicTestCase(
            agent_id=AGENT_ID,
            thread=Thread(
                id=TEST_CASE_2_THREAD_ID,
                name="Test Case #2",
                user_id=USER_ID,
                agent_id=AGENT_ID,
                creation=parse_date("2025-02-21T12:11:00"),
                is_test_case=True
            ),
            last_update=parse_date("2025-02-21T12:11:00")
        ),
        PublicTestCase(
            agent_id=AGENT_ID,
            thread=Thread(
                id=TEST_CASE_4_THREAD_ID,
                name="Test Case #4",
                user_id=USER_ID,
                agent_id=AGENT_ID,
                creation=parse_date("2025-02-21T12:13:00"),
                is_test_case=True
            ),
            last_update=parse_date("2025-02-21T12:15:00")
        )
    ]


async def test_find_test_cases(client: AsyncClient, test_cases: List[PublicTestCase]):
    resp = await _find_test_cases(client, AGENT_ID)
    assert_response(resp, [test_cases[0], test_cases[1], test_cases[2]])


async def _find_test_cases(client: AsyncClient, agent_id: int) -> Response:
    return await client.get(TEST_CASES_PATH.format(agent_id=agent_id))


async def test_find_test_cases_unauthorized_agent(client: AsyncClient):
    resp = await _find_test_cases(client, NON_VISIBLE_AGENT_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@freeze_time(CURRENT_TIME)
async def test_add_test_case(client: AsyncClient, test_cases: List[PublicTestCase], last_thread_id: int):
    resp = await _add_test_case(AGENT_ID, client)
    resp.raise_for_status()
    resp = await _find_test_cases(client, AGENT_ID)
    assert_response(resp, [test_cases[0],
        test_cases[1],
        test_cases[2],
        PublicTestCase(
            thread=Thread(
                id=last_thread_id + 1,
                name="Test Case #4",
                user_id=USER_ID,
                agent_id=AGENT_ID,
                creation=CURRENT_TIME,
                is_test_case=True
            ),
        agent_id=AGENT_ID,
        last_update=CURRENT_TIME
    )])


async def _add_test_case(agent_id: int, client: AsyncClient) -> Response:
    return await client.post(TEST_CASES_PATH.format(agent_id=agent_id))


async def test_add_test_case_unauthorized_agent(client: AsyncClient):
    resp = await _add_test_case(NON_VISIBLE_AGENT_ID, client)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@freeze_time(CURRENT_TIME)
async def test_clone_test_case(client: AsyncClient, test_cases: List[PublicTestCase], last_thread_id: int):
    resp = await _clone_test_case(client, AGENT_ID, TEST_CASE_1_THREAD_ID)
    expected_clone = PublicTestCase(
        agent_id=AGENT_ID,
        thread=Thread(
            id=last_thread_id + 1,
            name="Test Case #1 (copy)",
            user_id=USER_ID,
            agent_id=AGENT_ID,
            creation=CURRENT_TIME,
            is_test_case=True
        ),
        last_update=CURRENT_TIME
    )
    assert_response(resp, expected_clone)

    resp = await _find_test_cases(client, AGENT_ID)
    assert_response(resp, [test_cases[0], test_cases[1], test_cases[2], expected_clone])


async def _clone_test_case(client: AsyncClient, agent_id: int, test_case_id: int) -> Response:
    return await client.post(TEST_CASE_CLONE_PATH.format(agent_id=agent_id, test_case_id=test_case_id))


async def test_clone_test_case_unauthorized_agent(client: AsyncClient):
    resp = await _clone_test_case(client, NON_VISIBLE_AGENT_ID, TEST_CASE_1_THREAD_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_clone_test_case_not_found(client: AsyncClient):
    resp = await _clone_test_case(client, AGENT_ID, 999)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_clone_test_case_from_another_agent(client: AsyncClient):
    resp = await _clone_test_case(client, AGENT_ID, TEST_CASE_3_THREAD_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_find_test_case(client: AsyncClient, test_cases: List[PublicTestCase]):
    resp = await _find_test_case(client, AGENT_ID, TEST_CASE_1_THREAD_ID)
    assert_response(resp, test_cases[0])


async def _find_test_case(client: AsyncClient, agent_id: int, test_case_id: int) -> Response:
    return await client.get(TEST_CASE_PATH.format(agent_id=agent_id, test_case_id=test_case_id))


async def test_find_test_case_not_found(client: AsyncClient):
    resp = await _find_test_case(client, AGENT_ID, 999)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_find_test_case_unauthorized_agent(client: AsyncClient):
    resp = await _find_test_case(client, NON_VISIBLE_AGENT_ID, TEST_CASE_1_THREAD_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_find_test_case_from_another_agent(client: AsyncClient):
    resp = await _find_test_case(client, AGENT_ID, TEST_CASE_3_THREAD_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_test_case(client: AsyncClient, test_cases: List[PublicTestCase]):
    resp = await _delete_test_case(client, AGENT_ID, TEST_CASE_2_THREAD_ID)
    assert resp.status_code == status.HTTP_204_NO_CONTENT

    resp = await _find_test_case(client, AGENT_ID, TEST_CASE_2_THREAD_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND

    resp = await _find_test_cases(client, AGENT_ID)
    assert_response(resp, [test_cases[0], test_cases[2]])


async def _delete_test_case(client: AsyncClient, agent_id: int, test_case_id: int) -> Response:
    return await client.delete(TEST_CASE_PATH.format(agent_id=agent_id, test_case_id=test_case_id))


async def test_delete_test_case_not_found(client: AsyncClient):
    resp = await _delete_test_case(client, AGENT_ID, 999)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_test_case_unauthorized_agent(client: AsyncClient):
    resp = await _delete_test_case(client, NON_VISIBLE_AGENT_ID, TEST_CASE_1_THREAD_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_delete_test_case_from_another_agent(client: AsyncClient):
    resp = await _delete_test_case(client, AGENT_ID, TEST_CASE_3_THREAD_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def _assert_test_case_stream(resp: Response, suite_run_id: int, test_cases: List[TestCaseExpectation],
                                   skipped_test_case_ids: Optional[List[int]] = None, remove_analysis_from_response: bool = True):
    buffer, events = [], []
    separator = "\r\n\r\n"

    def flush_buffer():
        if buffer:
            events.append(f"data: {''.join(buffer)}{separator}".encode())
            buffer.clear()

    async for chunk in resp.aiter_bytes():
        decoded_chunk = chunk.decode()
        for event in decoded_chunk.split(separator):
            if event.startswith("data: "):
                buffer.append(event[6:])
            else:
                flush_buffer()
                if event:
                    if remove_analysis_from_response:
                        # Remove the entire "analysis" field including null or string values, and any surrounding commas
                        event = re.sub(r'(?:,\s*)?"analysis"\s*:\s*(null|"[^"]*")(?:\s*,)?', '', event)
                    events.append(f"{event}{separator}".encode())

    flush_buffer()

    expected_events = []

    for test_case in test_cases:
        expected_events.append(
            ServerSentEvent(event="suite.test.start", data=str(json.dumps({
                "testCaseId": test_case.test_case_id,
                "resultId": test_case.result_id
            }))).encode()
        )

        expected_events.append(
            ServerSentEvent(event="suite.test.metadata", data=str(json.dumps({
                "testCaseId": test_case.test_case_id,
                "resultId": test_case.result_id
            }))).encode()
        )

        for step in test_case.steps:
            expected_events.append(
                ServerSentEvent(event="suite.test.phase", data=str(json.dumps({
                    "phase": "executing"
                }))).encode()
            )

            expected_events.append(
                ServerSentEvent(event="suite.test.userMessage", data=str(json.dumps({
                    "id": step.user_message_id,
                    "text": step.input
                }))).encode()
            )

            expected_events.append(
                ServerSentEvent(event="suite.test.agentMessage.start", data=str(json.dumps({
                    "id": step.agent_message_id
                }))).encode()
            )

            if step.execution_statuses is None:
                expected_events.append(
                    ServerSentEvent(event="suite.test.executionStatus", data=str(json.dumps(
                        AgentActionEvent(action=AgentAction.PRE_MODEL_HOOK).model_dump()))
                    ).encode()
                )
            else:
                for status_event in step.execution_statuses:
                    expected_events.append(
                        ServerSentEvent(event="suite.test.executionStatus", data=str(json.dumps(
                            status_event.model_dump()))
                        ).encode()
                    )

            for chunk in step.response_chunks:
                expected_events.append(
                    ServerSentEvent(event="suite.test.agentMessage.chunk", data=str(json.dumps({
                        "id": step.agent_message_id,
                        "chunk": chunk
                    }))).encode()
                )

            expected_events.append(
                ServerSentEvent(event="suite.test.agentMessage.complete", data=str(json.dumps({
                    "id": step.agent_message_id,
                    "text": ''.join(step.response_chunks)
                }))).encode()
            )

            expected_events.append(
                ServerSentEvent(event="suite.test.phase", data=str(json.dumps({
                    "phase": "evaluating"
                }))).encode()
            )

        expected_events.append(
            ServerSentEvent(event="suite.test.phase", data=str(json.dumps({
                "phase": "completed",
                "status": test_case.status.value,
                "evaluation": {
                    "passed": test_case.status == TestCaseResultStatus.SUCCESS
                }
            }))).encode()
        )

        expected_events.append(
            ServerSentEvent(event="suite.test.complete", data=str(json.dumps({
                "testCaseId": test_case.test_case_id,
                "resultId": test_case.result_id,
                "status": test_case.status.value,
                "evaluation": {}
            }))).encode()
        )

    passed = sum(1 for tc in test_cases if tc.status == TestCaseResultStatus.SUCCESS)
    failed = sum(1 for tc in test_cases if tc.status == TestCaseResultStatus.FAILURE)
    errors = sum(1 for tc in test_cases if tc.status == TestCaseResultStatus.ERROR)
    skipped = len(skipped_test_case_ids) if skipped_test_case_ids else 0

    suite_status = "SUCCESS" if failed == 0 and errors == 0 else "FAILURE"

    expected_events.append(
        ServerSentEvent(event="suite.complete", data=str(json.dumps({
            "suiteRunId": suite_run_id,
            "status": suite_status,
            "totalTests": len(test_cases) + skipped,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped
        }))).encode()
    )

    assert events == expected_events


async def test_get_test_case_result(client: AsyncClient):
    suite_run_id = 1
    resp = await _find_suite_run_results(client, AGENT_ID, suite_run_id)
    analysis = _get_analysis_from_response(resp)
    assert_response(resp, [
        TestCaseResult(
            id=1,
            thread_id=EXECUTION_THREAD_1_ID,
            test_case_id=TEST_CASE_1_THREAD_ID,
            test_suite_run_id=suite_run_id,
            status=TestCaseResultStatus.SUCCESS,
            evaluator_analysis=analysis[1],
            executed_at=parse_date("2025-02-21T12:15:00"),
            test_case_name="Test Case #1"
        ),
        TestCaseResult(
            id=2,
            thread_id=EXECUTION_THREAD_2_ID,
            test_case_id=TEST_CASE_2_THREAD_ID,
            test_suite_run_id=suite_run_id,
            status=TestCaseResultStatus.SUCCESS,
            evaluator_analysis=analysis[0],
            executed_at=parse_date("2025-02-21T12:16:00"),
            test_case_name="Test Case #2"
        )
    ])


async def _find_suite_run_results(client: AsyncClient, agent_id: int, suite_run_id: int) -> Response:
    return await client.get(TEST_SUITE_RUN_RESULTS_PATH.format(agent_id=agent_id, suite_run_id=suite_run_id))


async def test_get_suite_run_results_not_found(client: AsyncClient):
    resp = await _find_suite_run_results(client, AGENT_ID, 999)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_get_suite_run_results_unauthorized_agent(client: AsyncClient):
    resp = await _find_suite_run_results(client, NON_VISIBLE_AGENT_ID, 1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_get_suite_run_results_from_another_agent(client: AsyncClient):
    resp = await _find_suite_run_results(client, AGENT_ID, 2)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_get_test_case_run_messages(client: AsyncClient):
    resp = await _get_suite_run_result_messages(client, AGENT_ID, 1, 1)
    assert_response(resp, [
        ThreadMessagePublic(
            id=17,
            thread_id=EXECUTION_THREAD_1_ID,
            text="Which is the first natural number? Only provide the number",
            origin=ThreadMessageOrigin.USER,
            timestamp=parse_date("2025-02-21T12:15:00"),
            minutes_saved=None,
            stopped=False,
            files=[]
        ),
        ThreadMessagePublic(
            id=18,
            thread_id=EXECUTION_THREAD_1_ID,
            text="1",
            origin=ThreadMessageOrigin.AGENT,
            timestamp=parse_date("2025-02-21T12:16:00"),
            minutes_saved=None,
            stopped=False,
            files=[]
        )
    ])


async def _get_suite_run_result_messages(client: AsyncClient, agent_id: int, suite_run_id: int, result_id: int) -> Response:
    return await client.get(TEST_SUITE_RUN_RESULT_MESSAGE_PATH.format(agent_id=agent_id, suite_run_id=suite_run_id, result_id=result_id))


async def test_get_suite_run_result_messages_not_found(client: AsyncClient):
    resp = await _get_suite_run_result_messages(client, AGENT_ID, 1, 999)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_get_suite_run_result_messages_unauthorized_agent(client: AsyncClient):
    resp = await _get_suite_run_result_messages(client, NON_VISIBLE_AGENT_ID, 1, 1)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_get_suite_run_result_messages_from_another_agent(client: AsyncClient):
    resp = await _get_suite_run_result_messages(client, AGENT_ID, 2, 3)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_find_test_case_messages(client: AsyncClient):
    resp = await _find_test_case_messages(client, AGENT_ID, TEST_CASE_4_THREAD_ID)
    assert_response(resp, [
        ThreadMessagePublic(
            id=23,
            thread_id=TEST_CASE_4_THREAD_ID,
            text="What is 2 + 2? Only provide the number",
            origin=ThreadMessageOrigin.USER,
            timestamp=parse_date("2025-02-21T12:13:00"),
            minutes_saved=None,
            stopped=False,
            files=[],
            status_updates=None
        ),
        ThreadMessagePublic(
            id=24,
            thread_id=TEST_CASE_4_THREAD_ID,
            text="4",
            origin=ThreadMessageOrigin.AGENT,
            timestamp=parse_date("2025-02-21T12:14:00"),
            minutes_saved=None,
            stopped=False,
            files=[],
            status_updates=None
        ),
        ThreadMessagePublic(
            id=25,
            thread_id=TEST_CASE_4_THREAD_ID,
            text="What is 3 + 3? Only provide the number",
            origin=ThreadMessageOrigin.USER,
            timestamp=parse_date("2025-02-21T12:14:00"),
            minutes_saved=None,
            stopped=False,
            files=[],
            status_updates=None
        ),
        ThreadMessagePublic(
            id=26,
            thread_id=TEST_CASE_4_THREAD_ID,
            text="6",
            origin=ThreadMessageOrigin.AGENT,
            timestamp=parse_date("2025-02-21T12:15:00"),
            minutes_saved=None,
            stopped=False,
            files=[],
            status_updates=None
        )
    ])


async def _find_test_case_messages(client: AsyncClient, agent_id: int, test_case_id: int) -> Response:
    return await client.get(TEST_CASE_MESSAGES_PATH.format(agent_id=agent_id, test_case_id=test_case_id))


async def test_find_test_case_messages_unauthorized_agent(client: AsyncClient):
    resp = await _find_test_case_messages(client, NON_VISIBLE_AGENT_ID, TEST_CASE_1_THREAD_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_find_test_case_messages_from_another_agent(client: AsyncClient):
    resp = await _find_test_case_messages(client, AGENT_ID, TEST_CASE_3_THREAD_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@freeze_time(CURRENT_TIME)
async def test_add_test_case_message(client: AsyncClient, last_message_id: int):
    message_data = NewTestCaseMessage(text="New test message", origin=ThreadMessageOrigin.USER)
    expected_messages = [
        ThreadMessagePublic(
            id=11,
            thread_id=TEST_CASE_1_THREAD_ID,
            text="Which is the first natural number? Only provide the number",
            origin=ThreadMessageOrigin.USER,
            timestamp=parse_date("2025-02-21T12:10:00"),
            minutes_saved=None,
            stopped=False,
            files=[],
            status_updates=None
        ),
        ThreadMessagePublic(
            id=12,
            thread_id=TEST_CASE_1_THREAD_ID,
            text="1",
            origin=ThreadMessageOrigin.AGENT,
            timestamp=parse_date("2025-02-21T12:11:00"),
            minutes_saved=None,
            stopped=False,
            files=[],
            status_updates=None
        ),
        ThreadMessagePublic(
            id=last_message_id + 1,
            thread_id=TEST_CASE_1_THREAD_ID,
            text=message_data.text,
            origin=message_data.origin,
            timestamp=CURRENT_TIME,
            minutes_saved=None,
            stopped=False,
            files=[],
            status_updates=None
        )
    ]
    resp = await _add_test_case_message(client, AGENT_ID, TEST_CASE_1_THREAD_ID, message_data)
    assert_response(resp, expected_messages[-1])
    resp = await _find_test_case_messages(client, AGENT_ID, TEST_CASE_1_THREAD_ID)
    assert_response(resp, cast(List[BaseModel], expected_messages))


async def _add_test_case_message(client: AsyncClient, agent_id: int, test_case_id: int, message_data: NewTestCaseMessage) -> Response:
    return await client.post(TEST_CASE_MESSAGES_PATH.format(agent_id=agent_id, test_case_id=test_case_id), json={"text": message_data.text, "origin": message_data.origin.value})


async def test_add_test_case_message_unauthorized_agent(client: AsyncClient):
    resp = await _add_test_case_message(client, NON_VISIBLE_AGENT_ID, TEST_CASE_1_THREAD_ID, NewTestCaseMessage(text="Test message", origin=ThreadMessageOrigin.USER))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_add_test_case_message_to_another_agent(client: AsyncClient):
    resp = await _add_test_case_message(client, AGENT_ID, TEST_CASE_3_THREAD_ID, NewTestCaseMessage(text="Malicious message", origin=ThreadMessageOrigin.USER))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@freeze_time(CURRENT_TIME)
async def test_update_test_case_message(client: AsyncClient):
    resp = await _update_test_case_message(client, AGENT_ID, TEST_CASE_1_THREAD_ID, 11, UpdateTestCaseMessage(text="Updated test message"))
    assert_response(resp, ThreadMessagePublic(
        id=11,
        thread_id=TEST_CASE_1_THREAD_ID,
        text="Updated test message",
        origin=ThreadMessageOrigin.USER,
        timestamp=parse_date("2025-02-21T12:10:00"),
        minutes_saved=None,
        stopped=False,
        files=[],
        status_updates=None
    ))


async def _update_test_case_message(client: AsyncClient, agent_id: int, test_case_id: int, message_id: int, message_data: UpdateTestCaseMessage) -> Response:
    return await client.put(TEST_CASE_MESSAGE_PATH.format(agent_id=agent_id, test_case_id=test_case_id, message_id=message_id), json=message_data.model_dump())


async def test_update_test_case_message_not_found(client: AsyncClient):
    resp = await _update_test_case_message(client, AGENT_ID, TEST_CASE_1_THREAD_ID, 999, UpdateTestCaseMessage(text="Updated message"))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_update_test_case_message_unauthorized_agent(client: AsyncClient):
    resp = await _update_test_case_message(client, NON_VISIBLE_AGENT_ID, TEST_CASE_1_THREAD_ID, 1, UpdateTestCaseMessage(text="Updated message"))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_update_message_from_another_agent_test_case(client: AsyncClient):
    resp = await _update_test_case_message(client, AGENT_ID, TEST_CASE_3_THREAD_ID, 15, UpdateTestCaseMessage(text="Malicious update"))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_update_message_with_wrong_message_id(client: AsyncClient):
    resp = await _update_test_case_message(client, AGENT_ID, TEST_CASE_1_THREAD_ID, 15, UpdateTestCaseMessage(text="Wrong message update"))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_update_message_from_regular_thread(client: AsyncClient):
    resp = await _update_test_case_message(client, AGENT_ID, TEST_CASE_1_THREAD_ID, 1, UpdateTestCaseMessage(text="Trying to modify regular thread message"))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_update_message_from_execution_thread(client: AsyncClient):
    resp = await _update_test_case_message(client, AGENT_ID, TEST_CASE_1_THREAD_ID, 17, UpdateTestCaseMessage(text="Trying to modify execution thread message"))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_update_message_from_different_test_case_same_agent(client: AsyncClient):
    resp = await _update_test_case_message(client, AGENT_ID, TEST_CASE_1_THREAD_ID, 13, UpdateTestCaseMessage(text="Trying to modify different test case message"))
    assert resp.status_code == status.HTTP_404_NOT_FOUND


async def test_generate_test_case_name_after_messages(client: AsyncClient):
    create_resp = await _add_test_case(AGENT_ID, client)
    create_resp.raise_for_status()
    new_test_case = create_resp.json()
    new_test_case_id = new_test_case["thread"]["id"]

    user_message_resp = await _add_test_case_message(
        client,
        AGENT_ID,
        new_test_case_id,
        NewTestCaseMessage(text="Reset the password for user Alice.", origin=ThreadMessageOrigin.USER),
    )
    user_message_resp.raise_for_status()

    test_case_resp = await _find_test_case(client, AGENT_ID, new_test_case_id)
    assert test_case_resp.json()["thread"]["name"].startswith("Test Case #")

    agent_message_resp = await _add_test_case_message(
        client,
        AGENT_ID,
        new_test_case_id,
        NewTestCaseMessage(
            text="The password was reset successfully and an email confirmation was sent.",
            origin=ThreadMessageOrigin.AGENT,
        ),
    )
    agent_message_resp.raise_for_status()

    updated_test_case_resp = await _find_test_case(client, AGENT_ID, new_test_case_id)
    assert not updated_test_case_resp.json()["thread"]["name"].startswith("Test Case #")


async def test_find_test_case_runs(client: AsyncClient):
    resp = await _find_test_case_runs(client, AGENT_ID)
    assert_response(resp, [
        TestSuiteRun(
            id=1,
            agent_id=AGENT_ID,
            status=TestSuiteRunStatus.SUCCESS,
            executed_at=parse_date("2025-02-21T12:15:00"),
            completed_at=parse_date("2025-02-21T12:17:00"),
            total_tests=2,
            passed_tests=2,
            failed_tests=0,
            error_tests=0,
            skipped_tests=0
        )
    ])


async def _find_test_case_runs(client: AsyncClient, agent_id: int) -> Response:
    return await client.get(f"{TEST_CASES_PATH}/runs".format(agent_id=agent_id))


async def test_find_test_case_runs_unauthorized_agent(client: AsyncClient):
    resp = await _find_test_case_runs(client, NON_VISIBLE_AGENT_ID)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


@freeze_time(CURRENT_TIME)
async def test_run_test_suite_with_specific_test_cases(client: AsyncClient, last_thread_id: int, last_message_id: int, last_suite_run_id: int, last_result_id: int):
    expected_input = "Which is the first natural number? Only provide the number"
    expected_response_chunks = ["1"]
    expected_suite_run_id = last_suite_run_id + 1
    expected_result_id = last_result_id + 1
    request_body = {"test_case_ids": [TEST_CASE_1_THREAD_ID]}

    resp = await _run_test_suite(client, AGENT_ID, request_body)
    assert_response(resp, TestSuiteRun(
        id=expected_suite_run_id,
        agent_id=AGENT_ID,
        status=TestSuiteRunStatus.RUNNING,
        executed_at=CURRENT_TIME,
        completed_at=None,
        total_tests=3,
        passed_tests=0,
        failed_tests=0,
        error_tests=0,
        skipped_tests=0
    ))

    async with _stream_test_suite_execution(client, AGENT_ID, expected_suite_run_id) as resp:
        resp.raise_for_status()
        await _assert_test_case_stream(
            resp,
            expected_suite_run_id,
            [
                TestCaseExpectation(
                    test_case_id=TEST_CASE_1_THREAD_ID,
                    result_id=expected_result_id,
                    status=TestCaseResultStatus.SUCCESS,
                    steps=[
                        TestCaseStep(
                            input=expected_input,
                            response_chunks=expected_response_chunks,
                            user_message_id=last_message_id + 1,
                            agent_message_id=last_message_id + 2
                        )
                    ]
                )
            ],
            skipped_test_case_ids=[TEST_CASE_2_THREAD_ID, TEST_CASE_4_THREAD_ID]
        )

    resp = await _find_suite_run_results(client, AGENT_ID, expected_suite_run_id)
    analysis = _get_analysis_from_response(resp)
    assert_response(resp, [
        TestCaseResult(
            id=expected_result_id,
            thread_id=last_thread_id + 1,
            test_case_id=TEST_CASE_1_THREAD_ID,
            test_suite_run_id=expected_suite_run_id,
            status=TestCaseResultStatus.SUCCESS,
            evaluator_analysis=analysis[0],
            executed_at=CURRENT_TIME,
            test_case_name="Test Case #1"
        ),
        TestCaseResult(
            id=expected_result_id + 1,
            thread_id=None,
            test_case_id=TEST_CASE_2_THREAD_ID,
            test_suite_run_id=expected_suite_run_id,
            status=TestCaseResultStatus.SKIPPED,
            evaluator_analysis=analysis[1],
            executed_at=CURRENT_TIME,
            test_case_name="Test Case #2"
        ),
        TestCaseResult(
            id=expected_result_id + 2,
            thread_id=None,
            test_case_id=TEST_CASE_4_THREAD_ID,
            test_suite_run_id=expected_suite_run_id,
            status=TestCaseResultStatus.SKIPPED,
            evaluator_analysis=analysis[2],
            executed_at=CURRENT_TIME,
            test_case_name="Test Case #4"
        )
    ])


async def _run_test_suite(client: AsyncClient, agent_id: int, request_body: dict) -> Response:
    return await client.post(f"{TEST_CASES_PATH}/runs".format(agent_id=agent_id), json=request_body)


@asynccontextmanager
async def _stream_test_suite_execution(client: AsyncClient, agent_id: int, suite_run_id: int):
    async with client.stream("GET", f"{TEST_CASES_PATH}/runs/{suite_run_id}/stream".format(agent_id=agent_id)) as resp:
        yield resp


@freeze_time(CURRENT_TIME)
async def test_run_test_suite_with_all_test_cases(client: AsyncClient, last_thread_id: int, last_message_id: int, last_suite_run_id: int, last_result_id: int):
    expected_suite_run_id = last_suite_run_id + 1
    expected_result_id = last_result_id + 1

    resp = await _run_test_suite(client, AGENT_ID, {})
    assert_response(resp, TestSuiteRun(
        id=expected_suite_run_id,
        agent_id=AGENT_ID,
        status=TestSuiteRunStatus.RUNNING,
        executed_at=CURRENT_TIME,
        completed_at=None,
        total_tests=3,
        passed_tests=0,
        failed_tests=0,
        error_tests=0,
        skipped_tests=0
    ))

    async with _stream_test_suite_execution(client, AGENT_ID, expected_suite_run_id) as resp:
        resp.raise_for_status()
        await _assert_test_case_stream(
            resp,
            expected_suite_run_id,
            [
                TestCaseExpectation(
                    test_case_id=TEST_CASE_1_THREAD_ID,
                    result_id=expected_result_id,
                    status=TestCaseResultStatus.SUCCESS,
                    steps=[
                        TestCaseStep(
                            input="Which is the first natural number? Only provide the number",
                            response_chunks=["1"],
                            user_message_id=last_message_id + 1,
                            agent_message_id=last_message_id + 2,
                            execution_statuses=[
                                AgentActionEvent(action=AgentAction.PRE_MODEL_HOOK)
                            ]
                        )
                    ]
                ),
                TestCaseExpectation(
                    test_case_id=TEST_CASE_2_THREAD_ID,
                    result_id=expected_result_id + 1,
                    status=TestCaseResultStatus.SUCCESS,
                    steps=[
                        TestCaseStep(
                            input="Which is the capital of Uruguay? Output just the name",
                            response_chunks=["Monte", "video"],
                            user_message_id=last_message_id + 3,
                            agent_message_id=last_message_id + 4,
                            execution_statuses=[
                                AgentActionEvent(action=AgentAction.PRE_MODEL_HOOK)
                            ]
                        )
                    ]
                ),
                TestCaseExpectation(
                    test_case_id=TEST_CASE_4_THREAD_ID,
                    result_id=expected_result_id + 2,
                    status=TestCaseResultStatus.SUCCESS,
                    steps=[
                        TestCaseStep(
                            input="What is 2 + 2? Only provide the number",
                            response_chunks=["4"],
                            user_message_id=last_message_id + 5,
                            agent_message_id=last_message_id + 6,
                            execution_statuses=[
                                AgentActionEvent(action=AgentAction.PRE_MODEL_HOOK)
                            ]
                        ),
                        TestCaseStep(
                            input="What is 3 + 3? Only provide the number",
                            response_chunks=["6"],
                            user_message_id=last_message_id + 7,
                            agent_message_id=last_message_id + 8,
                            execution_statuses=[
                                AgentActionEvent(action=AgentAction.PRE_MODEL_HOOK)
                            ]
                        )
                    ]
                )
            ]
        )

    resp = await _find_suite_run_results(client, AGENT_ID, expected_suite_run_id)
    analysis = _get_analysis_from_response(resp)
    assert_response(resp, [
        TestCaseResult(
            id=expected_result_id,
            thread_id=last_thread_id + 1,
            test_case_id=TEST_CASE_1_THREAD_ID,
            test_suite_run_id=expected_suite_run_id,
            status=TestCaseResultStatus.SUCCESS,
            evaluator_analysis=analysis[0],
            executed_at=CURRENT_TIME,
            test_case_name="Test Case #1"
        ),
        TestCaseResult(
            id=expected_result_id + 1,
            thread_id=last_thread_id + 2,
            test_case_id=TEST_CASE_2_THREAD_ID,
            test_suite_run_id=expected_suite_run_id,
            status=TestCaseResultStatus.SUCCESS,
            evaluator_analysis=analysis[1],
            executed_at=CURRENT_TIME,
            test_case_name="Test Case #2"
        ),
        TestCaseResult(
            id=expected_result_id + 2,
            thread_id=last_thread_id + 3,
            test_case_id=TEST_CASE_4_THREAD_ID,
            test_suite_run_id=expected_suite_run_id,
            status=TestCaseResultStatus.SUCCESS,
            evaluator_analysis=analysis[2],
            executed_at=CURRENT_TIME,
            test_case_name="Test Case #4"
        )
    ])


@freeze_time(CURRENT_TIME)
async def test_run_test_suite_with_multi_step_test_case(client: AsyncClient, last_thread_id: int, last_message_id: int, last_suite_run_id: int, last_result_id: int):
    expected_suite_run_id = last_suite_run_id + 1
    expected_result_id = last_result_id + 1

    request_body = {"test_case_ids": [TEST_CASE_4_THREAD_ID]}

    resp = await _run_test_suite(client, AGENT_ID, request_body)
    assert_response(resp, TestSuiteRun(
        id=expected_suite_run_id,
        agent_id=AGENT_ID,
        status=TestSuiteRunStatus.RUNNING,
        executed_at=CURRENT_TIME,
        completed_at=None,
        total_tests=3,
        passed_tests=0,
        failed_tests=0,
        error_tests=0,
        skipped_tests=0
    ))

    async with _stream_test_suite_execution(client, AGENT_ID, expected_suite_run_id) as resp:
        resp.raise_for_status()
        await _assert_test_case_stream(
            resp,
            expected_suite_run_id,
            [
                TestCaseExpectation(
                    test_case_id=TEST_CASE_4_THREAD_ID,
                    result_id=expected_result_id + 2,
                    status=TestCaseResultStatus.SUCCESS,
                    steps=[
                        TestCaseStep(
                            input="What is 2 + 2? Only provide the number",
                            response_chunks=["4"],
                            user_message_id=last_message_id + 1,
                            agent_message_id=last_message_id + 2,
                            execution_statuses=[
                                AgentActionEvent(action=AgentAction.PRE_MODEL_HOOK)
                            ]
                        ),
                        TestCaseStep(
                            input="What is 3 + 3? Only provide the number",
                            response_chunks=["6"],
                            user_message_id=last_message_id + 3,
                            agent_message_id=last_message_id + 4,
                            execution_statuses=[
                                AgentActionEvent(action=AgentAction.PRE_MODEL_HOOK)
                            ]
                        )
                    ]
                )
            ],
            skipped_test_case_ids=[TEST_CASE_1_THREAD_ID, TEST_CASE_2_THREAD_ID]
        )

    resp = await _find_suite_run_results(client, AGENT_ID, expected_suite_run_id)
    analysis = _get_analysis_from_response(resp)
    assert_response(resp, [
        TestCaseResult(
            id=expected_result_id,
            thread_id=None,
            test_case_id=TEST_CASE_1_THREAD_ID,
            test_suite_run_id=expected_suite_run_id,
            status=TestCaseResultStatus.SKIPPED,
            evaluator_analysis=analysis[0],
            executed_at=CURRENT_TIME,
            test_case_name="Test Case #1"
        ),
        TestCaseResult(
            id=expected_result_id + 1,
            thread_id=None,
            test_case_id=TEST_CASE_2_THREAD_ID,
            test_suite_run_id=expected_suite_run_id,
            status=TestCaseResultStatus.SKIPPED,
            evaluator_analysis=analysis[1],
            executed_at=CURRENT_TIME,
            test_case_name="Test Case #2"
        ),
        TestCaseResult(
            id=expected_result_id + 2,
            thread_id=last_thread_id + 1,
            test_case_id=TEST_CASE_4_THREAD_ID,
            test_suite_run_id=expected_suite_run_id,
            status=TestCaseResultStatus.SUCCESS,
            evaluator_analysis=analysis[2],
            executed_at=CURRENT_TIME,
            test_case_name="Test Case #4"
        )
    ])


async def test_run_test_suite_with_invalid_test_case_ids(client: AsyncClient):
    resp = await _run_test_suite(client, AGENT_ID, {"test_case_ids": [999, 1000]})
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


async def test_run_test_suite_unauthorized_agent(client: AsyncClient):
    request_body = {"test_case_ids": [TEST_CASE_1_THREAD_ID]}
    resp = await _run_test_suite(client, NON_VISIBLE_AGENT_ID, request_body)
    assert resp.status_code == status.HTTP_404_NOT_FOUND


def _get_analysis_from_response(response: Response) -> list[str]:
    return [obj.get("evaluatorAnalysis", "") for obj in response.json()]
