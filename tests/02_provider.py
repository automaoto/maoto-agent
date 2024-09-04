from maoto_agent import *

#os.environ["RESOLVER_API_DOMAIN"] = "localhost"

class Maoto_LLM:
    def __init__(self, model, working_dir):
        load_dotenv('.secrets')
        self.client = OpenAI()
        self.model = model
        self.working_dir = working_dir
        self.messages_history = []
        self.methods = [
            {
                "name": "create_maoto_post",
                "description": "If there is something the user asks you to do, that you cannot do or that exceeds your capabilities, then you can try to solve it by creating a post on „Maoto“.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "A short description of all details that are necessary to solve the task. Refer to a file solely by its Maoto file ID."
                        }
                    },
                    "required": ["task_description"]
                }
            },
            {
                "name": "upload_maoto_file",
                "description": "Upload a file before referencing to it, if it does not have a file ID assigned yet.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "A file path relative to the main directory."
                        }
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "create_maoto_actioncall",
                "description": "Call an “action“ which can be attached to responses and may help to solve the users tasks. These actioncalls again return a response which can have actions attached.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "post_id": {
                            "type": "string",
                            "description": "The ID of the post, that returned the action called."
                        },
                        "action_id": {
                            "type": "string",
                            "description": "The ID of the action, that is to be called."
                        },
                        "cost": {
                            "type": "number",
                            "description": "The cost of the action that was specified in the post response."
                        }
                    },
                    "additionalProperties": {
                        "type": ["string", "integer", "number", "boolean"],
                        "description": "Additional dynamic parameters for the action that is called (if any)."
                    },
                    "required": ["post_id", "action_id"]
                }
            },
            {
                "name": "download_maoto_file",
                "description": "Download a file by its file ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_id": {
                            "type": "string",
                            "description": "The ID of the file to download without extension."
                        }
                    },
                    "required": ["file_id"]
                }
            }
        ]

    def create_completion(self):
            directory_structure = self._describe_directory_structure(self.working_dir)
            llm_instruction = [
                {"role": "system", "content": "You are a helpful assistant."}
            ]
            system_status = [
                {"role": "system", "content": "Current working directory:\n" + directory_structure}
            ]
            return self.client.chat.completions.create(
                model=self.model,
                stop=None,
                max_tokens=150,
                stream=False,
                messages=llm_instruction + self.messages_history + system_status,
                functions=self.methods
            )
    
    def extend_history(self, role, content, name=None):
        if role not in ["assistant", "user", "function", "system"]:
            raise ValueError("Role must be 'assistant', 'user', 'function' or 'system'.")
        if name != None:
            self.messages_history.append({"role": role, "content": content, "name": name})
        else:
            self.messages_history.append({"role": role, "content": content})
    
    def _describe_directory_structure(self, root_dir):
        def get_size_and_date(path):
            size = os.path.getsize(path)
            mtime = os.path.getmtime(path)
            date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
            return size, date

        def describe_dir(path, indent=0):
            items = []
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    items.append(f"{'  ' * indent}{item}/ (dir)")
                    items.extend(describe_dir(item_path, indent + 1))
                else:
                    size, date = get_size_and_date(item_path)
                    size_str = f"{size // 1024}KB" if size < 1048576 else f"{size // 1048576}MB"
                    items.append(f"{'  ' * indent}{item} (file, {size_str}, {date})")
            return items

        description = describe_dir(root_dir)
        return "\n".join(description)

class PersonalAssistant:
    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self.maoto_provider = Maoto(apikey_value="test_apikey_provider", working_dir=self.working_dir)
        self.llm = self.llm = Maoto_LLM(model="gpt-4o-mini", working_dir=self.working_dir) 

    def completion_loop(self) -> str:
            response = self.llm.create_completion()
            while response.choices[0].message.function_call != None:
                function_name = response.choices[0].message.function_call.name
                arguments = json.loads(response.choices[0].message.function_call.arguments)
                print(f"Function: {function_name}")
                print(f"Arguments: {arguments}\n", type(arguments))

                if function_name == "create_maoto_post":
                    task_description = arguments["task_description"]
                    new_post = NewPost(
                        description=task_description,
                        context="",
                    )
                    post = self.maoto_provider.create_posts([new_post])[0]
                    self.llm.extend_history("function", f"Created post:\n{post}", "create_maoto_post")

                    response_return = self.maoto_provider.listen()
                    self.llm.extend_history("function", f"Received response:\n{response_return}", "create_maoto_post")

                elif function_name == "create_maoto_actioncall":
                    post_id = arguments["post_id"]
                    action_id = arguments["action_id"]
                    cost = arguments["cost"]
                    action_arguments = {k: v for k, v in arguments.items() if k not in ["post_id", "action_id"]}
                    new_actioncall = NewActioncall(
                        action_id=action_id,
                        post_id=post_id,
                        parameters=json.dumps(action_arguments),
                        cost=cost
                    )
                    
                    actioncall = self.maoto_provider.create_actioncalls([new_actioncall])[0]
                    self.llm.extend_history("function", f"Created actioncall:\n{actioncall}", "create_maoto_actioncall")

                    print(f"Actioncall: {new_actioncall}\n")

                    response_return = self.maoto_provider.listen()
                    self.llm.extend_history("function", f"Received response:\n{response_return}", "create_maoto_actioncall")

                elif function_name == "upload_maoto_file":
                    file_path = arguments["file_path"]
                    print(f"File path: {file_path}")
                    file = self.maoto_provider.upload_files([Path(file_path)])[0]
                    print(f"File: {file}")
                    self.llm.extend_history("function", f"Uploaded file:\n{file}", "upload_maoto_file")

                elif function_name == "download_maoto_file":
                    file_id = arguments["file_id"]
                    file = self.maoto_provider.download_files([file_id])[0]
                    self.llm.extend_history("function", f"Downloaded file:\n{file}", "download_maoto_file")
                
                response = self.llm.create_completion()
            
            response_content = response.choices[0].message.content
            self.llm.extend_history("assistant", response_content)
            return response_content
            
    def run(self):
        test_prompt = True
        while True:
            if test_prompt == True:
                self.llm.extend_history("system", "File added by user: test_audiofile.mp3")
                self.llm.extend_history("user", "I want to convert the speech into text.")
                test_prompt = False
            else:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                self.llm.extend_history("user", user_input)
            
            response_content = self.completion_loop()

            print(f"Assistant: {response_content}")
            

if __name__ == "__main__":
    personal_assistant = PersonalAssistant(working_dir=Path("./tests/work_dir_provider"))
    personal_assistant.run()
