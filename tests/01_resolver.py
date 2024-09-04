import shutil
from maoto_agent import *
import numpy as np

# Initialize Maoto with the given API key from env var
#os.environ["RESOLVER_API_DOMAIN"] = "localhost"

maoto_resolver = Maoto(apikey_value="test_apikey_resolver", working_dir=Path("./tests/work_dir_resolver/"))

user_database = np.array([["provider1", "password1", None], ["provider2", "password2", "2"], [None, None, "3"]])

class MyAuthenticateProvider(AuthenticateProvider):
    def authenticate(username: str, password: str, maoto_user_id) -> bool:
        for user in user_database:
            if user[0] == username and user[1] == password:
                user[2] = maoto_user_id
                return True
        return False
        
    def new_user(apikey_id: str) -> bool:
        for user in user_database:
            if user[2] == apikey_id:
                return False
        user_database = np.append(user_database, np.array([[None, None, apikey_id]]), axis=0)
        return True

maoto_resolver.init_authentication(MyAuthenticateProvider())

@maoto_resolver.register_action("audio_to_text")
def audio_to_text(actioncall: Actioncall, parameters) -> str:
    # def user_exists(apikey_id: str) -> bool:
    #     for user in user_database:
    #         if user[2] == apikey_id:
    #             return True
    #     return False
    # if not user_exists(actioncall.get_apikey_id()):
    #    return f"You did not connect to a audio_to_text account yet. Please authenticate first."
    
    audio_file_id = json.loads(parameters)['audio_file_id']
    try:
        audio_file = maoto_resolver.download_missing_files([audio_file_id])[0]
        audio_file_path = maoto_resolver.download_dir / str(audio_file.get_file_id()) / audio_file.get_extension()
        
        # pretents to convert audio file to text
        audio_file_path = maoto_resolver.working_dir / 'text_output.txt'
        new_file_path = (Path("text_outputs") / str(uuid.uuid4())).with_suffix(".txt")
        shutil.copy(audio_file_path,  maoto_resolver.working_dir / new_file_path)
        
        text_output_file = maoto_resolver.upload_files([new_file_path])[0]
        return f"Successfully converted audio file {audio_file_id} to text file {text_output_file.get_file_id()}."

    except Exception as e:
       return f"Failed to convert audio file {audio_file_id} to text. Try again later.{e}"

created_actions = maoto_resolver.create_actions([
    NewAction(
        name="audio_to_text",
        parameters=json.dumps({'audio_file_id': 'str'}),
        description="Transform audio file to text.",
        tags=["convert", "audio", "text", "transform", "file"],
        cost=1.0,
        followup=False
    ),
    NewAction(
        name="research",
        parameters=json.dumps({'topic': 'str'}),
        description="Research on a specific topic.",
        tags=["research", "topic"],
        cost=0.5,
        followup=False
    )
])

if __name__ == "__main__":
    maoto_resolver.resolver_loop()
