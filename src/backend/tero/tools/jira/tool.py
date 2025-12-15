import aiofiles
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
from http import HTTPMethod
import logging
from typing import Any, Optional, cast
from urllib.parse import quote

import httpx
from langchain_core.tools import BaseTool, StructuredTool
from pydantic import AnyHttpUrl
from sqlmodel import Field, SQLModel, and_, select, delete
from sqlmodel.ext.asyncio.session import AsyncSession

from ...agents.domain import AgentToolConfig
from ...core.assets import solve_asset_path
from ...core.repos import scalar
from ..core import AgentTool, StatusUpdateCallbackHandler, load_schema
from ..oauth import AgentToolOauth, ToolAuthCallback, ToolOAuthClientInfo, ToolOAuthClientInfoRepository, ToolOAuthState, ToolOAuthRepository, OAuthMetadata


logger = logging.getLogger(__name__)
JIRA_TOOL_ID = "jira"
SWAGGER_URL = "https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json"
JIRA_BASE_API_URL = "https://api.atlassian.com"


class JiraToolConfig(SQLModel, table=True):
    __tablename__ : Any = "jira_tool_config"
    agent_id: int = Field(primary_key=True)
    cloud_id: str


class JiraToolConfigRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def find_by_agent_id(self, agent_id: int) -> Optional[JiraToolConfig]:
        stmt = select(JiraToolConfig).where(JiraToolConfig.agent_id == agent_id)
        result = await self._db.exec(stmt)
        return result.first()
    
    async def save(self, config: JiraToolConfig):
        self._db.add(config)
        await self._db.commit()

    async def delete(self, agent_id: int):
        stmt = scalar(delete(JiraToolConfig).where(and_(JiraToolConfig.agent_id == agent_id)))
        await self._db.exec(stmt)
        await self._db.commit()


