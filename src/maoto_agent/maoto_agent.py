import os
import sys
import json
import uuid
import asyncio
import aiohttp
import aiofiles
import requests
import threading
from pathlib import Path
from .app_types import *
from openai import OpenAI
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from gql import gql, Client
from abc import ABC, abstractmethod
from concurrent.futures import Future
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport

DATA_CHUNK_SIZE = 1024 * 1024  # 1 MB in bytes

if sys.version_info < (3, 10):
    raise RuntimeError("This package requires Python 3.10 or higher. Please update your Python version.")

class AsyncQueueWrapper:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.queue = asyncio.Queue()
        self.loop_thread = threading.Thread(target=self._start_loop, daemon=True)
        self.loop_thread.start()
        self.producer_task = None
        self._cleanup_done = False

    def _start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def put(self, item):
        await self.queue.put(item)

    def get(self):
        future = Future()
        asyncio.run_coroutine_threadsafe(self._get_coroutine(future), self.loop)  

        return future.result()

    async def _get_coroutine(self, future):
        item = await self.queue.get()
        future.set_result(item)
        self.queue.task_done()

    def start_producer(self, producer_function):
        self.producer_task = asyncio.run_coroutine_threadsafe(producer_function(), self.loop)

    async def cleanup(self):
        if not self._cleanup_done:
            self._cleanup_done = True
            if self.producer_task is not None:
                self.producer_task.cancel()
                try:
                    await self.producer_task
                except asyncio.CancelledError:
                    pass

            # Stop the event loop
            self.loop.call_soon_threadsafe(self.loop.stop)
            self.loop_thread.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        asyncio.run(self.cleanup())

    def __del__(self):
        if not self._cleanup_done:
            try:
                asyncio.run(self.cleanup())
            except RuntimeError as e:
                if str(e) == "Event loop is closed":
                    pass

