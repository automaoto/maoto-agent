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
                "forwardOfferCallResponse": OfferCallResponse,
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
    
    async def get_own_api_key(self) -> ApiKey:
        # Query to fetch the user's own API keys, limiting the result to only one
        query = gql_client('''
        query {
            getOwnApiKey {
                apikey_id
                user_id
                name
                time
                roles
            }
        }
        ''')

        result = await self._graphql_service_marketplace.execute_async(query)
        data = result["getOwnApiKey"]

        # Return the first API key (assume the list is ordered by time or relevance)
        if data:
            return ApiKey(**data)
        else:
            raise Exception("No API key found for the user.")
    
    async def check_status_marketplace(self) -> bool:
        """
        Check if the Marketplace service is currently available.

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
        Check if the Assistant service is currently available.

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

    async def send_intent(self, new_intent: NewIntent) -> None:
        """
        Send an intent to the Marketplace for resolution.

        Parameters
        ----------
        new_intent : NewIntent
            The intent object to create and send.
        """
        query = gql_client('''
        mutation createIntent($input: NewIntent!) {
            createIntent(input: $input)
        }
        ''')
        await self._graphql_service_marketplace.execute_async(query, variable_values={"input": new_intent.model_dump()})
    
    async def unregister(self, obj: Skill | OfferCallable | OfferReference | None = None, obj_type: type[Skill | OfferCallable | OfferReference] | None = None, id: uuid.UUID | None = None, solver_id: uuid.UUID | None = None) -> bool:
        """
        Unregister a Skill, OfferCallable, or OfferReference to make it unavailable.

        Parameters
        ----------
        obj : Skill or OfferCallable or OfferReference, optional
            The object instance to unregister.
        obj_type : type, optional
            The type of object (used if `obj` is not given).
        id : uuid.UUID, optional
            ID of the object to unregister.
        solver_id : uuid.UUID, optional
            Solver ID of the object to unregister.

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
    
    async def send_response(self, obj: NewOfferResponse | NewOfferCallResponse | NewOfferCallableCostResponse | NewOfferReferenceCostResponse) -> bool:
        """
        Send a response object to the Marketplace to complete a request or update its status.

        Parameters
        ----------
        obj : NewOfferResponse or NewOfferCallResponse or NewOfferCallableCostResponse or NewOfferReferenceCostResponse
            The response object to send. One of:

            - **NewOfferResponse**  
            Sent in response to an OfferRequest.  
            Informs the Marketplace of the offers made when an intent matches a registered skill.
            
            - **NewOfferCallResponse**  
            Sent in response to an OfferCall.  
            Informs the caller of status updates related to the offer call.

            - **NewOfferCallableCostResponse**  
            Sent in response to an OfferCallableCostRequest.  
            Provides the actual cost for a callable offer.

            - **NewOfferReferenceCostResponse**  
            Sent in response to an OfferReferenceCostRequest.  
            Provides the cost and/or URL for a reference offer.

        Returns
        -------
        bool
            True if the response was successfully sent.

        Raises
        ------
        ValueError
            If the object type is unsupported.
        """

        if isinstance(obj, NewOfferResponse):
            query = gql_client('''
            mutation sendOfferResponse($input: NewOfferResponse!) {
                sendOfferResponse(input: $input)
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
            return result["sendOfferResponse"]
        
        if isinstance(obj, NewOfferCallResponse):
            query = gql_client('''
            mutation sendOfferCallResponse($input: OfferCallResponse!) {
                sendOfferCallResponse(input: $input)
            }
            ''')
            result = await self._graphql_service_marketplace.execute_async(query, variable_values={"input": obj.model_dump()})
            return result["sendOfferCallResponse"]
        
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
        Register a new object with the Marketplace to make it available.

        Parameters
        ----------
        obj : NewSkill or NewOfferCallable or NewOfferReference
            The object to register. One of:

            - **NewSkill**  
            Registers a set of skills the agent can respond to.  
            Enables the Marketplace to send OfferRequests when an intent matches.
            
            - **NewOfferCallable**  
            Registers a callable offer that the agent can fulfill.  
            Enables cost resolution and execution via the Marketplace.
            
            - **NewOfferReference**  
            Registers a reference offer linking to external resources.  
            Enables cost/URL resolution or execution through the Marketplace.

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
    
    async def get_registered(self, type_ref: Skill | OfferCallable | OfferReference) -> list[Skill | OfferCallable | OfferReference]:
        """
        Retrieve registered objects of a given type from the Marketplace.

        Parameters
        ----------
        type_ref : type
            One of the following types:
            
            - **Skill**
            - **OfferCallable**
            - **OfferReference**

        Returns
        -------
        list
            A list of registered objects of the given type.

        Raises
        ------
        ValueError
            If the provided type is not supported.
        """
        if type_ref == Skill:
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
        
        elif type_ref == OfferCallable:
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
        
        elif type_ref == OfferReference:
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
        Refund an OfferCall due to an error, cancellation, or other issues.

        Parameters
        ----------
        offercall : OfferCall, optional
            The OfferCall object to refund.
        id : uuid.UUID, optional
            The ID of the OfferCall.

        Returns
        -------
        bool
            True if the refund was successful.

        Raises
        ------
        ValueError
            If neither an object nor ID is provided.
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
        Send a new OfferCall to the Marketplace.

        Parameters
        ----------
        new_offercall : NewOfferCall
            The OfferCall to create.

        Returns
        -------
        OfferCall
            The created OfferCall object.

        Raises
        ------
        ValueError
            If the input is invalid.
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
        Set or update the webhook URL associated with this agent's API key.

        Parameters
        ----------
        url : str, optional
            The webhook URL to be set. If not provided, reads from `MAOTO_AGENT_URL`.

        Raises
        ------
        ValueError
            If neither a `url` nor `MAOTO_AGENT_URL` is available.
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

    def register_handler(self, event_type: type[OfferCall | OfferRequest | OfferCallableCostRequest | OfferReferenceCostRequest | Response | PaymentRequest | LinkConfirmation]):
        """
        Register a handler function for a specific event type.

        Parameters
        ----------
        event : OfferCall or OfferRequest or OfferCallableCostRequest or OfferReferenceCostRequest or Response or PaymentRequest or LinkConfirmation
            The event type for which to register a handler.

        Returns
        -------
        function
            The decorator function used to register the handler.

        Raises
        ------
        ValueError
            If the event type is not supported.
        """
        def decorator(func):
            self._handler_registry[event] = func
            return func
        return decorator
        
    async def send_to_assistant(self, obj: PALocationResponse | PAUserResponse | PANewConversation | PASupportRequest):
        """
        Send a supported object to the Assistant service via GraphQL.

        Parameters
        ----------
        obj : PALocationResponse or PAUserResponse or PANewConversation or PASupportRequest
            The object to send. One of:

            - **PALocationResponse**  
            Sends location info from a user back to the Assistant.

            - **PAUserResponse**  
            Sends a user's response back to the Assistant.

            - **PANewConversation**  
            Starts a new conversation with the Assistant.

            - **PASupportRequest**  
            Sends a support-related request.

        Raises
        ------
        GraphQLError
            If the object type is not supported.
        """
        if isinstance(obj, PALocationResponse):
            value_name = "input"
            query = gql_client('''
                mutation forwardPALocationResponse($input: PALocationResponse!) {
                    forwardPALocationResponse(input: $input)
                }
            ''')
        elif isinstance(obj, PAUserResponse):
            value_name = "input"
            query = gql_client('''
                mutation forwardPAUserResponse($input: PAUserResponse!) {
                    forwardPAUserResponse(input: $input)
                }
            ''')
        elif isinstance(obj, PANewConversation):
            value_name = "input"
            query = gql_client('''
                mutation forwardPANewConversation($input: PANewConversation!) {
                    forwardPANewConversation(input: $input)
                }
            ''')
        elif isinstance(obj, PASupportRequest):
            value_name = "input"
            query = gql_client('''
                mutation forwardPASupportRequest($input: PASupportRequest!) {
                    forwardPASupportRequest(input: $input)
                }
            ''')
        else:
            raise GraphQLError(f"Object type {type(obj).__name__} not supported.")

        await self._graphql_service_assistant.execute_async(query, variable_values={value_name: obj.model_dump()})