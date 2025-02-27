from datetime import datetime
import json
from typing import Optional
import uuid

class NewUser:
    def __init__(self, username: str, password: str, roles: list):
        self.username = username
        self.password = password
        self.roles = roles

    def get_username(self):
        return self.username
    
    def get_roles(self):
        return self.roles
    
    def __str__(self):
        return f"\nUsername: {self.username}\nRoles: {self.roles}"
    
    def __repr__(self):
        return f"NewUser(username='{self.username}', roles='{self.roles}')"

class User:
    def __init__(self, user_id: uuid.UUID, time: datetime, username: str, roles: list):
        self.user_id = user_id
        self.time = time
        self.username = username
        self.roles = roles

    def get_user_id(self):
        return self.user_id
    
    def get_time(self):
        return self.time

    def get_username(self):
        return self.username
    
    def get_roles(self):
        return self.roles
    
    def __str__(self):
        return f"\nUser ID: {self.user_id}\nTime: {self.time}\nUsername: {self.username}\nRoles: {self.roles}"
    
    def __repr__(self):
        return f"User(user_id='{self.user_id}', time='{self.time}', username='{self.username}', roles='{self.roles}')"
    
class NewApiKey:
    def __init__(self, user_id: uuid.UUID, name: str, roles: list):
        self.user_id = user_id
        self.name = name
        self.roles = roles

    def get_user_id(self):
        return self.user_id
    
    def get_name(self):
        return self.name
    
    def get_roles(self):
        return self.roles
    
    def __str__(self):
        return f"\nUser ID: {self.user_id}\nAPI Key Name: {self.name}\nRoles: {self.roles}"
    
    def __repr__(self):
        return f"NewApiKey(user_id='{self.user_id}', name='{self.name}', roles='{self.roles}')"

class ApiKey:
    def __init__(self, apikey_id: uuid.UUID, time: datetime, user_id: uuid.UUID, name: str, roles: list, url: str | None = None):
        self.apikey_id = apikey_id
        self.time = time
        self.user_id = user_id
        self.name = name
        self.roles = roles
        self.url = url

    def get_apikey_id(self):
        return self.apikey_id
    
    def get_time(self):
        return self.time
    
    def get_user_id(self):
        return self.user_id
    
    def get_name(self):
        return self.name
    
    def get_roles(self):
        return self.roles
    
    def set_roles(self, roles: list):
        self.roles = roles
    
    def get_url(self):
        return self.url
    
    def __str__(self):
        return f"\nAPI Key ID: {self.apikey_id}\nTime: {self.time}\nUser ID: {self.user_id}\nKey Name: {self.name}\nRoles: {self.roles}\nURL: {self.url}"
    
    def __repr__(self):
        return f"ApiKey(apikey_id='{self.apikey_id}', time='{self.time}', user_id='{self.user_id}', name='{self.name}', roles='{self.roles}', url='{self.url}')"
    
class ApiKeyWithSecret(ApiKey):
    def __init__(self, apikey_id: uuid.UUID, time: datetime, user_id: uuid.UUID, name: str, roles: list, value: str):
        super().__init__(apikey_id, time, user_id, name, roles)
        self.value = value
    
    def get_value(self):
        return self.value
    
    def __str__(self):
        return f"\nAPI Key ID: {self.apikey_id}\nTime: {self.time}\nUser ID: {self.user_id}\nKey Name: {self.name}\nRoles: {self.roles}\nValue: {self.value}"
    
    def __repr__(self):
        return f"ApiKeyWithSecret(apikey_id='{self.apikey_id}', time='{self.time}', user_id='{self.user_id}', name='{self.name}', roles='{self.roles}', value='{self.value}')"

class NewAction:
    def __init__(self, name: str, parameters: str, description: str, tags: list[str], cost: float, followup: bool):
        self.name = name
        self.parameters = parameters
        self.description = description
        self.tags = tags
        self.cost = cost
        self.followup = followup

    def get_name(self):
        return self.name

    def get_parameters(self):
        return self.parameters

    def get_description(self):
        return self.description

    def get_tags(self):
        return self.tags

    def get_cost(self):
        return self.cost
    
    def set_cost(self, cost: float):
        self.cost = cost

    def get_followup(self):
        return self.followup

    def __str__(self):
        return f"\nName: {self.name}\nParameters: {self.parameters}\nDescription: {self.description}\nTags: {self.tags}\nCost: {self.cost}\nFollowup: {self.followup}"
    
    def __repr__(self):
        return f"NewAction(name='{self.name}', parameters='{self.parameters}', description='{self.description}', tags='{self.tags}', cost='{self.cost}', followup='{self.followup}')"
    
