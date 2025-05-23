import asyncio
import uuid
from importlib.metadata import version
from importlib.resources import files
from typing import Literal
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, Request, Header, HTTPException, Depends, APIRouter
import hmac
import hashlib
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from typing import Sequence
from pydantic import BaseModel, HttpUrl

from .agent_settings import AgentSettings
from .app_types import *


class Maoto(FastAPI):    
    def __init__(self, apikey: SecretStr | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        settings_kwargs = {}
        if apikey is not None:
            settings_kwargs["apikey"] = apikey
        self._settings = AgentSettings(**settings_kwargs)

        self.debug = self._settings.debug

        logger.remove()

        self._setup_routes()

        self._version = version("maoto_agent")
        self._headers = {
            "Authorization": self._settings.apikey.get_secret_value(),
            "Version": self._version,
        }

        self.supported_event_types = {
                OfferCall: "Represents a request to initiate an offer-related call or interaction.",
                OfferRequest: "Represents a request to fetch or create an offer.",
                OfferCallableCostRequest: "Used to retrieve the cost of a callable offer.",
                OfferReferenceCostRequest: "Used to retrieve the cost based on a reference offer.",
                IntentResponse: "Captures the outcome or interpretation of a user's intent.",
                OfferCallResponse: "Contains the response data from an offer call interaction.",
                PaymentRequest: "Used to initiate a payment process for a service or product.",
                LinkConfirmation: "Confirms that the user linked his UI id with a maoto account.",
                PAUserMessage: "A message directed to the user in the personal assistant flow.",
                PALocationRequest: "Asks the UI to share or request the user's location.",
                PALinkUrl: "Requests the user to login before calling an action that has cost associated.",
                PAPaymentRequest: "Personal assistant version of a payment request, possibly with more context or user-specific handling.",
            }

    def _setup_routes(self):
        @self.get("/healthz", include_in_schema=False)
        async def healthz_check():
            return {"status":"ok"}

        @self.get("/health", include_in_schema=False)
        async def human_health_check():
            return {"status":"ok"}

        static_path = files("maoto_agent").joinpath("assets")
        @self.get("/favicon.ico", include_in_schema=False)
        async def favicon():
            return FileResponse(static_path / "favicon.ico")

    def register_handler(
        self,
        event_type: type[
            OfferCall
            | OfferRequest
            | OfferCallableCostRequest
            | OfferReferenceCostRequest
            | IntentResponse
            | OfferCallResponse
            | PaymentRequest
            | LinkConfirmation
            | PALocationRequest
            | PAUserMessage
            | PALinkUrl
            | PAPaymentRequest
        ],
    ):
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
            if event_type not in self.supported_event_types.keys():
                raise ValueError(
                    f"Unsupported event type: {event_type}. Supported types are: {self.supported_event_types}"
                )

            async def instant_response(input: event_type):
                asyncio.create_task(func(input))

            self.add_api_route(
                dependencies=[Depends(self._verify_hmac)],
                path=f"/{event_type.__name__}",
                endpoint=instant_response,
                summary=f"Handle {event_type.__name__} events",
                description=self.supported_event_types[event_type],
                methods=["POST"],
                response_model=None,
            )
            return func

        return decorator

    @staticmethod
    def safe_urljoin(base: HttpUrl, *paths: str) -> str:
        """
        Safely join base URL with one or more path segments.
        """
        base_str = str(base)
        if not base_str.endswith("/"):
            base_str += "/"
        full_path = "/".join(segment.strip("/") for segment in paths)
        return urljoin(base_str, full_path)

    @staticmethod
    def _make_signature(method: str, path: str, ts: str, body: bytes | None, secret: SecretStr) -> str:
        if body is None:
            body = b""
        signing_str = f"{ts}|{method.upper()}|{path}|".encode() + body
        return hmac.new(secret.get_secret_value().encode(), signing_str, hashlib.sha256).hexdigest()

    async def _verify_hmac(
        self,
        request: Request,
        signature: str = Header(..., alias="Signature"),
        timestamp: str  = Header(..., alias="Timestamp"),
    ):
        body = await request.body()
        expected = self._make_signature(request.method, request.url.path, timestamp, body, self._settings.apikey_hashed)
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(403, "Invalid signature")

    async def _request(
        self,
        method: Literal["GET", "POST", "PUT", "DELETE"],
        input: BaseModel | dict | None = None,
        params: dict | None = None,
        result_type: type | None = None,
        is_list: bool = False,
        route: str | None = None,
        url: HttpUrl = None,
    ) -> BaseModel:
        """Send a request to another FastAPI server with a Pydantic object and return a validated response."""
        full_url = url if not route else self.safe_urljoin(url, route)
        request_kwargs = {"headers": self._headers}

        if isinstance(input, BaseModel):
            request_kwargs["json"] = input.model_dump(mode="json")
        elif isinstance(input, dict):
            request_kwargs["json"] = input

        if isinstance(params, BaseModel):
            params = params.model_dump(mode="json")
        elif isinstance(params, dict):
            request_kwargs["params"] = params

        MAX_RETRIES = 3
        RETRY_DELAY = 1  # in seconds

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(method, str(full_url), **request_kwargs)
                    response.raise_for_status()
                break  # success
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.RemoteProtocolError) as conn_exc:
                if attempt == MAX_RETRIES:
                    raise
                await asyncio.sleep(RETRY_DELAY)
            except httpx.HTTPStatusError as exc:
                # Original HTTPX message, e.g. "429 Too Many Requests…"
                orig = str(exc)

                # Safely attempt to parse JSON detail, otherwise fall back to text
                detail = None
                try:
                    body = exc.response.json()
                    # if body is a dict, try to pull out a "detail" field
                    if isinstance(body, dict):
                        detail = body.get("detail")
                except (ValueError, TypeError):
                    # not JSON, or not a dict
                    pass

                if not detail:
                    detail = exc.response.text or "<no response body>"

                msg = f"{orig}\nDetail: {detail}"
                raise httpx.HTTPStatusError(
                    msg, request=exc.request, response=exc.response
                ) from exc

        if result_type is None:
            return None

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
            result_type=ApiKey, route="get_own_apikey", url=self._settings.url_mp, method="GET"
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
            result_type=str, route="healthz", url=self._settings.url_mp, method="GET"
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
            result_type=str, route="healthz", url=self._settings.url_pa, method="GET"
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
            route=f"{type(new_intent).__name__}",
            url=self._settings.url_mp,
            method="POST",
        )

    async def unregister(
        self,
        obj: Skill | OfferCallable | OfferReference | None = None,
        obj_type: type[Skill | OfferCallable | OfferReference] | None = None,
        id: uuid.UUID | None = None,
        solver_id: uuid.UUID | None = None,
    ):
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
            if not isinstance(obj, (Skill, OfferCallable, OfferReference)):
                raise ValueError("Input must be one of: Skill, OfferCallable, OfferReference.")
            obj_type = type(obj)
            param = f"id={obj.id}"
        elif (id or solver_id) and obj_type:
            if not isinstance(id, uuid.UUID) and not isinstance(solver_id, uuid.UUID):
                raise ValueError("ID or solver_id must be a valid UUID.")
            if obj_type not in {Skill, OfferCallable, OfferReference}:
                raise ValueError(
                    "Unsupported type. Must be one of: Skill, OfferCallable, OfferReference."
                )
            param = f"id={id}" if id else f"solver_id={solver_id}"
        else:
            raise ValueError("Either obj or (obj_type and id/solver_id) must be provided.")

        await self._request(
            route=f"unregister{obj_type.__name__}?{param}",
            url=self._settings.url_mp,
            method="POST",
        )

    async def send_response(
        self,
        obj: NewOfferResponse
        | NewOfferCallResponse
        | NewOfferCallableCostResponse
        | NewOfferReferenceCostResponse,
    ):
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
        if not isinstance(
            obj,
            (
                NewOfferResponse,
                NewOfferCallResponse,
                NewOfferCallableCostResponse,
                NewOfferReferenceCostResponse,
            ),
        ):
            raise ValueError(
                "Input must be one of: NewOfferResponse, NewOfferCallResponse, NewOfferCallableCostResponse, NewOfferReferenceCostResponse."
            )

        await self._request(
            input=obj,
            route=f"{type(obj).__name__}",
            url=self._settings.url_mp,
            method="POST",
        )

    async def register(
        self, obj: NewSkill | NewOfferCallable | NewOfferReference
    ) -> Skill | OfferCallable | OfferReference:
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

        if isinstance(obj, NewSkill):
            result_type = Skill
        elif isinstance(obj, NewOfferCallable):
            result_type = OfferCallable
        elif isinstance(obj, NewOfferReference):
            result_type = OfferReference
        else:
            raise ValueError(
                "Unsupported type. Must be one of: NewSkill, NewOfferCallable, NewOfferReference."
            )

        return await self._request(
            input=obj,
            result_type=result_type,
            route=f"register{type(obj).__name__}",
            url=self._settings.url_mp,
            method="POST",
        )

    async def get_registered(
        self, type_ref: type[Skill | OfferCallable | OfferReference]
    ) -> list[Skill | OfferCallable | OfferReference]:
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
            raise ValueError(
                "Unsupported type. Must be one of: Skill, OfferCallable, OfferReference."
            )

        return await self._request(
            result_type=type_ref,
            is_list=True,
            route=f"get{type_ref.__name__}s",
            url=self._settings.url_mp,
            method="GET",
        )

    async def refund_offercall(
        self, offercall: OfferCall | None = None, id: uuid.UUID | None = None
    ) -> bool:
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
            method="POST",
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
            route="NewOfferCall",
            url=self._settings.url_mp,
            method="POST",
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

        if not (url or self._settings.agent_url):
            raise ValueError(
                "No URL provided. Please set MAOTO_AGENT_URL in your environment variables or pass a URL as an argument."
            )

        return await self._request(
            input={"url": str(url or self._settings.agent_url)},
            result_type=str,
            route="setWebhook",
            url=self._settings.url_mp,
            method="POST",
        )

    async def send_to_assistant(
        self, obj: PALocationResponse | PAUserResponse | PANewConversation | PASupportRequest
    ):
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
        if not isinstance(
            obj, (PALocationResponse, PAUserResponse, PANewConversation, PASupportRequest)
        ):
            raise ValueError(
                "Input must be one of: PALocationResponse, PAUserResponse, PANewConversation, PASupportRequest."
            )

        await self._request(
            input=obj,
            route=f"{type(obj).__name__}",
            url=self._settings.url_pa,
            method="POST",
        )

    async def get_refcodes(self) -> list[RefCode]:
        """
        Retrieve all reference codes associated with this agent.

        Returns
        -------
        list[RefCode]
            A list of reference codes.

        Examples
        --------
        >>> refcodes = await maoto.get_refcodes()
        >>> for code in refcodes:
        >>>     print(code.value)
        """
        return await self._request(
            result_type=RefCode,
            is_list=True,
            route="RefCodes",
            url=self._settings.url_pa,
            method="GET",
        )

    async def create_refcode(self, new_refcode: NewRefCode):
        """
        Creates a new reference code to the assistant.
        Parameters
        ----------
        new_refcode :
            The reference code to add.
        """
        if not isinstance(new_refcode, NewRefCode):
            raise ValueError("Input must be a NewRefCode object.")

        await self._request(
            input=new_refcode,
            result_type=NewRefCode,
            route="NewRefCode",
            url=self._settings.url_pa,
            method="POST",
        )

    async def delete_refcode(self, value: str | None = None, offercallable_id: UUID | None = None):
        """
        Delete a reference code from the assistant.
        Parameters
        ----------
        refcode : str, optional
            The reference code to delete.
        offercallable_id : UUID, optional
            The ID of the offer callable associated with the reference code.
        """
        if not value and not offercallable_id:
            raise ValueError("Either refcode or offercallable_id must be provided.")

        await self._request(
            params={"value": str(value)} if value else {"offercallable_id": str(offercallable_id)},
            route="RefCode",
            url=self._settings.url_pa,
            method="DELETE",
        )