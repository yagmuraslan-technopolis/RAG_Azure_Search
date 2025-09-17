from typing import Optional, List, Dict, BinaryIO
from azure.storage.blob import ContainerClient
from azure.core.exceptions import ResourceExistsError, HttpResponseError, ResourceNotFoundError
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient

from azure.core.credentials import AzureKeyCredential

from dotenv import load_dotenv
import os
import sys
from azure.storage.blob import BlobServiceClient
from pathlib import Path
from loguru import logger

from azure_search_utils.azure_search_index import build_azure_search_index
from azure_search_utils.azure_search_storage_connection import data_source_connection
from azure_search_utils.azure_search_skillset import build_skillset
from azure_search_utils.azure_search_indexer import build_indexer


# Load from default .env file in current directory
load_dotenv()

STORAGE_CONNECTION_STRING=os.environ.get("AZURE_BLOB_CONNECTION_STRING")
FILE_PATH=os.environ.get("FILE_PATH")

AZURE_SEARCH_SERVICE_ENDPOINT=os.environ.get("AZURE_AI_SEARCH_ENDPOINT")
AZURE_MULTI_SERVICE_RESOURCE=os.environ.get("AZURE_MULTI_OPENAI_ENDPOINT")
AZURE_COGNITIVE_API_KEY=os.environ.get("AZURE_COGNITIVE_API")

AZURE_AI_SEARCH_API_KEY = os.environ.get("AZURE_AI_SEARCH_API_KEY")
EMBEDDING_DEPLOYMENT=os.environ.get("EMBEDDING_DEPLOYMENT")

credential = AzureKeyCredential(AZURE_AI_SEARCH_API_KEY)


