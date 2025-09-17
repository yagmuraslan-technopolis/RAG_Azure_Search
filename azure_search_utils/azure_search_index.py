
# This script builds or updates and Azure Search Index

from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SearchIndex
)

# Create a search index  
def build_azure_search_index(index_name, 
                              openai_resource_url, 
                              cognitive_api_key,
                              deployment_name):
   

        fields = [
            SearchField(name="parent_id", type=SearchFieldDataType.String),
            SearchField(name="title", type=SearchFieldDataType.String),
            SearchField(
                name="locations",
                type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                filterable=True
            ),
            SearchField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                key=True,
                sortable=True,
                filterable=True,
                facetable=True,
                analyzer_name="keyword"
            ),
            SearchField(
                name="chunk",
                type=SearchFieldDataType.String,
                sortable=False,
                filterable=False,
                facetable=False
            ),
            SearchField(
                name="text_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=1536,
                vector_search_profile_name="myHnswProfile"
            )
        ]

        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name="myHnsw")
            ],
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="myHnsw",
                    vectorizer_name="myOpenAI"
                )
            ],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name="myOpenAI",
                    kind="azureOpenAI",
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=openai_resource_url,
                        deployment_name=deployment_name,
                        api_key=cognitive_api_key,
                        model_name=deployment_name
                    )
                )
            ]
        )

        index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
        
        return index

      
# Configure the semantic search configuration
"""
semantic_config = SemanticConfiguration(  
    name="my-semantic-config",  
    prioritized_fields=PrioritizedFields(  
        prioritized_content_fields=[SemanticField(field_name="description")]  
    ),  
)
 
semantic_settings = SemanticSettings(configurations=[semantic_config])
 

"""