class Action(NewAction):
    def __init__(self, action_id: uuid.UUID, time: datetime, apikey_id: uuid.UUID, name: str, parameters: str, description: str, tags: list[str], cost: float, followup: bool):
        super().__init__(name, parameters, description, tags, cost, followup)
        self.action_id = action_id
        self.time = time
        self.apikey_id = apikey_id

    def get_action_id(self):
        return self.action_id

    def get_apikey_id(self):
        return self.apikey_id

    def get_time(self):
        return self.time

    def __str__(self):
        return f"\nAction ID: {self.action_id}\nTime: {self.time}\nAPI Key ID: {self.apikey_id}\nName: {self.name}\nParameters: {self.parameters}\nDescription: {self.description}\nTags: {self.tags}\nCost: {self.cost}\nFollowup: {self.followup}"
    
    def __repr__(self):
        return f"Action(action_id='{self.action_id}', time='{self.time}', apikey_id='{self.apikey_id}', name='{self.name}', parameters='{self.parameters}', description='{self.description}', tags='{self.tags}', cost='{self.cost}', followup='{self.followup}')"

class NewPost:
    def __init__(self, description: str, context: str):
        self.description = description
        self.context = context

    def get_description(self):
        return self.description

    def get_context(self):
        return self.context

    def __str__(self):
        return f"\nDescription: {self.description}\nContext: {self.context}"

    def __repr__(self):
        return f"NewPost(description='{self.description}', context='{self.context}')"

class Post(NewPost):
    def __init__(self, post_id: uuid.UUID, time: datetime, description: str, context: str, apikey_id: uuid.UUID, resolved: bool):
        super().__init__(description, context)
        self.post_id = post_id
        self.time = time
        self.apikey_id = apikey_id
        self.resolved = resolved

    def get_post_id(self):
        return self.post_id

    def get_time(self):
        return self.time

    def get_apikey_id(self):
        return self.apikey_id

    def get_resolved(self):
        return self.resolved
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            post_id=uuid.UUID(data["post_id"]),
            time=datetime.fromisoformat(data["time"]),
            description=data["description"],
            context=data["context"] if "context" in data else None,
            apikey_id=uuid.UUID(data["apikey_id"]),
            resolved=data["resolved"]
        )
    
    def to_dict(self):
        return {
            "post_id": str(self.post_id),
            "time": self.time.isoformat(),
            "description": self.description,
            "context": self.context,
            "apikey_id": str(self.apikey_id),
            "resolved": self.resolved
        }

    def __str__(self):
        return f"\nPost ID: {self.post_id}\nTime: {self.time}\nDescription: {self.description}\nContext: {self.context}\nAPI Key ID: {self.apikey_id}\nResolved: {self.resolved}"

    def __repr__(self):
        return f"Post(post_id='{self.post_id}', time='{self.time}', description='{self.description}', context='{self.context}', apikey_id='{self.apikey_id}', resolved='{self.resolved}')"

class NewResponse:
    def __init__(self, post_id: uuid.UUID, description: str):
        self.post_id = post_id
        self.description = description

    def get_post_id(self):
        return self.post_id

    def get_description(self):
        return self.description
    
    def __str__(self):
        return f"\nPost ID: {self.post_id}\nDescription: {self.description}"

    def __repr__(self):
        return f"NewResponse(post_id='{self.post_id}', description='{self.description}')"
    
