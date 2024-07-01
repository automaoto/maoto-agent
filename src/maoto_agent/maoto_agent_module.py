import os
import json
import uuid
from datetime import datetime
from graphqlclient import GraphQLClient

class MNewUser:
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password

    def get_username(self):
        return self.username
    
    def __str__(self):
        return f"Username: {self.username}"
    
    def __repr__(self):
        return f"MNewUser(username='{self.username}')"

class MUser:
    def __init__(self, username: str, userId: uuid.UUID, time: datetime):
        self.username = username
        self.userId = userId
        self.time = time

    def get_username(self):
        return self.username
    
    def get_user_id(self):
        return self.userId
    
    def get_time(self):
        return self.time
    
    def __str__(self):
        return f"Username: {self.username}\nUser ID: {self.userId}\nTime: {self.time}"
    
    def __repr__(self):
        return f"MUser(username='{self.username}', userId='{self.userId}', time='{self.time}')"
    
class MNewApiKey:
    def __init__(self, apiKeyName: str, userId: uuid.UUID):
        self.apiKeyName = apiKeyName
        self.userId = userId

    def get_api_key_name(self):
        return self.apiKeyName
    
    def get_user_id(self):
        return self.userId
    
    def __str__(self):
        return f"API Key Name: {self.apiKeyName}\nUser ID: {self.userId}"
    
    def __repr__(self):
        return f"MNewApiKey(apiKeyName='{self.apiKeyName}', userId='{self.userId}')"

class MApiKey:
    def __init__(self, apiKeyId: uuid.UUID, userId: uuid.UUID, time: datetime, apiKeyName: str):
        self.apiKeyId = apiKeyId
        self.userId = userId
        self.time = time
        self.apiKeyName = apiKeyName

    def get_api_key_id(self):
        return self.apiKeyId
    
    def get_user_id(self):
        return self.userId
    
    def get_time(self):
        return self.time
    
    def get_api_key_name(self):
        return self.apiKeyName
    
    def __str__(self):
        return f"API Key ID: {self.apiKeyId}\nUser ID: {self.userId}\nTime: {self.time}\nAPI Key Name: {self.apiKeyName}"
    
    def __repr__(self):
        return f"MApiKey(apiKeyId='{self.apiKeyId}', userId='{self.userId}', time='{self.time}', apiKeyName='{self.apiKeyName}')"

class MTask:
    def __init__(self, description: str, context: str):
        self.description = description
        self.context = context

    def get_description(self):
        return self.description

    def get_context(self):
        return self.context
    
    def __str__(self):
        return f"Description: {self.description}\nContext: {self.context}"
    
    def __repr__(self):
        return f"MTask(description='{self.description}', context='{self.context}')"
    
class MAuction:
    def __init__(self, postId: uuid.UUID, start: datetime, bidIds: list):
        self.postId = postId
        self.start = start
        self.bidIds = bidIds

    def get_post_id(self):
        return self.postId
    
    def get_start(self):
        return self.start
    
    def get_bid_ids(self):
        return self.bidIds
    
    def __str__(self):
        return f"Post ID: {self.postId}\nStart: {self.start}\nBid IDs: {self.bidIds}"
    
    def __repr__(self):
        return f"MAuction(postId={self.postId!r}, start={self.start!r}, bidIds={self.bidIds!r})"
    
class MBidPost:
    def __init__(self, bidId: uuid.UUID, amount: float, userId: uuid.UUID, time: datetime, auctionId: uuid.UUID, postId: uuid.UUID):
        self.bidId = bidId
        self.amount = amount
        self.userId = userId
        self.time = time
        self.auctionId = auctionId
        self.postId = postId

    def get_bidId(self):
        return self.bidId
    
    def get_amount(self):
        return self.amount
    
    def get_user_id(self):
        return self.userId
    
    def get_time(self):
        return self.time
    
    def get_auction_id(self):
        return self.auctionId
    
    def __str__(self):
        return f"Bid ID: {self.bidId}\nAmount: {self.amount}\nUser ID: {self.userId}\nTime: {self.time}\nAuction ID: {self.auctionId}\nPost ID: {self.postId}"
    
    def __repr__(self):
        return (f"MBidPost(bidId={repr(self.bidId)}, amount={repr(self.amount)}, "
                f"userId={repr(self.userId)}, time={repr(self.time)}, "
                f"auctionId={repr(self.auctionId)}, "
                f"postId={repr(self.postId)})")

