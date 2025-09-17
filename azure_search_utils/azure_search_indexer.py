from azure.search.documents.indexes.models import (
    SearchIndexer,
    FieldMapping,
    IndexingParameters,
    IndexingParametersConfiguration
)

def build_indexer(
    indexer_name: str,
    skillset_name: str,
    index_name: str,
    data_source_name: str,
):
    indexer = SearchIndexer(
        name=indexer_name,
        description="Indexer to index documents and generate embeddings",
        skillset_name=skillset_name,
        target_index_name=index_name,
        data_source_name=data_source_name,
        field_mappings=[
            FieldMapping(
                source_field_name="metadata_storage_name",
                target_field_name="title"
            )
        ],
        parameters=IndexingParameters(
            batch_size=1,
            max_failed_items=None,
            max_failed_items_per_batch=None,
            configuration=IndexingParametersConfiguration(
                additional_properties={
                    "indexedFileNameExtensions": ".pdf,.docx,.txt,.md,.html,.pptx",
                    "dataToExtract": "contentAndMetadata",
                    "executionEnvironment": "private"
                },
                query_timeout=None
            )
        )
    )
    return indexer

  