class Response(NewResponse):
    def __init__(self, response_id: uuid.UUID, time: datetime, post_id: uuid.UUID,  description: str, apikey_id: uuid.UUID | None = None):
        super().__init__(post_id, description)
        self.response_id = response_id
        self.apikey_id = apikey_id
        self.time = time

    def get_response_id(self):
        return self.response_id
    
    def get_apikey_id(self):
        return self.apikey_id

    def get_time(self):
        return self.time
    
    # Serialization method (to_dict)
    def to_dict(self):
        # Initial dictionary with all fields
        data = {
            "response_id": str(self.response_id),
            "time": self.time.isoformat(),  # Convert datetime to ISO 8601 string
            "post_id": str(self.post_id),
            "apikey_id": str(self.apikey_id) if self.apikey_id else None,
            "description": self.description
        }

        # Remove None values
        return {k: v for k, v in data.items() if v is not None}

    # Deserialization method (from_dict)
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            response_id=uuid.UUID(data["response_id"]),
            time=datetime.fromisoformat(data["time"]),  # Convert ISO 8601 string back to datetime
            post_id=uuid.UUID(data["post_id"]),
            apikey_id=uuid.UUID(data["apikey_id"]) if data.get("apikey_id") else None,
            description=data.get("description", '')  # Defaults to an empty string if 'description' is missing
        )

    def __str__(self):
        return f"\nResponse ID: {self.response_id}\nTime: {self.time}\nPost ID: {self.post_id}\nAPI Key ID: {self.apikey_id}\nDescription: {self.description}"
    
    def __repr__(self):
        return f"Response(response_id='{self.response_id}', time='{self.time}', post_id='{self.post_id}', apikey_id='{self.apikey_id}', description='{self.description}')"

class NewActioncall:
    def __init__(self, action_id: uuid.UUID, post_id: uuid.UUID, parameters: str):
        self.action_id = action_id
        self.post_id = post_id
        self.parameters = parameters

    def get_action_id(self):
        return self.action_id
    
    def get_post_id(self):
        return self.post_id
    
    def get_parameters(self):
        return self.parameters
    
    def __str__(self):
        return f"Action ID: {self.action_id}\nPost ID: {self.post_id}\nParameters: {self.parameters}"
    
    def __repr__(self):
        return f"NewActioncall(action_id='{self.action_id}', post_id='{self.post_id}', parameters='{self.parameters}')"
    
class Actioncall(NewActioncall):
    def __init__(self, actioncall_id: uuid.UUID, apikey_id: uuid.UUID, time: datetime, action_id: uuid.UUID, post_id: uuid.UUID, parameters: str):
        super().__init__(action_id, post_id, parameters)
        self.apikey_id = apikey_id
        self.actioncall_id = actioncall_id
        self.time = time

    def get_apikey_id(self):
        return self.apikey_id

    def get_actioncall_id(self):
        return self.actioncall_id
    
    def get_time(self):
        return self.time
    
    # Serialization method (to_dict)
    def to_dict(self):
        return {
            "actioncall_id": str(self.actioncall_id),
            "apikey_id": str(self.apikey_id),
            "time": self.time.isoformat(),  # Convert datetime to ISO 8601 string
            "action_id": str(self.action_id),
            "post_id": str(self.post_id),
            "parameters": self.parameters
        }

    # Deserialization method (from_dict)
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            actioncall_id=uuid.UUID(data["actioncall_id"]),
            apikey_id=uuid.UUID(data["apikey_id"]),
            time=datetime.fromisoformat(data["time"]),
            action_id=uuid.UUID(data["action_id"]),
            post_id=uuid.UUID(data["post_id"]),
            parameters=data["parameters"]
        )
    
    def __str__(self):
        return f"\nActioncall ID: {self.actioncall_id}\nAPI Key ID: {self.apikey_id}\nTime: {self.time}\nAction ID: {self.action_id}\nPost ID: {self.post_id}\nParameters: {self.parameters}"
    
    def __repr__(self):
        return f"Actioncall(actioncall_id='{self.actioncall_id}', apikey_id='{self.apikey_id}', time='{self.time}', action_id='{self.action_id}', post_id='{self.post_id}', parameters='{self.parameters}')"

class NewFile:
    def __init__(self, extension: str):
        self.extension = extension
    
    def get_extension(self):
        return self.extension
    
    def __str__(self):
        return f"\nExtension: {self.extension}"
    
    def __repr__(self):
        return f"NewFile(extension='{self.extension}')"
    
class File(NewFile):
    def __init__(self, file_id: uuid.UUID, time: datetime, apikey_id: uuid.UUID, extension: str):
        super().__init__(extension)
        self.file_id = file_id
        self.time = time
        self.apikey_id = apikey_id

    def get_file_id(self):
        return self.file_id
    
    def get_apikey_id(self):
        return self.apikey_id
    
    def get_time(self):
        return self.time
    
    def __str__(self):
        return f"\nFile ID: {self.file_id}\nTime: {self.time}\nAPI Key ID: {self.apikey_id}\nExtension: {self.extension}"
    
    def __repr__(self):
        return f"File(file_id='{self.file_id}', time='{self.time}', apikey_id='{self.apikey_id}', extension='{self.extension}')"