class JiraTool(AgentTool):
    id: str = JIRA_TOOL_ID
    name: str = "Jira"
    description: str = "Allows to use interact with Jira"
    config_schema: dict = load_schema(__file__)
    _BODY_LOCATION = "body"
    _CLIENT_SECRET_MASK = "********"
    
    async def _setup_tool(self, prev_config: Optional[AgentToolConfig]) -> Optional[dict]:
        await self._save_client_info(self.config)
        if prev_config and self.config != prev_config.config:
            await ToolOAuthRepository(self.db).delete_token(self.user_id, self.agent.id, self.id)
            await JiraToolConfigRepository(self.db).delete(self.agent.id)
        async with self.load():
            pass
        # masking clientSecret to avoid storing it in plain text in tool configuration table. It is already store encrypted in client info table.
        return {prop: val if prop != "clientSecret" else self._CLIENT_SECRET_MASK for prop, val in self.config.items()}
    
    async def _save_client_info(self, config: dict):
        repo = ToolOAuthClientInfoRepository(self.db)
        client_info = await repo.find_by_ids(self.agent.id, self.id)
        client_id = config["clientId"]
        client_secret = config["clientSecret"]
        scope = " ".join(config["scope"])
        if not client_info:
            client_info = ToolOAuthClientInfo(
                agent_id=self.agent.id,
                tool_id=self.id,
                client_id=client_id,
                client_secret=client_secret,
                scope=scope)
        else:
            client_info.client_id = client_id
            client_info.client_secret = client_secret if client_secret != self._CLIENT_SECRET_MASK else client_info.client_secret
            client_info.scope = scope
        await repo.save(client_info)
        
    @asynccontextmanager
    async def load(self) -> AsyncIterator['JiraTool']:
       self._oauth = await self._load_oauth()
       await self._oauth.solve_tokens()
       cloud_id = await self._find_cloud_id()
       self._api_url = f"{JIRA_BASE_API_URL}/ex/jira/{cloud_id}"
       yield self

    async def _load_oauth(self) -> AgentToolOauth:
        base_url = "https://auth.atlassian.com"
        oauth_metadata = OAuthMetadata(
            issuer=AnyHttpUrl(base_url),
            authorization_endpoint=AnyHttpUrl(f"{base_url}/authorize"),
            token_endpoint=AnyHttpUrl(f"{base_url}/oauth/token")
        )
        client_info = await ToolOAuthClientInfoRepository(self.db).find_by_ids(self.agent.id, self.id)
        # add offline_access scope to be able to refresh tokens
        return AgentToolOauth(base_url, oauth_metadata, cast(str, cast(ToolOAuthClientInfo, client_info).scope) + " offline_access", self.agent.id, self.id, self.user_id, self.db)

    async def _find_cloud_id(self):
        repo = JiraToolConfigRepository(self.db)
        jira_config = await repo.find_by_agent_id(self.agent.id)
        if jira_config:
            return jira_config.cloud_id
        resp = await self._invoke_rest_api(HTTPMethod.GET, f"{JIRA_BASE_API_URL}/oauth/token/accessible-resources")
        ret = next(resource["id"] for resource in resp)
        await repo.save(JiraToolConfig(agent_id=self.agent.id, cloud_id=ret))
        return ret

    async def _invoke_rest_api(self, method: str, url: str, params: Optional[dict] = None, headers: Optional[dict] = None, body: Optional[dict] = None) -> Any:
        headers = headers or {}
        tokens = await cast(AgentToolOauth, self._oauth).solve_tokens()
        if tokens:
            headers["Authorization"] = f"Bearer {tokens.access_token}"
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, params=params, headers=headers, json=body)
            response.raise_for_status()
            if response.status_code == 204:
                return None
            return response.json()

    async def auth(self, auth_callback: ToolAuthCallback, state: ToolOAuthState):
        oauth = await self._load_oauth()
        await oauth.callback(auth_callback, state)

    async def teardown(self):
        await ToolOAuthRepository(self.db).delete_token(self.user_id, self.agent.id, self.id)
        await ToolOAuthClientInfoRepository(self.db).delete(self.agent.id, self.id)
        await JiraToolConfigRepository(self.db).delete(self.agent.id)

    async def build_langchain_tools(self) -> list[BaseTool]:
        api_spec = await self._load_json("jira-api-spec.json")
        schemas = api_spec["components"]["schemas"]
        doc_node_schema = await self._load_json("simplified-doc-node-schema.json")
        # using simplified schema instead of the original one from https://unpkg.com/@atlaskit/adf-schema@49.0.1/dist/json-schema/v1/full.json 
        # since original schema is huge, consuming time, tokens and making llm confused with so much information
        # additionally, just having version after content in doc_node makes the llm to generate a call without the version attribute, which makes the request to fail
        schemas.update(doc_node_schema["definitions"])
        return [self._build_langchain_tool(path, method, method_spec, schemas) 
                for path, path_spec in api_spec["paths"].items() if self._is_filtered_path(path)
                for method, method_spec in path_spec.items()]

    async def _load_json(self, filename: str) -> dict:
        # we use a local file to avoid the need to request the api spec from the server every time the tool is used (improve performance, avoid connectivity issues, avoid potential unsupported changes in file content)
        async with aiofiles.open(solve_asset_path(filename, __file__)) as file:
            return json.loads(await file.read())

    # there is a limitation of up to 128 functions that can be passed to OpenAI, and JIRA API has more than 590 methods. This method filters the most common and used ones.
    def _is_filtered_path(self, path: str) -> bool:
        base_path = "/rest/api/3"
        issues_path = f"{base_path}/issue"
        issue_path = f"{issues_path}/{{issueIdOrKey}}"
        comments_path = f"{issue_path}/comment"
        properties_path = f"{issue_path}/properties"
        search_path = f"{base_path}/search"
        projects_path = f"{base_path}/project"
        project_path = f"{projects_path}/{{projectIdOrKey}}"
        return path in [
            issues_path, issue_path, f"{issue_path}/assignee", f"{issue_path}/attachments", f"{issue_path}/changelog", 
            comments_path, f"{comments_path}/{{id}}", properties_path, f"{properties_path}/{{propertyKey}}", f"{issue_path}/transitions", 
            f"{search_path}/approximate-count", f"{search_path}/jql", f"{projects_path}/search", f"{project_path}", f"{project_path}/statuses", 
            f"{base_path}/myself", f"{base_path}/users/search"]
    
    def _build_langchain_tool(self, path: str, method: str, method_spec: dict, schemas: dict) -> BaseTool:
        async def call_tool(**arguments: dict[str, Any]) -> str:
            param_type = self._find_unique_parameter_type(method_spec)
            params = {param_type: arguments} if param_type else arguments
            path_params = {key: quote(str(value)) for key, value in params.get("path", {}).items()}
            final_path = path.format(**path_params) if path_params else path
            return await self._invoke_rest_api(method, f"{self._api_url}{final_path}", params.get("query"), params.get("header"), params.get("body"))
        
        name = "Jira-" + method_spec["operationId"]
        description = "Jira tool that " + method_spec["description"]
        return StructuredTool(
            name=name,
            description=description,
            args_schema=self._build_args_schema(method_spec, schemas),
            coroutine=call_tool,
            callbacks=[StatusUpdateCallbackHandler(name, description=description)]
        )
    
    def _find_unique_parameter_type(self, method_spec: dict) -> Optional[str]:
        ret = None
        for param in method_spec.get("parameters", []):
            location = param["in"]
            if ret and ret != location:
                return None
            ret = location
        body_schema = self._find_body_schema(method_spec)
        if ret and body_schema:
            return None
        return ret if not body_schema else self._BODY_LOCATION

    def _find_body_schema(self, method_spec: dict) -> Optional[dict]:
        # currently we are only supporting json body requests
        return method_spec.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
    
    def _build_args_schema(self, method_spec: dict, schemas: dict) -> dict[str, Any]:
        ret = self._build_params_schema(method_spec)
        body_schema = self._find_body_schema(method_spec)
        props = ret["properties"]
        if body_schema:
            props[self._BODY_LOCATION] = body_schema
        input_schemas = [schema for schema in props.values() if schema]
        ret = input_schemas[0] if len(input_schemas) == 1 else ret
        self._refactor_schema_refs(ret, schemas)
        return ret
    
    def _build_params_schema(self, method_spec: dict) -> dict:
        ret = self._build_empty_schema()
        props = ret["properties"]
        for param in method_spec.get("parameters", []):
            location = param["in"]
            props[location] = props.get(location, self._build_empty_schema())
            location_params = props[location]
            name = param["name"]
            param_schema = param["schema"]
            description = param.get("description")
            if description:
                param_schema["description"] = description
            location_params["properties"][name] = param_schema
            if param.get("required"):
                location_params["required"].append(name)
        return ret
    
    def _build_empty_schema(self) -> dict:
        return {"type": "object", "properties": {}, "required": []}
    
    def _refactor_schema_refs(self, schema: dict, schemas: dict):
        refs = set()
        self._collect_and_refactor_schema_refs(schema, schemas, refs)
        if refs:
            schema["$defs"] = {ref: schemas[ref] for ref in refs}

    def _collect_and_refactor_schema_refs(self, schema: dict, schemas: dict, refs: set):
        ref = schema.get("$ref")
        if ref:
            self._refactor_ref(schema, ref.split("/")[-1], schemas, refs)
        self._refactor_subschemas_refs("allOf", schema, schemas, refs)
        self._refactor_subschemas_refs("anyOf", schema, schemas, refs)
        self._refactor_subschemas_refs("oneOf", schema, schemas, refs)
        schema_type = schema.get("type")
        if not schema_type:
            # fixing jira schema which does not properly define the schema for comments
            if "Atlassian Document Format" in schema.get("description", ""):
                self._refactor_ref(schema, "doc_node", schemas, refs)
        elif schema_type == "array":
            items = schema.get("items")
            if items:
                self._collect_and_refactor_schema_refs(items, schemas, refs)
        elif schema_type == "object":
            for value in schema.get("properties", {}).values():
                self._collect_and_refactor_schema_refs(value, schemas, refs)
            # removing additional properties to simplify schema since so far we haven't identified any use case for them when used by the llm
            if schema.get("additionalProperties"):
                del schema["additionalProperties"]

    def _refactor_ref(self, schema: dict, simple_ref: str, schemas: dict, refs: set):
        schema["$ref"] = f"#/$defs/{simple_ref}"
        # passing refs as parameter and modify it instead of returning it to be able to make this check to avoid infinite recursion in cyclic references
        if simple_ref not in refs:
            refs.add(simple_ref)
            self._collect_and_refactor_schema_refs(schemas[simple_ref], schemas, refs)

    def _refactor_subschemas_refs(self, subschema_key: str, schema: dict, schemas: dict, refs: set):
        for subSchema in schema.get(subschema_key, []):
            self._collect_and_refactor_schema_refs(subSchema, schemas, refs)
    
    async def clone(self, agent_id: int, cloned_agent_id: int, tool_id: str, user_id: int, db: AsyncSession) -> None:
        pass
