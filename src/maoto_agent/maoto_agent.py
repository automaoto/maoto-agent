import inspect
import os
import sys
import json
import time
import queue
import signal
import uuid
import atexit
from typing import Callable
import psutil
import logging
import random
import asyncio
import functools
import threading
from .app_types import *
from datetime import datetime
from gql import gql as gql_client
from gql import Client
from pkg_resources import get_distribution
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport

# Server Mode:
import importlib.resources
from graphql import GraphQLError, FieldDefinitionNode
from dateutil import parser
from ariadne import gql as gql_server
from ariadne import make_executable_schema, QueryType, MutationType, SchemaDirectiveVisitor, ScalarType, SubscriptionType, upload_scalar, UnionType
from ariadne.asgi import GraphQL

DATA_CHUNK_SIZE = 1024 * 1024  # 1 MB in bytes

class Maoto:
    class EventDrivenQueueProcessor:
        def __init__(self, logger: logging.Logger, worker_count=10, min_workers=1, max_workers=20, scale_threshold=5, scale_down_delay=30):
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

            self.start_workers(worker_func, self.initial_worker_count)
            self.start_producer(lambda task_queue, stop_event: producer_func(task_queue, stop_event))

            self.monitor_thread = threading.Thread(target=self.monitor_system, args=(worker_func,))
            self.monitor_thread.daemon = True
            self.monitor_thread.start()

    class ServerMode:
        class AuthDirective(SchemaDirectiveVisitor):
            def visit_field_definition(self, field: FieldDefinitionNode, _) -> FieldDefinitionNode:
                original_resolver = field.resolve

                async def resolve_auth(root, info, **kwargs):
                    """Authenticate and authorize API key."""
                    
                    request = info.context["request"]
                    value = request.headers.get("Authorization")

                    if not value:
                        raise GraphQLError("Authentication failed. No API key provided.")
                    # random uuid
                    random_uuid = uuid.uuid4()
                    if value in ["marketplace_apikey_value", "assistant_apikey_value"]:
                        info.context['apikey'] = ApiKey(
                            id=uuid.uuid4(),
                            time=datetime.now(),
                            user_id=uuid.uuid4(),
                            name=value,
                            roles=[],
                            url=None,
                        )
                    else:
                        raise GraphQLError("Wrong apikey value.")

                    return await original_resolver(root, info, **kwargs)

                field.resolve = resolve_auth
                return field
            
        def __init__(self, logger: logging.Logger, resolver: Callable[[object], None], debug: bool):
            self.logger, self.resolver, self.debug = logger, resolver, debug
            
            self.query, self.mutation = QueryType(), MutationType()
            self.scalars = [
                ScalarType(name, serializer=serializer, value_parser=parser_)
                for name, (serializer, parser_) in {
                    "Datetime": (lambda v: v.isoformat(), lambda v: parser.parse(v)),
                    "DICTSTR": (json.dumps, json.loads),
                    "UUID": (str, uuid.UUID),
                }.items()
            ]

            mutation_mappings = {
                "callOffer": OfferCall,
                "requestCallableOfferCost": OfferCallableCostRequest,
                "requestReferenceOfferCost": OfferReferenceCostRequest,
                "requestOffers": OfferRequest,
                "forwardResponse": Response,
                "forwardPaymentRequest": PaymentRequest,
                "forwardLinkConfirmation": LinkConfirmation,
                "forwardPAPaymentRequest": PAPaymentRequest,
                "forwardPALocationRequest": PALocationRequest,
                "forwardPAUserMessage": PAUserMessage,
                "forwardPALinkUrl": PALinkUrl,
            }

            for field_name, model_class in mutation_mappings.items():
                @self.mutation.field(field_name)
                async def resolver(_, info, input: dict[str, object], model_class=model_class):
                    instance = model_class(**input)
                    asyncio.create_task(self.resolver(instance))
                    return True
                
            schema_str = (importlib.resources.files(__package__) / "agent.graphql").read_text()
            self.executable_schema = make_executable_schema(
                schema_str, [self.query, self.mutation] + self.scalars,
                directives={"auth": self.AuthDirective}
            )

            self.graphql_app = GraphQL(
                self.executable_schema, 
                debug=self.debug,
            )

    class GraphQLService:
        def __init__(self, url: str, apikey_value: str, schema = None, version: str = "undefined"):
            self._url, self._apikey_value, self._schema, self._version = url, apikey_value, schema, version

        def _get_client(self, server_url: str) -> Client:
            transport = AIOHTTPTransport(
                ssl=True,
                url=server_url,
                headers={"Authorization": self._apikey_value, "Version": self._version},
            )
            client = Client(
                transport=transport,
                fetch_schema_from_transport=False,
                schema=self._schema,
            )
            return client
        
        async def execute_async(self, query, variable_values=None):
            gql_client = self._get_client(self._url)
            return await gql_client.execute_async(query, variable_values=variable_values)

    def __init__(self, logging_level=None, assistant=True, marketplace=True, apikey_value: str | None = None):
        self._apikey = None
        
        # Set up logging and debug mode
        self._debug = os.getenv("DEBUG", "False").lower() == "true" or os.getenv("MAOTO_DEBUG", "False").lower() == "true"
        # Set up logging
        self._logging_level = logging_level if logging_level else logging.DEBUG if self._debug else logging.INFO
        logging.basicConfig(level=self._logging_level, format="%(asctime)s - %(levelname)s - %(message)s")
        self.logger = logging.getLogger(__name__)
        # Disable INFO logs for gql and websockets
        logging.getLogger("gql").setLevel(logging.DEBUG if self._debug else logging.WARNING)
        logging.getLogger("websockets").setLevel(logging.DEBUG if self._debug else logging.WARNING)
        
        self._domain_mp = os.environ.get("DOMAIN_MP", "mp.maoto.world")
        self._domain_pa = os.environ.get("DOMAIN_PA", "pa.maoto.world")

        self._use_ssl = os.environ.get("USE_SSL", "true").lower() == "true"
        self._protocol = "https" if self._use_ssl else "http"
        self._port_mp = os.environ.get("PORT_MP", "443" if self._use_ssl else "80")
        self._port_pa = os.environ.get("PORT_PA", "443" if self._use_ssl else "80")

        self._url_mp = self._protocol + "://" + self._domain_mp + ":" + self._port_mp + "/graphql"
        self._url_pa = self._protocol + "://" + self._domain_pa + ":" + self._port_pa + "/graphql"

        self._protocol_websocket = "wss" if self._use_ssl else "ws"
        self._url_marketplace_subscription = self._url_mp.replace(self._protocol, self._protocol_websocket)
        
        self._apikey_value = apikey_value or os.environ.get("MAOTO_API_KEY")
        if not self._apikey_value:
            raise ValueError("API key is required.")

        self._handler_registry = dict()

        if assistant:
            self._graphql_service_assistant = self.GraphQLService(url=self._url_pa, apikey_value=self._apikey_value, version=get_distribution("maoto_agent").version)

        if marketplace:
            self._graphql_service_marketplace = self.GraphQLService(url=self._url_mp, apikey_value=self._apikey_value, version=get_distribution("maoto_agent").version)

        self._server = self.ServerMode(self.logger, self._resolve_event, self._debug)
        self.handle_request = self._server.graphql_app.handle_request

    async def _resolve_event(self, event_obj: object):
        event = type(event_obj)
        if event in self._handler_registry:
            self._handler_registry[event](event_obj)
        else:
            self.logger.warning(f"No handler registered for event type {event}")

    def start_polling(self, blocking=True):
        """
        Start the event-driven polling process.

        Parameters
        ----------
        blocking : bool, optional
            If True, blocks the main thread and waits for a termination signal (Ctrl+C). Default is True.

        Notes
        -----
        When `blocking` is enabled, this method will not return until interrupted.
        Useful for running long-lived agents or services.
        """

        self.polling = self.EventDrivenQueueProcessor(self.logger, worker_count=1, scale_threshold=10)
        self.polling.run(self._subscribe_to_events, self._resolve_event)
            
        if blocking:
            def handler(signum, frame):
                self.logger.info("Stopped by Ctrl+C")
                sys.exit(0)

            # Assign the SIGINT (Ctrl+C) signal to the handler
            signal.signal(signal.SIGINT, handler)

            self.logger.info("Running... Press Ctrl+C to stop.")
            signal.pause()  # Blocks here until a signal (Ctrl+C) is received
    
    async def _get_own_api_key(self) -> ApiKey:
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

        result = await self._graphql_service_marketplace.execute_async(query)
        data_list = result["getOwnApiKeys"]

        # Return the first API key (assume the list is ordered by time or relevance)
        if data_list:
            data = data_list[0]
            return ApiKey(**data)
        else:
            raise Exception("No API keys found for the user.")

    
    async def get_own_api_key(self) -> ApiKey:
        """
        Retrieve and cache the current API key.

        Returns
        -------
        ApiKey
            The API key associated with this agent instance.
        """
        if not self._apikey:
            self._apikey = await self._get_own_api_key()
        return self._apikey

    
    async def check_status_marketplace(self) -> bool:
        """
        Check if the Marketplace service is available.

        Returns
        -------
        bool
            True if the Marketplace is operational, False otherwise.
        """
        query = gql_client('''
        query {
            checkStatus
        }
        ''')
        result = await self._graphql_service_marketplace.execute_async(query)
        return result["checkStatus"]

    
    async def check_status_assistant(self) -> bool:
        """
        Check if the Assistant service is available.

        Returns
        -------
        bool
            True if the Assistant is operational, False otherwise.
        """
        query = gql_client('''
        query {
            checkStatus
        }
        ''')
        result = await self._graphql_service_assistant.execute_async(query)
        return result["checkStatus"]

    async def send_intent(self, obj: NewIntent) -> None:
        """
        Create a new Intent.

        Parameters
        ----------
        obj : NewIntent
            The Intent object to create.
        """
        query = gql_client('''
        mutation createIntent($input: NewIntent!) {
            createIntent(input: $input)
        }
        ''')
        await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
    
    async def unregister(self, obj: Skill | OfferCallable | OfferReference | None = None, obj_type: type | None = None, id: uuid.UUID | None = None, solver_id: type | None = None) -> bool:
        """
        Unregister an existing Skill, OfferCallable, or OfferReference from the Marketplace.

        Parameters
        ----------
        obj : Skill or OfferCallable or OfferReference or None, optional
            The object to unregister.
        obj_type : type, optional
            The type of the object if `obj` is not provided.
        id : uuid.UUID, optional
            The ID of the object to unregister.
        solver_id : type, optional
            The solver ID, used if `id` is not provided.

        Returns
        -------
        bool
            True if the object was successfully unregistered.

        Raises
        ------
        ValueError
            If required parameters are missing or the object type is unsupported.
        """
        if obj:
            obj_type, obj_id = type(obj), obj.id
        elif obj_type and (id or solver_id):
            obj_id = id or solver_id
        else:
            raise ValueError("Either obj or obj_type and id/solver_id must be provided.")
        
        if obj_type == Skill:
            query = gql_client('''
                mutation unregisterSkill($skill_id: ID!) {
                    unregisterSkill(skill_id: $skill_id)
                }
            ''')
            variable_values = {"skill_id": str(obj_id)}
            result = await self._graphql_service_marketplace.execute_async(query, variable_values=variable_values)
            return result["unregisterSkill"]
        
        elif obj_type == OfferCallable:
                query = gql_client('''
                    mutation unregisterOfferCallable($offercallable_id: ID!) {
                        unregisterOfferCallable(offercallable_id: $offercallable_id)
                    }
                ''')
                variable_values = {"offercallable_id": str(obj_id)}
                result = await self._graphql_service_marketplace.execute_async(query, variable_values=variable_values)
                return result["unregisterOfferCallable"]
        
        elif obj_type == OfferReference:
            query = gql_client('''
                mutation unregisterOfferReference($offerreference_id: ID!) {
                    unregisterOfferReference(offerreference_id: $offerreference_id)
                }
            ''')
            variable_values = {"offerreference_id": str(obj_id)}
            result = await self._graphql_service_marketplace.execute_async(query, variable_values=variable_values)
            return result["unregisterOfferReference"]
        
        else:
            raise ValueError(f"Object type {obj_type} not supported.")
    
    
    async def send_response(self, obj: NewOfferCallResponse | OfferResponse | NewOfferCallableCostResponse | NewOfferReferenceCostResponse) -> bool:
        """
        Send a response object to the Marketplace.

        Parameters
        ----------
        obj : NewOfferCallResponse or OfferResponse or NewOfferCallableCostResponse or NewOfferReferenceCostResponse
            The response object to send.

        Returns
        -------
        bool
            True if the response was successfully sent.

        Raises
        ------
        ValueError
            If the object type is unsupported.
        """
        if isinstance(obj, NewOfferCallResponse):
            query = gql_client('''
            mutation sendOfferCallResponse($input: OfferCallResponse!) {
                sendOfferCallResponse(input: $input)
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
            return result["sendOfferCallResponse"]

        if isinstance(obj, OfferResponse):
            query = gql_client('''
            mutation sendOfferResponse($input: OfferResponse!) {
                sendOfferResponse(input: $input)
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
            return result["sendOfferResponse"]
        
        elif isinstance(obj, NewOfferCallableCostResponse):
            query = gql_client('''
            mutation sendNewOfferCallableCostResponse($input: NewOfferCallableCostResponse!) {
                sendNewOfferCallableCostResponse(input: $input)
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
            return result["sendOfferCallableCostResponse"]

        elif isinstance(obj, NewOfferReferenceCostResponse):
            query = gql_client('''
            mutation sendNewOfferReferenceCostResponse($input: NewOfferReferenceCostResponse!) {
                sendNewOfferReferenceCostResponse(input: $input)
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
            return result["sendOfferReferenceCostResponse"]
        
        else:
            raise ValueError(f"Object type {type(obj)} not supported.")

    
    async def register(self, obj: NewSkill | NewOfferCallable | NewOfferReference) -> bool:
        """
        Register a new Skill, OfferCallable, or OfferReference with the Marketplace.

        Parameters
        ----------
        obj : NewSkill or NewOfferCallable or NewOfferReference
            The object to register.

        Returns
        -------
        bool
            True if the object was successfully registered.
        """
        if isinstance(obj, NewSkill):
            query = gql_client('''
            mutation registerSkill($input: NewSkill!) {
                registerSkill(input: $input)
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
            return result["registerSkill"]
        
        elif isinstance(obj, NewOfferCallable):
            query = gql_client('''
            mutation registerOfferCallable($input: NewOfferCallable!) {
                registerOfferCallable(input: $input)
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
            return result["registerOfferCallable"]
        
        elif isinstance(obj, NewOfferReference):
            query = gql_client('''
            mutation registerOfferReference($input: NewOfferReference!) {
                registerOfferReference(input: $input)
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
            return result["registerOfferReference"]
    
    
    async def get_registered(self, obj_type: type) -> list[Skill | OfferCallable | OfferReference]:
        """
        Retrieve registered objects of a specified type from the Marketplace.

        Parameters
        ----------
        obj_type : type
            The type of object to retrieve. Must be one of: Skill, OfferCallable, or OfferReference.

        Returns
        -------
        list of Skill or OfferCallable or OfferReference
            A list of registered objects of the specified type.

        Raises
        ------
        ValueError
            If the provided type is not supported.
        """
        if obj_type == Skill:
            query = gql_client('''
            query {
                getSkills {
                    id
                    time
                    description
                    tags
                }
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query)
            return [Skill(**data) for data in result["getSkills"]]
        
        elif obj_type == OfferCallable:
            query = gql_client('''
            query {
                getOfferCallables {
                    id
                    time
                    parameters
                    description
                    tags
                    followup
                    cost
                }
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query)
            return [OfferCallable(**data) for data in result["getOfferCallables"]]
        
        elif obj_type == OfferReference:
            query = gql_client('''
            query {
                getOfferReferences {
                    id
                    time
                    url
                    description
                    tags
                    followup
                    cost
                }
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query)
            return [OfferReference(**data) for data in result["getOfferReferences"]]

    
    async def refund_offercall(self, offercall: OfferCall | None = None, id: uuid.UUID | None = None) -> bool:
        """
        Refund an OfferCall.

        Parameters
        ----------
        offercall : OfferCall or None, optional
            The OfferCall object to refund.
        id : uuid.UUID, optional
            The ID of the OfferCall to refund.

        Returns
        -------
        bool
            True if the OfferCall was successfully refunded.

        Raises
        ------
        ValueError
            If required parameters are missing.
        """            
        offercall_id = (offercall.id if offercall else None) or id
        if not offercall_id:
            raise ValueError("Either offercall or id must be provided.")
        
        query = gql_client('''
        mutation refundOfferCall($offer_call_id: ID!) {
            refundOfferCall(offer_call_id: $offer_call_id)
        }
        ''')
        result = await self._graphql_service_marketplace.execute_async(query, variable_values={"offer_call_id": str(offercall_id)})
        return result["refundOfferCall"]

    
    async def send_newoffercall(self, new_offercall: NewOfferCall) -> OfferCall:
        """
        Create a new OfferCall.

        Parameters
        ----------
        new_offercall : NewOfferCall
            The OfferCall object to create.
        
        Returns
        -------
        OfferCall
            The created OfferCall object.

        Raises
        ------
        ValueError
            If the OfferCall object is invalid.
        """
        query = gql_client('''
        mutation createNewOfferCall($input: NewOfferCall!) {
            createNewOfferCall(input: $input) {
                id
                time
                apikey_id
                offer_id
                deputy_apikey_id
                parameters
            }
        }
        ''')
        result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": new_offercall.model_dump()})
        return OfferCall(**result["createNewOfferCall"])

    
    async def set_webhook(self, url: str = None):
        """
        Set or update the webhook URL associated with the agent's API key.

        Parameters
        ----------
        url : str, optional
            The webhook URL to be set. If not provided, the value is retrieved from the
            MAOTO_AGENT_URL environment variable.

        Raises
        ------
        ValueError
            If neither a `url` argument nor the MAOTO_AGENT_URL environment variable is provided.
        """
        if not url:
            env_url = os.getenv("MAOTO_AGENT_URL")
            if not env_url:
                raise ValueError("No URL provided in environment variable MAOTO_AGENT_URL.")
            url = Url(env_url)

        query = gql_client('''
        mutation addUrlToApikey($url: String!) {
            addUrlToApikey(urls: $url)
        }
        ''')

        result = await self._graphql_service_marketplace.execute_async(query, variable_values={"url": url})

    # only used for open connection server
    async def _subscribe_to_events(self, task_queue, stop_event):
        # Subscription to listen for both actioncalls and responses using __typename
        subscription = gql_client('''
        subscription subscribeToEvents {
            subscribeToEvents {
                __typename
                ... on OfferCall {
                    id
                    time
                    apikey_id
                    offer_id
                    deputy_apikey_id
                    parameters
                }
                ... on RequestOffers {
                    skill_id
                    resolver_id
                    offer
                }
                ... on OfferCallableCostRequest {
                    offerreference
                    parameters
                }
                ... on OfferReferenceCostRequest {
                    offerreference
                    parameters
                }
                ... on Response {
                    id
                    time
                    offercallable_id
                    description
                    apikey_id
                }
                ... on PaymentRequest {
                    actioncall_id
                    post_id
                    payment_link
                }
                                  
                ... on LinkConfirmation {
                    pa_user_id
                    apikey_id
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
                    fetch_schema_from_transport=False
                ) as session:
                    self.logger.info("Successfully connected. Listening for events.")
                    attempt = 0  # Reset attempt count on successful connection

                    # if reconnect:
                    #     try:
                    #         actions = await self._create_actions_core(self._action_cache)
                    #     except Exception as e:
                    #         self.logger.info(f"Error recreating actions.")

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
        event_data = result['subscribeToEvents']
        event_type = event_data["__typename"]
        try:
            cls = locals().get(event_type)
            event_obj = cls(**event_data)
        except Exception as e:
            self.logger.error(f"Error creating event object: {e}")
            return
        task_queue.put(event_obj)

    def register_handler(self, event: type):
        def decorator(func):
            self._handler_registry[event] = func
            return func
        return decorator
        
    async def send_to_assistant(self, obj: PALocationResponse | PAUserResponse | PANewConversation | PASupportRequest):
        """
        Send a supported object to the Assistant service via a GraphQL mutation.

        Parameters
        ----------
        obj : PALocationResponse or PAUserResponse or PANewConversation or PASupportRequest
            The object to forward to the Assistant service.

        Raises
        ------
        GraphQLError
            If the provided object type is not supported.
        """
        if isinstance(obj, PALocationResponse):
            value_name = "pa_locationresponse"
            query = gql_client('''
                mutation forwardPALocationResponse($pa_locationresponse: PALocationResponse!) {
                    forwardPALocationResponse(pa_locationresponse: $pa_locationresponse)
                }
            ''')
        elif isinstance(obj, PAUserResponse):
            value_name = "pa_userresponse"
            query = gql_client('''
                mutation forwardPAUserResponse($pa_userresponse: PAUserResponse!) {
                    forwardPAUserResponse(pa_userresponse: $pa_userresponse)
                }
            ''')
        elif isinstance(obj, PANewConversation):
            value_name = "pa_newconversation"
            query = gql_client('''
                mutation forwardPANewConversation($pa_newconversation: PANewConversation!) {
                    forwardPANewConversation(pa_newconversation: $pa_newconversation)
                }
            ''')
        elif isinstance(obj, PASupportRequest):
            value_name = "pa_supportrequest"
            query = gql_client('''
                mutation forwardPASupportRequest($pa_supportrequest: PASupportRequest!) {
                    forwardPASupportRequest(pa_supportrequest: $pa_supportrequest)
                }
            ''')
        else:
            raise GraphQLError(f"Object type {type(obj).__name__} not supported.")

        await self._graphql_service_assistant.execute_async(query, variable_values={value_name: obj.model_dump()})