class NewHistoryElement:
    def __init__(self, text: str, tree_id: uuid.UUID, parent_id: uuid.UUID = None, apikey_id: uuid.UUID = None, role: str | None = None, file_ids: list[uuid.UUID] = None, name: str | None = None):
        self.text = text
        self.file_ids = file_ids if file_ids else []
        self.tree_id = tree_id
        self.parent_id = parent_id
        self.apikey_id = apikey_id
        self.role = role
        self.name = name

    def get_text(self):
        return self.text

    def get_file_ids(self):
        return self.file_ids
    
    def get_tree_id(self):
        return self.tree_id
    
    def get_parent_id(self):
        return self.parent_id

    def get_apikey_id(self):
        return self.apikey_id
    
    def get_role(self):
        return self.role
    
    def get_name(self):
        return self.name

    def __str__(self):
        return f"\nText: {self.text}\nFile IDs: {[str(file_id) for file_id in self.file_ids]}\nTree ID: {self.tree_id}\nParent ID: {self.parent_id}\nAPI Key ID: {self.apikey_id}\nRole: {self.role}\nName: {self.name}"
    
    def __repr__(self):
        return f"NewHistoryElement(text='{self.text}', file_ids='{self.file_ids}', tree_id='{self.tree_id}', parent_id='{self.parent_id}', apikey_id='{self.apikey_id}', role='{self.role}', name='{self.name}')"

class HistoryElement(NewHistoryElement):
    def __init__(self, history_id: uuid.UUID, role: uuid.UUID, name: str, text: str, time: datetime, apikey_id: uuid.UUID | None, file_ids: list[uuid.UUID] = None, tree_id: uuid.UUID = None, parent_id: uuid.UUID = None):
        super().__init__(text, tree_id, parent_id, apikey_id, role, file_ids, name)
        self.history_id = history_id
        self.time = time

    def get_history_id(self):
        return self.history_id

    def get_time(self):
        return self.time
    
    # Serialization method (to_dict)
    def to_dict(self):
        # Initial dictionary with all fields
        data = {
            "history_id": str(self.history_id),
            "time": self.time.isoformat(), 
            "role": self.role,
            "name": self.name,
            "text": self.text,
            "apikey_id": str(self.apikey_id) if self.apikey_id else None,
            # Convert file_ids to JSON string if it's not empty, otherwise use an empty string
            "file_ids": json.dumps([str(file_id) for file_id in self.file_ids]) if self.file_ids else '[]',
            "tree_id": str(self.tree_id) if self.tree_id else None,
            "parent_id": str(self.parent_id) if self.parent_id else None
        }

        # Remove None values
        return {k: v for k, v in data.items() if v is not None}


    # Deserialization method (from_dict)
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            history_id=uuid.UUID(data["history_id"]),
            role=data["role"],
            name=data.get('name'),  # Handle missing 'name', defaults to None
            text=data["text"],
            time=datetime.fromisoformat(data["time"]),  # Convert ISO 8601 string back to datetime
            apikey_id=uuid.UUID(data["apikey_id"]) if data.get("apikey_id") else None,  
            
            # Decode file_ids JSON string into a list of strings, or None if missing
            file_ids=[uuid.UUID(file_id) for file_id in json.loads(data.get("file_ids", "[]"))],

            # Handle missing 'tree_id', default to None if the key is missing
            tree_id=uuid.UUID(data["tree_id"]) if data.get("tree_id") else None,

            # Handle missing 'parent_id', default to None if the key is missing
            parent_id=uuid.UUID(data["parent_id"]) if data.get("parent_id") else None
        )


    def __str__(self):
        return f"\nHistory ID: {self.history_id}\nRole: {self.role}\nName: {self.name}\nTime: {self.time}\nAPI Key ID: {self.apikey_id}\nText: {self.text}\nFile IDs: {[str(file_id) for file_id in self.file_ids]}\nTree ID: {self.tree_id}\nParent ID: {self.parent_id}"
    
    def __repr__(self):
        return f"HistoryElement(history_id='{self.history_id}', role='{self.role}', name='{self.name}', time='{self.time}', apikey_id='{self.apikey_id}', text='{self.text}', file_ids='{self.file_ids}', tree_id='{self.tree_id}', parent_id='{self.parent_id}')"
    
