import os
import uuid
import logging
import httpx
from .app_types import *
from fastapi import FastAPI
from pkg_resources import get_distribution
from pydantic import BaseModel, HttpUrl
from .agent_settings import AgentSettings
from typing import Literal

class Maoto:
    def __init__(self, apikey_value: SecretStr | None = None):
        kwargs = {}
        if apikey_value is not None:
            kwargs["apikey"] = apikey_value
        self._settings = AgentSettings(**kwargs)
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self._settings.logging_level.upper(), logging.WARNING))

        self._app = FastAPI(debug=self._settings.debug)
        self._version = get_distribution("maoto_agent").version
        self._headers = {"Authorization": self._settings.apikey.get_secret_value(), "Version": self._version}

        self.app = self._app

    def register_handler(self, event_type: type[OfferCall | OfferRequest | OfferCallableCostRequest | OfferReferenceCostRequest | IntentResponse | OfferCallResponse | PaymentRequest | LinkConfirmation | PALocationRequest]):
        """
        Decorator to register a handler function for a specific event type.

        Parameters
        ----------
        event_type : type
            The event type to handle. One of the supported incoming event models like OfferCall, OfferRequest, etc.

        Returns
        -------
        function
            A decorator function that registers the given handler.
        
        Raises
        ------
        ValueError
            If the provided type is not among supported event types.

        Examples
        --------
        >>> @maoto.register_handler(OfferCall)
        >>> def handle_offer_call(event):
        >>>     print("Handling OfferCall", event)
        """
        def decorator(func):
            no_return_models = {PALinkUrl, PALocationRequest, PAPaymentRequest, PAUserMessage}
            chosen_response_model = None if event_type in no_return_models else event_type

            self._app.add_api_route(
                path=f"/{event_type.__name__}",
                endpoint=func,
                methods=["POST", "GET"],
                response_model=chosen_response_model
            )
            return func
        return decorator

    async def _request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        input: BaseModel | dict | None = None,
        result_type: type | None = None,
        is_list: bool = False,
        route: str | None = None,
        url: HttpUrl = None,
    ) -> BaseModel:
        """Send a request to another FastAPI server with a Pydantic object and return a validated response."""
        full_url = f"{url}/{route}" if route else url
        request_kwargs = {"headers": self._headers}

        if method in {"POST", "PUT"}:
            if isinstance(input, BaseModel):
                request_kwargs["json"] = input.model_dump(mode="json")
            elif isinstance(input, dict):
                request_kwargs["json"] = input
            else:
                raise Exception("Invalid input type for POST/PUT requests.")

        async with httpx.AsyncClient() as client:
            response = await client.request(method, str(full_url), **request_kwargs)
            response.raise_for_status()
        
        if result_type is str:
            return response.text
        
        data = response.json()
        if result_type is bool:
            return data
        if is_list:
            return [result_type.model_validate(item) for item in data]
        return result_type.model_validate(data)

    async def get_own_apikey(self) -> ApiKey:
        """
        Retrieve the API key associated with the current agent.

        Returns
        -------
        ApiKey
            The API key object containing the key details.

        Raises
        ------
        Exception
            If no API key is found for the user.

        Examples
        --------
        >>> apikey = await maoto.get_own_apikey()
        >>> print(apikey.key)
        """
        return await self._request(
            result_type=ApiKey,
            route="get_own_apikey",
            url=self._settings.url_mp,
            method="GET"
        )
    
    async def health_marketplace(self) -> bool:
        """
        Check if the Marketplace service is currently available.

        Returns
        -------
        bool
            True if the Marketplace is operational, False otherwise.

        Examples
        --------
        >>> is_up = await maoto.check_status_marketplace()
        >>> print("Marketplace is up" if is_up else "Marketplace is down")
        """
        return await self._request(
            result_type=str,
            route="healthz",
            url=self._settings.url_mp,
            method="GET"
        )

    async def health_assistant(self) -> bool:
        """
        Check if the Assistant service is currently available.

        Returns
        -------
        bool
            True if the Assistant is operational, False otherwise.

        Examples
        --------
        >>> is_up = await maoto.check_status_assistant()
        >>> print("Assistant is running" if is_up else "Assistant is down")
        """
        return await self._request(
            result_type=str,
            route="healthz",
            url=self._settings.url_pa,
            method="GET"
        )

    async def send_intent(self, new_intent: NewIntent) -> None:
        """
        Send an intent to the Marketplace for resolution.

        Parameters
        ----------
        new_intent : NewIntent
            The intent object to create and send.

        Examples
        --------
        >>> intent = NewIntent(name="BookFlight", parameters={"destination": "Tokyo"})
        >>> await maoto.send_intent(intent)
        """
        return await self._request(
            input=new_intent,
            result_type=Intent,
            route="createIntent",
            url=self._settings.url_mp,
            method="POST"
        )
    
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

        Examples
        --------
        >>> await maoto.unregister(obj=my_skill)
        >>> await maoto.unregister(obj_type=Skill, id=UUID("abc123"))
        """
        if obj:
            obj_type, obj_id = type(obj), obj.id
        elif obj_type and (id or solver_id):
            obj_id = id or solver_id
        else:
            raise ValueError("Either obj or obj_type and id/solver_id must be provided.")
        
        # check types of provided parameters if they are defined (optionals)
        if obj_type and obj_id:
            if obj_type not in {Skill, OfferCallable, OfferReference}:
                raise ValueError("Unsupported type. Must be one of: Skill, OfferCallable, OfferReference.")
            if not isinstance(obj_id, uuid.UUID):
                raise ValueError("ID must be a valid UUID.")
        elif obj:
            if not isinstance(obj, (Skill, OfferCallable, OfferReference)):
                raise ValueError("Input must be one of: Skill, OfferCallable, OfferReference.")
        
        return await self._request(
            input={"id": str(obj_id)},
            result_type=bool,
            route=f"unregister{obj_type.__name__}",
            url=self._settings.url_mp,
            method="POST"
        )
    
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

        Examples
        --------
        >>> response = NewOfferResponse(...)  # Fill with valid response data
        >>> await maoto.send_response(response)
        """
        if not isinstance(obj, (NewOfferResponse, NewOfferCallResponse, NewOfferCallableCostResponse, NewOfferReferenceCostResponse)):
            raise ValueError("Input must be one of: NewOfferResponse, NewOfferCallResponse, NewOfferCallableCostResponse, NewOfferReferenceCostResponse.")
        
        await self._request(
            input=obj,
            result_type=bool,
            route=f"{type(obj).__name__}",
            url=self._settings.url_mp,
            method="POST"
        )
    
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

        Examples
        --------
        >>> skill = NewSkill(name="TranslateText", ...)  # Fill in your data
        >>> await maoto.register(skill)
        """
        if not isinstance(obj, (NewSkill, NewOfferCallable, NewOfferReference)):
            raise ValueError("Input must be one of: NewSkill, NewOfferCallable, NewOfferReference.")
        
        return await self._request(
            input=obj,
            result_type=bool,
            route=f"register{type(obj).__name__}",
            url=self._settings.url_mp,
            method="POST"
        )
    
    async def get_registered(self, type_ref: type[Skill | OfferCallable | OfferReference]) -> list[Skill | OfferCallable | OfferReference]:
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

        Examples
        --------
        >>> skills = await maoto.get_registered(Skill)
        >>> for skill in skills:
        >>>     print(skill.name)
        """
        if type_ref not in {Skill, OfferCallable, OfferReference}:
            raise ValueError("Unsupported type. Must be one of: Skill, OfferCallable, OfferReference.")
        
        return await self._request(
            result_type=type_ref,
            is_list=True,
            route=f"get{type_ref.__name__}",
            url=self._settings.url_mp,
            method="GET"
        )

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

        Examples
        --------
        >>> await maoto.refund_offercall(id=UUID("abc123"))
        >>> await maoto.refund_offercall(offercall=some_offercall)
        """
        offercallid = (offercall.id if offercall else None) or id
        if not offercallid:
            raise ValueError("Either offercall or id must be provided.")
        
        return await self._request(
            input={"id": str(offercallid)},
            result_type=bool,
            route="refundOfferCall",
            url=self._settings.url_mp,
            method="POST"
        )

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

        Examples
        --------
        >>> new_call = NewOfferCall(...)  # Fill with valid details
        >>> offer_call = await maoto.send_newoffercall(new_call)
        >>> print(offer_call.id)
        """
        if not isinstance(new_offercall, NewOfferCall):
            raise ValueError("Input must be a NewOfferCall object.")
        
        return await self._request(
            input=new_offercall,
            result_type=OfferCall,
            route="sendNewOfferCall",
            url=self._settings.url_mp,
            method="POST"
        )

    async def set_webhook(self, url: str = None) -> str:
        """
        Set or update the webhook URL associated with this agent's API key.

        Parameters
        ----------
        url : str, optional
            The webhook URL to be set. If not provided, reads from `MAOTO_AGENT_URL`.

        Returns
        -------
        bool
            True if the webhook URL was successfully set.
        Raises
        ------
        ValueError
            If no URL is provided and `MAOTO_AGENT_URL` is not set.

        Examples
        --------
        >>> await maoto.set_webhook("https://agent.example.com/webhook")
        """
        if not url:
            env_url = os.getenv("MAOTO_AGENT_URL")
            if not env_url:
                raise ValueError("No URL provided in environment variable MAOTO_AGENT_URL.")
            url = HttpUrl(env_url)

        return await self._request(
            input={"url": str(url)},
            result_type=str,
            route="setWebhook",
            url=self._settings.url_mp,
            method="POST"
        )
        
    async def send_to_assistant(self, obj: PALocationResponse | PAUserResponse | PANewConversation | PASupportRequest) -> bool:
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
        ValueError
            If the object type is unsupported.

        Examples
        --------
        >>> response = PAUserResponse(user_id="xyz", message="Yes")
        >>> await maoto.send_to_assistant(response)
        """
        if not isinstance(obj, (PALocationResponse, PAUserResponse, PANewConversation, PASupportRequest)):
            raise ValueError("Input must be one of: PALocationResponse, PAUserResponse, PANewConversation, PASupportRequest.")
        
        return await self._request(
            input=obj,
            result_type=bool,
            route=f"{type(obj).__name__}",
            url=self._settings.url_pa,
            method="POST"
        )