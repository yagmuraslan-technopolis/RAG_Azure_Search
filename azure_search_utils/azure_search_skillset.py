

from azure.search.documents.indexes.models import (
    SplitSkill,
    AzureOpenAIEmbeddingSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    SearchIndexerSkillset,
    SearchIndexerIndexProjection,
    SearchIndexerIndexProjectionSelector,
    SearchIndexerIndexProjectionsParameters,
    IndexProjectionMode
)


def build_skillset(
    skillset_name: str,
    index_name: str,
    openai_resource_url: str,
    cognitive_api_key: str,
    deployment_name: str = "text-embedding-ada-002",
    embedding_dimensions: int = 1536
):
    # Define skills
    split_skill = SplitSkill(
        description="Split skill to chunk documents",
        text_split_mode="pages",
        context="/document",
        maximum_page_length=4096,
        page_overlap_length=0,
        maximum_pages_to_take=2000,
        inputs=[InputFieldMappingEntry(name="text", source="/document/content")],
        outputs=[OutputFieldMappingEntry(name="textItems", target_name="pages")]
    )

    embedding_skill = AzureOpenAIEmbeddingSkill(
        description="Skill to generate embeddings via Azure OpenAI",
        context="/document/pages/*",
        resource_url=openai_resource_url,
        api_key=cognitive_api_key,
        deployment_name=deployment_name,
        model_name=deployment_name,
        dimensions=embedding_dimensions,
        inputs=[InputFieldMappingEntry(name="text", source="/document/pages/*")],
        outputs=[OutputFieldMappingEntry(name="embedding", target_name="text_vector")]
    )

    # Define projection
    index_projections = SearchIndexerIndexProjection(
        selectors=[
            SearchIndexerIndexProjectionSelector(
                target_index_name=index_name,
                parent_key_field_name="parent_id",
                source_context="/document/pages/*",
                mappings=[
                    InputFieldMappingEntry(name="chunk", source="/document/pages/*"),
                    InputFieldMappingEntry(name="text_vector", source="/document/pages/*/text_vector"),
                    InputFieldMappingEntry(name="locations", source="/document/pages/*/locations"),
                    InputFieldMappingEntry(name="title", source="/document/metadata_storage_name"),
                ]
            )
        ],
        parameters=SearchIndexerIndexProjectionsParameters(
            projection_mode=IndexProjectionMode.SKIP_INDEXING_PARENT_DOCUMENTS
        )
    )

    skillset = SearchIndexerSkillset(
        name=skillset_name,
        description="Skillset to chunk documents and generate embeddings",
        skills=[split_skill, embedding_skill],
        index_projection=index_projections
    )

    
    return skillset
