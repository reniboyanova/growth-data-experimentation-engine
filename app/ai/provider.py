import json, os
from typing import TypeVar
import httpx
from pydantic import BaseModel

T=TypeVar("T",bound=BaseModel)

class OllamaProvider:
    def __init__(self,base_url:str|None=None,model:str|None=None,timeout:float|None=None):
        self.base_url=(base_url or os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434")).rstrip("/")
        self.model=model or os.getenv("OLLAMA_MODEL","qwen2.5:3b")
        self.timeout=timeout or float(os.getenv("OLLAMA_TIMEOUT_SECONDS","60"))

    def structured(self,system:str,prompt:str,schema:type[T])->T:
        body={"model":self.model,"system":system,"prompt":prompt,"stream":False,"format":schema.model_json_schema(),"options":{"temperature":0}}
        with httpx.Client(timeout=self.timeout) as client:
            response=client.post(f"{self.base_url}/api/generate",json=body); response.raise_for_status()
        content=response.json().get("response","")
        return schema.model_validate_json(content)

    def health(self)->dict:
        with httpx.Client(timeout=3) as client:
            response=client.get(f"{self.base_url}/api/tags"); response.raise_for_status(); data=response.json()
        return {"available":True,"model":self.model,"installed_models":[m.get("name") for m in data.get("models",[])]}