class MBid:
    def __init__(self, postId: uuid.UUID, amount: float):
        self.postId = postId
        self.amount = amount

    def get_postId(self):
        return self.postId
    
    def get_amount(self):
        return self.amount
    
    def __str__(self):
        return f"Post ID: {self.postId}\nAmount: {self.amount}"
    
    def __repr__(self):
        return f"MBid(postId={repr(self.postId)}, amount={repr(self.amount)})"

class MPost(MTask):
    def __init__(self, task: MTask, postId: uuid.UUID, splits: int, userId: uuid.UUID, time: datetime, parentId: uuid.UUID = None, resolved: bool = False, auctioned: bool = False):
        super().__init__(task.description, task.context)
        self.postId = postId
        self.parentId = parentId
        self.resolved = resolved
        self.auctioned = auctioned
        self.splits = splits
        self.userId = userId
        self.time = time

    def get_postId(self):
        return self.postId

    def get_parent_id(self):
        return self.parentId
    
    def get_resolved(self):
        return self.resolved
    
    def get_auctioned(self):
        return self.auctioned
    
    def get_splits(self):
        return self.splits
    
    def get_user_id(self):
        return self.userId
    
    def get_time(self):
        return self.time
    
    def __str__(self):
        return f"ID: {self.postId}\nParent ID: {self.parentId}\nDescription: {self.description}\nContext: {self.context}\nSplits: {self.splits}\nResolved: {self.resolved}\nAuctioned: {self.auctioned}\nUser ID: {self.userId}\nTime: {self.time}"

    def __repr__(self):
        return (f"MPost(task=MTask(description={self.description!r}, context={self.context!r}), "
                f"postId={self.postId!r}, parentId={self.parentId!r}, resolved={self.resolved!r}, "
                f"auctioned={self.auctioned!r}, splits={self.splits!r}, userId={self.userId!r}, "
                f"time={self.time!r})")

