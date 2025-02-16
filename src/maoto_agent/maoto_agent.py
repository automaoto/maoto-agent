import os
import sys
import json
import time
import queue
import fcntl
import signal
import atexit
import psutil
import logging
import random
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
from contextlib import asynccontextmanager

# Server Mode:
import hashlib
from graphql import GraphQLError, FieldDefinitionNode
from dateutil import parser
import databases
import asyncpg
from ariadne import gql as gql_server
from ariadne import make_executable_schema, QueryType, MutationType, SchemaDirectiveVisitor, ScalarType, SubscriptionType, upload_scalar, UnionType
from ariadne.asgi import GraphQL
from ariadne.asgi.handlers import GraphQLTransportWSHandler
from starlette.routing import Route, WebSocketRoute
from starlette.responses import JSONResponse
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
                        self.logger.debug(f"Scaling down: Removing workers (Current: {current_worker_count})")
                        self.stop_extra_workers(1)
                        self.last_scale_down_time = current_time  # Update the last scale-down time

                # Log system status
                self.logger.debug(
                    f"Queue size: {queue_size}, Active workers: {current_worker_count}, "
                    f"Completed tasks: {self.completed_tasks}, Errors: {self.error_count}"
                )
                self.completed_tasks = 0

                # Monitor system resources
                cpu_usage = psutil.cpu_percent(interval=1)
                memory_usage = psutil.virtual_memory().percent
                self.logger.debug(f"System CPU Usage: {cpu_usage}%, Memory Usage: {memory_usage}%")

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
            logger = None
            fetch_all = None

            @classmethod
            def configure(cls, logger, fetch_all):
                cls.logger = logger
                cls.fetch_all = fetch_all
                
            def visit_field_definition(self, field: FieldDefinitionNode, _) -> FieldDefinitionNode:
                original_resolver = field.resolve

                async def resolve_auth(root, info, **kwargs):
                    """Authenticate and authorize API key."""
                    
                    request = info.context["request"]
                    value = request.headers.get("Authorization")

                    if not value:
                        raise GraphQLError("Authentication failed. No API key provided.")

                    if value in ["marketplace_apikey_value", "assistant_apikey_value"]:
                        info.context['apikey'] = ApiKey(
                            apikey_id=None,
                            time=None,
                            user_id=None,
                            name=None,
                            roles=[],
                            url=None,
                        )

                        # address = request.headers.get("Origin", "")
                        # if address not in ["https://api.maoto.world", "http://localhost"]:
                        #     raise GraphQLError(f"Unauthorized: Request not from allowed domain {address}.")

                    else:
                        hash_value = hashlib.sha256(value.encode()).hexdigest()

                        try:
                            # Fetch API key and user ID
                            query = "SELECT apikey_id, name, user_id, url, time FROM apikeys WHERE hash = :hash"
                            values = {"hash": hash_value}
                            result = await self.fetch_all(query, values)

                            if result is None:
                                raise GraphQLError("Authentication failed. Invalid API key.")

                            info.context['apikey'] = ApiKey(
                                apikey_id=result[0]["apikey_id"],
                                time=result[0]["time"],
                                user_id=result[0]["user_id"],
                                name=result[0]["name"],
                                roles=[], # TODO: later when accessing the shared apikey / user db: fetch roles and check for validity with @auth
                                url=result[0]["url"],

                            )

                        except Exception as e:
                            self.logger.error("Error in authorization: %s", e)
                            raise GraphQLError("Authorization error.")

                    return await original_resolver(root, info, **kwargs)

                field.resolve = resolve_auth
                return field
            
        def __init__(self, logger, outer_class=None):
            self.logger = logger
            self.outer_class = outer_class
                        
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
            
            self.json_scalar = ScalarType("JSON")
            @self.json_scalar.serializer
            def serialize_json(value: dict) -> str:
                return json.dumps(value)
            @self.json_scalar.value_parser
            def parse_json_value(value: str) -> dict:
                return json.loads(value)

            @self.mutation.field("forwardActioncalls")
            async def forward_actioncalls(_, info, actioncalls: list[dict[str, object]]) -> list[bool]:
                actioncalls = [Actioncall(
                    actioncall_id=uuid.UUID(actioncall["actioncall_id"]),
                    apikey_id=uuid.UUID(actioncall["apikey_id"]),
                    time=datetime.fromisoformat(actioncall["time"]),
                    action_id=uuid.UUID(actioncall["action_id"]),
                    post_id=uuid.UUID(actioncall["post_id"]),
                    parameters=actioncall["parameters"],
                ) for actioncall in actioncalls]

                status = []
                for actioncall in actioncalls:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(actioncall, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving actioncall: {e}")
                        status.append(False)

                return status

            @self.mutation.field("forwardResponses")
            async def forward_responses(_, info, responses: list[dict[str, object]]) -> list[bool]:
                responses = [Response(
                    response_id=uuid.UUID(response["response_id"]),
                    post_id=uuid.UUID(response["post_id"]),
                    description=response["description"],
                    apikey_id=uuid.UUID(response["apikey_id"]) if "apikey_id" in response else None, #TODO why is this not send as None?
                    time=response["time"],
                ) for response in responses]

                status = []
                for response in responses:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(response, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving response: {e}")
                        status.append(False)

                return status

            @self.mutation.field("forwardBidRequests")
            async def forward_bidrequests(_, info, bidrequests: list[dict[str, object]]) -> list[bool]:
                bidrequests = [BidRequest(
                    action_id=bidrequest["action_id"],
                    post=Post(
                        post_id=uuid.UUID(bidrequest["post"]["post_id"]),
                        description=bidrequest["post"]["description"],
                        context=bidrequest["post"]["context"],
                        apikey_id=uuid.UUID(bidrequest["post"]["apikey_id"]),
                        time=datetime.fromisoformat(bidrequest["post"]["time"]),
                        resolved=bidrequest["post"]["resolved"],
                    )
                ) for bidrequest in bidrequests]

                status = []
                for bidrequest in bidrequests:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(bidrequest, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving bid request: {e}")
                        status.append(False)

                return status

            @self.mutation.field("forwardPaymentRequests")
            async def forward_paymentrequests(_, info, paymentrequests: list[dict[str, object]]) -> list[bool]:
                paymentrequests = [PaymentRequest(
                    actioncall_id=uuid.UUID(paymentrequest["actioncall_id"]),
                    post_id=uuid.UUID(paymentrequest["post_id"]),
                    payment_link=paymentrequest["payment_link"],
                ) for paymentrequest in paymentrequests]

                status = []
                for paymentrequest in paymentrequests:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(paymentrequest, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving payment request: {e}")
                        status.append(False)

                return status
            
            @self.mutation.field("forwardPAPaymentRequests")
            async def forward_paymentrequests(_, info, pa_paymentrequests: list[dict[str, object]]) -> list[bool]:
                paymentrequests = [PAPaymentRequest(
                    ui_id=pa_paymentrequest["ui_id"],
                    payment_link=pa_paymentrequest["payment_link"],
                ) for pa_paymentrequest in pa_paymentrequests]

                status = []
                for paymentrequest in paymentrequests:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(paymentrequest, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving payment request: {e}")
                        status.append(False)

                return status
            
            @self.mutation.field("forwardPALocationResponses")
            async def forward_locationresponses(_, info, pa_locationresponses: list[dict[str, object]]) -> list[bool]:
                locationresponses = [PALocationResponse(
                    ui_id=pa_locationresponse["ui_id"],
                    location=Location(
                        latitude=pa_locationresponse["location"]["latitude"],
                        longitude=pa_locationresponse["location"]["longitude"],
                    )
                ) for pa_locationresponse in pa_locationresponses]

                status = []
                for locationresponse in locationresponses:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(locationresponse, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving location response: {e}")
                        status.append(False)

                return status

            @self.mutation.field("forwardPALocationRequests")
            async def forward_locationrequests(_, info, pa_locationrequests: list[dict[str, object]]) -> list[bool]:
                locationrequests = [PALocationRequest(
                    ui_id=pa_locationrequest["ui_id"],
                ) for pa_locationrequest in pa_locationrequests]

                status = []
                for locationrequest in locationrequests:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(locationrequest, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving location request: {e}")
                        status.append(False)

                return status

            @self.mutation.field("forwardPAUserMessages")
            async def forward_usermessages(_, info, pa_usermessages: list[dict[str, object]]) -> list[bool]:
                usermessages = [PAUserMessage(
                    ui_id=pa_usermessage["ui_id"],
                    text=pa_usermessage["text"],
                ) for pa_usermessage in pa_usermessages]

                status = []
                for usermessage in usermessages:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(usermessage, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving user message: {e}")
                        status.append(False)

                return status
            
            @self.mutation.field("forwardPAUserResponses")
            async def forward_userresponses(_, info, pa_userresponses: list[dict[str, object]]) -> list[bool]:
                userresponses = [PAUserResponse(
                    ui_id=pa_userresponse["ui_id"],
                    text=pa_userresponse["text"],
                ) for pa_userresponse in pa_userresponses]

                status = []
                for userresponse in userresponses:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(userresponse, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving user response: {e}")
                        status.append(False)

                return status
            
            @self.mutation.field("forwardPANewConversations")
            async def forward_newconversations(_, info, pa_newconversations: list[dict[str, object]]) -> list[bool]:
                newconversations = [PANewConversation(
                    ui_id=pa_newconversation["ui_id"],
                ) for pa_newconversation in pa_newconversations]

                status = []
                for newconversation in newconversations:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(newconversation, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving new conversation: {e}")
                        status.append(False)

                return status
            
            @self.mutation.field("forwardPAUrls")
            async def forward_paurl(_, info, pa_urls: list[dict[str, object]]) -> list[bool]:
                urls = [PAUrl(
                    url=pa_url["url"],
                ) for pa_url in pa_urls]

                status = []
                for url in urls:
                    try:
                        asyncio.create_task(self.outer_class._resolve_event(url, info.context['apikey']))

                        status.append(True)
                    except Exception as e:
                        self.logger.error(f"Error resolving url: {e}")
                        status.append(False)

                return status

            self.AuthDirective.configure(logger=self.logger, fetch_all=self.outer_class.fetch_all)

            # Create the executable schema
            self.schema = make_executable_schema(self.outer_class._schema, self.query, self.mutation, self.datetime_scalar, self.json_scalar, directives={"auth": self.AuthDirective})

            self.graphql_app = GraphQL(
                self.schema, 
                debug=self.outer_class._debug,
            )

            async def health_check(request):
                return JSONResponse({"status": "ok"})

            self.routes=[
                Route("/graphql", self.graphql_app.handle_request, methods=["GET", "POST", "OPTIONS"]),
                Route("/healthz", health_check, methods=["GET"]),
            ]

            self.middleware = [
                Middleware(
                    TrustedHostMiddleware,
                    allowed_hosts=['maoto.world', '*.maoto.world', 'localhost', '*.svc.cluster.local', '*.amazonaws.com', '*.ngrok.app', '*.ngrok-free.app']
                ),
            ]

        def custom_format_error(error, debug=False):
            logging.exception(error)

            return {"message": "An unexpected error occurred, please contact support."}

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

    class GraphQLService:
        def __init__(self, outer_class, apikey_value: str):
            self._outer_class = outer_class
            self._apikey_value = apikey_value

        def _get_client(self, server_url: str) -> Client:
            transport = AIOHTTPTransport(
                url=server_url,
                headers={"Authorization": self._apikey_value, "Version": get_distribution("maoto_agent").version},
            )
            client = Client(
                transport=transport,
                fetch_schema_from_transport=False,  # Schema is already provided
                schema=self._outer_class._schema,  # Use the preloaded schema
            )
            return client
        
        async def send_without_connection(self, objects: list[object], server_url: str): 
            results = []
            for obj in objects:
                # get key from obj
                key = self._outer_class._map_obj_to_handler_in_registry[type(obj)]
                match key:
                    case "Actioncall":
                        value_name = "actioncalls"
                        query = gql_client('''
                            mutation forwardActioncalls($actioncalls: [Actioncall!]!) {
                                forwardActioncalls(actioncalls: $actioncalls)
                            }
                        ''')
                    case "Response":
                        value_name = "responses"
                        query = gql_client('''
                            mutation forwardResponses($responses: [Response!]!) {
                                forwardResponses(responses: $responses)
                            }
                        ''')
                    case "BidRequest":
                        value_name = "bidrequests"
                        query = gql_client('''
                            mutation forwardBidRequests($bidrequests: [BidRequest!]!) {
                                forwardBidRequests(bidrequests: $bidrequests)
                            }
                        ''')
                    case "PaymentRequest":
                        value_name = "paymentrequests"
                        query = gql_client('''
                            mutation forwardPaymentRequests($paymentrequests: [PaymentRequest!]!) {
                                forwardPaymentRequests(paymentrequests: $paymentrequests)
                            }
                        ''')
                    case "PALocationRequest":
                        value_name = "pa_locationrequests"
                        query = gql_client('''
                            mutation forwardPALocationRequests($pa_locationrequests: [PALocationRequest!]!) {
                                forwardPALocationRequests(pa_locationrequests: $pa_locationrequests)
                            }
                        ''')
                    case "PALocationResponse":
                        value_name = "pa_locationresponses"
                        query = gql_client('''
                            mutation forwardPALocationResponses($pa_locationresponses: [PALocationResponse!]!) {
                                forwardPALocationResponses(pa_locationresponses: $pa_locationresponses)
                            }
                        ''')
                    case "PAUserMessage":
                        value_name = "pa_usermessages"
                        query = gql_client('''
                            mutation forwardPAUserMessages($pa_usermessages: [PAUserMessage!]!) {
                                forwardPAUserMessages(pa_usermessages: $pa_usermessages)
                            }
                        ''')
                    case "PAUserResponse":
                        value_name = "pa_userresponses"
                        query = gql_client('''
                            mutation forwardPAUserResponses($pa_userresponses: [PAUserResponse!]!) {
                                forwardPAUserResponses(pa_userresponses: $pa_userresponses)
                            }
                        ''')
                    case "PAPaymentRequest":
                        value_name = "pa_paymentrequests"
                        query = gql_client('''
                            mutation forwardPAPaymentRequests($pa_paymentrequests: [PAPaymentRequest!]!) {
                                forwardPAPaymentRequests(pa_paymentrequests: $pa_paymentrequests)
                            }
                        ''')
                    case "PANewConversation":
                        value_name = "pa_newconversations"
                        query = gql_client('''
                            mutation forwardPANewConversations($pa_newconversations: [PANewConversation!]!) {
                                forwardPANewConversations(pa_newconversations: $pa_newconversations)
                            }
                        ''')
                    case "PAUrl":
                        value_name = "pa_urls"
                        query = gql_client('''
                            mutation forwardPAUrls($pa_urls: [PAUrl!]!) {
                                forwardPAUrls(pa_urls: $pa_urls)
                            }
                        ''')
                    case _:  # Fallback
                        raise ValueError(f"Invalid key: {key}")
                
                graphql_client = self._get_client(server_url)
                result = await graphql_client.execute_async(query, variable_values={value_name: [obj.to_dict()]})
                results.append(result)

            return results

    def __init__(self, logging_level=None, connection_mode: str = "nat", db_connection=False):
        # Set up logging and debug mode
        self._debug = os.getenv("DEBUG", "False").lower() == "true" or os.getenv("MAOTO_DEBUG", "False").lower() == "true"
        # Set up logging
        self._logging_level = logging_level if logging_level else logging.DEBUG if self._debug else logging.INFO
        logging.basicConfig(level=self._logging_level, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        # Disable INFO logs for gql and websockets
        logging.getLogger("gql").setLevel(logging.DEBUG if self._debug else logging.WARNING)
        logging.getLogger("websockets").setLevel(logging.DEBUG if self._debug else logging.WARNING)

        self._db_connection = db_connection
        self._db_connection_pool = None
        if self._db_connection:
            # Environment variables for database connection
            self._db_hostname = os.getenv("POSTGRES_HOST")
            self._db_name = os.getenv("POSTGRES_DB")
            self._db_username = os.getenv("POSTGRES_USER")
            self._db_user_password = os.getenv("POSTGRES_PASSWORD")
            self._db_port = os.getenv("POSTGRES_PORT")

            # Validate that all required env variables are set
            if not all([self._db_hostname, self._db_name, self._db_username, self._db_user_password, self._db_port]):
                raise EnvironmentError(
                    "POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_PORT must be set"
                )

            # Construct the PostgreSQL connection URL
            self._database_url = (
                f"postgresql+asyncpg://{self._db_username}:{self._db_user_password}"
                f"@{self._db_hostname}:{self._db_port}/{self._db_name}"
            )

            # Create a connection pool
            self._db_connection_pool = databases.Database(self._database_url)

        self._schema = gql_server("""
            directive @auth on FIELD_DEFINITION

            scalar Datetime
            scalar JSON
                                    
            input Actioncall {
                actioncall_id: ID!
                action_id: ID!
                post_id: ID!
                apikey_id: ID!
                parameters: JSON
                time: Datetime!
            }
                                    
            input Response {
                response_id: ID!
                post_id: ID!
                description: String!
                apikey_id: ID
                time: Datetime!
            }
                                    
            input Post {
                post_id: ID!
                description: String!
                context: String!
                apikey_id: ID!
                time: Datetime!
                resolved: Boolean!
            }
                                    
            input BidRequest {
                action_id: ID
                post: Post
            }
            
            input PaymentRequest {
                actioncall_id: ID
                post_id: ID
                payment_link: String
            }
                                    
            input Location {
                latitude: Float
                longitude: Float
            }
                                    
            input PALocationRequest {
                ui_id: String
            }
                                    
            input PALocationResponse {
                ui_id: String
                location: Location
            }
                                    
            input PAUserMessage {
                ui_id: String
                text: String
            }
                                  
            input PAUserResponse {
                ui_id: String
                text: String
            }
                                    
            input PAPaymentRequest {
                ui_id: String
                payment_link: String
            }
                                  
            input PANewConversation {
                ui_id: String
            }
                                  
            input PAUrl {
                url: String                
            }
                                    
            type Query {
                _dummy: String
            }

            type Mutation {
                forwardActioncalls(actioncalls: [Actioncall!]!): [Boolean!]! @auth
                forwardResponses(responses: [Response!]!): [Boolean!]! @auth
                forwardBidRequests(bidrequests: [BidRequest!]!): [Boolean!]! @auth
                forwardPaymentRequests(paymentrequests: [PaymentRequest!]!): [Boolean!]! @auth
                                    
                forwardPALocationResponses(pa_locationresponses: [PALocationResponse!]!): [Boolean!]! @auth
                forwardPALocationRequests(pa_locationrequests: [PALocationRequest!]!): [Boolean!]! @auth
                forwardPAUserMessages(pa_usermessages: [PAUserMessage!]!): [Boolean!]! @auth
                forwardPAUserResponses(pa_userresponses: [PAUserResponse!]!): [Boolean!]! @auth
                forwardPAPaymentRequests(pa_paymentrequests: [PAPaymentRequest!]!): [Boolean!]! @auth
                forwardPANewConversations(pa_newconversations: [PANewConversation!]!): [Boolean!]! @auth 
                forwardPAUrls(pa_urls: [PAUrl!]!): [Boolean!]! @auth          
            }
            """)
        
        self.domain_mp = os.environ.get("DOMAIN_MP", "mp.maoto.world")
        self.domain_pa = os.environ.get("DOMAIN_PA", "pa.maoto.world")

        self._protocol = os.environ.get("SERVER_PROTOCOL", "http")
        self._port_mp = os.environ.get("PORT_MP") if os.environ.get("PORT_MP") else "4000"
        self._port_pa = os.environ.get("PORT_PA") if os.environ.get("PORT_PA") else "4000"

        self._url_mp = self._protocol + "://" + self.domain_mp + ":" + self._port_mp + "/graphql"
        self._url_pa = self._protocol + "://" + self.domain_pa + ":" + self._port_pa + "/graphql"

        self._url_marketplace_subscription = self._url_mp.replace(self._protocol, "ws")
        
        self._apikey_value = os.environ.get("MAOTO_API_KEY")
        if self._apikey_value in [None, ""]:
            raise ValueError("API key is required. (Set MAOTO_API_KEY environment variable)")


        self._action_cache = []
        self._id_action_map = {}

        self._map_obj_to_handler_in_registry = {
            Response: "Response",
            Actioncall: "Actioncall",
            BidRequest: "BidRequest",
            PaymentRequest: "PaymentRequest",

            PAPaymentRequest: "PAPaymentRequest",
            PALocationRequest: "PALocationRequest",
            PAUserMessage: "PAUserMessage",

            PALocationResponse: "PALocationResponse",
            PAUserResponse: "PAUserResponse",
            PANewConversation: "PANewConversation",
            PAUrl: "PAUrl",
        }

        self._handler_registry = {
            "CustomStartup": None,
            "CustomShutdown": None,

            "Response": None,
            "Actioncall": {},
            "Actioncall_fallback": None,
            "PaymentRequest": None,
            "BidRequest": {},
            "BidRequest_fallback": None,

            "PAPaymentRequest": None,
            "PALocationResponse": None,
            "PALocationRequest": None,
            "PAUserMessage": None,
            "PAUserResponse": None,
            "PANewConversation": None,
            "PAUrl": None,
        }

        self._connection_mode = connection_mode
        if self._connection_mode not in ["marketplace", "no_nat", "nat", "closed"]:
            raise ValueError("Invalid connection mode.")
        
        # CLient to send messages to ui and personal assistant
        self._graphql_service = self.GraphQLService(self, self._apikey_value)

        # to send messages to marketplace
        if self._connection_mode != "closed":
            transport = AIOHTTPTransport(
                url=self._url_mp,
                headers={"Authorization": self._apikey_value},
            )
            self.client = Client(transport=transport, fetch_schema_from_transport=True)

        if self._connection_mode == "nat":
            self.server = self.EventDrivenQueueProcessor(self.logger, worker_count=1, scale_threshold=10, outer_class=self)
        if self._connection_mode == "no_nat":
            self.server = self.ServerMode(self.logger, self)

    def start_server(self, blocking=False) -> Starlette | None:
        if self._connection_mode == "closed":
            raise self.logger.warning("Cannot start server when mode is set closed.")
        
        elif self._connection_mode == "nat":
            self.server.run(self._subscribe_to_events, self._resolve_event)
            
            if blocking:
                def handler(signum, frame):
                    self.logger.info("Stopped by Ctrl+C")
                    sys.exit(0)

                # Assign the SIGINT (Ctrl+C) signal to the handler
                signal.signal(signal.SIGINT, handler)

                self.logger.info("Running... Press Ctrl+C to stop.")
                signal.pause()  # Blocks here until a signal (Ctrl+C) is received
    
            return None
        elif self._connection_mode == "no_nat":
            return self.server.start_server()
        else:
            raise ValueError("Invalid connection mode.")

    async def _at_startup(self):
        if self._db_connection:
            await self._startup_db_conn_pool()

        if self._handler_registry["CustomStartup"]:
            await self._handler_registry["CustomStartup"]()

    async def _at_shutdown(self):
        if self._db_connection:
            await self._shutdown_db_conn_pool()

        if self._handler_registry["CustomShutdown"]:
            await self._handler_registry["CustomShutdown"]()

    async def _startup_db_conn_pool(self):
        """Establish a database connection with automatic reconnection."""
        retries = 5
        while retries:
            try:
                await self._db_connection_pool.connect()
                self.logger.info("Connected to the database!")
                break
            except asyncpg.exceptions.ConnectionDoesNotExistError:
                self.logger.warning(f"Database connection failed. Retrying in 5 seconds... ({retries} attempts left)")
                retries -= 1
                await asyncio.sleep(5)

        if not retries:
            raise RuntimeError("Failed to establish a database connection after multiple attempts.")

    async def _shutdown_db_conn_pool(self):
        """Disconnect from the database."""
        if self._db_connection_pool:
            await self._db_connection_pool.disconnect()
            self.logger.info("Disconnected from the database.")

    async def fetch_all(self, query, values=None):
        """Fetch multiple records from the database."""
        try:
            return await self._db_connection_pool.fetch_all(query=query, values=values)
        except asyncpg.exceptions.PostgresError as e:
            self.logger.error("Database error: %s", e)
            raise GraphQLError("Database error occurred.")

    async def execute(self, query, values=None):
        """Execute an INSERT, UPDATE, or DELETE statement."""
        try:
            return await self._db_connection_pool.execute(query=query, values=values)
        except asyncpg.exceptions.PostgresError as e:
            self.logger.error("Database execution error: %s", e)
            raise GraphQLError("Database execution error.")
    
    @asynccontextmanager
    async def transaction(self):
        """
        Return an async context manager so that
        `async with agent.transaction(): ...` works.
        """
        async with self._db_connection_pool.transaction():
            # You can do any setup here if needed
            yield
            # teardown or exception handling automatically

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

    async def _create_actions_core(self, new_actions: list[NewAction]) -> list[Action]: # TODO: confirm this the first time when agent is started as well (not only when reconnecting)
        if new_actions:
            actions = [{'name': action.get_name(), 'parameters': action.get_parameters(), 'description': action.get_description(), 'tags': action.get_tags(), 'cost': action.get_cost(), 'followup': action.get_followup()} for action in new_actions]
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
            self._id_action_map.update({data["action_id"]: data["name"] for data in data_list})

            actions = [Action(
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

            self.logger.info(f"Successfully created {len(actions)} actions.")
            
        else:
            actions = []

        return actions

    @_sync_or_async
    async def create_actions(self, new_actions: list[NewAction]) -> list[Action]:
        self._action_cache.extend(new_actions)

        actions = await self._create_actions_core(new_actions)

        return actions

    @_sync_or_async
    async def delete_actions(self, action_ids: list[Action | str]) -> list[bool]: #TODO: this should not actually delete but deactivate only
        action_ids = [str(action.get_action_id()) if isinstance(action, Action) else str(action) for action in action_ids]
        query = gql_client('''
        mutation deleteActions($action_ids: [ID!]!) {
            deleteActions(action_ids: $action_ids)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"action_ids": action_ids})

        # remove the respecitive actions from the cache
        self._action_cache = [action for action in self._action_cache if action.get_action_id() not in action_ids]

        return result["deleteActions"]
    
    @_sync_or_async
    async def refund_payment(self, actioncall_id: uuid.UUID) -> bool:
        query = gql_client('''
        mutation refundPayment($actioncall_id: ID!) {
            refundPayment(actioncall_id: $actioncall_id)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"actioncall_id": str(actioncall_id)})
        return result["refundPayment"]
    
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
    async def fetch_action_info(self, new_posts: list[NewPost]) -> list[str]:
        posts = [{'description': post.get_description(), 'context': post.get_context()} for post in new_posts]
        query = gql_client('''
        query fetchActionInfo($new_posts: [NewPost!]!) {
            fetchActionInfo(new_posts: $new_posts)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"new_posts": posts})
        return result["fetchActionInfo"]

    @_sync_or_async
    async def create_posts(self, new_posts: list[NewPost]) -> list[Post]:
        posts = [{'description': post.get_description(), 'context': post.get_context()} for post in new_posts]
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

        try:
            result = await self.client.execute_async(query, variable_values={"new_posts": posts})
        except Exception as e:
            self.logger.error(f"Error creating posts: {e}")
            GraphQLError(f"Error creating posts: {e}")
            
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
    async def delete_posts(self, post_ids: list[Post | str]) -> list[bool]: # TODO: only make this deactivate instead of delete (mark as done)
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
        data_list = await self.client.execute_async(query, variable_values={"bidresponses": bidresponses}
        )

        # 'createBidResponses' is already a list of booleans, so just return it.
        return data_list['createBidResponses']
    
    @_sync_or_async
    async def add_url_to_apikey(self, urls: list[Url]) -> list[bool]:
        urls = [{'url': url.get_url()} for url in urls]
        query = gql_client('''
        mutation addUrlToApikey($urls: [Url!]!) {
            addUrlToApikey(urls: $urls)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"urls": urls})
        return result["addUrlToApikey"]

    @_sync_or_async
    async def set_webhook(self):
        await self.add_url_to_apikey([PAUrl(os.getenv("MAOTO_AGENT_URL"))]) # TODO: change this to be normal webhook once the normal webhook goes to marketplace only (shared database) and assistant shares the same database

    # only used for open connection server
    async def _subscribe_to_events(self, task_queue, stop_event):
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
                ... on PaymentRequest {
                    actioncall_id
                    post_id
                    payment_link
                }
            }
        }
        ''')

        # A helper to stop the subscription task when stop_event is triggered
        async def monitor_stop_event(subscription_task):
            while not stop_event.is_set():
                await asyncio.sleep(1)
            subscription_task.cancel()

        # Create a task to monitor for stop_event in parallel
        subscription_task = asyncio.create_task(
            self._run_subscription_with_reconnect(task_queue, subscription, stop_event)
        )
        stop_monitoring_task = asyncio.create_task(
            monitor_stop_event(subscription_task)
        )

        try:
            await subscription_task
        except asyncio.CancelledError:
            self.logger.info("Subscription was cancelled")
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {e}")
        finally:
            stop_monitoring_task.cancel()

    async def _run_subscription_with_reconnect(self, task_queue, subscription, stop_event):
        """
        This method continuously attempts to subscribe. If the subscription breaks,
        it retries (unless stop_event is set), using randomized exponential backoff.
        """
        base_delay = 6  # Initial delay in seconds
        max_delay = 60  # Max delay before retrying
        attempt = 0     # Track the number of consecutive failures
        reconnect = False

        while not stop_event.is_set():
            try:

                # Create transport for each attempt
                transport = WebsocketsTransport(
                    url=self._url_marketplace_subscription,
                    headers={"Authorization": self._apikey_value},
                )

                # Open a session and subscribe
                async with Client(
                    transport=transport,
                    fetch_schema_from_transport=True
                ) as session:
                    self.logger.info("Successfully connected. Listening for events.")
                    attempt = 0  # Reset attempt count on successful connection

                    if reconnect:
                        try:
                            actions = await self._create_actions_core(self._action_cache)
                        except Exception as e:
                            self.logger.info(f"Error recreating actions.")

                    reconnect = True # Set reconnect flag to True if reconnected

                    async for result in session.subscribe(subscription):
                        # Process the subscription event
                        await self._handle_subscription_event(task_queue, result)

            except asyncio.CancelledError:
                self.logger.warning("Subscription task cancelled. This error is only shown when the task is cancelled inproperly.")
                break
            except Exception as e:
                self.logger.warning(f"Subscription interrupted. Will attempt to reconnect.")

            # Calculate exponential backoff with jitter
            if not stop_event.is_set():
                delay = min(base_delay * (2 ** attempt), max_delay)  # Exponential growth
                jitter = random.uniform(0.5, 1.5)  # Random jitter multiplier (±50%)
                delay *= jitter  # Apply jitter

                self.logger.info(f"Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
                attempt += 1  # Increase attempt count for next retry

        self.logger.info("Stopped subscription due to stop_event or cancellation.")

    async def _handle_subscription_event(self, task_queue, result):
        """
        Handle the result of the subscription. Identify the
        event type via __typename, instantiate the corresponding
        event object, and put it on the queue.
        """
        event_data = result['subscribeToEvents']
        event_type = event_data["__typename"]

        if event_type == "Actioncall":
            event = Actioncall( #  TODO: make these class inits use class methods (from dict?)
                actioncall_id=uuid.UUID(event_data["actioncall_id"]),
                action_id=uuid.UUID(event_data["action_id"]),
                post_id=uuid.UUID(event_data["post_id"]),
                apikey_id=uuid.UUID(event_data["apikey_id"]),
                parameters=event_data["parameters"],
                time=datetime.fromisoformat(event_data["time"])
            )
        elif event_type == "Response":
            event = Response(
                response_id=uuid.UUID(event_data["response_id"]),
                post_id=uuid.UUID(event_data["post_id"]),
                description=event_data["description"],
                apikey_id=uuid.UUID(event_data["apikey_id"]) if event_data["apikey_id"] else None,
                time=datetime.fromisoformat(event_data["time"])
            )
        elif event_type == "BidRequest":
            post_data = event_data["post"]
            post = Post(
                post_id=uuid.UUID(post_data["post_id"]),
                description=post_data["description"],
                context=post_data["context"],
                apikey_id=uuid.UUID(post_data["apikey_id"]),
                time=datetime.fromisoformat(post_data["time"]),
                resolved=post_data["resolved"]
            )
            event = BidRequest(
                action_id=uuid.UUID(event_data["action_id"]),
                post=post
            )
        elif event_type == "PaymentRequest":
            event = PaymentRequest(
                actioncall_id=uuid.UUID(event_data["actioncall_id"]),
                post_id=uuid.UUID(event_data["post_id"]),
                payment_link=event_data["payment_link"]
            )
        else:
            self.logger.error(f"Unknown event type: {event_type}")
            return

        # Put the event on the queue for handling in your system
        task_queue.put(event)

    def register_handler(self, event_type: str, name: str | None = None):
        def decorator(func):
            # python case (new version) statement here
            if name is not None:
                self._handler_registry[event_type][name] = func
            else:
                self._handler_registry[event_type] = func
            return func
        return decorator

    async def _resolve_event(self, obj: object, apikey: ApiKey | None = None):
        # get handler registry key for the object
        handler_registry_key = self._map_obj_to_handler_in_registry[type(obj)]

        # get handler from registry
        try:
            if handler_registry_key in ["Actioncall", "BidRequest"]:
                try:
                    handler = self._handler_registry[handler_registry_key][self._id_action_map[str(obj.get_action_id())]]
                except KeyError:
                    handler = self._handler_registry[f"{handler_registry_key}_fallback"]
                
                if handler_registry_key == "Actioncall":
                    response_description = await handler(obj)
                    new_response = NewResponse(
                        post_id=obj.get_post_id(),
                        description=response_description
                    )
                    await self.create_responses([new_response])

                elif handler_registry_key == "BidRequest":
                    bid_value = await handler(obj.get_post())
                    new_bid = BidResponse(
                        action_id=obj.get_action_id(),
                        post_id=obj.get_post().get_post_id(),
                        cost=bid_value
                    )
                    await self.create_bidresponses([new_bid])

            else:
                handler = self._handler_registry[handler_registry_key]
                if handler_registry_key in ["PAUserMessage", "PAPaymentRequest", "PALocationRequest"]:
                    await handler(obj)
                else:
                    await handler(obj, apikey)
        except KeyError:
            self.logger.error(f"No handler found for {handler_registry_key}")
            return
        
    async def send_to_assistant(self, objects: list[object]):
        await self._graphql_service.send_without_connection(objects, self._url_pa)

    @_sync_or_async
    async def _set_webhook_pa(self, url: str | None = None):
        try:
            LOCK_FILE = "/tmp/maoto_webhook.lock"
            with open(LOCK_FILE, "w") as lockfile: # Check if the process is the first process (otherwise if every worker runs this, telegram complains for too many requests)
                try:
                    # Try to get an exclusive lock (fails if another process holds it)
                    fcntl.flock(lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)

                    # If we acquired the lock, register the webhook
                    new_url = url if url else os.getenv("MAOTO_AGENT_URL")
                    await self.send_to_assistant([PAUrl(new_url)])
                    self.logger.info(f"Process {os.getpid()} registered maoto webhook url: {os.getenv('MAOTO_AGENT_URL')}")

                except BlockingIOError:
                    # Another process is holding the lock, so we skip registration
                    self.logger.info(f"Process {os.getpid()} skipped registration (another process is handling it).")
        except Exception as e:
            self.logger.error(f"Error registering webhook (following). Did you start multiple containers at once? (in that case you should only do the webhook registration once by locking it using redis database. {e}")
