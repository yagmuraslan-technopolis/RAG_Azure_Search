from azure.search.documents.indexes.models import (
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection
)

def data_source_connection(
    data_source_name: str,
    container_name: str,
    storage_connection_string: str
):
    
    container = SearchIndexerDataContainer(name=container_name)
    data_source_connection = SearchIndexerDataSourceConnection(
        name=data_source_name,
        type="azureblob",
        connection_string=storage_connection_string,
        container=container
    )

    return data_source_connection