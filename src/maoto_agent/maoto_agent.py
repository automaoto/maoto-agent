import os
import sys
import json
import time
import queue
import signal
import atexit
import psutil
import logging
import asyncio
import aiohttp
import aiofiles
import functools
import threading
from pathlib import Path
from .app_types import *
from datetime import datetime
from gql import gql as gql_client
from gql import Client
from pkg_resources import get_distribution
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport

# Server Mode:
import hashlib
from graphql import GraphQLError, FieldDefinitionNode
from dateutil import parser
import psycopg2
from psycopg2 import pool, OperationalError
from psycopg2.extras import RealDictCursor, DictCursor
from ariadne import gql as gql_server
from ariadne import make_executable_schema, QueryType, MutationType, SchemaDirectiveVisitor, ScalarType, SubscriptionType, upload_scalar, UnionType
from ariadne.asgi import GraphQL
from ariadne.asgi.handlers import GraphQLTransportWSHandler
from starlette.routing import Route, WebSocketRoute
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

DATA_CHUNK_SIZE = 1024 * 1024  # 1 MB in bytes

class Maoto:
    class EventDrivenQueueProcessor:
        def __init__(self, logger, worker_count=10, min_workers=1, max_workers=20, scale_threshold=5, scale_down_delay=30, outer_class=None):
            self.outer_class = outer_class
            self.task_queue = queue.Queue()
            self.initial_worker_count = worker_count
            self.max_workers = max_workers
            self.min_workers = min_workers
            self.scale_threshold = scale_threshold
            self.workers = []
            self.stop_event = threading.Event()
            self.producer_thread = None
            self.monitor_thread = None
            self.completed_tasks = 0
            self.error_count = 0
            self.lock = threading.Lock()
            self.last_scale_down_time = 0
            self.scale_down_delay = scale_down_delay  # Minimum time (seconds) between scale-downs
            self.logger = logger

            atexit.register(self.cleanup)

        def start_workers(self, worker_func, count):
            for _ in range(count):
                worker = threading.Thread(target=self.worker_process, args=(worker_func,))
                worker.daemon = True
                worker.start()
                self.workers.append(worker)

        def start_producer(self, producer_func):
            self.producer_thread = threading.Thread(target=self.run_producer, args=(producer_func,))
            self.producer_thread.daemon = True
            self.producer_thread.start()

        def stop_extra_workers(self, count):
            for _ in range(count):
                self.task_queue.put(None)  # Insert None as a poison pill to terminate one worker

        def cleanup(self):
            """Cleanup function to ensure graceful termination."""
            self.logger.info("Cleaning up...")

            self.stop_event.set()

            # Wait for the producer thread to finish
            if self.producer_thread:
                self.producer_thread.join()

            # Insert poison pills to stop worker threads
            for _ in range(len(self.workers)):
                self.task_queue.put(None)

            # Wait for all worker threads to finish
            for worker in self.workers:
                worker.join()

            # Wait for the monitor thread to finish
            if self.monitor_thread:
                self.monitor_thread.join()

            if self.outer_class:
                if self.outer_class._at_shutdown:
                    asyncio.run(self.outer_class._at_shutdown())

            self.logger.info("All processes have been terminated gracefully.")

        def run_producer(self, producer_func):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(producer_func(self.task_queue, self.stop_event))
            except Exception as e:
                self.logger.error(f"Producer encountered an exception: {e}")
            finally:
                loop.close()

        def worker_process(self, worker_func):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def process_tasks():
                while not self.stop_event.is_set() or not self.task_queue.empty():
                    try:
                        task = self.task_queue.get(timeout=1)
                        if task is None:  # Poison pill received
                            self.task_queue.task_done()
                            break
                        await worker_func(task)
                        self.task_queue.task_done()
                        with self.lock:
                            self.completed_tasks += 1
                    except queue.Empty:
                        continue
                    except Exception as e:
                        with self.lock:
                            self.error_count += 1
                        self.logger.error(f"Worker encountered an exception: {e}")

            try:
                loop.run_until_complete(process_tasks())
            finally:
                # Remove the current worker from the workers list on termination
                with self.lock:
                    self.workers.remove(threading.current_thread())
                loop.close()

        def signal_handler(self, signum, frame):
            self.logger.info("Termination signal received")
            
            self.cleanup()

            # After handling the signal, forward it to the main program
            self.logger.info(f"Forwarding signal {signum} to the main process.")
            signal.signal(signum, signal.SIG_DFL)  # Reset the signal handler to default
            os.kill(os.getpid(), signum)  # Re-raise the signal to propagate it

        def monitor_system(self, worker_func):
            while not self.stop_event.is_set():
                with self.lock:
                    queue_size = self.task_queue.qsize()
                    current_worker_count = len(self.workers)

                # Scale up workers if the queue size exceeds the threshold and we haven't reached max_workers
                if queue_size > self.scale_threshold and current_worker_count < self.max_workers:
                    self.logger.info(f"Scaling up: Adding workers (Current: {current_worker_count})")
                    additional_workers = max(min(int((((max(queue_size - self.scale_threshold, 0)) * 0.2) ** 1.3)), self.max_workers - current_worker_count), 0)
                    self.start_workers(worker_func, additional_workers)

                # Scale down if the queue is well below the threshold, we have more workers than min_workers,
                # and it's been long enough since the last scale down
                elif queue_size < self.scale_threshold / 2 and current_worker_count > self.min_workers:
                    current_time = time.time()
                    if current_time - self.last_scale_down_time > self.scale_down_delay:
                        self.logger.info(f"Scaling down: Removing workers (Current: {current_worker_count})")
                        self.stop_extra_workers(1)
                        self.last_scale_down_time = current_time  # Update the last scale-down time

                # Log system status
                self.logger.info(
                    f"Queue size: {queue_size}, Active workers: {current_worker_count}, "
                    f"Completed tasks: {self.completed_tasks}, Errors: {self.error_count}"
                )
                self.completed_tasks = 0

                # Monitor system resources
                cpu_usage = psutil.cpu_percent(interval=1)
                memory_usage = psutil.virtual_memory().percent
                self.logger.info(f"System CPU Usage: {cpu_usage}%, Memory Usage: {memory_usage}%")

                # Sleep before the next monitoring check
                time.sleep(5)

        def run(self, producer_func, worker_func):
            # Clear the stop event in case it's set from a previous run
            self.stop_event.clear()

            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

            if self.outer_class:
                if self.outer_class._at_startup:
                    asyncio.run(self.outer_class._at_startup())
                    

            self.start_workers(worker_func, self.initial_worker_count)
            self.start_producer(lambda task_queue, stop_event: producer_func(task_queue, stop_event))

            self.monitor_thread = threading.Thread(target=self.monitor_system, args=(worker_func,))
            self.monitor_thread.daemon = True
            self.monitor_thread.start()

    class ServerMode:
        class AuthDirective(SchemaDirectiveVisitor):
            def visit_field_definition(self, field: FieldDefinitionNode, _) -> FieldDefinitionNode:
                original_resolver = field.resolve

                def resolve_auth(root, info, **kwargs):
                    request = info.context["request"]
                    
                    # Extract the request headers from context
                    try:
                        address = request.headers.get("Origin", "")
                        if address not in ["https://api.maoto.world", "http://localhost"]:
                            raise GraphQLError(f"Unauthorized: Request not from allowed domain {address}.")
                        
                    except Exception as e:
                        raise GraphQLError(f"Authorization failed: {str(e)}")

                    # Proceed to the original resolver if authentication passes
                    return original_resolver(root, info, **kwargs)

                field.resolve = resolve_auth
                return field
            
        def __init__(self, logger, outer_class=None):
            self.logger = logger
            self.outer_class = outer_class

            self.type_defs = gql_server("""
                directive @auth on FIELD_DEFINITION

                scalar Datetime
                            
                input Response {
                    response_id: ID! 
                    apikey_id: ID
                    time: Datetime!
                    post_id: ID!
                    description: String!
                }
                            
                input Actioncall {
                    actioncall_id: ID!
                    apikey_id: ID
                    time: Datetime!
                    action_id: ID!
                    post_id: ID!
                    parameters: String!
                }
                                        
                type Query {
                    _dummy: String
                }

                type Mutation {
                    forwardActioncall(actioncalls: [Actioncall!]): [Boolean!] @auth
                    forwardResponse(responses: [Response!]): [Boolean!] @auth
                }
                """)
                        
            # Resolver functions
            self.query = QueryType()
            self.mutation = MutationType()
            self.subscription = SubscriptionType()
            self.datetime_scalar = ScalarType("Datetime")
            @self.datetime_scalar.serializer
            def serialize_datetime(value: datetime) -> str:
                return value.isoformat()
            @self.datetime_scalar.value_parser
            def parse_datetime_value(value: str) -> datetime:
                return parser.parse(value)

            # define other functions here? -----------------------------
            @self.mutation.field("forwardActioncall")
            async def forward_actioncall(_, info, forwarded_actioncalls: list[Actioncall]) -> list[bool]:
                # get actioncalls
                success = []
                for forwarded_actioncall in forwarded_actioncalls:
                    try:
                        actioncall = Actioncall(
                            actioncall_id=uuid.UUID(forwarded_actioncall["actioncall_id"]),
                            action_id=uuid.UUID(forwarded_actioncall["action_id"]),
                            post_id=uuid.UUID(forwarded_actioncall["post_id"]),
                            apikey_id=uuid.UUID(forwarded_actioncall["apikey_id"]),
                            parameters=forwarded_actioncall["parameters"],
                            time=datetime.fromisoformat(forwarded_actioncall["time"])
                        )
                        await self.outer_class._resolve_actioncall(actioncall)
                        success.append(True)
                    except Exception as e:
                        self.logger.error(f"Error forwarding actioncall: {e}")
                        success.append(False)
                return success
            
            @self.mutation.field("forwardResponse")
            async def forward_response(_, info, forwarded_responses: list[Response]) -> list[bool]:
                success = []
                for forwarded_response in forwarded_responses:
                    try:
                        response = Response(
                            response_id=uuid.UUID(forwarded_response["response_id"]),
                            post_id=uuid.UUID(forwarded_response["post_id"]),
                            description=forwarded_response["description"],
                            apikey_id=uuid.UUID(forwarded_response["apikey_id"]) if forwarded_response["apikey_id"] else None,
                            time=datetime.fromisoformat(forwarded_response["time"])
                        )
                        await self.outer_class._resolve_response(response)
                        success.append(True)
                    except Exception as e:
                        self.logger.error(f"Error forwarding response: {e}")
                        success.append(False)
                return success

            self.authdirective = self.AuthDirective
            
            # Create the executable schema
            self.schema = make_executable_schema(self.type_defs, self.query, self.mutation, self.datetime_scalar, directives={"auth": self.authdirective})

            self.graphql_app = GraphQL(
                self.schema, 
                debug=True,
            )
            self.routes=[
                Route("/graphql", self.graphql_app.handle_request, methods=["GET", "POST", "OPTIONS"]),
            ]

            self.middleware = [
                Middleware(
                    TrustedHostMiddleware,
                    allowed_hosts=['maoto.world', '*.maoto.world', 'localhost', '*.svc.cluster.local']
                ),
                # TODO: HTTPS not working yet: incompatible versions?
                # https://chatgpt.com/c/c50f8b80-05be-4f39-a4de-540725536ed3
                # Middleware(HTTPSRedirectMiddleware)
            ]

        def start_server(self):
            self.app = Starlette(
                routes=self.routes,
                middleware=self.middleware,
                on_startup=[self.startup],
                on_shutdown=[self.shutdown]
            )
            return self.app

        async def startup(self):
            """
            Actions to perform on application startup.
            """

            if self.outer_class:
                if self.outer_class._at_startup:
                    await self.outer_class._at_startup()

        async def shutdown(self):
            """
            Actions to perform on application shutdown.
            """

            if self.outer_class:
                if self.outer_class._at_shutdown:
                    await self.outer_class._at_shutdown()
                    
    def __init__(self, logging_level=logging.INFO, receive_messages=True, open_connection=False, db_connection=False):
        self._db_connection = db_connection
        self._db_connection_pool = None
        if self._db_connection:
            # Environment variables for database connection
            self._db_hostname = os.getenv('POSTGRES_HOST')
            self._db_name = os.getenv('POSTGRES_DB')
            self._db_username = os.getenv('POSTGRES_USER')
            self._db_user_password = os.getenv('POSTGRES_PASSWORD')
            self._db_port = os.getenv('POSTGRES_PORT')

            if not self._db_hostname or not self._db_name or not self._db_username or not self._db_user_password or not self._db_port:
                raise EnvironmentError("POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, and POSTGRES_PASSWORD, POSTGRES_PORT must be set")

            # enable uuid dict to be returned as list of uuids
            psycopg2.extras.register_uuid()
            
        # Set up logging
        logging.basicConfig(level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        # Disable INFO logs for gql and websockets
        logging.getLogger("gql").setLevel(logging.WARNING)
        logging.getLogger("websockets").setLevel(logging.WARNING)

        self.server_domain = os.environ.get("API_DOMAIN", "api.maoto.world")
        if os.environ.get("SERVER_LOCAL") == "True":
            self.server_domain = "localhost"
        self.protocol = "http"
        server_port = os.environ.get("SERVER_PORT") if os.environ.get("SERVER_PORT") else "4000"
        self.server_url = self.protocol + "://" + self.server_domain + ":" + server_port
        self.graphql_url = self.server_url + "/graphql"
        self.subscription_url = self.graphql_url.replace(self.protocol, "ws")
        
        self.apikey_value = os.environ.get("MAOTO_API_KEY")
        if self.apikey_value in [None, ""]:
            raise ValueError("API key is required. (Set MAOTO_API_KEY environment variable)")

        transport = AIOHTTPTransport(
            url=self.graphql_url,
            headers={"Authorization": self.apikey_value},
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=True)

        self.id_action_map = {}
        self.action_handler_registry = {}
        self.default_action_handler_method = None
        self.bid_handler_registry = {}
        self.default_bid_handler_method = None
        self.auth_handler_method = None
        self.response_handler_method = None
        self.custom_startup_method = None
        self.custom_shutdown_method = None

        self.receive_messages = receive_messages
        if self.receive_messages:
            self._open_connection = open_connection
            if self._open_connection:
                self.server = self.EventDrivenQueueProcessor(self.logger, worker_count=1, scale_threshold=10, outer_class=self)
            else:
                self.server = self.ServerMode(self.logger, self)

    def start_server(self, blocking=False) -> Starlette | None:
        if not self.receive_messages:
            raise ValueError("Message receiving is disabled. Set receive_messages=True to enable.")
        
        if self._open_connection:
            self.server.run(self.subscribe_to_events, self.maoto_worker)
            
            if blocking:
                def handler(signum, frame):
                    self.logger.info("Stopped by Ctrl+C")
                    sys.exit(0)

                # Assign the SIGINT (Ctrl+C) signal to the handler
                signal.signal(signal.SIGINT, handler)

                self.logger.info("Running... Press Ctrl+C to stop.")
                signal.pause()  # Blocks here until a signal (Ctrl+C) is received
    
            return None
        else:
            return self.server.start_server()

    def custom_startup(self):
        def decorator(func):
            self.custom_startup_method = func
            return func
        return decorator
    
    def custom_shutdown(self):
        def decorator(func):
            self.custom_shutdown_method = func
            return func
        return decorator

    async def _at_startup(self):
        if self._db_connection:
            self._startup_db_conn_pool()

        if self.custom_startup_method:
            await self.custom_startup_method()

    async def _at_shutdown(self):
        if self._db_connection:
            self._shutdown_db_conn_pool()

        if self.custom_shutdown_method:
            await self.custom_shutdown_method()

    def _startup_db_conn_pool(self):
        try:
            self._db_connection_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                host=self._db_hostname,
                dbname=self._db_name,
                user=self._db_username,
                password=self._db_user_password,
                port=self._db_port
            )
            self.logger.info("Database connection pool created successfully.")
        except OperationalError as e:
            self.logger.error("Error setting up database connection pool: %s", e)
            raise GraphQLError("Error setting up database connection pool.")

    def _shutdown_db_conn_pool(self):
        if self._db_connection_pool:
            self._db_connection_pool.closeall()
            self.logger.info("Database connection pool closed.")

    def get_con(self):
        try:
            return self._db_connection_pool.getconn()
        except Exception as e:
            self.logger.error("Error getting connection from pool: %s", e)
            raise GraphQLError("Error getting connection from pool.")

    def put_con(self, conn):
        try:
            self._db_connection_pool.putconn(conn)
        except Exception as e:
            self.logger.error("Error putting connection back to pool: %s", e)
            raise GraphQLError("Error putting connection back to pool.")

    # Decorator to allow synchronous and asynchronous usage of the same method
    @staticmethod
    def _sync_or_async(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Check if there's an active event loop
                loop = asyncio.get_running_loop()
                # If we're inside an active loop, just return the coroutine
                return func(*args, **kwargs)
            except RuntimeError:
                # If no loop is running, create a new one
                return asyncio.run(func(*args, **kwargs))
        return wrapper
    
    @_sync_or_async
    async def check_status(self) -> bool:
        query = gql_client('''
        query {
            checkStatus
        }
        ''')
        result = await self.client.execute_async(query)
        return result["checkStatus"]

    @_sync_or_async
    async def _check_version_compatibility(self):

        query = gql_client('''
        query CheckVersionCompatibility($client_version: String!) {
            checkVersionCompatibility(client_version: $client_version)
        }
        ''')
        package_version = get_distribution("maoto_agent").version
        result = await self.client.execute_async(query, {'client_version': package_version})
        compatibility = result["checkVersionCompatibility"]
        if not compatibility:
            raise ValueError(f"Incompatible version {package_version}. Please update the agent to the latest version.")

    @_sync_or_async
    async def get_own_user(self) -> User:
        query = gql_client('''
        query {
            getOwnUser {
                user_id
                username
                time
                roles
            }
        }
        ''')

        result = await self.client.execute_async(query)
        data = result["getOwnUser"]
        return User(data["username"], uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["roles"])

    @_sync_or_async
    async def get_own_api_key(self) -> ApiKey:
        # Query to fetch the user's own API keys, limiting the result to only one
        query = gql_client('''
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

        result = await self.client.execute_async(query)
        data_list = result["getOwnApiKeys"]

        # Return the first API key (assume the list is ordered by time or relevance)
        if data_list:
            data = data_list[0]
            return ApiKey(
                apikey_id=uuid.UUID(data["apikey_id"]),
                user_id=uuid.UUID(data["user_id"]),
                time=datetime.fromisoformat(data["time"]),
                name=data["name"],
                roles=data["roles"]
            )
        else:
            raise Exception("No API keys found for the user.")


    @_sync_or_async
    async def get_own_api_keys(self) -> list[bool]:
        # Note: the used API key id is always the first one
        query = gql_client('''
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

        result = await self.client.execute_async(query)
        data_list = result["getOwnApiKeys"]
        return [ApiKey(uuid.UUID(data["apikey_id"]), uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["name"], data["roles"]) for data in data_list]

    @_sync_or_async
    async def create_users(self, new_users: list[NewUser]):
        users = [{'username': user.username, 'password': user.password, 'roles': user.roles} for user in new_users]
        query = gql_client('''
        mutation createUsers($new_users: [NewUser!]!) {
            createUsers(new_users: $new_users) {
                username
                user_id
                time
                roles
            }
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"new_users": users})
        data_list = result["createUsers"]
        return [User(data["username"], uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["roles"]) for data in data_list]

    @_sync_or_async
    async def delete_users(self, user_ids: list[User | str]) -> bool:
        user_ids = [str(user.get_user_id()) if isinstance(user, User) else str(user) for user in user_ids]
        query = gql_client('''
        mutation deleteUsers($user_ids: [ID!]!) {
            deleteUsers(user_ids: $user_ids)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"user_ids": user_ids})
        return result["deleteUsers"]
    
    @_sync_or_async
    async def get_users(self) -> list[User]:
        query = gql_client('''
        query {
            getUsers {
                user_id
                username
                time
                roles
            }
        }
        ''')

        result = await self.client.execute_async(query)
        data_list = result["getUsers"]
        return [User(data["username"], uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["roles"]) for data in data_list]
    
    @_sync_or_async
    async def create_apikeys(self, api_keys: list[NewApiKey]) -> list[ApiKey]:
        api_keys_data = [{'name': key.get_name(), 'user_id': str(key.get_user_id()), 'roles': key.get_roles()} for key in api_keys]
        query = gql_client('''
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

        result = await self.client.execute_async(query, variable_values={"new_apikeys": api_keys_data})
        data_list = result["createApiKeys"]
        return [ApiKeyWithSecret(uuid.UUID(data["apikey_id"]), uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["name"], data["roles"], data["value"]) for data in data_list]
        
    @_sync_or_async
    async def delete_apikeys(self, apikey_ids: list[ApiKey | str]) -> list[bool]:
        api_key_ids = [str(apikey.get_apikey_id()) if isinstance(apikey, ApiKey) else str(apikey) for apikey in apikey_ids]
        query = gql_client('''
        mutation deleteApiKeys($apikey_ids: [ID!]!) {
            deleteApiKeys(apikey_ids: $apikey_ids)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"apikey_ids": api_key_ids})
        return result["deleteApiKeys"]

    @_sync_or_async
    async def get_apikeys(self, user_ids: list[User | str]) -> list[ApiKey]:
        user_ids = [str(user.get_user_id()) if isinstance(user, User) else str(user) for user in user_ids]
        query = gql_client('''
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

        result = await self.client.execute_async(query, variable_values={"user_ids": user_ids})
        data_list = result["getApiKeys"]
        return [ApiKey(uuid.UUID(data["apikey_id"]), uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["name"], data["roles"]) for data in data_list]

    @_sync_or_async
    async def create_actions(self, new_actions: list[NewAction]) -> list[Action]:
        actions = [{'name': action.name, 'parameters': action.parameters, 'description': action.description, 'tags': action.tags, 'cost': action.cost, 'followup': action.followup} for action in new_actions]
        query = gql_client('''
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

        result = await self.client.execute_async(query, variable_values={"new_actions": actions})
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

    @_sync_or_async
    async def delete_actions(self, action_ids: list[Action | str]) -> list[bool]:
        action_ids = [str(action.get_action_id()) if isinstance(action, Action) else str(action) for action in action_ids]
        query = gql_client('''
        mutation deleteActions($action_ids: [ID!]!) {
            deleteActions(action_ids: $action_ids)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"action_ids": action_ids})
        return result["deleteActions"]
    
    @_sync_or_async
    async def get_actions(self, apikey_ids: list[ApiKey | str]) -> list[Action]:
        apikey_ids = [str(apikey.get_apikey_id()) if isinstance(apikey, ApiKey) else str(apikey) for apikey in apikey_ids]
        query = gql_client('''
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

        result = await self.client.execute_async(query, variable_values={"apikey_ids": apikey_ids})
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
    
    @_sync_or_async
    async def get_own_actions(self) -> list[Action]:
        query = gql_client('''
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

        result = await self.client.execute_async(query)
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
    
    @_sync_or_async
    async def create_posts(self, new_posts: list[NewPost]) -> list[Post]:
        posts = [{'description': post.description, 'context': post.context} for post in new_posts]
        query = gql_client('''
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

        result = await self.client.execute_async(query, variable_values={"new_posts": posts})
        data_list = result["createPosts"]
        return [Post(
            post_id=uuid.UUID(data["post_id"]),
            description=data["description"],
            context=data["context"],
            apikey_id=uuid.UUID(data["apikey_id"]),
            time=datetime.fromisoformat(data["time"]),
            resolved=data["resolved"]
        ) for data in data_list]

    @_sync_or_async
    async def delete_posts(self, post_ids: list[Post | str]) -> list[bool]:
        post_ids = [str(post.get_post_id()) if isinstance(post, Post) else str(post) for post in post_ids]
        query = gql_client('''
        mutation deletePosts($post_ids: [ID!]!) {
            deletePosts(post_ids: $post_ids)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"post_ids": post_ids})
        return result["deletePosts"]

    @_sync_or_async
    async def get_posts(self, apikey_ids: list[ApiKey | str]) -> list[Post]:
        apikey_ids = [str(apikey.get_apikey_id()) if isinstance(apikey, ApiKey) else str(apikey) for apikey in apikey_ids]
        query = gql_client('''
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

        result = await self.client.execute_async(query, variable_values={"apikey_ids": apikey_ids})
        data_list = result["getPosts"]
        return [Post(
            post_id=uuid.UUID(data["post_id"]),
            description=data["description"],
            context=data["context"],
            apikey_id=uuid.UUID(data["apikey_id"]),
            time=datetime.fromisoformat(data["time"]),
            resolved=data["resolved"]
        ) for data in data_list]

    @_sync_or_async
    async def get_own_posts(self) -> list[Post]:
        query = gql_client('''
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

        result = await self.client.execute_async(query)
        data_list = result["getOwnPosts"]
        return [Post(
            post_id=uuid.UUID(data["post_id"]),
            description=data["description"],
            context=data["context"],
            apikey_id=uuid.UUID(data["apikey_id"]),
            time=datetime.fromisoformat(data["time"]),
            resolved=data["resolved"]
        ) for data in data_list]
    
    @_sync_or_async
    async def create_actioncalls(self, new_actioncalls: list[NewActioncall]) -> list[Actioncall]:
        actioncalls = [{'action_id': str(actioncall.action_id), 'post_id': str(actioncall.post_id), 'parameters': actioncall.parameters} for actioncall in new_actioncalls]
        query = gql_client('''
        mutation createActioncalls($new_actioncalls: [NewActioncall!]!) {
            createActioncalls(new_actioncalls: $new_actioncalls) {
                actioncall_id
                action_id
                post_id
                apikey_id
                parameters
                time
            }
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"new_actioncalls": actioncalls})
        data_list = result["createActioncalls"]
        return [Actioncall(
            actioncall_id=uuid.UUID(data["actioncall_id"]),
            action_id=uuid.UUID(data["action_id"]),
            post_id=uuid.UUID(data["post_id"]),
            apikey_id=uuid.UUID(data["apikey_id"]),
            parameters=data["parameters"],
            time=datetime.fromisoformat(data["time"])
        ) for data in data_list]
    
    @_sync_or_async
    async def create_responses(self, new_responses: list[NewResponse]) -> list[Response]:
        responses = [{'post_id': str(response.post_id), 'description': response.description} for response in new_responses]
        query = gql_client('''
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

        result = await self.client.execute_async(query, variable_values={"new_responses": responses})
        data_list = result["createResponses"]
        return [Response(
            response_id=uuid.UUID(data["response_id"]),
            post_id=uuid.UUID(data["post_id"]),
            description=data["description"],
            apikey_id=uuid.UUID(data["apikey_id"]),
            time=datetime.fromisoformat(data["time"])
        ) for data in data_list]
    
    @_sync_or_async
    async def create_bidresponses(self, bidresponses: list[BidResponse]) -> list[bool]:
        # Prepare the input
        bidresponses = [
            {
                'action_id': str(bidresponse.get_action_id()),
                'post_id': str(bidresponse.get_post_id()),
                'cost': bidresponse.get_cost()
            }
            for bidresponse in bidresponses
        ]

        # Define the GQL mutation
        query = gql_client('''
        mutation createBidResponses($bidresponses: [BidResponse!]!) {
            createBidResponses(bidresponses: $bidresponses)
        }
        ''')

        # Execute asynchronously
        data_list = await self.client.execute_async(
            query,
            variable_values={"bidresponses": bidresponses}
        )

        # 'createBidResponses' is already a list of booleans, so just return it.
        return data_list['createBidResponses']

    # only used for open connection server
    async def maoto_worker(self, element):
        if isinstance(element, Actioncall):
            await self._resolve_actioncall(element)
        elif isinstance(element, Response):
            await self._resolve_response(element)
        elif isinstance(element, BidRequest):
            await self._resolve_bidrequest(element)
        else:
            self.logger.error(f"Unknown event type: {element}")

    # only used for open connection server
    async def subscribe_to_events(self, task_queue, stop_event):
        # Subscription to listen for both actioncalls and responses using __typename
        subscription = gql_client('''
        subscription subscribeToEvents {
            subscribeToEvents {
                __typename
                ... on Actioncall {
                    actioncall_id
                    action_id
                    post_id
                    apikey_id
                    parameters
                    time
                }
                ... on Response {
                    response_id
                    post_id
                    description
                    apikey_id
                    time
                }
                ... on BidRequest {
                    action_id
                    post {
                        post_id
                        description
                        context
                        apikey_id
                        time
                        resolved
                    }
                }
            }
        }
        ''')

        transport = WebsocketsTransport(
            url=self.subscription_url,
            headers={"Authorization": self.apikey_value},
        )

        async def monitor_stop_event(subscription_task):
            while not stop_event.is_set():
                await asyncio.sleep(1)
            subscription_task.cancel()

        try:
            subscription_task = asyncio.create_task(self._run_subscription(task_queue, subscription, transport))
            stop_monitoring_task = asyncio.create_task(monitor_stop_event(subscription_task))
            await subscription_task
            stop_monitoring_task.cancel()

        except asyncio.CancelledError:
            self.logger.info("Subscription was cancelled")
        except Exception as e:
            self.logger.error(f"An error occurred during subscription: {e}")

    # only used for open connection server
    async def _run_subscription(self, task_queue, subscription, transport):
        async with Client(
            transport=transport,
            fetch_schema_from_transport=True,
        ) as session:
            async for result in session.subscribe(subscription):
                event_data = result['subscribeToEvents']
                # Use __typename to identify the type of the event
                if event_data["__typename"] == "Actioncall":
                    event = Actioncall(
                        actioncall_id=uuid.UUID(event_data["actioncall_id"]),
                        action_id=uuid.UUID(event_data["action_id"]),
                        post_id=uuid.UUID(event_data["post_id"]),
                        apikey_id=uuid.UUID(event_data["apikey_id"]),
                        parameters=event_data["parameters"],
                        time=datetime.fromisoformat(event_data["time"])
                    )
                elif event_data["__typename"] == "Response":
                    event = Response(
                        response_id=uuid.UUID(event_data["response_id"]),
                        post_id=uuid.UUID(event_data["post_id"]),
                        description=event_data["description"],
                        apikey_id=uuid.UUID(event_data["apikey_id"]) if event_data["apikey_id"] else None,
                        time=datetime.fromisoformat(event_data["time"])
                    )
                elif event_data["__typename"] == "BidRequest":
                    # Extract the nested Post data
                    post_data = event_data["post"]
                    post = Post(
                        post_id=uuid.UUID(post_data["post_id"]),
                        description=post_data["description"],
                        context=post_data["context"],
                        apikey_id=uuid.UUID(post_data["apikey_id"]),
                        time=datetime.fromisoformat(post_data["time"]),
                        resolved=post_data["resolved"]
                    )
                    
                    # Create a BidRequest object
                    event = BidRequest(
                        action_id=uuid.UUID(event_data["action_id"]),
                        post=post
                    )
                else:
                    self.logger.error(f"Unknown event type: {event_data['__typename']}")
                
                task_queue.put(event)

    @_sync_or_async
    async def _download_file_async(self, file_id: str, destination_dir: Path) -> File:
        query = gql_client('''
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

    @_sync_or_async
    async def download_files(self, file_ids: list[str], download_dir: Path) -> list[File]:
        downloaded_files = []
        for file_id in file_ids:
            downloaded_file = await self._download_file_async(file_id, download_dir)
            downloaded_files.append(downloaded_file)
        return downloaded_files

    @_sync_or_async
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

    @_sync_or_async
    async def upload_files(self, file_paths: list[Path]) -> list[File]:
        uploaded_files = []
        for file_path in file_paths:
            uploaded_file = await self._upload_file_async(file_path)
            uploaded_files.append(uploaded_file)
        return uploaded_files
    
    @_sync_or_async
    async def download_missing_files(self, file_ids: list[str], download_dir: Path) -> list[File]:
        def _if_filenames_in_dir(self, filenames: list[str], dir: Path) -> list[str]:
            missing_files = []
            for filename in filenames:
                file_path = download_dir / str(filename)
                if not file_path.exists():
                    missing_files.append(filename)
            return missing_files
        files_missing = _if_filenames_in_dir(file_ids)
        downloaded_files = await self.download_files(files_missing)
        return downloaded_files

    def register_auth_handler(self):
        def decorator(func):
            self.auth_handler_method = func
            return func
        return decorator
    
    def register_response_handler(self):
        def decorator(func):
            self.response_handler_method = func
            return func
        return decorator

    def register_action_handler(self, name: str):
        def decorator(func):
            self.action_handler_registry[name] = func
            return func
        return decorator

    def register_action_handler_fallback(self):
        def decorator(func):
            self.default_action_handler_method = func
            return func
        return decorator
    
    def register_bid_handler(self, name: str):
        def decorator(func):
            self.bid_handler_registry[name] = func
            return func
        return decorator
    
    def register_bid_handler_fallback(self):
        def decorator(func):
            self.default_bid_handler_method = func
            return func
        return decorator
    
    async def _resolve_response(self, response: Response):
        try:
            if self.auth_handler_method:
                    self.auth_handler_method(response)
        except Exception as e:
            self.logger.info(f"Authentication failed: {e}")
            GraphQLError("Authentication failed")

        if self.response_handler_method:
            await self.response_handler_method(response)

    async def _resolve_bidrequest(self, bid_request: BidRequest):
        try:
            bidder = self.bid_handler_registry[self.id_action_map[str(bid_request.get_action_id())]]
            bid_value = bidder(bid_request.get_post())
        except KeyError:
            if self.default_bid_handler_method:
                bidder = self.default_bid_handler_method
                bid_value = bidder(bid_request)

        new_bid = BidResponse(
            action_id=bid_request.get_action_id(),
            post_id=bid_request.get_post().get_post_id(),
            cost=bid_value
        )
        await self.create_bidresponses([new_bid])

    async def _resolve_actioncall(self, actioncall: Actioncall):  
        try:
            if self.auth_handler_method:
                    self.auth_handler_method(actioncall)
        except Exception as e:
            self.logger.info(f"Authentication failed: {e}")
            GraphQLError("Authentication failed")

        try:
            action = self.action_handler_registry[self.id_action_map[str(actioncall.get_action_id())]]
        except KeyError:
            if self.default_action_handler_method:
                action = self.default_action_handler_method

        response_description = action(actioncall.get_apikey_id(), actioncall.get_parameters())
        
        new_response = NewResponse(
            post_id=actioncall.get_post_id(),
            description=response_description
        )
        await self.create_responses([new_response])