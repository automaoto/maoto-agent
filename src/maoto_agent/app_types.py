import json
from abc import ABC
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, HttpUrl, SecretStr, field_validator


class NewUser(BaseModel):
    email: EmailStr
    name: str | None
    roles: list[str]


class User(NewUser):
    id: UUID
    time: datetime
    verified: bool


class NewUserWithSecret(NewUser):
    password: SecretStr


class NewApiKey(BaseModel):
    user_id: UUID
    name: str
    roles: list[str]
    url: HttpUrl | None


class ApiKey(NewApiKey):
    id: UUID
    time: datetime


class ApiKeyWithSecret(ApiKey):
    value: SecretStr


class IntentResponse(BaseModel):
    intent_id: UUID
    provider_id: str
    description: str


class NewOfferCallResponse(BaseModel):
    offercall_id: UUID
    offercallable_id: UUID
    description: str


class OfferCallResponse(NewOfferCallResponse):
    id: UUID
    provider_id: str
    time: datetime
    apikey_id: UUID


class NewIntent(BaseModel):
    description: str
    provider_id: str | None
    tags: list[str]


class Intent(NewIntent):
    id: UUID
    apikey_id: UUID
    test: bool
    time: datetime
    resolved: bool


class NewOffer(BaseModel, ABC):
    solver_id: UUID | None
    description: str
    params: dict
    tags: list[str]
    followup: bool
    cost: float | None

    @field_validator("params", mode="before")
    @classmethod
    def ensure_dict(cls, value) -> dict:
        if isinstance(value, dict):
            return value
        return json.loads(str(value))


class Offer(NewOffer, ABC):
    id: UUID
    time: datetime
    apikey_id: UUID


class NewOfferCallable(NewOffer):
    pass


class OfferCallable(Offer):
    pass


class NewOfferReference(NewOffer):
    url: HttpUrl | None


class OfferReference(Offer):
    url: HttpUrl | None


class NewSkill(BaseModel):
    description: str
    params: dict
    solver_id: UUID | None
    tags: list[str]

    @field_validator("params", mode="before")
    @classmethod
    def ensure_dict(cls, value) -> dict:
        if isinstance(value, dict):
            return value
        return json.loads(str(value))


class Skill(NewSkill):
    id: UUID
    apikey_id: UUID
    time: datetime


class MissingInfo(BaseModel):
    description: str


class OfferCallableCostRequest(BaseModel):
    offercallable_id: UUID
    solver_id: UUID | None
    intent: Intent


class OfferReferenceCostRequest(BaseModel):
    offerreference_id: UUID
    solver_id: UUID | None
    intent: Intent


class NewOfferCallableCostResponse(BaseModel):
    offercallable_id: UUID
    intent_id: UUID
    cost: float


class OfferCallableCostResponse(NewOfferCallableCostResponse):
    id: UUID


class NewOfferReferenceCostResponse(BaseModel):
    offerreference_id: UUID
    intent_id: UUID
    cost: float
    url: HttpUrl


class OfferReferenceCostResponse(NewOfferReferenceCostResponse):
    id: UUID


class OfferRequest(BaseModel):
    skill_id: UUID
    solver_id: UUID | None
    intent: Intent


class NewOfferResponse(BaseModel):
    intent_id: UUID

    offerreference_ids: list[UUID]
    offercallable_ids: list[UUID]

    missinginfos: list[MissingInfo]
    newoffercallables: list[NewOfferCallable]
    newofferreferences: list[NewOfferReference]


class OfferResponse(NewOfferResponse):
    apikey: ApiKey


class NewOfferCall(BaseModel):
    offercallable_id: UUID
    provider_id: str | None
    deputy_apikey_id: UUID | None
    args: dict

    @field_validator("args", mode="before")
    @classmethod
    def ensure_dict(cls, value) -> dict:
        if isinstance(value, dict):
            return value
        return json.loads(str(value))


class OfferCall(NewOfferCall):
    id: UUID
    time: datetime
    apikey_id: UUID
    solver_id: UUID | None


class NewFile(BaseModel):
    extension: str


class File(NewFile):
    id: UUID
    time: datetime
    apikey_id: UUID


class NewHistoryElement(BaseModel):
    text: str
    tree_id: UUID
    parent_id: UUID | None
    apikey_id: UUID | None
    role: str
    file_ids: list[UUID]
    name: str | None


class HistoryElement(NewHistoryElement):
    id: UUID
    time: datetime


class PaymentRequest(BaseModel):
    offercall_id: UUID
    payment_link: str


class Location(BaseModel):
    latitude: float
    longitude: float


class PAUserMessage(BaseModel):
    ui_id: str
    text: str


class PAPaymentRequest(BaseModel):
    ui_id: str
    payment_link: HttpUrl


class PALocationRequest(BaseModel):
    ui_id: str


class PALocationResponse(BaseModel):
    ui_id: str
    location: Location


class PAUserResponse(BaseModel):
    ui_id: str
    text: str


class PANewConversation(BaseModel):
    ui_id: str


class PALinkUrl(BaseModel):
    ui_id: UUID
    text: str
    url: HttpUrl


class LinkAgentConfirmation(BaseModel):
    pa_user_id: UUID
    apikey_id: UUID


class LinkConfirmation(BaseModel):
    pa_user_id: UUID
    apikey_id: UUID


class LoginUserRequest(BaseModel):
    email: EmailStr
    password: SecretStr
    query_params: dict

    @field_validator("query_params", mode="before")
    @classmethod
    def ensure_dict(cls, value) -> dict:
        if isinstance(value, dict):
            return value
        return json.loads(str(value))


class LoginUserResponse(BaseModel):
    token: str


class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: SecretStr
    query_params: dict

    @field_validator("query_params", mode="before")
    @classmethod
    def ensure_dict(cls, value) -> dict:
        if isinstance(value, dict):
            return value
        return json.loads(str(value))


class EmailVerif(BaseModel):
    token: SecretStr
    query_params: dict

    @field_validator("query_params", mode="before")
    @classmethod
    def ensure_dict(cls, value) -> dict:
        if isinstance(value, dict):
            return value
        return json.loads(str(value))


class RegisterUserResponse(BaseModel):
    success: bool
    message: str


class PASupportRequest(BaseModel):
    ui_id: str
    text: str


class PAUrl(BaseModel):
    url: HttpUrl


class Url(BaseModel):
    url: HttpUrl


class SessionToken(BaseModel):
    token: SecretStr

class NewRefCode(BaseModel):
    value: str
    offercallable_id: UUID

class RefCode(NewRefCode):
    id: UUID
    apikey_id: UUID
    time: datetime