class AuthenticateProvider(ABC):
    @abstractmethod
    def authenticate(username: str, password: str, apikey_id: str) -> bool:
        """
        Abstract method to authenticate a user by username and password or by apikey_id.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def new_user(apikey_id: str) -> bool:
        """
        Abstract method to create a new user.
        Must be implemented by subclasses.
        """
        pass

class Maoto:
    def __init__(self, apikey_value=None, working_dir: Path = None, download_dir: Path = None):
        self.working_dir = working_dir
        self.server_domain = os.environ.get("RESOLVER_API_DOMAIN", "api.maoto.world")
        self.protocol = "http"
        self.server_url = self.protocol + "://" + self.server_domain + ":4000"
        self.graphql_url = self.server_url + "/graphql"
        self.subscription_url = self.graphql_url.replace(self.protocol, "ws")

        self.working_dir = working_dir or os.environ.get("MAOTO_WORKING_DIR")
        if self.working_dir == None or self.working_dir == "":
            raise ValueError("Working directory is required.")
        self.download_dir = download_dir or os.environ.get("MAOTO_DOWNLOAD_DIR") or self.working_dir / 'downloaded_files'

        self.apikey_value = apikey_value or os.environ.get("MAOTO_API_KEY")
        if self.apikey_value == None or self.apikey_value == "":
            raise ValueError("API key is required.")

        transport = AIOHTTPTransport(
            url=self.graphql_url,
            headers={"Authorization": self.apikey_value},
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=True)
        
        self._check_version_compatibility()
        self.apikey = self.get_own_api_keys()[0]

        self.queue_wrapper = AsyncQueueWrapper()
        if "provider" in self.apikey.get_roles():
            self.queue_wrapper.start_producer(self.subscribe_to_responses)
        elif "resolver" in self.apikey.get_roles():
            self.queue_wrapper.start_producer(self.subscribe_to_actioncalls) 

        self.id_action_map = {}
        self.action_registry = {}

    def _check_version_compatibility(self):
        query = gql('''
        query CheckVersionCompatibility($version: String!) {
            checkVersionCompatibility(version: $version)
        }
        ''')

        variables = {
            'version': '1.1.1'
        }

        result = self.client.execute(query, variables)
        compatibility = result["checkVersionCompatibility"]
        if not compatibility:
            raise ValueError("Incompatible version. Please update the agent to the latest version.")

    def init_authentication(self, authenticate_provider: AuthenticateProvider):
        # check if authenticate_provider is an instance of AuthenticateProvider
        if not isinstance(authenticate_provider, AuthenticateProvider):
            raise ValueError("authenticate_provider must be an instance of AuthenticateProvider.")
        self.authenticate_provider = authenticate_provider

    def register_action(self, name: str):
        def decorator(func):
            self.action_registry[name] = func
            return func
        return decorator

    def resolver_loop(self):
        while True:
            print("Waiting for next action call...")
            actioncall_return = self.listen()
            print(f"Received action call: {actioncall_return}\n")
            new_response = self.resolve_actioncall(actioncall_return)
            print(f"Sending response: {new_response}\n")
            created_response = self.create_responses([new_response])[0]

    def get_own_user(self) -> User:
        query = gql('''
        query {
            getOwnUser {
                user_id
                username
                time
                roles
            }
        }
        ''')

        result = self.client.execute(query)
        data = result["getOwnUser"]
        return User(data["username"], uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["roles"])

    def get_own_api_keys(self) -> list[bool]:
        query = gql('''
        query {
            getOwnApiKeys {
                apikey_id
                user_id
                name
                time
                roles
            }
        }
        ''')

        result = self.client.execute(query)
        data_list = result["getOwnApiKeys"]
        return [ApiKey(uuid.UUID(data["apikey_id"]), uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["name"], data["roles"]) for data in data_list]

    def create_users(self, new_users: list[NewUser]):
        users = [{'username': user.username, 'password': user.password, 'roles': user.roles} for user in new_users]
        query = gql('''
        mutation createUsers($new_users: [NewUser!]!) {
            createUsers(new_users: $new_users) {
                username
                user_id
                time
                roles
            }
        }
        ''')

        result = self.client.execute(query, variable_values={"new_users": users})
        data_list = result["createUsers"]
        return [User(data["username"], uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["roles"]) for data in data_list]

    def delete_users(self, user_ids: list[User | str]) -> bool:
        user_ids = [str(user.get_user_id()) if isinstance(user, User) else str(user) for user in user_ids]
        query = gql('''
        mutation deleteUsers($user_ids: [ID!]!) {
            deleteUsers(user_ids: $user_ids)
        }
        ''')

        result = self.client.execute(query, variable_values={"user_ids": user_ids})
        return result["deleteUsers"]
    
    def get_users(self) -> list[User]:
        query = gql('''
        query {
            getUsers {
                user_id
                username
                time
                roles
            }
        }
        ''')

        result = self.client.execute(query)
        data_list = result["getUsers"]
        return [User(data["username"], uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["roles"]) for data in data_list]
    
    def create_apikeys(self, api_keys: list[NewApiKey]) -> list[ApiKey]:
        api_keys_data = [{'name': key.get_name(), 'user_id': str(key.get_user_id()), 'roles': key.get_roles()} for key in api_keys]
        query = gql('''
        mutation createApiKeys($new_apikeys: [NewApiKey!]!) {
            createApiKeys(new_apikeys: $new_apikeys) {
                apikey_id
                user_id
                name
                time
                roles
                value
            }
        }
        ''')

        result = self.client.execute(query, variable_values={"new_apikeys": api_keys_data})
        data_list = result["createApiKeys"]
        return [ApiKeyWithSecret(uuid.UUID(data["apikey_id"]), uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["name"], data["roles"], data["value"]) for data in data_list]
        
    def delete_apikeys(self, apikey_ids: list[ApiKey | str]) -> list[bool]:
        api_key_ids = [str(apikey.get_apikey_id()) if isinstance(apikey, ApiKey) else str(apikey) for apikey in apikey_ids]
        query = gql('''
        mutation deleteApiKeys($apikey_ids: [ID!]!) {
            deleteApiKeys(apikey_ids: $apikey_ids)
        }
        ''')

        result = self.client.execute(query, variable_values={"apikey_ids": api_key_ids})
        return result["deleteApiKeys"]

    def get_apikeys(self, user_ids: list[User | str]) -> list[ApiKey]:
        user_ids = [str(user.get_user_id()) if isinstance(user, User) else str(user) for user in user_ids]
        query = gql('''
        query getApiKeys($user_ids: [ID!]!) {
            getApiKeys(user_ids: $user_ids) {
                apikey_id
                user_id
                name
                time
                roles
            }
        }
        ''')

        result = self.client.execute(query, variable_values={"user_ids": user_ids})
        data_list = result["getApiKeys"]
        return [ApiKey(uuid.UUID(data["apikey_id"]), uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["name"], data["roles"]) for data in data_list]

    def create_actions(self, new_actions: list[NewAction]) -> list[Action]:
        actions = [{'name': action.name, 'parameters': action.parameters, 'description': action.description, 'tags': action.tags, 'cost': action.cost, 'followup': action.followup} for action in new_actions]
        query = gql('''
        mutation createActions($new_actions: [NewAction!]!) {
            createActions(new_actions: $new_actions) {
                action_id
                apikey_id
                name
                parameters
                description
                tags
                cost
                followup
                time
            }
        }
        ''')

        result = self.client.execute(query, variable_values={"new_actions": actions})
        data_list = result["createActions"]
        self.id_action_map.update({data["action_id"]: data["name"] for data in data_list})

        return [Action(
            action_id=uuid.UUID(data["action_id"]),
            apikey_id=uuid.UUID(data["apikey_id"]),
            name=data["name"],
            parameters=data["parameters"],
            description=data["description"],
            tags=data["tags"],
            cost=data["cost"],
            followup=data["followup"],
            time=datetime.fromisoformat(data["time"])
        ) for data in data_list]

    def delete_actions(self, action_ids: list[Action | str]) -> list[bool]:
        action_ids = [str(action.get_action_id()) if isinstance(action, Action) else str(action) for action in action_ids]
        query = gql('''
        mutation deleteActions($action_ids: [ID!]!) {
            deleteActions(action_ids: $action_ids)
        }
        ''')

        result = self.client.execute(query, variable_values={"action_ids": action_ids})
        return result["deleteActions"]
    
    def get_actions(self, apikey_ids: list[ApiKey | str]) -> list[Action]:
        apikey_ids = [str(apikey.get_apikey_id()) if isinstance(apikey, ApiKey) else str(apikey) for apikey in apikey_ids]
        query = gql('''
        query getActions($apikey_ids: [ID!]!) {
            getActions(apikey_ids: $apikey_ids) {
                action_id
                apikey_id
                name
                parameters
                description
                tags
                cost
                followup
                time
            }
        }
        ''')

        result = self.client.execute(query, variable_values={"apikey_ids": apikey_ids})
        data_list = result["getActions"]
        return [Action(
            action_id=uuid.UUID(data["action_id"]),
            apikey_id=uuid.UUID(data["apikey_id"]),
            name=data["name"],
            parameters=data["parameters"],
            description=data["description"],
            tags=data["tags"],
            cost=data["cost"],
            followup=data["followup"],
            time=datetime.fromisoformat(data["time"])
        ) for data in data_list]
    
    def get_own_actions(self) -> list[Action]:
        query = gql('''
        query {
            getOwnActions {
                action_id
                apikey_id
                name
                parameters
                description
                tags
                cost
                followup
                time
            }
        }
        ''')

        result = self.client.execute(query)
        data_list = result["getOwnActions"]
        return [Action(
            action_id=uuid.UUID(data["action_id"]),
            apikey_id=uuid.UUID(data["apikey_id"]),
            name=data["name"],
            parameters=data["parameters"],
            description=data["description"],
            tags=data["tags"],
            cost=data["cost"],
            followup=data["followup"],
            time=datetime.fromisoformat(data["time"])
        ) for data in data_list]
    
    def create_posts(self, new_posts: list[NewPost]) -> list[Post]:
        posts = [{'description': post.description, 'context': post.context} for post in new_posts]
        query = gql('''
        mutation createPosts($new_posts: [NewPost!]!) {
            createPosts(new_posts: $new_posts) {
                post_id
                description
                context
                apikey_id
                time
                resolved
            }
        }
        ''')

        result = self.client.execute(query, variable_values={"new_posts": posts})
        data_list = result["createPosts"]
        return [Post(
            post_id=uuid.UUID(data["post_id"]),
            description=data["description"],
            context=data["context"],
            apikey_id=uuid.UUID(data["apikey_id"]),
            time=datetime.fromisoformat(data["time"]),
            resolved=data["resolved"]
        ) for data in data_list]

    def delete_posts(self, post_ids: list[Post | str]) -> list[bool]:
        post_ids = [str(post.get_post_id()) if isinstance(post, Post) else str(post) for post in post_ids]
        query = gql('''
        mutation deletePosts($post_ids: [ID!]!) {
            deletePosts(post_ids: $post_ids)
        }
        ''')

        result = self.client.execute(query, variable_values={"post_ids": post_ids})
        return result["deletePosts"]

    def get_posts(self, apikey_ids: list[ApiKey | str]) -> list[Post]:
        apikey_ids = [str(apikey.get_apikey_id()) if isinstance(apikey, ApiKey) else str(apikey) for apikey in apikey_ids]
        query = gql('''
        query getPosts($apikey_ids: [ID!]!) {
            getPosts(apikey_ids: $apikey_ids) {
                post_id
                description
                context
                apikey_id
                time
                resolved
            }
        }
        ''')

        result = self.client.execute(query, variable_values={"apikey_ids": apikey_ids})
        data_list = result["getPosts"]
        return [Post(
            post_id=uuid.UUID(data["post_id"]),
            description=data["description"],
            context=data["context"],
            apikey_id=uuid.UUID(data["apikey_id"]),
            time=datetime.fromisoformat(data["time"]),
            resolved=data["resolved"]
        ) for data in data_list]

    def get_own_posts(self) -> list[Post]:
        query = gql('''
        query {
            getOwnPosts {
                post_id
                description
                context
                apikey_id
                time
                resolved
            }
        }
        ''')

        result = self.client.execute(query)
        data_list = result["getOwnPosts"]
        return [Post(
            post_id=uuid.UUID(data["post_id"]),
            description=data["description"],
            context=data["context"],
            apikey_id=uuid.UUID(data["apikey_id"]),
            time=datetime.fromisoformat(data["time"]),
            resolved=data["resolved"]
        ) for data in data_list]
    
    def create_actioncalls(self, new_actioncalls: list[NewActioncall]) -> list[Actioncall]:
        actioncalls = [{'action_id': str(actioncall.action_id), 'post_id': str(actioncall.post_id), 'parameters': actioncall.parameters, 'cost': actioncall.cost} for actioncall in new_actioncalls]
        query = gql('''
        mutation createActioncalls($new_actioncalls: [NewActioncall!]!) {
            createActioncalls(new_actioncalls: $new_actioncalls) {
                actioncall_id
                action_id
                post_id
                apikey_id
                parameters
                cost
                time
            }
        }
        ''')

        result = self.client.execute(query, variable_values={"new_actioncalls": actioncalls})
        data_list = result["createActioncalls"]
        return [Actioncall(
            actioncall_id=uuid.UUID(data["actioncall_id"]),
            action_id=uuid.UUID(data["action_id"]),
            post_id=uuid.UUID(data["post_id"]),
            apikey_id=uuid.UUID(data["apikey_id"]),
            parameters=data["parameters"],
            cost=data["cost"],
            time=datetime.fromisoformat(data["time"])
        ) for data in data_list]
    
    def create_responses(self, new_responses: list[NewResponse]) -> list[Response]:
        responses = [{'post_id': str(response.post_id), 'description': response.description} for response in new_responses]
        query = gql('''
        mutation createResponses($new_responses: [NewResponse!]!) {
            createResponses(new_responses: $new_responses) {
                response_id
                post_id
                description
                apikey_id
                time
            }
        }
        ''')

        result = self.client.execute(query, variable_values={"new_responses": responses})
        data_list = result["createResponses"]
        return [Response(
            response_id=uuid.UUID(data["response_id"]),
            post_id=uuid.UUID(data["post_id"]),
            description=data["description"],
            apikey_id=uuid.UUID(data["apikey_id"]),
            time=datetime.fromisoformat(data["time"])
        ) for data in data_list]

    async def subscribe_to_responses(self):
        subscription = gql('''
        subscription subscribeToResponses {
            subscribeToResponses {
                response_id
                post_id
                description
                apikey_id
                time
            }
        }
        ''')

        transport = WebsocketsTransport(
            url=self.subscription_url,
            headers={"Authorization": self.apikey_value},
        )
        async with Client(
            transport=transport,
            fetch_schema_from_transport=True,
        ) as session:
            async for result in session.subscribe(subscription):
                # Log each received result for debugging
                response_data = result['subscribeToResponses']
                response = Response(
                    response_id=uuid.UUID(response_data["response_id"]),
                    post_id=uuid.UUID(response_data["post_id"]),
                    description=response_data["description"],
                    apikey_id=response_data["apikey_id"],
                    time=datetime.fromisoformat(response_data["time"])
                )
                await self.queue_wrapper.put(response)

    async def subscribe_to_actioncalls(self):
        subscription = gql('''
        subscription subscribeToActioncalls {
            subscribeToActioncalls {
                actioncall_id
                action_id
                post_id
                apikey_id
                parameters
                cost
                time
            }
        }
        ''')

        transport = WebsocketsTransport(
            url=self.subscription_url,
            headers={"Authorization": self.apikey_value},
        )
        async with Client(
            transport=transport,
            fetch_schema_from_transport=True,
        ) as session:
            async for result in session.subscribe(subscription):
                # Log each received result for debugging
                response_data = result['subscribeToActioncalls']
                response = Actioncall(
                    actioncall_id=uuid.UUID(response_data["actioncall_id"]),
                    action_id=uuid.UUID(response_data["action_id"]),
                    post_id=uuid.UUID(response_data["post_id"]),
                    apikey_id=uuid.UUID(response_data["apikey_id"]),
                    parameters=response_data["parameters"],
                    cost=response_data["cost"],
                    time=datetime.fromisoformat(response_data["time"])
                )
                await self.queue_wrapper.put(response)
    
    def listen(self, block=True) -> Response | Actioncall | None:
            if block:
                return self.queue_wrapper.get()
            else:
                # TODO
                raise NotImplementedError("Implementation missing error")


    async def _download_file_async(self, file_id: str, destination_dir: Path) -> File:
        query = gql('''
        query downloadFile($file_id: ID!) {
            downloadFile(file_id: $file_id) {
                file_id
                apikey_id
                extension
                time
            }
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"file_id": file_id})
        file_metadata = result["downloadFile"]
        
        download_url = f"{self.server_url}/download/{str(file_id)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, headers={"Authorization": self.apikey_value}) as response:
                if response.status == 200:
                    filename = f"{str(file_id)}{file_metadata['extension']}"
                    destination_path = destination_dir / filename
                    
                    async with aiofiles.open(destination_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(DATA_CHUNK_SIZE)
                            if not chunk:
                                break
                            await f.write(chunk)

                    return File(
                        file_id=uuid.UUID(file_metadata["file_id"]),
                        apikey_id=uuid.UUID(file_metadata["apikey_id"]),
                        extension=file_metadata["extension"],
                        time=datetime.fromisoformat(file_metadata["time"])
                    )
                else:
                    raise Exception(f"Failed to download file: {response.status}")
    
    def download_files(self, file_ids: list[str]) -> list[File]:
        downloaded_files = []
        for file_id in file_ids:
            future = asyncio.run_coroutine_threadsafe(self._download_file_async(file_id, self.download_dir), self.queue_wrapper.loop)
            downloaded_file = future.result()
            downloaded_files.append(downloaded_file)
        return downloaded_files

    async def _upload_file_async(self, file_path: Path) -> File:
        new_file = NewFile(
            extension=file_path.suffix,
        )
        query_str = '''
        mutation uploadFile($new_file: NewFile!, $file: Upload!) {
            uploadFile(new_file: $new_file, file: $file) {
                file_id
                apikey_id
                extension
                time
            }
        }'''
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(file_path, 'rb') as f:
                form = aiohttp.FormData()
                form.add_field('operations', json.dumps({
                    'query': query_str,
                    'variables': {"new_file": {"extension": new_file.get_extension()}, "file": None}
                }))
                form.add_field('map', json.dumps({
                    '0': ['variables.file']
                }))
                form.add_field('0', await f.read(), filename=str(file_path))

                headers = {
                    "Authorization": self.apikey_value
                }
                async with session.post(self.graphql_url, data=form, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to upload file: {response.status}")
                    result = await response.json()

        file_metadata = result["data"]["uploadFile"]
        return File(
            file_id=uuid.UUID(file_metadata["file_id"]),
            apikey_id=uuid.UUID(file_metadata["apikey_id"]),
            extension=file_metadata["extension"],
            time=datetime.fromisoformat(file_metadata["time"])
        )
    
    def upload_files(self, file_paths: list[Path]) -> list[File]:
        file_paths = [self.working_dir / file_path for file_path in file_paths]
        uploaded_files = []
        for file_path in file_paths:
            future = asyncio.run_coroutine_threadsafe(self._upload_file_async(file_path), self.queue_wrapper.loop)
            uploaded_file = future.result()
            uploaded_files.append(uploaded_file)
        return uploaded_files
    
    def _check_if_downloaded(self, file_ids: list[str]) -> list[str]:
        missing_files = []
        for file_id in file_ids:
            download_dir = self.working_dir / self.download_dir
            os.makedirs(download_dir, exist_ok=True)
            file_path = download_dir / str(file_id)
            if not file_path.exists():
                missing_files.append(file_id)
        return missing_files
    
    def download_missing_files(self, file_ids: list[str]) -> list[File]:
        files_missing = self._check_if_downloaded(file_ids)
        downloaded_files = self.download_files(files_missing)
        return downloaded_files
    
    def _id_to_action(self, action_id: uuid) -> callable:
        return self.action_registry[self.id_action_map[str(action_id)]]
        
    def resolve_actioncall(self, actioncall: Actioncall) -> Response:
        action = self._id_to_action(actioncall.get_action_id())
        response_description = action(actioncall.get_apikey_id(), actioncall.get_parameters())
        new_response = NewResponse(
            post_id=actioncall.get_post_id(),
            description=response_description
        )
        response = self.create_responses([new_response])[0]
        return response
