from maoto_agent import *

class OutsourcedMaotoAgentMethods(Maoto):
    def __init__(self, logging_level=logging.INFO, receive_messages=True, open_connection=False, db_connection=False):
        super().__init__(logging_level, receive_messages, open_connection, db_connection)

    @_sync_or_async
    async def get_own_user(self) -> User:
        query = gql_client('''
        query {
            getOwnUser {
                user_id
                username
                time
                roles
            }
        }
        ''')

        result = await self.client.execute_async(query)
        data = result["getOwnUser"]
        return User(data["username"], uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["roles"])

    @_sync_or_async
    async def get_own_api_key(self) -> ApiKey:
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

        result = await self.client.execute_async(query)
        data_list = result["getOwnApiKeys"]

        # Return the first API key (assume the list is ordered by time or relevance)
        if data_list:
            data = data_list[0]
            return ApiKey(
                apikey_id=uuid.UUID(data["apikey_id"]),
                user_id=uuid.UUID(data["user_id"]),
                time=datetime.fromisoformat(data["time"]),
                name=data["name"],
                roles=data["roles"]
            )
        else:
            raise Exception("No API keys found for the user.")


    @_sync_or_async
    async def get_own_api_keys(self) -> list[bool]:
        # Note: the used API key id is always the first one
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

        result = await self.client.execute_async(query)
        data_list = result["getOwnApiKeys"]
        return [ApiKey(uuid.UUID(data["apikey_id"]), uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["name"], data["roles"]) for data in data_list]

    @_sync_or_async
    async def create_users(self, new_users: list[NewUser]):
        users = [{'username': user.username, 'password': user.password, 'roles': user.roles} for user in new_users]
        query = gql_client('''
        mutation createUsers($new_users: [NewUser!]!) {
            createUsers(new_users: $new_users) {
                username
                user_id
                time
                roles
            }
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"new_users": users})
        data_list = result["createUsers"]
        return [User(data["username"], uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["roles"]) for data in data_list]

    @_sync_or_async
    async def delete_users(self, user_ids: list[User | str]) -> bool:
        user_ids = [str(user.get_user_id()) if isinstance(user, User) else str(user) for user in user_ids]
        query = gql_client('''
        mutation deleteUsers($user_ids: [ID!]!) {
            deleteUsers(user_ids: $user_ids)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"user_ids": user_ids})
        return result["deleteUsers"]
    
    @_sync_or_async
    async def get_users(self) -> list[User]:
        query = gql_client('''
        query {
            getUsers {
                user_id
                username
                time
                roles
            }
        }
        ''')

        result = await self.client.execute_async(query)
        data_list = result["getUsers"]
        return [User(data["username"], uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["roles"]) for data in data_list]
    
    @_sync_or_async
    async def create_apikeys(self, api_keys: list[NewApiKey]) -> list[ApiKey]:
        api_keys_data = [{'name': key.get_name(), 'user_id': str(key.get_user_id()), 'roles': key.get_roles()} for key in api_keys]
        query = gql_client('''
        mutation createApiKeys($new_apikeys: [NewApiKey!]!) {
            createApiKeys(new_apikeys: $new_apikeys) {
                apikey_id
                user_id
                name
                time
                roles
                value
            }
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"new_apikeys": api_keys_data})
        data_list = result["createApiKeys"]
        return [ApiKeyWithSecret(uuid.UUID(data["apikey_id"]), uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["name"], data["roles"], data["value"]) for data in data_list]
        
    @_sync_or_async
    async def delete_apikeys(self, apikey_ids: list[ApiKey | str]) -> list[bool]:
        api_key_ids = [str(apikey.get_apikey_id()) if isinstance(apikey, ApiKey) else str(apikey) for apikey in apikey_ids]
        query = gql_client('''
        mutation deleteApiKeys($apikey_ids: [ID!]!) {
            deleteApiKeys(apikey_ids: $apikey_ids)
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"apikey_ids": api_key_ids})
        return result["deleteApiKeys"]

    @_sync_or_async
    async def get_apikeys(self, user_ids: list[User | str]) -> list[ApiKey]:
        user_ids = [str(user.get_user_id()) if isinstance(user, User) else str(user) for user in user_ids]
        query = gql_client('''
        query getApiKeys($user_ids: [ID!]!) {
            getApiKeys(user_ids: $user_ids) {
                apikey_id
                user_id
                name
                time
                roles
            }
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"user_ids": user_ids})
        data_list = result["getApiKeys"]
        return [ApiKey(uuid.UUID(data["apikey_id"]), uuid.UUID(data["user_id"]), datetime.fromisoformat(data["time"]), data["name"], data["roles"]) for data in data_list]

    @_sync_or_async
    async def _download_file_async(self, file_id: str, destination_dir: Path) -> File:
        query = gql_client('''
        query downloadFile($file_id: ID!) {
            downloadFile(file_id: $file_id) {
                file_id
                apikey_id
                extension
                time
            }
        }
        ''')

        result = await self.client.execute_async(query, variable_values={"file_id": file_id})
        file_metadata = result["downloadFile"]
        
        download_url = f"{self.server_url}/download/{str(file_id)}"
        async with aiohttp.ClientSession() as session:
            async with session.get(download_url, headers={"Authorization": self.apikey_value}) as response:
                if response.status == 200:
                    filename = f"{str(file_id)}{file_metadata['extension']}"
                    destination_path = destination_dir / filename
                    
                    async with aiofiles.open(destination_path, 'wb') as f:
                        while True:
                            chunk = await response.content.read(DATA_CHUNK_SIZE)
                            if not chunk:
                                break
                            await f.write(chunk)

                    return File(
                        file_id=uuid.UUID(file_metadata["file_id"]),
                        apikey_id=uuid.UUID(file_metadata["apikey_id"]),
                        extension=file_metadata["extension"],
                        time=datetime.fromisoformat(file_metadata["time"])
                    )
                else:
                    raise Exception(f"Failed to download file: {response.status}")

    @_sync_or_async
    async def download_files(self, file_ids: list[str], download_dir: Path) -> list[File]:
        downloaded_files = []
        for file_id in file_ids:
            downloaded_file = await self._download_file_async(file_id, download_dir)
            downloaded_files.append(downloaded_file)
        return downloaded_files

    @_sync_or_async
    async def _upload_file_async(self, file_path: Path) -> File:
        new_file = NewFile(
            extension=file_path.suffix,
        )
        query_str = '''
        mutation uploadFile($new_file: NewFile!, $file: Upload!) {
            uploadFile(new_file: $new_file, file: $file) {
                file_id
                apikey_id
                extension
                time
            }
        }'''
        async with aiohttp.ClientSession() as session:
            async with aiofiles.open(file_path, 'rb') as f:
                form = aiohttp.FormData()
                form.add_field('operations', json.dumps({
                    'query': query_str,
                    'variables': {"new_file": {"extension": new_file.get_extension()}, "file": None}
                }))
                form.add_field('map', json.dumps({
                    '0': ['variables.file']
                }))
                form.add_field('0', await f.read(), filename=str(file_path))

                headers = {
                    "Authorization": self.apikey_value
                }
                async with session.post(self.graphql_url, data=form, headers=headers) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to upload file: {response.status}")
                    result = await response.json()

        file_metadata = result["data"]["uploadFile"]
        return File(
            file_id=uuid.UUID(file_metadata["file_id"]),
            apikey_id=uuid.UUID(file_metadata["apikey_id"]),
            extension=file_metadata["extension"],
            time=datetime.fromisoformat(file_metadata["time"])
        )

    @_sync_or_async
    async def upload_files(self, file_paths: list[Path]) -> list[File]:
        uploaded_files = []
        for file_path in file_paths:
            uploaded_file = await self._upload_file_async(file_path)
            uploaded_files.append(uploaded_file)
        return uploaded_files
    
    @_sync_or_async
    async def download_missing_files(self, file_ids: list[str], download_dir: Path) -> list[File]:
        def _if_filenames_in_dir(self, filenames: list[str], dir: Path) -> list[str]:
            missing_files = []
            for filename in filenames:
                file_path = download_dir / str(filename)
                if not file_path.exists():
                    missing_files.append(filename)
            return missing_files
        files_missing = _if_filenames_in_dir(file_ids)
        downloaded_files = await self.download_files(files_missing)
        return downloaded_files