from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging
from typing import Any, Optional, cast, Mapping

from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient, SSEConnection
from langchain_mcp_adapters.tools import load_mcp_tools
from pydantic import AnyHttpUrl
from sqlmodel.ext.asyncio.session import AsyncSession

from ...agents.domain import Agent, AgentToolConfig
from ..core import AgentTool, StatusUpdateCallbackHandler, load_schema
from ..oauth import AgentToolOauth, ToolAuthCallback, ToolOAuthClientInfoRepository, ToolOAuthState, ToolOAuthRepository


MCP_TOOL_ID = "mcp"
logger = logging.getLogger(__name__)


class McpTool(AgentTool):
    id: str = MCP_TOOL_ID + "-*"
    name: str = "MCP"
    description: str = "Allows to use a set of tools provided by a MCP server"
    config_schema: dict = load_schema(__file__)
    _oauth: Optional[AgentToolOauth] = None
    _tools: Optional[list[BaseTool]] = None
    
    def configure(self, agent: Agent, user_id: int, config: dict, db: AsyncSession, thread_id: Optional[int] = None):
        super().configure(agent, user_id, config, db, thread_id)
        self.id = MCP_TOOL_ID + "-" + cast(str, AnyHttpUrl(config.get("serverUrl") or "").host)
        self._oauth = AgentToolOauth(config.get("serverUrl") or "", None, None, agent.id, self.id, user_id, db)

    async def _setup_tool(self, prev_config: Optional[AgentToolConfig]) -> Optional[dict]:
        try:
            if prev_config and self.config != prev_config.config:
                await self.teardown()
            async with self.load():
                # we invoke this method to validate the complete url
                await self.build_langchain_tools()
        except Exception:
            logger.exception("Failed to setup MCP tool")
            raise ValueError("Invalid MCP tool configuration")

    async def teardown(self):
        await ToolOAuthRepository(self.db).delete_token(self.user_id, self.agent.id, self.id)
        await ToolOAuthClientInfoRepository(self.db).delete(self.agent.id, self.id)

    @asynccontextmanager
    async def load(self) -> AsyncIterator['McpTool']:
        oauth = self._get_oauth()
        tokens = await oauth.solve_tokens()
        app_name = cast(str, AnyHttpUrl(oauth.server_url).host)
        transport = "sse" if oauth.server_url.endswith("/sse") else "streamable_http"
        base_config = {
            "transport": transport,
            "url": oauth.server_url,
            "headers": {"Authorization": f"Bearer {tokens.access_token}"} if tokens else {}
        }
        connections: Mapping[str, Any] = {app_name: cast(SSEConnection, base_config) if transport == "sse" else base_config}
        async with MultiServerMCPClient(connections).session(app_name) as mcp_session:
            tools = await load_mcp_tools(mcp_session)
            # this is required since https://mcp.atlassian.com/v1/sse returns arrays with no items description and openAI doesn't like tool with such schema,
            # same happens with https://browser.mcp.cloudflare.com/sse returning a type object with no properties
            self._tools = self._fix_tools_schemas(tools)
            for tool in self._tools:
                tool.callbacks = [StatusUpdateCallbackHandler(tool.name, description=tool.description)]
            yield self
    
    def _get_oauth(self) -> AgentToolOauth:
        if not self._oauth:
            raise RuntimeError("MCP tool has not been set up properly")
        return self._oauth

    async def build_langchain_tools(self) -> list[BaseTool]:
        if not self._tools:
            raise RuntimeError("MCP tool has not been set up properly")
        return self._tools
    
    def _fix_tools_schemas(self, tools: list[BaseTool]) -> list[BaseTool]:
        ret = []
        for tool in tools:
            tool.args_schema = self._fix_schema(tool.args_schema)
            ret.append(tool)
        return ret
    
    def _fix_schema(self, schema: Any) -> Any:
        if isinstance(schema, dict):
            items = schema.get("items", {})
            if schema.get("type") == "array" and not items.get("type"):
                if not items:
                    schema["items"] = {"type": "string"}
                else:
                    schema["items"]["type"] = "string"
                return schema
            elif schema.get("type") == "object" and not schema.get("properties"):
                schema["properties"] = {}
                return schema
            else:
                return { key: self._fix_schema(value) for key, value in schema.items() }
        elif isinstance(schema, list):
            return [self._fix_schema(item) for item in schema]
        else:
            return schema
        
    async def auth(self, auth_callback: ToolAuthCallback, state: ToolOAuthState):
        await self._get_oauth().callback(auth_callback, state)

    async def clone(self, agent_id: int, cloned_agent_id: int, tool_id: str, user_id: int, db: AsyncSession) -> None:
        pass