class UserDocumentCollection:
    def __init__(self, user_name: str):
        self.user_name = user_name
        self.storage_connection_string = STORAGE_CONNECTION_STRING
        self.client = BlobServiceClient.from_connection_string(
            str(self.storage_connection_string)
            )
        
        self.index_name=self.user_name + "_index"
        self.data_source_name = self.user_name+ "-ds"
        self.skillset_name = self.user_name + "-ss"
        self.indexer_name = self.user_name + "-indexer"


        self.search_service_endpoint=AZURE_SEARCH_SERVICE_ENDPOINT
        self.credential=AzureKeyCredential(AZURE_AI_SEARCH_API_KEY)
        self.openai_resource_url=AZURE_MULTI_SERVICE_RESOURCE
        self.cognitive_api_key=AZURE_COGNITIVE_API_KEY
        self.deployment_name=EMBEDDING_DEPLOYMENT

        self.container = self.get_container()

    def get_container(self) -> ContainerClient:

        try:
            container_client = self.client.get_container_client(self.user_name)
            container_client.create_container()
            logger.info(f"Created container: '{self.user_name}'")
        except Exception as e:
            if "ContainerAlreadyExists" in str(e):
                logger.info(f"Container '{self.user_name}' already exists.")
            else:
                logger.error(f"Error creating container '{self.user_name}': {e}")
                raise
        return container_client
    

    def delete_container(self): 

        try:
            self.container.delete_container()
            logger.info(f"Deleted the container: '{self.user_name}'")
        except ResourceNotFoundError:
            logger.warning(f"⚠️ Container '{self.user_name}' not found. Nothing to delete.")
            return False
        except HttpResponseError as e:
            status = getattr(getattr(e, "response", None), "status_code", "?")
            code = getattr(e, "error_code", "?")
            logger.error(f"❌ Failed to delete container '{self.user_name}' (status={status}, code={code}): {e}")
            return False
        except Exception as e:
            logger.exception(f"❌ Unexpected error while deleting container '{self.user_name}': {e}")
            return False

    
    def add_file_to_blob_container(self, file_path : str, file: BinaryIO):
        container = self.container
        file_name = Path(file_path).name
        try:
            container.upload_blob(file_name, file, overwrite=False)
            logger.info(f"Uploaded '{file_name}' to container '{self.user_name}'.")
            return True  # uploaded now
        except ResourceExistsError as e:
            logger.warning(f"File '{file_name}' already exists in container '{self.user_name}'. Skipping upload.")
            return False  # already there


    def get_index_config(self) -> dict:
        required = {
        "index_name": self.index_name,
        "openai_resource_url": self.openai_resource_url,
        "cognitive_api_key": self.cognitive_api_key,
        "deployment_name": self.deployment_name
    }
        for key, val in required.items():
            if not val:
                raise ValueError(f"Missing required configuration: {key}")
        return required
        

    @property
    def search_index_client(self) -> SearchIndexClient:
        return SearchIndexClient(
            endpoint=self.search_service_endpoint,
            credential=self.credential
        )
    
    
    def create_user_search_index(self):
        try:
            index_config = self.get_index_config()
            index = build_azure_search_index(**index_config)  
            result = self.search_index_client.create_or_update_index(index)
            logger.info(f"✅ Index '{result.name}' created or updated successfully.")
        except HttpResponseError as e:
            logger.error(f"❌ Failed to create index '{self.index_name}': {e.message}")
        except Exception as e:
            logger.exception(f"❌ Unexpected error while creating index '{self.index_name}': {str(e)}")




    def delete_user_search_index(self) :
        try:
            self.search_index_client.delete_index(self.index_name)
            logger.info(f"🗑️ Index '{self.index_name}' deleted successfully.")
        except HttpResponseError as e:
            if "IndexNotFound" in str(e.message):
                logger.warning(f"⚠️ Index '{self.index_name}' not found. Nothing to delete.")
            else:
                logger.error(f"❌ Failed to delete index '{self.index_name}': {e.message}")
        except Exception as e:
            logger.exception(f"❌ Unexpected error while deleting index '{self.index_name}': {str(e)}")


    @property
    def search_indexer_client(self) -> SearchIndexerClient:
        return SearchIndexerClient(
            endpoint=self.search_service_endpoint,
            credential=self.credential
        )
    
    
    def create_data_source_connection(self):
        try:
            data_source = data_source_connection(
                data_source_name=self.data_source_name,
                container_name=self.user_name,
                storage_connection_string=self.storage_connection_string
            )
            result = self.search_indexer_client.create_or_update_data_source_connection(data_source)
            logger.info(f"✅ Data source connection '{result.name}' created or updated successfully.")
        except HttpResponseError as e:
            logger.error(f"❌ Failed to create data source connection '{self.data_source_name}': {e.message}")
        except Exception as e:
            logger.exception(f"❌ Unexpected error while creating data source connection '{self.data_source_name}': {str(e)}")


    def delete_data_source_connection(self):
        try:
            self.search_indexer_client.delete_data_source_connection(self.data_source_name)
            logger.info(f"🗑️ Data source connection '{self.data_source_name}' deleted successfully.")
        except HttpResponseError as e:
            if "DataSourceConnectionNotFound" in str(e.message):
                logger.warning(f"⚠️ Data source connection '{self.data_source_name}' not found. Nothing to delete.")
            else:
                logger.error(f"❌ Failed to delete data source connection '{self.data_source_name}': {e.message}")
        except Exception as e:
            logger.exception(f"❌ Unexpected error while deleting data source connection '{self.data_source_name}': {str(e)}")


    def get_skillset_config(self) -> dict:
        required = {
            "skillset_name": self.skillset_name,
            "index_name": self.index_name,
            "openai_resource_url": self.openai_resource_url,
            "cognitive_api_key": self.cognitive_api_key,
        }
        for key, val in required.items():
            if not val:
                raise ValueError(f"Missing required configuration: {key}")
        return required
    


    def create_user_skillset(self):
        try:
            skillset_config = self.get_skillset_config()
           
            skillset = build_skillset(**skillset_config)
            result = self.search_indexer_client.create_or_update_skillset(skillset)
            logger.info(f"✅ Skillset '{result.name}' created or updated successfully.")
        except HttpResponseError as e:
            logger.error(f"❌ Failed to create skillset '{self.skillset_name}': {e.message}")
        except Exception as e:
            logger.exception(f"❌ Unexpected error while creating skillset '{self.skillset_name}': {str(e)}")


    def delete_user_skillset(self):
        try:
            self.search_indexer_client.delete_skillset(self.skillset_name)
            logger.info(f"🗑️ Skillset '{self.skillset_name}' deleted successfully.")
        except HttpResponseError as e:
            if "SkillsetNotFound" in str(e.message):
                logger.warning(f"⚠️ Skillset '{self.skillset_name}' not found. Nothing to delete.")
            else:
                logger.error(f"❌ Failed to delete skillset '{self.skillset_name}': {e.message}")
        except Exception as e:
            logger.exception(f"❌ Unexpected error while deleting skillset '{self.skillset_name}': {str(e)}")

        
    def create_user_indexer(self):
        try:
            indexer = build_indexer(
                indexer_name=self.indexer_name,
                skillset_name=self.skillset_name,
                index_name=self.index_name,
                data_source_name=self.data_source_name
            )
            result = self.search_indexer_client.create_or_update_indexer(indexer)
            logger.info(f"✅ Indexer '{result.name}' created or updated successfully.")
        except HttpResponseError as e:
            logger.error(f"❌ Failed to create indexer '{self.indexer_name}': {e.message}")
        except Exception as e:
            logger.exception(f"❌ Unexpected error while creating indexer '{self.indexer_name}': {str(e)}")


    def delete_user_indexer(self):
        try:
            self.search_indexer_client.delete_indexer(self.indexer_name)
            logger.info(f"🗑️ Indexer '{self.indexer_name}' deleted successfully.")
        except HttpResponseError as e:
            if "IndexerNotFound" in str(e.message):
                logger.warning(f"⚠️ Indexer '{self.indexer_name}' not found. Nothing to delete.")
            else:
                logger.error(f"❌ Failed to delete indexer '{self.indexer_name}': {e.message}")
        except Exception as e:
            logger.exception(f"❌ Unexpected error while deleting indexer '{self.indexer_name}': {str(e)}")


    def setup_user_index_pipeline(self):
        self.create_user_search_index()
        self.create_data_source_connection()
        self.create_user_skillset()
        self.create_user_indexer()


    def user_logout_delete_pipeline(self):
        self.delete_container()
        self.delete_user_search_index()
        self.delete_data_source_connection()
        self.delete_user_skillset()
        self.delete_user_indexer()


def load_document_collection(user: str) -> UserDocumentCollection:
    """Retrieves the document collection for the given group name"""
    return UserDocumentCollection(user)

"""
test:
colect = DocumentCollection("new4")
colect.create_client_search_index()
colect.create_client_skillset()
"""

"""
with open(FILE_PATH, "rb") as file_obj:
    colect.add_file_to_blob_container(FILE_PATH, file_obj)


"""
