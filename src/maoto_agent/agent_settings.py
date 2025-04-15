from functools import cached_property

from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    debug: bool = False
    domain_mp: str = "mp.maoto.world"
    domain_pa: str = "assistant.maoto.world"
    use_ssl: bool = True
    port_mp: int = 443
    port_pa: int = 443
    apikey: SecretStr
    logging_level: str = "INFO"

    @cached_property
    def protocol(self) -> str:
        return "https" if self.use_ssl else "http"

    @cached_property
    def protocol_websocket(self) -> str:
        return "wss" if self.use_ssl else "ws"

    @cached_property
    def url_mp(self) -> HttpUrl:
        return HttpUrl(f"{self.protocol}://{self.domain_mp}:{self.port_mp}/mp/")

    @cached_property
    def url_pa(self) -> HttpUrl:
        return HttpUrl(f"{self.protocol}://{self.domain_pa}:{self.port_pa}/assistant/")

    class Config:
        env_prefix = "MAOTO_"
        extra = "ignore"
