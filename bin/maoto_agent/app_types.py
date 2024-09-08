from datetime import datetime
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
    def __init__(self, apikey_id: uuid.UUID, time: datetime, user_id: uuid.UUID, name: str, roles: list):
        self.apikey_id = apikey_id
        self.time = time
        self.user_id = user_id
        self.name = name
        self.roles = roles

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
    
    def __str__(self):
        return f"\nAPI Key ID: {self.apikey_id}\nTime: {self.time}\nUser ID: {self.user_id}\nKey Name: {self.name}\nRoles: {self.roles}"
    
    def __repr__(self):
        return f"ApiKey(apikey_id='{self.apikey_id}', time='{self.time}', user_id='{self.user_id}', name='{self.name}', roles='{self.roles}')"
    
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
    def __init__(self, response_id: uuid.UUID, time: datetime, post_id: uuid.UUID, apikey_id: uuid.UUID, description: str):
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

    def __str__(self):
        return f"\nResponse ID: {self.response_id}\nTime: {self.time}\nPost ID: {self.post_id}\nAPI Key ID: {self.apikey_id}\nDescription: {self.description}"
    
    def __repr__(self):
        return f"Response(response_id='{self.response_id}', time='{self.time}', post_id='{self.post_id}', apikey_id='{self.apikey_id}', description='{self.description}')"

class NewActioncall:
    def __init__(self, action_id: uuid.UUID, post_id: uuid.UUID, parameters: str, cost: float):
        self.action_id = action_id
        self.post_id = post_id
        self.parameters = parameters
        self.cost = cost

    def get_action_id(self):
        return self.action_id
    
    def get_post_id(self):
        return self.post_id
    
    def get_parameters(self):
        return self.parameters
    
    def get_cost(self):
        return self.cost
    
    def __str__(self):
        return f"Action ID: {self.action_id}\nPost ID: {self.post_id}\nParameters: {self.parameters}\nCost: {self.cost}"
    
    def __repr__(self):
        return f"NewActioncall(action_id='{self.action_id}', post_id='{self.post_id}', parameters='{self.parameters}', cost='{self.cost}')"
    
class Actioncall(NewActioncall):
    def __init__(self, actioncall_id: uuid.UUID, apikey_id: uuid.UUID, time: datetime, action_id: uuid.UUID, post_id: uuid.UUID, parameters: str, cost: float):
        super().__init__(action_id, post_id, parameters, cost)
        self.apikey_id = apikey_id
        self.actioncall_id = actioncall_id
        self.time = time

    def get_apikey_id(self):
        return self.apikey_id

    def get_actioncall_id(self):
        return self.actioncall_id
    
    def get_time(self):
        return self.time
    
    def __str__(self):
        return f"\nActioncall ID: {self.actioncall_id}\nAPI Key ID: {self.apikey_id}\nTime: {self.time}\nAction ID: {self.action_id}\nPost ID: {self.post_id}\nParameters: {self.parameters}\nCost: {self.cost}"
    
    def __repr__(self):
        return f"Actioncall(actioncall_id='{self.actioncall_id}', apikey_id='{self.apikey_id}', time='{self.time}', action_id='{self.action_id}', post_id='{self.post_id}', parameters='{self.parameters}', cost='{self.cost}')"

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
