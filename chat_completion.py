import os
from openai import AzureOpenAI
from dotenv import load_dotenv


load_dotenv()
CHAT_DEPLOYMENT=os.environ.get("CHAT_DEPLOYMENT")

client = AzureOpenAI(
    azure_endpoint=os.environ["AZURE_COGNITIVE_SERVICES_ENDPOINT"],
    api_key=os.environ["AZURE_COGNITIVE_API"],
    api_version="2024-10-21",  # 2024-02-01+ supports data_sources
)



def run_completion(prompt: str, filter: str, index_name: str, model="gpt-4.1", response_format="text"):
    if response_format == "json":
        response_format = {"type": "json_object"}
    elif response_format == "text":
        response_format = None
    completion=  client.chat.completions.create(
        model=CHAT_DEPLOYMENT,
        messages=[{"role": "user", "content": prompt}],
        response_format=response_format,
        extra_body={
            "data_sources": [{
                "type": "azure_search",
                "parameters": {
                    "endpoint": os.environ["AZURE_AI_SEARCH_ENDPOINT"],
                    "index_name": index_name,
                    "authentication": {
                        "type": "api_key",
                        "key": os.environ["AZURE_AI_SEARCH_API_KEY"],
                    },
                    "fields_mapping": {
                        "title_field": "title",
                        "filepath_field": "filepath",
                        "url_field": "url",
                    },
                    "filter": filter,
                    "in_scope": True,
                },
            }]
        }
    )

    return completion.choices[0].message