class Marketplace:
    def __init__(self, api_key=None, url_flask=None):
        self.url_flask = url_flask or os.environ.get("RESOLVER_API_URL", "http://marketplace.maoto.world:4000")
        self.graphql_url = self.url_flask + "/graphql"
        self.client = GraphQLClient(self.graphql_url)

        self.api_key = api_key or os.environ.get("M_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required.")
        self.client.inject_token("Authentication", self.api_key)
        self.userId = self._get_userId(self)

    def _get_userId(self):
        query = '''
            mutation {
                getUserId {
                    userId
                }
            }
        '''
        response = self.client.execute(query)
        return json.loads(response)["data"]["getUserId"]["userId"]
    
    def get_userId(self):
        return self.userId

    def create_users(self, m_new_users):
        users = []
        for m_new_user in m_new_users:
            username = m_new_user.username
            password = m_new_user.password
            users.append(f'{{username: "{username}", password: "{password}"}}')

        query = '''
        mutation createUsers {
            createUsers(users: [%s]) {
                users {
                    username
                    userId
                    time
                }
            }
        }
        ''' % ', '.join(users)

        result = self.client.execute(query)
        data_list = json.loads(result)["data"]["createUsers"]["users"]

        for data in data_list:
            m_user = MUser(data["username"], uuid.UUID(data["userId"]), datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%S"))
            users.append(m_user)
        
        return users
    
    def delete_users(self, users):
        success_list = []
        id_list = []
        for user in users:
            user_id = user.get_user_id() if isinstance(user, MUser) else user
            id_list.append(f'"{user_id}"')
        
        id_list = [str(user.get_user_id()) for user in users]
        id_string = ', '.join(id_list)

        query = f'''
        mutation deleteUsers {{
            deleteUsers(userIds: [{id_string}]) {{
                successList
            }}
        }}
        '''

        result = self.client.execute(query)
        data = json.loads(result)["data"]["deleteUsers"]
        success_list = data["successList"]

        return success_list
    
    def get_users(self):
        query = '''
        mutation getUsers {
            getUsers() {
                users {
                    username
                    userId
                    time
                }
            }
        }
        '''

        result = self.client.execute(query)
        data_list = json.loads(result)["data"]["getUsers"]["users"]
        users = [MUser(data["username"], uuid.UUID(data["userId"]), datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%S")) for data in data_list]

        return users
    
    def create_api_keys(self, m_new_users):
        api_keys = []
        for m_new_user in m_new_users:
            api_key_name = m_new_user.apiKeyName
            user_id = m_new_user.userId
            api_keys.append(f'{{apiKeyName: "{api_key_name}", userId: "{user_id}"}}')

        query = '''
        mutation createApiKeys {
            createApiKeys(apiKeys: [%s]) {
                apiKeys {
                    apiKeyId
                    userId
                    time
                    apiKeyName
                }
            }
        }
        ''' % ', '.join(api_keys)

        result = self.client.execute(query)
        data_list = json.loads(result)["data"]["createApiKeys"]["apiKeys"]

        for data in data_list:
            m_api_key = MApiKey(uuid.UUID(data["apiKeyId"]), uuid.UUID(data["userId"]), datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%S"), data["apiKeyName"])
            api_keys.append(m_api_key)

        return api_keys
    
    def delete_api_keys(self, api_keys):
        success_list = []
        id_list = []
        for api_key in api_keys:
            api_key_id = api_key.get_api_key_id() if isinstance(api_key, MApiKey) else api_key
            id_list.append(f'"{api_key_id}"')
        
        id_list = [str(api_key.get_api_key_id()) for api_key in api_keys]
        id_string = ', '.join(id_list)
        
        query = f'''
        mutation deleteApiKeys {{
            deleteApiKeys(apiKeyIds: [{id_string}]) {{
                successList
            }}
        }}
        '''
        
        # Execute the mutation query
        result = self.client.execute(query)
        data = json.loads(result)["data"]["deleteApiKeys"]

        # Parse the result to get the success list
        success_list = data["successList"]
        
        return success_list
    
    def get_api_keys(self, users):
        
        api_keys = []
        userIds = []
        for user in users:
            userId = user.get_user_id() if isinstance(user, MUser) else user
            userIds.append(f'"{userId}"')

        userIds = [str(user.get_user_id()) for user in users]
        user_ids = ', '.join(userIds)

        query = '''
        mutation getApiKeys($ids: [ID!]!) {
            getApiKeys(userIds: $ids) {
                apiKeys {
                    apiKeyId
                    userId
                    time
                    apiKeyName
                }
            }
        }
        '''

        variables = {'ids': user_ids}
        result = self.client.execute(query, variables)
        data_list = json.loads(result)["data"]["getApiKeys"]["apiKeys"]
        api_keys = [MApiKey(uuid.UUID(data["apiKeyId"]), uuid.UUID(data["userId"]), datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%S"), data["apiKeyName"]) for data in data_list]

        return api_keys
            

    def post_tasks(self, m_tasks):
        m_posts = []
        tasks = []
        
        for m_task in m_tasks:
            description = m_task.get_description()
            context = m_task.get_context()
            tasks.append(f'{{description: "{description}", context: "{context}"}}')

        query = '''
        mutation postTasks {
            postTasks(tasks: [%s]) {
                posts {
                    postId
                    parentId
                    description
                    context
                    splits
                    resolved
                    auctioned
                    userId
                    time
                }
            }
        }
        ''' % ', '.join(tasks)

        result = self.client.execute(query)
        data_list = json.loads(result)["data"]["postTasks"]["posts"]

        for data in data_list:
            m_post = MPost(MTask(data["description"], data["context"]),
                    postId=uuid.UUID(data["postId"]),
                    splits=data["splits"],
                    userId=uuid.UUID(data["userId"]),
                    time=datetime.strptime(data["time"], "%Y-%m-%dT%H:%M:%S"),
                    parentId=uuid.UUID(data["parentId"]) if data["parentId"] else None,
                    resolved=data["resolved"],
                    auctioned=data["auctioned"])
            m_posts.append(m_post)

        return m_posts

    def delete_posts(self, posts):
        success_list = []
        id_list = []
        for post in posts:
            post_id = post.get_postId() if isinstance(post, MPost) else post
            id_list.append(f'"{post_id}"')
        
        id_string = ', '.join(id_list)
        
        query = f'''
        mutation {{
            deletePosts(postIds: [{id_string}]) {{
                successList
            }}
        }}
        '''
        
        # Execute the mutation query
        result = self.client.execute(query)
        data = json.loads(result)["data"]["deletePosts"]

        # Parse the result to get the success list
        success_list = data["successList"]
        
        return success_list
    
    def split_posts(self, parent_id, m_tasks):

        if isinstance(parent_id, MPost):
            parent_id = parent_id.get_postId()

        tasks = [
            {'description': task.get_description(), 'context': task.get_context()}
            for task in m_tasks
        ]

        query = '''
        mutation ($parentId: ID!, $tasks: [TaskType!]!) {
            splitPosts(parentId: $parentId, tasks: $tasks) {
                posts {
                    postId
                    parentId
                    description
                    context
                    splits
                    resolved
                    auctioned
                    userId
                    time
                }
            }
        }
        '''

        variables = {'parentId': str(parent_id), 'tasks': tasks}
        result = self.client.execute(query, variables)
        posts_data = json.loads(result)["data"]["splitPosts"]["posts"]

        return [
            MPost(
                MTask(post["description"], post["context"]),
                postId=uuid.UUID(post["postId"]),
                splits=post["splits"],
                userId=uuid.UUID(post["userId"]),
                time=datetime.strptime(post["time"], "%Y-%m-%dT%H:%M:%S"),
                parentId=uuid.UUID(post["parentId"]) if post["parentId"] else None,
                resolved=post["resolved"],
                auctioned=post["auctioned"]
            )
            for post in posts_data
        ]
    
    def resolve_posts(self, post_ids):
        success_list = []
        id_string = ', '.join([f'"{post.get_postId()}"' if isinstance(post, MPost) else f'"{post}"' for post in post_ids])
        
        query = f'''
        mutation {{
            resolvePosts(ids: [{id_string}]) {{
                successList
            }}
        }}
        '''
        
        # Execute the mutation query
        result = self.client.execute(query)
        data = json.loads(result)["data"]["resolvePosts"]

        # Parse the result to get the success list
        success_list = data["successList"]
        
        return success_list
    
    def bid_on_posts(self, bids):
        # Construct the bids list for the mutation query
        bid_list = ', '.join([f'{{amount: {bid.amount}, postId: "{bid.postId}"}}' for bid in bids])
        
        # Construct the mutation query
        query = f'''
        mutation {{
            bidOnPosts(bids: [{bid_list}]) {{
                successList
            }}
        }}
        '''

        # Execute the mutation query
        result = self.client.execute(query)
        data = json.loads(result)["data"]["bidOnPosts"]

        # Parse the result to get the success list
        success_list = data["successList"]
        
        return success_list

    def get_post_bids(self, post_ids):
        if post_ids and isinstance(post_ids[0], MPost):
            post_ids = [post.get_postId() for post in post_ids]
        post_ids = [str(post_id) for post_id in post_ids]
        
        query = '''
        mutation getPostBids($ids: [ID!]!) {
            getPostBids(postIds: $ids) {
                postBidLists {
                    bidId
                    amount
                    userId
                    time
                    auctionId
                    postId
                }
            }
        }
        '''

        variables = {'ids': post_ids}
        result = self.client.execute(query, variables)
        data = json.loads(result).get("data", {}).get("getPostBids", {}).get("postBidLists", [])
        post_bids = [[MBidPost(**bid) for bid in bids_list] for bids_list in data]
        
        return post_bids
    
    def get_posts(self, post_ids=None):
        post_ids = post_ids or []
        if post_ids and isinstance(post_ids[0], MPost):
            post_ids = [post.get_postId() for post in post_ids]
        post_ids = [str(post_id) for post_id in post_ids]

        query = f'''
        mutation getPosts($ids: [ID!]!) {{
            getPosts(ids: $ids) {{
                posts {{
                    postId
                    parentId
                    description
                    context
                    splits
                    resolved
                    auctioned
                    userId
                    time
                }}
            }}
        }}
        '''

        variables = {'ids': post_ids}
        result = self.client.execute(query, variables)
        data = json.loads(result).get("data", {}).get("getPosts", {}).get("posts", [])
        m_posts = [MPost(
            MTask(
                item["description"],
                item["context"]
            ),
            postId=uuid.UUID(item["postId"]),
            splits=item["splits"],
            userId=uuid.UUID(item["userId"]),
            time=datetime.strptime(item["time"], "%Y-%m-%dT%H:%M:%S"),
            parentId=uuid.UUID(item["parentId"]) if item["parentId"] else None,
            resolved=item["resolved"],
            auctioned=item["auctioned"]) for item in data
        ]
        
        return m_posts
