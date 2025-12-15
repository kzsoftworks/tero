from typing import Callable

from .common import *

from tero.teams.domain import PublicTeamRole, Role, TeamRoleStatus
from tero.users.api import CURRENT_USER_PATH, USERS_PATH
from tero.users.domain import UserProfile, UserListItem


async def test_get_user_profile(client: AsyncClient, teams:list[Team]):
    resp = await client.get(CURRENT_USER_PATH)
    assert_response(resp, UserProfile(teams=[PublicTeamRole(id=teams[0].id, name=teams[0].name, role=Role.TEAM_OWNER, status=TeamRoleStatus.ACCEPTED),
                                             PublicTeamRole(id=teams[1].id, name=teams[1].name, role=Role.TEAM_OWNER, status=TeamRoleStatus.ACCEPTED),
                                             PublicTeamRole(id=teams[2].id, name=teams[2].name, role=Role.TEAM_MEMBER, status=TeamRoleStatus.ACCEPTED)]))


async def test_get_users(client: AsyncClient, users: List[UserListItem]):
    resp = await client.get(USERS_PATH)
    assert_response(resp, [users[0], users[1], users[3]])


async def test_get_users_unauthorized(client: AsyncClient, override_user: Callable[[int], None]):
    override_user(5)
    resp = await client.get(USERS_PATH)
    assert resp.status_code == 401
