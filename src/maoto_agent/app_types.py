from pydantic import BaseModel, EmailStr, HttpUrl, SecretStr
from uuid import UUID
from datetime import datetime
from abc import ABC, abstractmethod

class ErrorResponse(BaseModel):
    message: str

class SuccessResponse(BaseModel):
    message: str

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

class NewResponse(BaseModel):
    intent_id: UUID
    description: str

class Response(NewResponse):
    pass

class NewOfferCallResponse(BaseModel):
    offercall_id: UUID
    offercallable_id: UUID
    description: str

class OfferCallResponse(NewOfferCallResponse):
    id: UUID
    time: datetime
    apikey_id: UUID

class NewIntent(BaseModel):
    description: str
    tags: list[str]

class Intent(NewIntent):
    id: UUID
    apikey_id: UUID
    test: bool
    time: datetime
    resolved: bool

class NewOffer(BaseModel, ABC):
    apikey_id: UUID
    resolver_id: UUID | None
    description: str
    params: str
    tags: list[str]
    followup: bool
    cost: float | None

class Offer(NewOffer, ABC):
    id: UUID
    time: datetime

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
    args: str
    resolver_id: UUID | None
    tags: list[str]

class Skill(NewSkill):
    id: UUID
    apikey_id: UUID
    time: datetime

class MissingInfo(BaseModel):
    description: str

class OfferCallableCostRequest(BaseModel):
    offercallable_id: UUID
    resolver_id: UUID | None
    intent: Intent

class OfferReferenceCostRequest(BaseModel):
    offerreference_id: UUID
    resolver_id: UUID | None
    intent: Intent

class NewOfferCallableCostResponse(BaseModel):
    offercallable_id: UUID
    intent_id: UUID
    cost: float

class OfferCallableCostResponse(NewOfferCallableCostResponse):
    id: UUID

class NewOfferReferenceCostResponse(BaseModel):
    offerreference_id: UUID
    cost: float
    url: HttpUrl

class OfferReferenceCostResponse(NewOfferReferenceCostResponse):
    id: UUID

class OfferRequest(BaseModel):
    skill_id: UUID
    resolver_id: UUID | None
    intent: Intent

class NewOfferResponse(BaseModel):
    intent_id: UUID
    
    offerreference_ids: list[UUID]
    offercallable_ids: list[UUID]

    missinginfo: list[MissingInfo]
    newoffercallables: list[NewOfferCallable]
    newofferreferences: list[NewOfferReference]

class OfferResponse(NewOfferResponse):
    apikey_id: UUID
    time: datetime

class NewOfferCall(BaseModel):
    offercallable_id: UUID
    deputy_apikey_id: UUID | None
    args: str

class OfferCall(NewOfferCall):
    id: UUID
    time: datetime
    apikey_id: UUID

class NewFile(BaseModel):
    extension: str

class File(NewFile):
    file_id: UUID
    time: datetime
    apikey_id: UUID

class NewHistoryElement(BaseModel):
    text: str
    tree_id: UUID
    parent_id: UUID | None
    apikey_id: UUID | None
    role: str | None
    file_ids: list[UUID]
    name: str | None

class HistoryElement(NewHistoryElement):
    history_id: UUID
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
    payment_link: str

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
    params: str

class LoginUserResponse(BaseModel):
    token: str

class RegisterUserRequest(BaseModel):
    email: EmailStr
    password: SecretStr
    params: str

class EmailVerif(BaseModel):
    token: SecretStr
    params: str

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



# intent = Intent(
#     id=UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
#     time=datetime.now(),
#     apikey_id=UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
#     description="description",
#     tags=["tag1", "tag2"],
#     resolved=True
# )

# dumped = intent.model_dump(mode="json")
# print(dumped, type(dumped))

# intent = Intent.model_validate(dumped)
# print(f"{intent!r}")