class BidRequest():
    def __init__(self, action_id: uuid.UUID, post: Post):
        self.action_id = action_id
        self.post = post

    def get_action_id(self):
        return self.action_id
    
    def get_post(self):
        return self.post
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            action_id=uuid.UUID(data["action_id"]),
            post=Post.from_dict(data["post"])
        )
    
    def to_dict(self):
        return {
            "action_id": str(self.action_id),
            "post": self.post.to_dict()
        }
    
    def __str__(self):
        return f"\nAction ID: {self.action_id}\nPost: {self.post}"
    
    def __repr__(self):
        return f"BidRequest(action_id='{self.action_id}', post='{self.post}')"
    
class BidResponse():
    def __init__(self, action_id: uuid.UUID, post_id: uuid.UUID, cost: float | None):
        self.action_id = action_id
        self.post_id = post_id
        self.cost = cost

    def get_action_id(self):
        return self.action_id
    
    def get_post_id(self):
        return self.post_id
    
    def get_cost(self):
        return self.cost
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            action_id=uuid.UUID(data["action_id"]),
            post_id=uuid.UUID(data["post_id"]),
            cost=float.fromhex(data["cost"]) if data.get("cost") is not None else None
        )
    
    def to_dict(self):
        return {
            "action_id": str(self.action_id),
            "post_id": str(self.post_id),
            "cost": self.cost.hex() if self.cost is not None else None
        }
    
    def __str__(self):
        return f"\nAction ID: {self.action_id}\nPost ID: {self.post_id}\nCost: {self.cost}"
    
    def __repr__(self):
        return f"BidResponse(action_id='{self.action_id}', post_id='{self.post_id}', cost='{self.cost}')"

class PaymentRequest():
    def __init__(self, actioncall_id: uuid.UUID, post_id: uuid.UUID, payment_link: str):
        self.actioncall_id = actioncall_id
        self.post_id = post_id
        self.payment_link = payment_link

    def get_actioncall_id(self):
        return self.actioncall_id

    def get_post_id(self):
        return self.post_id
    
    def get_payment_link(self):
        return self.payment_link
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            actioncall_id=uuid.UUID(data["actioncall_id"]),
            post_id=uuid.UUID(data["post_id"]),
            payment_link=data["payment_link"]
        )
    
    def to_dict(self):
        return {
            "actioncall_id": str(self.actioncall_id),
            "post_id": str(self.post_id),
            "payment_link": self.payment_link
        }
    
    def __str__(self):
        return f"\nActioncall ID: {self.actioncall_id}\nPost ID: {self.post_id}\nPayment Link: {self.payment_link}"
    
    def __repr__(self):
        return f"PaymentRequest(actioncall_id='{self.actioncall_id}', post_id='{self.post_id}', payment_link='{self.payment_link}')"

class Location():
    def __init__(self, latitude: float, longitude: float):
        self.latitude = latitude
        self.longitude = longitude

    def get_longitude(self):
        return self.longitude
    
    def get_latitude(self):
        return self.latitude
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            latitude=data["latitude"],
            longitude=data["longitude"]
        )
    
    def to_dict(self):
        return {
            "latitude": self.latitude,
            "longitude": self.longitude
        }
    
    def __str__(self):
        return f"\nLatitude: {self.latitude}\nLongitude: {self.longitude}"
    
    def __repr__(self):
        return f"Location(latitude='{self.latitude}', longitude='{self.longitude}')"   

class PAUserMessage():
    def __init__(self, ui_id: str, text: str):
        self.ui_id = ui_id
        self.text = text

    def get_ui_id(self):
        return self.ui_id
    
    def get_text(self):
        return self.text
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            ui_id=data["ui_id"],
            text=data["text"]
        )
    
    def to_dict(self):
        return {
            "ui_id": self.ui_id,
            "text": self.text
        }
    
    def __str__(self):
        return f"\nUI ID: {self.ui_id}\nText: {self.text}"
    
    def __repr__(self):
        return f"PAUserMessage(ui_id='{self.ui_id}', text='{self.text}')"
    
class PAPaymentRequest():
    def __init__(self, ui_id: str, payment_link: str):
        self.ui_id = ui_id
        self.payment_link = payment_link

    def get_ui_id(self):
        return self.ui_id
    
    def get_payment_link(self):
        return self.payment_link
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            ui_id=data["ui_id"],
            payment_link=data["payment_link"]
        )
    
    def to_dict(self):
        return {
            "ui_id": self.ui_id,
            "payment_link": self.payment_link
        }
    
    def __str__(self):
        return f"\nUI ID: {self.ui_id}\nPayment Link: {self.payment_link}"
    
    def __repr__(self):
        return f"PAPaymentRequest(ui_id='{self.ui_id}', payment_link='{self.payment_link}')"

class PALocationRequest():
    def __init__(self, ui_id: str):
        self.ui_id = ui_id

    def get_ui_id(self):
        return self.ui_id
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            ui_id=data["ui_id"]
        )
    
    def to_dict(self):
        return {
            "ui_id": self.ui_id
        }
    
    def __str__(self):
        return f"\nUI ID: {self.ui_id}"
    
    def __repr__(self):
        return f"PALocationRequest(ui_id='{self.ui_id}')" 
    
class PALocationResponse():
    def __init__(self, ui_id: str, location: Location):
        self.ui_id = ui_id
        self.location = location

    def get_ui_id(self):
        return self.ui_id

    def get_location(self):
        return self.location
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            ui_id=data["ui_id"],
            location=Location.from_dict(data["location"])
        )
    
    def to_dict(self):
        return {
            "ui_id": self.ui_id,
            "location": self.get_location().to_dict()
        }
    
    def __str__(self):
        return f"\nUI ID: {self.ui_id}\nLocation: {self.location}"
    
    def __repr__(self):
        return f"PALocationResponse(ui_id='{self.ui_id}', location='{self.location}')"

class PAUserResponse():
    def __init__(self, ui_id: str, text: str):
        self.ui_id = ui_id
        self.text = text

    def get_ui_id(self):
        return self.ui_id
    
    def get_text(self):
        return self.text
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            ui_id=data["ui_id"],
            text=data["text"]
        )
    
    def to_dict(self):
        return {
            "ui_id": self.ui_id,
            "text": self.text
        }
    
    def __str__(self):
        return f"\nUI ID: {self.ui_id}\nText: {self.text}"
    
    def __repr__(self):
        return f"PAUserResponse(ui_id='{self.ui_id}', text='{self.text}')"
    
class PANewConversation():
    def __init__(self, ui_id: str):
        self.ui_id = ui_id

    def get_ui_id(self):
        return self.ui_id
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            ui_id=data["ui_id"]
        )
    
    def to_dict(self):
        return {
            "ui_id": self.ui_id
        }
    
    def __str__(self):
        return f"\nUI ID: {self.ui_id}"
    
    def __repr__(self):
        return f"PANewConversation(ui_id='{self.ui_id}')"
    
class PASupportRequest():
    def __init__(self, ui_id: str, text: str):
        self.ui_id = ui_id
        self.text = text

    def get_ui_id(self):
        return self.ui_id
    
    def get_text(self):
        return self.text
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            ui_id=data["ui_id"],
            text=data["text"]
        )
    
    def to_dict(self):
        return {
            "ui_id": self.ui_id,
            "text": self.text
        }
    
    def __str__(self):
        return f"\nUI ID: {self.ui_id}\nText: {self.text}"
    
    def __repr__(self):
        return f"PASupportRequest(ui_id='{self.ui_id}', text='{self.text}')"
    
class PAUrl():
    def __init__(self, url: str):
        self.url = url

    def get_url(self):
        return self.url
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            url=data["url"]
        )
    
    def to_dict(self):
        return {
            "url": self.url
        }
    
    def __str__(self):
        return f"\nUrl: {self.url}"
    
    def __repr__(self):
        return f"PAUrl(url='{self.url}')"
    
class Url():
    def __init__(self, url: str):
        self.url = url

    def get_url(self):
        return self.url
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            url=data["url"]
        )
    
    def to_dict(self):
        return {
            "url": self.url
        }
    
    def __str__(self):
        return f"\nUrl: {self.url}"
    
    def __repr__(self):
        return f"Url(url='{self.url}')"
    